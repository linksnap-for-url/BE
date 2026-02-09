# CloudWatch 모니터링 + Discord 알람 모듈

AWS CloudWatch를 사용한 Lambda 함수 모니터링 및 Discord Webhook을 통한 알람 전송 모듈

## 구성 요소

### 1. CloudWatch Log Groups
- Lambda 함수별 로그 그룹 자동 생성
- 보존 기간 설정 가능 (기본 14일)

### 2. CloudWatch Alarms
| 알람 유형 | 설명 | 기본 임계값 |
|----------|------|------------|
| Lambda Errors | Lambda 함수 에러 횟수 | 5회/5분 |
| Lambda Duration | Lambda 실행 시간 | 5000ms |
| Lambda Throttles | 동시 실행 제한 초과 | 1회 |
| API 5XX Errors | 서버 에러 | 10회/5분 |
| API 4XX Errors | 클라이언트 에러 | 50회/5분 |
| API Latency | 응답 지연 시간 | 3000ms |
| Log Errors | 로그 에러 패턴 감지 | 3회/5분 |

### 3. CloudWatch Dashboard
- Lambda 호출 수 시각화
- Lambda 에러 현황
- Lambda 실행 시간
- 알람 상태 모니터링

### 4. Discord 알람
- SNS → Lambda → Discord Webhook 구조
- 알람 상태별 색상 구분 (빨강/녹색/노랑)
- 상세 정보 포함 (메트릭, 임계값, 대상 등)
- ALARM 상태 시 @here 멘션

## Discord Webhook 설정 방법

### 1. Discord 웹훅 생성
1. Discord 서버에서 알람을 받을 채널로 이동
2. 채널 설정 클릭
3. **연동** > **웹훅** 선택
4. **새 웹훅** 클릭
5. 이름 설정 (예: "AWS CloudWatch")
6. **웹훅 URL 복사** 클릭

### 2. Terraform 변수 설정

**방법 A: terraform.tfvars 파일 사용**
```hcl
discord_webhook_url = "https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN"
```

**방법 B: 환경 변수 사용**
```bash
export TF_VAR_discord_webhook_url="https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN"
```

**방법 C: 명령어 인자로 전달**
```bash
terraform apply -var="discord_webhook_url=https://discord.com/api/webhooks/..."
```

### 3. 테라폼 적용
```bash
cd terraform
terraform init
terraform plan
terraform apply
```

## 알람 메시지 예시

Discord에서 받게 되는 알람 메시지 형태:

```
@here DEV 환경에서 알람이 발생했습니다!

url-shortener-redirect-dev-errors
Lambda 함수 url-shortener-redirect-dev에서 에러가 5회 이상 발생했습니다.

상태 변경: OK → ALARM
환경: DEV
메트릭: AWS/Lambda/Errors
임계값: GreaterThanThreshold 5
대상: FunctionName: url-shortener-redirect-dev
상세 정보: Threshold Crossed: 6 datapoints [6.0 ...
```

## 알람 테스트 방법

### Lambda 함수 테스트 호출
```bash
# 의도적으로 에러 발생시키기
aws lambda invoke \
  --function-name url-shortener-create-short-url-dev \
  --payload '{"invalid": "data"}' \
  response.json
```

### 수동 알람 테스트
```bash
# 알람 상태를 강제로 ALARM으로 변경
aws cloudwatch set-alarm-state \
  --alarm-name "url-shortener-create-short-url-dev-errors" \
  --state-value ALARM \
  --state-reason "테스트 알람"
```

## 비용 고려사항

- **CloudWatch Logs**: 로그 수집 및 저장 비용 발생
- **CloudWatch Alarms**: 알람당 월 $0.10
- **SNS**: 첫 100만 요청 무료
- **Lambda (Discord Alert)**: 월 100만 요청 무료

예상 비용: 소규모 서비스 기준 월 $1~5

## 트러블슈팅

### Discord 알람이 오지 않는 경우
1. Webhook URL이 올바른지 확인
2. Discord Alert Lambda 로그 확인:
   ```bash
   aws logs tail /aws/lambda/url-shortener-discord-alert-dev --follow
   ```
3. SNS Topic 구독 상태 확인

### 너무 많은 알람이 오는 경우
`alarm_thresholds` 값을 조정하여 임계값을 높인다.

