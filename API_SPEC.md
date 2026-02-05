## LinkSnap API 명세서



| 항목 | 값 |
|------|-----|
| Base URL | `https://{api-gateway-domain}/{stage}` |
| Protocol | HTTPS |
| Content-Type | `application/json` |

### CORS 설정
- **Allowed Origins**: `*`
- **Allowed Methods**: `GET`, `POST`, `OPTIONS`
- **Allowed Headers**: `Content-Type`

---

## API 목록

| API | Method | Endpoint | 설명 |
|-----|--------|----------|------|
| [URL 단축 생성](#1-url-단축-생성) | POST | `/shorten` | 긴 URL을 짧은 URL로 변환 |
| [URL 리다이렉트](#2-url-리다이렉트) | GET | `/{shortCode}` | 단축 URL 접속 시 원본 URL로 리다이렉트 |
| [URL별 통계 조회](#3-url별-통계-조회) | GET | `/stats/{shortCode}` | 특정 단축 URL의 클릭 통계 |
| [전체 사이트 통계](#4-전체-사이트-통계-조회) | GET | `/stats` | 사이트 전체 통계 (인기 URL, 최근 URL 등) |

---

## 1. URL 단축 생성

긴 URL을 짧은 URL로 변환합니다.

### Request

```
POST /shorten
Content-Type: application/json
```

#### Body

| 필드 | 타입 | 설명 |
|------|------|------|
| `url` | string  | 단축할 원본 URL (`http://` 또는 `https://`로 시작해야 함) |

#### 예시

```json
{
  "url": "https://www.example.com/very/long/path/to/page"
}
```

### Response

#### 성공 (201 Created)

```json
{
  "urlId": "a1b2c3",
  "shortUrl": "https://api-gateway-url.amazonaws.com/dev/a1b2c3",
  "originalUrl": "https://www.example.com/very/long/path/to/page",
  "createdAt": "2026-02-05T12:30:00.000000",
  "expiresAt": "2026-03-07T12:30:00.000000"
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| `urlId` | string | 단축 URL 코드 (6자리) |
| `shortUrl` | string | 완전한 단축 URL |
| `originalUrl` | string | 원본 URL |
| `createdAt` | string | 생성 시간 (ISO 8601) |
| `expiresAt` | string | 만료 시간 (생성일 + 30일) |

#### 에러 응답

| Status Code | 에러 메시지 | 설명 |
|-------------|------------|------|
| 400 | `url is required` | URL이 제공되지 않음 |
| 400 | `url must start with http:// or https://` | 잘못된 URL 형식 |
| 500 | `{error message}` | 서버 에러 |

---

## 2. URL 리다이렉트

단축 URL 접속 시 원본 URL로 리다이렉트합니다.  
**주의**: 이 엔드포인트는 FE에서 직접 호출하지 않고, 사용자가 단축 URL을 브라우저에 입력하면 자동으로 처리됩니다.

### Request

```
GET /{shortCode}
```

#### Path Parameters

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `shortCode` | string  | 단축 URL 코드 (예: `a1b2c3`) |

#### 예시

```
GET /a1b2c3
```

### Response

#### 성공 (301 Moved Permanently)

```http
HTTP/1.1 301 Moved Permanently
Location: https://www.example.com/very/long/path/to/page
Cache-Control: no-cache
```

#### 에러 응답

| Status Code | 에러 메시지 | 설명 |
|-------------|------------|------|
| 400 | `shortCode is required` | shortCode가 없음 |
| 404 | `URL not found` | 존재하지 않는 단축 URL |
| 410 | `URL has expired` | 만료된 단축 URL |
| 500 | `{error message}` | 서버 에러 |

---

## 3. URL별 통계 조회

특정 단축 URL의 상세 클릭 통계를 조회합니다.

### Request

```
GET /stats/{shortCode}
```

#### Path Parameters

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `shortCode` | string | 단축 URL 코드 |

#### 예시

```
GET /stats/a1b2c3
```

### Response

#### 성공 (200 OK)

```json
{
  "urlId": "a1b2c3",
  "shortUrl": "https://api-gateway-url.amazonaws.com/dev/a1b2c3",
  "originalUrl": "https://www.example.com/very/long/path/to/page",
  "createdAt": "2026-02-05T12:30:00.000000",
  "stats": {
    "totalClicks": 150,
    "todayClicks": 25,
    "yesterdayClicks": 30,
    "hourlyClicks": [
      { "hour": 0, "clicks": 5 },
      { "hour": 1, "clicks": 3 },
      { "hour": 2, "clicks": 1 },
      ...
      { "hour": 23, "clicks": 8 }
    ],
    "dailyClicks": [
      { "date": "2026-02-05", "clicks": 25 },
      { "date": "2026-02-04", "clicks": 30 },
      { "date": "2026-02-03", "clicks": 28 }
    ],
    "deviceDistribution": {
      "desktop": 80,
      "mobile": 60,
      "tablet": 10
    },
    "refererDistribution": {
      "direct": 50,
      "google.com": 40,
      "facebook.com": 30,
      "twitter.com": 20
    }
  }
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| `urlId` | string | 단축 URL 코드 |
| `shortUrl` | string | 완전한 단축 URL |
| `originalUrl` | string | 원본 URL |
| `createdAt` | string | 생성 시간 (ISO 8601) |
| `stats` | object | 통계 데이터 |

#### Stats 객체

| 필드 | 타입 | 설명 |
|------|------|------|
| `totalClicks` | number | 전체 클릭 수 |
| `todayClicks` | number | 오늘 클릭 수 |
| `yesterdayClicks` | number | 어제 클릭 수 |
| `hourlyClicks` | array | 시간대별 클릭 (0-23시) |
| `dailyClicks` | array | 일별 클릭 (최근 30일, 최신순) |
| `deviceDistribution` | object | 디바이스별 클릭 분포 (`desktop`, `mobile`, `tablet`) |
| `refererDistribution` | object | 유입 경로별 클릭 분포 |

#### 에러 응답

| Status Code | 에러 메시지 | 설명 |
|-------------|------------|------|
| 400 | `shortCode is required` | shortCode가 없음 |
| 404 | `URL not found` | 존재하지 않는 단축 URL |
| 500 | `{error message}` | 서버 에러 |

---

## 4. 전체 사이트 통계 조회

사이트 전체의 URL 및 클릭 통계를 조회합니다.

### Request

```
GET /stats
```

### Response

#### 성공 (200 OK)

```json
{
  "totalUrls": 1500,
  "totalClicks": 50000,
  "todayClicks": 500,
  "yesterdayClicks": 480,
  "popularUrls": [
    {
      "urlId": "a1b2c3",
      "shortUrl": "https://api-gateway-url.amazonaws.com/dev/a1b2c3",
      "originalUrl": "https://www.example.com/popular-page",
      "clickCount": 1500,
      "createdAt": "2026-01-15T10:00:00.000000"
    }
  ],
  "recentUrls": [
    {
      "urlId": "x9y8z7",
      "shortUrl": "https://api-gateway-url.amazonaws.com/dev/x9y8z7",
      "originalUrl": "https://www.example.com/new-page",
      "clickCount": 10,
      "createdAt": "2026-02-05T14:00:00.000000"
    }
  ]
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| `totalUrls` | number | 전체 등록된 URL 수 |
| `totalClicks` | number | 전체 클릭 수 |
| `todayClicks` | number | 오늘 클릭 수 |
| `yesterdayClicks` | number | 어제 클릭 수 |
| `popularUrls` | array | 인기 URL 목록 (클릭수 기준 상위 10개) |
| `recentUrls` | array | 최근 등록 URL 목록 (최근 10개) |

#### Popular/Recent URL 객체

| 필드 | 타입 | 설명 |
|------|------|------|
| `urlId` | string | 단축 URL 코드 |
| `shortUrl` | string | 완전한 단축 URL |
| `originalUrl` | string | 원본 URL |
| `clickCount` | number | 클릭 수 |
| `createdAt` | string | 생성 시간 (ISO 8601) |

#### 에러 응답

| Status Code | 에러 메시지 | 설명 |
|-------------|------------|------|
| 500 | `{error message}` | 서버 에러 |

---

## 공통 에러 응답 형식

모든 에러 응답은 다음 형식을 따릅니다:

```json
{
  "error": "에러 메시지"
}
```

---

## 사용 예시 (JavaScript/Fetch)

### URL 단축 생성

```javascript
const response = await fetch('https://your-api-url/dev/shorten', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    url: 'https://www.example.com/very/long/url'
  })
});

const data = await response.json();
console.log(data.shortUrl); // 단축된 URL
```

### 전체 통계 조회

```javascript
const response = await fetch('https://your-api-url/dev/stats');
const data = await response.json();
console.log(`총 ${data.totalUrls}개의 URL, 총 ${data.totalClicks}회 클릭`);
```

### URL별 통계 조회

```javascript
const shortCode = 'a1b2c3';
const response = await fetch(`https://your-api-url/dev/stats/${shortCode}`);
const data = await response.json();
console.log(`디바이스 분포:`, data.stats.deviceDistribution);
```

---

## 참고 사항
1. **URL 만료**: 생성된 URL은 30일 후 자동 만료됩니다.
2. **클릭 추적**: 리다이렉트 시 자동으로 클릭 통계가 기록됩니다.
3. **시간대**: 모든 시간은 **UTC** 기준입니다.
4. **Rate Limiting**: 현재 별도의 Rate Limit이 적용되어 있지 않습니다.
