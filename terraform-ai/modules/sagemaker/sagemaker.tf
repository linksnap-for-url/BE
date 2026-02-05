# SageMaker 노트북 인스턴스
resource "aws_sagemaker_notebook_instance" "main" {
  name                  = "${var.project_name}-notebook-${var.environment}"
  instance_type         = "ml.t3.medium"  # 비용 최적화 (시간당 $0.05)
  role_arn              = var.sagemaker_role_arn
  
  # 자동 중지 설정 (유휴 시간 후)
  lifecycle_config_name = aws_sagemaker_notebook_instance_lifecycle_configuration.auto_stop.name
  
  # 볼륨 크기
  volume_size = 10  # GB

  tags = {
    Name = "${var.project_name}-notebook-${var.environment}"
  }
}

# 자동 중지 Lifecycle 설정 (비용 절감!)
resource "aws_sagemaker_notebook_instance_lifecycle_configuration" "auto_stop" {
  name = "${var.project_name}-auto-stop-${var.environment}"

  # 시작 시 실행되는 스크립트
  on_start = base64encode(<<-EOF
    #!/bin/bash
    set -e
    
    # 60분 유휴 후 자동 중지 스크립트 설치
    IDLE_TIME=3600  # 60분 (초 단위)
    
    echo "Auto-stop script installed. Notebook will stop after $IDLE_TIME seconds of idle time."
    
    cat > /home/ec2-user/SageMaker/auto-stop.py << 'SCRIPT'
import subprocess
import time
import os

IDLE_TIME = 3600  # 60분

def get_notebook_name():
    log_path = '/opt/ml/metadata/resource-metadata.json'
    if os.path.exists(log_path):
        import json
        with open(log_path, 'r') as f:
            return json.load(f).get('ResourceName', '')
    return ''

def is_idle():
    # Jupyter 커널 상태 확인
    result = subprocess.run(
        ['jupyter', 'notebook', 'list', '--json'],
        capture_output=True, text=True
    )
    return 'running' not in result.stdout.lower()

if __name__ == '__main__':
    idle_start = None
    while True:
        if is_idle():
            if idle_start is None:
                idle_start = time.time()
            elif time.time() - idle_start > IDLE_TIME:
                notebook_name = get_notebook_name()
                if notebook_name:
                    subprocess.run([
                        'aws', 'sagemaker', 'stop-notebook-instance',
                        '--notebook-instance-name', notebook_name
                    ])
                break
        else:
            idle_start = None
        time.sleep(60)
SCRIPT
    
    # 백그라운드에서 실행
    nohup python /home/ec2-user/SageMaker/auto-stop.py &
  EOF
  )
}
