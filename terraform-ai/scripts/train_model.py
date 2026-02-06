"""
SageMaker Training Job 실행 스크립트

사용법:
    python train_model.py --bucket {S3_BUCKET_NAME} --role {SAGEMAKER_ROLE_ARN}

학습 완료 후 모델 경로가 출력됩니다. 이 경로를 terraform에 설정하세요:
    terraform apply -var="deploy_endpoint=true" -var="model_artifact_path=s3://..."
"""

import boto3
import argparse
import time
from datetime import datetime

def run_training_job(bucket_name, role_arn):
    """SageMaker Training Job 실행"""
    
    sagemaker = boto3.client('sagemaker', region_name='ap-northeast-2')
    
    job_name = f"linksnap-conversion-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    print(f"Training Job 시작: {job_name}")
    print("=" * 50)
    
    # Training Job 생성
    response = sagemaker.create_training_job(
        TrainingJobName=job_name,
        RoleArn=role_arn,
        AlgorithmSpecification={
            'TrainingImage': '366743142698.dkr.ecr.ap-northeast-2.amazonaws.com/sagemaker-xgboost:1.5-1',
            'TrainingInputMode': 'File'
        },
        InputDataConfig=[
            {
                'ChannelName': 'train',
                'DataSource': {
                    'S3DataSource': {
                        'S3DataType': 'S3Prefix',
                        'S3Uri': f's3://{bucket_name}/training-data/train.csv'
                    }
                },
                'ContentType': 'text/csv'
            },
            {
                'ChannelName': 'validation',
                'DataSource': {
                    'S3DataSource': {
                        'S3DataType': 'S3Prefix',
                        'S3Uri': f's3://{bucket_name}/training-data/test.csv'
                    }
                },
                'ContentType': 'text/csv'
            }
        ],
        OutputDataConfig={
            'S3OutputPath': f's3://{bucket_name}/models/'
        },
        ResourceConfig={
            'InstanceCount': 1,
            'InstanceType': 'ml.m5.large',
            'VolumeSizeInGB': 10
        },
        StoppingCondition={
            'MaxRuntimeInSeconds': 3600
        },
        HyperParameters={
            'objective': 'binary:logistic',
            'num_round': '100',
            'max_depth': '5',
            'eta': '0.2',
            'eval_metric': 'auc',
            'subsample': '0.8',
            'colsample_bytree': '0.8'
        }
    )
    
    # 학습 완료 대기
    print("학습 진행 중...")
    while True:
        status = sagemaker.describe_training_job(TrainingJobName=job_name)
        job_status = status['TrainingJobStatus']
        
        if job_status == 'Completed':
            print(f"\n학습 완료!")
            model_path = status['ModelArtifacts']['S3ModelArtifacts']
            print(f"\n모델 경로: {model_path}")
            print("\n" + "=" * 50)
            print("다음 명령어로 Endpoint 배포:")
            print(f'terraform apply -var="deploy_endpoint=true" -var="model_artifact_path={model_path}"')
            print("=" * 50)
            return model_path
            
        elif job_status == 'Failed':
            print(f"\n학습 실패: {status.get('FailureReason', 'Unknown')}")
            return None
            
        elif job_status == 'Stopped':
            print("\n학습 중단됨")
            return None
            
        else:
            print(f"  상태: {job_status}...", end='\r')
            time.sleep(30)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--bucket', required=True, help='S3 버킷 이름')
    parser.add_argument('--role', required=True, help='SageMaker Role ARN')
    args = parser.parse_args()
    
    print("=" * 50)
    print("SageMaker Training Job 실행")
    print("=" * 50)
    print(f"버킷: {args.bucket}")
    print(f"Role: {args.role}")
    print()
    
    # 학습 실행
    model_path = run_training_job(args.bucket, args.role)
    
    if model_path:
        print("\n성공!")
    else:
        print("\n실패!")
        exit(1)


if __name__ == '__main__':
    main()
