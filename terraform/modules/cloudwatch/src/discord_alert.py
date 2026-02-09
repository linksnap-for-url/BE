"""
Discord Webhook Alert Lambda Function
CloudWatch Alarm → SNS → Lambda → Discord Webhook
"""
import json
import os
import urllib.request
import urllib.error
from datetime import datetime

# 환경 변수
DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK_URL')
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')
PROJECT_NAME = os.environ.get('PROJECT_NAME', 'url-shortener')

# 알람 상태별 색상 (Discord Embed Color)
ALARM_COLORS = {
    'ALARM': 0xFF0000,      # 빨간색 - 문제 발생
    'OK': 0x00FF00,         # 녹색 - 정상 복구
    'INSUFFICIENT_DATA': 0xFFFF00  # 노란색 - 데이터 부족
}

# 알람 상태별 이모지
ALARM_EMOJIS = {
    'ALARM': '🚨',
    'OK': '✅',
    'INSUFFICIENT_DATA': '⚠️'
}


def handler(event, context):
    """
    SNS 이벤트를 받아서 Discord Webhook으로 전송
    """
    print(f"Received event: {json.dumps(event)}")
    
    if not DISCORD_WEBHOOK_URL:
        print("ERROR: DISCORD_WEBHOOK_URL is not set")
        return {
            'statusCode': 500,
            'body': 'Discord Webhook URL not configured'
        }
    
    try:
        # SNS 메시지 파싱
        for record in event.get('Records', []):
            sns_message = record.get('Sns', {})
            message_str = sns_message.get('Message', '{}')
            
            try:
                # CloudWatch Alarm 메시지 파싱
                alarm_data = json.loads(message_str)
                discord_payload = create_alarm_embed(alarm_data)
            except json.JSONDecodeError:
                # JSON이 아닌 일반 텍스트 메시지인 경우
                discord_payload = create_text_message(message_str, sns_message)
            
            # Discord로 전송
            send_to_discord(discord_payload)
        
        return {
            'statusCode': 200,
            'body': 'Alert sent successfully'
        }
    
    except Exception as e:
        print(f"ERROR: {str(e)}")
        # 에러가 발생해도 Discord에 에러 알림 시도
        try:
            error_payload = create_error_message(str(e))
            send_to_discord(error_payload)
        except:
            pass
        
        return {
            'statusCode': 500,
            'body': f'Error: {str(e)}'
        }


def create_alarm_embed(alarm_data):
    """
    CloudWatch Alarm 데이터를 Discord Embed 형식으로 변환
    """
    alarm_name = alarm_data.get('AlarmName', 'Unknown Alarm')
    alarm_state = alarm_data.get('NewStateValue', 'UNKNOWN')
    old_state = alarm_data.get('OldStateValue', 'UNKNOWN')
    alarm_description = alarm_data.get('AlarmDescription', '설명 없음')
    state_reason = alarm_data.get('NewStateReason', '상세 정보 없음')
    timestamp = alarm_data.get('StateChangeTime', datetime.utcnow().isoformat())
    
    # 트리거 정보
    trigger = alarm_data.get('Trigger', {})
    metric_name = trigger.get('MetricName', 'N/A')
    namespace = trigger.get('Namespace', 'N/A')
    dimensions = trigger.get('Dimensions', [])
    threshold = trigger.get('Threshold', 'N/A')
    comparison = trigger.get('ComparisonOperator', 'N/A')
    
    # 차원 정보 포맷팅
    dimension_str = ', '.join([f"{d.get('name', 'N/A')}: {d.get('value', 'N/A')}" for d in dimensions])
    
    emoji = ALARM_EMOJIS.get(alarm_state, '❓')
    color = ALARM_COLORS.get(alarm_state, 0x808080)
    
    # AWS 콘솔 링크 생성
    region = alarm_data.get('Region', 'ap-northeast-2')
    alarm_console_url = f"https://{region}.console.aws.amazon.com/cloudwatch/home?region={region}#alarmsV2:alarm/{alarm_name}"
    
    embed = {
        "title": f"{emoji} {alarm_name}",
        "description": alarm_description,
        "color": color,
        "fields": [
            {
                "name": "1. 상태 변경",
                "value": f"`{old_state}` → `{alarm_state}`",
                "inline": True
            },
            {
                "name": "2. 환경",
                "value": f"`{ENVIRONMENT.upper()}`",
                "inline": True
            },
            {
                "name": "3. 메트릭",
                "value": f"`{namespace}/{metric_name}`",
                "inline": True
            },
            {
                "name": "4. 임계값",
                "value": f"`{comparison}` `{threshold}`",
                "inline": True
            },
            {
                "name": "5. 대상",
                "value": f"`{dimension_str}`" if dimension_str else "N/A",
                "inline": False
            },
            {
                "name": "6. 상세 정보",
                "value": state_reason[:500] + "..." if len(state_reason) > 500 else state_reason,
                "inline": False
            }
        ],
        "timestamp": timestamp,
        "footer": {
            "text": f"{PROJECT_NAME} | CloudWatch Alarm"
        }
    }
    
    payload = {
        "embeds": [embed]
    }
    
    # ALARM 상태일 때 @here 멘션 추가
    if alarm_state == 'ALARM':
        payload["content"] = f"@here **{ENVIRONMENT.upper()} 환경에서 알람이 발생했습니다!**"
    
    return payload


def create_text_message(message, sns_data):
    """
    일반 텍스트 메시지를 Discord 형식으로 변환
    """
    subject = sns_data.get('Subject', 'AWS Notification')
    timestamp = sns_data.get('Timestamp', datetime.utcnow().isoformat())
    
    return {
        "embeds": [{
            "title": f"Message from SNS: {subject}",
            "description": message[:2000],  # Discord 제한
            "color": 0x5865F2,  # Discord 블루
            "timestamp": timestamp,
            "footer": {
                "text": f"{PROJECT_NAME} | SNS Notification"
            }
        }]
    }


def create_error_message(error):
    """
    에러 발생 시 Discord 알림
    """
    return {
        "embeds": [{
            "title": " !!Alert Lambda Error!!",
            "description": f"알람 처리 중 에러가 발생했습니다.\n```\n{error}\n```",
            "color": 0xFF6B6B,
            "timestamp": datetime.utcnow().isoformat(),
            "footer": {
                "text": f"{PROJECT_NAME} | Error"
            }
        }]
    }


def send_to_discord(payload):
    """
    Discord Webhook으로 메시지 전송
    """
    data = json.dumps(payload).encode('utf-8')
    
    req = urllib.request.Request(
        DISCORD_WEBHOOK_URL,
        data=data,
        headers={
            'Content-Type': 'application/json',
            'User-Agent': 'AWS-Lambda-Discord-Alert'
        },
        method='POST'
    )
    
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            print(f"Discord response: {response.status}")
            return response.status
    except urllib.error.HTTPError as e:
        print(f"Discord HTTP Error: {e.code} - {e.read().decode()}")
        raise
    except urllib.error.URLError as e:
        print(f"Discord URL Error: {e.reason}")
        raise


# 테스트용 핸들러 (로컬 테스트시 사용)
if __name__ == "__main__":
    test_event = {
        "Records": [
            {
                "Sns": {
                    "Message": json.dumps({
                        "AlarmName": "test-lambda-errors",
                        "AlarmDescription": "테스트 알람입니다",
                        "NewStateValue": "ALARM",
                        "OldStateValue": "OK",
                        "NewStateReason": "Threshold Crossed: 5 errors in 5 minutes",
                        "StateChangeTime": "2024-01-15T12:00:00.000Z",
                        "Region": "ap-northeast-2",
                        "Trigger": {
                            "MetricName": "Errors",
                            "Namespace": "AWS/Lambda",
                            "Dimensions": [{"name": "FunctionName", "value": "test-function"}],
                            "Threshold": 5,
                            "ComparisonOperator": "GreaterThanThreshold"
                        }
                    })
                }
            }
        ]
    }
    
    # 실제 테스트 시 환경변수 설정 필요
    # os.environ['DISCORD_WEBHOOK_URL'] = 'your-webhook-url'
    # handler(test_event, None)
    print("Test event created. Set DISCORD_WEBHOOK_URL to test.")
