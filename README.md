## LinkSnap - URL Shortener Backend

AWS 기반 서버리스 URL 단축 서비스

Terraform으로 인프라를 관리하며 Lambda + API Gateway + DynamoDB 아키텍처와 EKS k8s 클러스터를 병행 운영합니다.

---

### 1. 아키텍처 구성도


```
[사용자] → [API Gateway / ALB] → [Lambda 함수 or K8s Pod]
                                        ↓
                                   [DynamoDB]
                                   ├── urls 테이블 (URL 저장)
                                   └── stats 테이블 (클릭 통계)

[CloudWatch] → [SNS] → [Discord Alert Lambda] → [Discord Webhook]
[Bedrock Claude 3 Haiku] → [AI Insights API]
```

---

### 2. 기술 스택

| 구분 | 기술 |
|---|---|
| IaC | Terraform (모듈 구조) |
| Compute | AWS Lambda (Python 3.10), EKS (FastAPI 컨테이너) |
| API | API Gateway HTTP API v2 |
| Database | DynamoDB (urls, stats 테이블) |
| AI | AWS Bedrock (Claude 3 Haiku) |
| Monitoring | CloudWatch (Logs, Alarms, Dashboard) |
| Alerting | SNS → Lambda → Discord Webhook |
| DNS | Route 53 + ACM (커스텀 도메인: shmall.store) |
| Container | ECR, EKS, Docker |
| K8s 시각화 | kube-ops-view |

---

### 3. API 엔드포인트

3.1 URL Shortener API

Base URL: `https://shmall.store`

| Method | Path | 설명 |
|---|---|---|
| POST | /shorten | URL 단축 생성 |
| GET | /{shortCode} | 원본 URL로 301 리다이렉트 |
| GET | /stats | 전체 사이트 통계 조회 |
| GET | /stats/{shortCode} | 개별 URL 통계 조회 |

3.2 AI Insights API

| Method | Path | 설명 |
|---|---|---|
| POST | /insights | AI 마케팅 인사이트 생성 (Bedrock Claude 3 Haiku) |

분석 타입: `full`, `traffic`, `conversion`

---

### 4. 인프라 분리 전략

세 개의 Terraform 프로젝트를 **독립적으로** 관리하여 비용을 최적화합니다.

| 프로젝트 | 용도 | 운영 방식 | 월 비용 |
|---|---|---|---|
| `terraform/` | Lambda, API GW, DynamoDB, CloudWatch | 항상 유지 | 프리 티어 |
| `terraform-ai/` | Bedrock AI Lambda | 항상 유지 | 사용량 기반 |
| `terraform-k8s/` | EKS 클러스터 | 필요 시 apply/destroy | 사용 시간 기반 |


---

### 5. EKS Kubernetes 구성

5.1 클러스터 사양

| 항목 | 설정 |
|---|---|
| EKS 버전 | 1.29 |
| 노드 타입 | t3.small (2 vCPU, 2GB RAM) |
| 노드 수 | min 1 / desired 2 / max 3 |
| 네트워크 | VPC + Public/Private Subnet 2개씩 |
| 이미지 저장소 | ECR (최근 5개 이미지만 유지) |

5.2 K8s 리소스

| 리소스 | 설명 |
|---|---|
| Namespace | `linksnap` - 리소스 격리 |
| ConfigMap | DynamoDB 테이블명, AWS 리전 등 환경변수 |
| Deployment | FastAPI Pod 2개 (replicas: 2) |
| Service | ClusterIP (내부 네트워크) |
| Ingress | ALB 연동 (외부 트래픽 라우팅) |
| HPA | CPU 70% 초과 시 Pod 자동 확장 (max 5) |

5.3 컨테이너 앱

Lambda 함수 4개를 FastAPI 서버 1개로 통합하여 컨테이너화

| Lambda 함수 | FastAPI 엔드포인트 |
|---|---|
| shorten_url.py | POST /shorten |
| redirect.py | GET /{shortCode} |
| get_site_stats.py | GET /stats |
| get_url_stats.py | GET /stats/{shortCode} |
| test용 | GET /health |

5.4 kube-ops-view 시각화

kube-ops-view를 통해 노드와 Pod 배치를 시각적으로 모니터링.

<img src="./docs/images/kube-ops.png" width="500" />

---

### 6. CloudWatch 모니터링 + Discord 알람

6.1 대시보드 구성

<img src="./docs/images/cloudwatch.png" width="500" />

| 위젯 | 내용 |
|---|---|
| Lambda Invocations / Errors / Duration | 메트릭 그래프 |
| Alarm Status | 알람 상태 표시 |
| 함수별 Error Logs | 에러/예외 로그 테이블 |
| 함수별 Recent Logs | 최근 로그 테이블 |
| Redirect / Stats Failure Logs | 리다이렉트 상세 로그 |
| Cold Start / Execution Report | 성능 분석 로그 |

6.2 알람 → Discord 알림

| 알람 | 조건 | 기본 임계값 |
|---|---|---|
| Lambda 에러 | 5분간 에러 수 초과 | 5회 |
| Lambda 실행시간 | 5분간 평균 초과 | 5,000ms |
| Lambda 스로틀 | 스로틀 발생 | 1회 |
| API 5XX 에러 | 5분간 5XX 초과 | 10회 |
| API 4XX 에러 | 5분간 4XX 초과 | 50회 |
| API 지연시간 | 5분간 평균 초과 | 3,000ms |
| 로그 에러 감지 | 5분간 ERROR/Exception 로그 | 3회 |

<img src="./docs/images/discord.png" width="500" />

---

### 8. 스크린샷

| 메인 페이지 | CloudWatch 대시보드 1 |
|---|---|
| <img src="./docs/images/main.png" width="400" /> | <img src="./docs/images/dashboard1.png" width="400" /> |

| CloudWatch 대시보드 2 | AI 인사이트 |
|---|---|
| <img src="./docs/images/dashboard2.png" width="400" /> | <img src="./docs/images/ai.png" width="400" /> |

