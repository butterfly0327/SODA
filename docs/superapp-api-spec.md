# SODA SuperApp API 명세서

## 개요

SSAFY SuperApp 플랫폼을 통해 SODA 서비스의 핵심 기능을 외부 애플리케이션에 제공하는 API입니다.

### 호출 흐름

```
1. SSAFY 로그인 → AccessToken 발급
2. 애플리케이션이 apiKey + AccessToken 포함하여 SuperApp API 호출
3. SSAFY 인증서버가 apiKey 검증 후 appId를 파라미터로 SuperApp API 서버에 전달
4. SuperApp API 서버가 Public Key로 AccessToken 검증
   - Public Key 획득: GET https://project.ssafy.com/ssafy/oauth2/jwks
   - 실패 시 401 반환
5. 검증 성공 시 appId + AccessToken 기반으로 서비스 로직 처리 후 응답 반환
```

### 공통 요청 형식

| 구분 | 항목 | 설명 | 필수 |
|------|------|------|------|
| URL | `/v1/soda/{resource}` | API 버전 및 프로젝트명 포함 | ✅ |
| Query Parameter | `appId` | API 호출 애플리케이션 ID | ✅ |
| HTTP Header | `X-Access-Token` | API 호출 사용자의 AccessToken | N |

### 공통 응답 형식

```json
{
  "status": "SUCCESS",
  "message": "메시지",
  "data": { }
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| status | String | `SUCCESS` / `FAIL` |
| message | String | 응답 메시지 |
| data | Object | 응답 데이터 (실패 시 null) |

### 공통 에러 코드

| HTTP Status | 설명 |
|-------------|------|
| 400 | 잘못된 요청 파라미터 |
| 401 | AccessToken 검증 실패 또는 미제공 |
| 404 | 리소스를 찾을 수 없음 |
| 500 | 서버 내부 오류 |

---

## API 목록

| # | 메서드 | 경로 | 설명 | 인증 |
|---|--------|------|------|------|
| 1 | GET | `/v1/soda/resources` | 리소스 목록 조회 | 불필요 |
| 2 | GET | `/v1/soda/resources/{type}/{id}` | 리소스 상세 조회 | 불필요 |
| 3 | POST | `/v1/soda/recommendations` | 프롬프트 기반 리소스 추천 | 필요 |

---

## 1. 리소스 목록 조회

### 기본 정보

| 항목 | 내용 |
|------|------|
| 메서드 | GET |
| URL | `/v1/soda/resources` |
| 인증 | 불필요 |

### 요청

**Query Parameters**

| 파라미터 | 타입 | 필수 | 기본값 | 설명 |
|----------|------|------|--------|------|
| appId | String | ✅ | - | 애플리케이션 ID |
| keyword | String | N | - | 검색 키워드 |
| type | String | N | `ALL` | `ALL` / `DATASET` / `OPEN_API` |
| sort | String | N | `SCORE` | `SCORE` (평점순) / `LATEST` (최신순) |
| page | Integer | N | `0` | 페이지 번호 (0부터 시작) |
| size | Integer | N | `20` | 페이지 크기 |

**요청 예시**

```
GET /v1/soda/resources?appId=myApp&keyword=날씨&type=OPEN_API&sort=SCORE&page=0&size=20
```

### 응답

**응답 예시**

```json
{
  "status": "SUCCESS",
  "message": "리소스 목록 조회가 완료되었습니다.",
  "data": {
    "totalCount": 120,
    "totalPages": 6,
    "currentPage": 0,
    "hasNext": true,
    "items": [
      {
        "id": 1,
        "type": "DATASET",
        "title": "서울시 날씨 데이터셋",
        "score": 4.3,
        "isFree": true,
        "createdAt": "2024-01-01T00:00:00",
        "datasetMeta": {
          "publisherName": "서울시",
          "sourceUpdatedAt": "2024-06-01",
          "sampleCount": 50000
        },
        "openApiMeta": null
      },
      {
        "id": 2,
        "type": "OPEN_API",
        "title": "기상청 날씨 Open API",
        "score": 3.8,
        "isFree": true,
        "createdAt": "2024-02-01T00:00:00",
        "datasetMeta": null,
        "openApiMeta": {
          "category": "날씨",
          "avgResponseTime": 0.25,
          "authType": "API_KEY",
          "dailyLimit": 1000
        }
      }
    ]
  }
}
```

**응답 필드**

| 필드 | 타입 | 설명 |
|------|------|------|
| totalCount | Integer | 전체 리소스 수 |
| totalPages | Integer | 전체 페이지 수 |
| currentPage | Integer | 현재 페이지 번호 |
| hasNext | Boolean | 다음 페이지 존재 여부 |
| items | Array | 리소스 목록 |
| items[].id | Long | 리소스 ID |
| items[].type | String | `DATASET` / `OPEN_API` |
| items[].title | String | 리소스 제목 |
| items[].score | Double | 평균 평점 (리뷰 없으면 null) |
| items[].isFree | Boolean | 무료 여부 |
| items[].createdAt | String | 등록일시 |
| items[].datasetMeta | Object | DATASET 타입일 때만 존재 |
| items[].datasetMeta.publisherName | String | 제공기관 |
| items[].datasetMeta.sourceUpdatedAt | String | 원본 최신화 일자 |
| items[].datasetMeta.sampleCount | Long | 데이터 행 수 |
| items[].openApiMeta | Object | OPEN_API 타입일 때만 존재 |
| items[].openApiMeta.category | String | 카테고리 |
| items[].openApiMeta.avgResponseTime | Double | 평균 응답 시간 (초) |
| items[].openApiMeta.authType | String | 인증 방식 |
| items[].openApiMeta.dailyLimit | Integer | 일일 호출 제한 |

---

## 2. 리소스 상세 조회

### 기본 정보

| 항목 | 내용 |
|------|------|
| 메서드 | GET |
| URL | `/v1/soda/resources/{type}/{id}` |
| 인증 | 불필요 |

### 요청

**Path Parameters**

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| type | String | ✅ | `DATASET` / `OPEN_API` |
| id | Long | ✅ | 리소스 ID |

**Query Parameters**

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| appId | String | ✅ | 애플리케이션 ID |

**요청 예시**

```
GET /v1/soda/resources/DATASET/1?appId=myApp
```

### 응답

**응답 예시 - DATASET**

```json
{
  "status": "SUCCESS",
  "message": "리소스 상세 조회가 완료되었습니다.",
  "data": {
    "id": 1,
    "type": "DATASET",
    "title": "서울시 날씨 데이터셋",
    "score": 4.3,
    "isFree": true,
    "createdAt": "2024-01-01T00:00:00",
    "datasetDetail": {
      "subtitle": "서울시 기상 관측 데이터",
      "descriptionShort": "서울시 25개 구의 시간별 날씨 데이터",
      "descriptionLong": "...",
      "publisherName": "서울시",
      "domains": ["날씨", "환경"],
      "tasks": ["분류", "예측"],
      "modalities": ["tabular"],
      "tags": ["날씨", "기온", "강수량"],
      "languages": ["ko"],
      "licenseName": "공공데이터 이용허락",
      "licenseUrl": "https://...",
      "commercialUseAllowed": true,
      "accessType": "PUBLIC",
      "rowCount": 50000,
      "datasetSizeBytes": 10485760,
      "sourceUpdatedAt": "2024-06-01",
      "canonicalUrl": "https://...",
      "landingUrl": "https://...",
      "schemaJson": "{\"fields\": [{\"name\": \"date\", \"type\": \"string\"}]}"
    },
    "openApiDetail": null,
    "reviews": [
      {
        "id": 1,
        "rating": 5,
        "content": "데이터 품질이 좋아요.",
        "createdAt": "2024-03-01T12:00:00"
      }
    ]
  }
}
```

**응답 예시 - OPEN_API**

```json
{
  "status": "SUCCESS",
  "message": "리소스 상세 조회가 완료되었습니다.",
  "data": {
    "id": 2,
    "type": "OPEN_API",
    "title": "기상청 날씨 Open API",
    "score": 3.8,
    "isFree": true,
    "createdAt": "2024-02-01T00:00:00",
    "datasetDetail": null,
    "openApiDetail": {
      "description": "기상청에서 제공하는 날씨 정보 API",
      "provider": "기상청",
      "baseUrl": "https://api.weather.go.kr",
      "docsUrl": "https://...",
      "authType": "API_KEY",
      "category": "날씨",
      "tags": ["날씨", "기온", "예보"],
      "rateLimit": 100,
      "dailyLimit": 1000,
      "pricingNote": "무료 (1,000회/일)",
      "commercialUse": true,
      "requiresApproval": false,
      "responseFormat": "JSON",
      "avgResponseTime": 0.25
    },
    "reviews": []
  }
}
```

**응답 필드**

| 필드 | 타입 | 설명 |
|------|------|------|
| id | Long | 리소스 ID |
| type | String | `DATASET` / `OPEN_API` |
| title | String | 리소스 제목 |
| score | Double | 평균 평점 (리뷰 없으면 null) |
| isFree | Boolean | 무료 여부 |
| createdAt | String | 등록일시 |
| datasetDetail | Object | DATASET 타입일 때만 존재 |
| openApiDetail | Object | OPEN_API 타입일 때만 존재 |
| reviews | Array | 리뷰 목록 |
| reviews[].id | Long | 리뷰 ID |
| reviews[].rating | Integer | 평점 (1~5) |
| reviews[].content | String | 리뷰 내용 |
| reviews[].createdAt | String | 작성일시 |

---

## 3. 프롬프트 기반 리소스 추천

### 기본 정보

| 항목 | 내용 |
|------|------|
| 메서드 | POST |
| URL | `/v1/soda/recommendations` |
| 인증 | 필요 (`X-Access-Token`) |
| 비고 | AI 추천 처리로 응답까지 수 초 소요될 수 있음 |

### 요청

**Query Parameters**

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| appId | String | ✅ | 애플리케이션 ID |

**HTTP Header**

| 헤더 | 필수 | 설명 |
|------|------|------|
| X-Access-Token | ✅ | 사용자 AccessToken |

**Request Body**

```json
{
  "message": "교통사고 예측 모델을 만들고 싶어. 관련 데이터셋과 API 추천해줘."
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| message | String | ✅ | 사용자 프롬프트 |

### 응답

**응답 예시**

```json
{
  "status": "SUCCESS",
  "message": "추천이 완료되었습니다.",
  "data": {
    "mergedReason": "## 추천 요약\n- 생활/관광 정보 서비스 목적에 맞춰 데이터셋과 Open API를 함께 선별했습니다.\n- 점수 기준을 통과한 항목만 반환합니다.",
    "datasetReason": "## 데이터셋 추천 근거\n- 지역 기반 생활정보 탐색에 바로 쓸 수 있는 공공 데이터셋을 우선 추천했습니다.",
    "openApiReason": "## Open API 추천 근거\n- 서비스 연동 문서가 명확하고 활용성이 높은 Open API를 우선 추천했습니다.",
    "datasetRecommendations": [
      {
        "datasetId": 10,
        "rank": 1,
        "suitabilityScore": 0.92,
        "card": {
          "title": "제주특별자치도 서귀포시_착한가격업소정보",
          "sourceName": "공공데이터포털",
          "updatedAt": "2026-03-19T09:29:27.469574+09:00",
          "isFree": true
        },
        "detail": {
          "canonicalUrl": "https://www.data.go.kr/...",
          "descriptionLong": "이 데이터는 서귀포시 내에서 물가 안정과 소비자 부담 완화를 위해 착한가격업소로 지정된 업소들의 정보를 제공합니다.",
          "rowCount": 90,
          "lastUpdate": "2025-09-15",
          "domains": ["서비스", "문화관광"],
          "tasks": ["물가안정", "가격비교"],
          "modalities": ["text", "tabular", "geospatial"],
          "tags": ["착한가격", "우수업소", "관광"],
          "accessType": "OPEN",
          "loginRequired": false,
          "approvalRequired": false,
          "isRestricted": false,
          "licenseName": "이용허락범위 제한 없음",
          "commercialUseAllowed": null,
          "languages": ["kor"],
          "metrics": {
            "viewCount": 4670,
            "requestCount": 1601
          },
          "sourceVersion": "20241025",
          "sourceCreatedAt": "2019-08-12T09:00:00+09:00",
          "sourceUpdatedAt": "2025-09-15T09:00:00+09:00",
          "createdAt": "2026-03-19T09:29:27.469574+09:00",
          "creators": [
            {
              "name": "제주특별자치도 서귀포시",
              "role": "creator",
              "phone": null,
              "url": null
            }
          ],
          "schemaJson": {
            "columns": [
              {
                "name": "업종",
                "unit": "해당없음",
                "data_type": "고정문자형(CHAR)",
                "max_length": "6",
                "description": "착한가격업소 업종 구분"
              }
            ]
          }
        },
        "reviews": []
      }
    ],
    "openApiRecommendations": [
      {
        "openApiId": 1,
        "rank": 2,
        "score": 0.87,
        "card": {
          "name": "한국문화관광연구원_관광실태조사서비스",
          "provider": "한국문화관광연구원",
          "updatedAt": "2026-03-24T10:52:52.163320+09:00",
          "isFree": true
        },
        "detail": {
          "docsUrl": "https://www.data.go.kr/...",
          "description": "관광실태 정보를 조회하기 위한 서비스로서 국민여행조사, 외래관광객조사, 관광사업체조사의 주요지수를 조회할 수 있습니다.",
          "authType": "API_KEY",
          "category": "정부자원관리",
          "responseFormat": "XML",
          "tags": ["조사통계", "국민여행조사", "외래관광객조사"],
          "pricingNote": "개발계정 : 1000/ 운영계정 : 활용사례 등록시 신청하면 트래픽 증가 가능",
          "commercialUse": true,
          "requiresApproval": false
        },
        "reviews": []
      }
    ]
  }
}
```

**응답 정책**

- 추천 개수는 요청 수를 강제로 채우지 않으며, 품질 기준을 통과한 결과만 `0..N` 범위로 반환됩니다.
- `mergedReason`, `datasetReason`, `openApiReason`은 markdown 문자열 형식입니다.
- 카드/상세 패널 렌더에 필요한 필드를 함께 내려주며, 프론트 미사용 필드는 제외합니다.

**응답 필드**

| 필드 | 타입 | 설명 |
|------|------|------|
| mergedReason | String | AI 추천 종합 설명 |
| datasetReason | String | 데이터셋 추천 요약 사유 (markdown) |
| openApiReason | String | Open API 추천 요약 사유 (markdown) |
| datasetRecommendations | Array | 추천 데이터셋 목록 |
| datasetRecommendations[].datasetId | Long | 데이터셋 ID |
| datasetRecommendations[].rank | Integer | 추천 순위 |
| datasetRecommendations[].suitabilityScore | Double | 적합도 점수 (0~1) |
| datasetRecommendations[].card.title | String | 카드 제목 |
| datasetRecommendations[].card.sourceName | String | 카드 제공처 |
| datasetRecommendations[].card.updatedAt | String | 카드 업데이트 시각 |
| datasetRecommendations[].card.isFree | Boolean | 카드 비용 여부 |
| datasetRecommendations[].detail.canonicalUrl | String | 상세 URL |
| datasetRecommendations[].detail.descriptionLong | String | 상세 설명 |
| datasetRecommendations[].detail.rowCount | Long | 행 수 |
| datasetRecommendations[].detail.lastUpdate | String | 상세 업데이트 시각 |
| datasetRecommendations[].detail.domains | Array | 도메인 |
| datasetRecommendations[].detail.tasks | Array | 작업(task) |
| datasetRecommendations[].detail.modalities | Array | 데이터 형식 |
| datasetRecommendations[].detail.tags | Array | 태그 |
| datasetRecommendations[].detail.accessType | String | 공개 상태 |
| datasetRecommendations[].detail.loginRequired | Boolean | 로그인 필요 여부 |
| datasetRecommendations[].detail.approvalRequired | Boolean | 승인 필요 여부 |
| datasetRecommendations[].detail.isRestricted | Boolean | 제한 여부 |
| datasetRecommendations[].detail.licenseName | String | 라이선스 |
| datasetRecommendations[].detail.commercialUseAllowed | Boolean | 상용 사용 가능 여부 |
| datasetRecommendations[].detail.languages | Array | 언어 |
| datasetRecommendations[].detail.metrics | Object | 사용 지표 |
| datasetRecommendations[].detail.metrics.viewCount | Long | 조회수 |
| datasetRecommendations[].detail.metrics.requestCount | Long | 요청수 |
| datasetRecommendations[].detail.sourceVersion | String | 데이터 버전 |
| datasetRecommendations[].detail.sourceCreatedAt | String | 원본 생성일 |
| datasetRecommendations[].detail.sourceUpdatedAt | String | 원본 수정일 |
| datasetRecommendations[].detail.createdAt | String | 메타데이터 수정일 |
| datasetRecommendations[].detail.creators | Array | 제작자 정보 |
| datasetRecommendations[].detail.creators[].name | String | 제작자명 |
| datasetRecommendations[].detail.creators[].role | String | 역할 |
| datasetRecommendations[].detail.creators[].phone | String | 연락처 |
| datasetRecommendations[].detail.creators[].url | String | 관련 URL |
| datasetRecommendations[].detail.schemaJson | Object | 스키마 정보 |
| datasetRecommendations[].detail.schemaJson.columns | Array | 컬럼 스키마 목록 |
| datasetRecommendations[].detail.schemaJson.columns[].name | String | 컬럼명 |
| datasetRecommendations[].detail.schemaJson.columns[].unit | String | 컬럼 단위 |
| datasetRecommendations[].detail.schemaJson.columns[].data_type | String | 컬럼 타입 |
| datasetRecommendations[].detail.schemaJson.columns[].max_length | String/Number | 컬럼 최대 길이 |
| datasetRecommendations[].detail.schemaJson.columns[].description | String | 컬럼 설명 |
| datasetRecommendations[].reviews | Array | 리뷰 목록 |
| datasetRecommendations[].reviews[].id | Long | 리뷰 ID |
| datasetRecommendations[].reviews[].name | String | 작성자 |
| datasetRecommendations[].reviews[].rating | Integer | 별점(1~5) |
| datasetRecommendations[].reviews[].content | String | 리뷰 내용 |
| datasetRecommendations[].reviews[].createdAt | String | 리뷰 작성 시각 |
| openApiRecommendations | Array | 추천 Open API 목록 |
| openApiRecommendations[].openApiId | Long | Open API ID |
| openApiRecommendations[].rank | Integer | 추천 순위 |
| openApiRecommendations[].score | Double | 추천 점수 (0~1) |
| openApiRecommendations[].card.name | String | 카드 제목 |
| openApiRecommendations[].card.provider | String | 카드 제공처 |
| openApiRecommendations[].card.updatedAt | String | 카드 업데이트 시각 |
| openApiRecommendations[].card.isFree | Boolean | 카드 비용 여부 |
| openApiRecommendations[].detail.docsUrl | String | 문서 URL |
| openApiRecommendations[].detail.description | String | 상세 설명 |
| openApiRecommendations[].detail.authType | String | 인증 방식 |
| openApiRecommendations[].detail.category | String | 카테고리 |
| openApiRecommendations[].detail.responseFormat | String | 응답 형식 |
| openApiRecommendations[].detail.tags | Array | 태그 목록 |
| openApiRecommendations[].detail.pricingNote | String | 가격 정책 |
| openApiRecommendations[].detail.commercialUse | Boolean | 상용 사용 가능 여부 |
| openApiRecommendations[].detail.requiresApproval | Boolean | 승인 필요 여부 |
| openApiRecommendations[].reviews | Array | 리뷰 목록 |
| openApiRecommendations[].reviews[].id | Long | 리뷰 ID |
| openApiRecommendations[].reviews[].name | String | 작성자 |
| openApiRecommendations[].reviews[].rating | Integer | 별점(1~5) |
| openApiRecommendations[].reviews[].content | String | 리뷰 내용 |
| openApiRecommendations[].reviews[].createdAt | String | 리뷰 작성 시각 |

**에러 응답**

| 상황 | HTTP Status | 메시지 |
|------|-------------|--------|
| AccessToken 미제공 또는 만료 | 401 | 인증에 실패했습니다. |
| AI 추천 처리 실패 | 500 | 추천 생성 중 오류가 발생했습니다. |
| 타임아웃 (300초 초과) | 504 | 추천 생성 시간이 초과되었습니다. |
