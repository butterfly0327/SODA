# FastAPI + RAG Server

이 디렉터리는 내부 FastAPI 서버입니다.

## Quick Start

Python `3.12.10` 기준

```bash
python3.12 -m venv .venv
.venv\Scripts\activate
pip install -r ../../requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Endpoints

- `GET /api/v1/health`: 서버 상태 확인
- `POST /api/v1/rag/query`: 기본 RAG 질의(보일러플레이트)
- `POST /api/v1/collector/datasets/runs`: 데이터셋 메타데이터 수집 비동기 시작
- `POST /api/v1/rag/recommend-openapi`: 내부 Open API 추천 생성
- `POST /api/v1/rag/recommend-datasets`: 내부 데이터셋 추천 생성
- `POST /api/v1/rag/merge-recommendation-reason`: 내부 전체 추천 이유 생성
- `POST /api/v1/rag/infer-recommendation-mode`: 내부 LLM 의도 분류
- `POST /api/v1/rag/chat-answer`: 내부 일반 Q&A 답변 생성

---

## 0326 수정사항 총정리 (최신 기준)

### 오늘 반영된 핵심 변경

1. 추천 개수 정책 상향
   - 기본 추천 개수: `5 -> 10`
   - 최대 추천 개수: `10 -> 20`

2. 저품질 추천 차단(점수 게이트)
   - score 기준 `60점 이하(<=60)`는 추천 결과에서 제외
   - 결과 개수는 요청 N을 강제로 채우지 않고 `0..N`으로 반환

3. 토큰 절감 로직 적용
   - Dataset: LLM 입력 후보를 요청 N 기반으로 동적 축소
   - OpenAPI: 점수 필터 후 후보가 비면 요약 LLM 호출 자체를 생략
   - OpenAPI 컨텍스트(description/tag) 길이 축소

4. 프롬프트 기반 자동 분기(모드 선택 UI 없이 동작)
   - 내부 LLM 의도 분류 결과에 따라 `CHAT_ONLY`, `DATASET_ONLY`, `OPENAPI_ONLY`, `BOTH` 분기
   - `CHAT_ONLY`면 추천 API 호출 없이 일반 Q&A 답변만 생성
   - 외부 공개 API(`POST /v1/chat/messages`)의 request/response 계약은 변경하지 않음

5. 신규 내부 API 추가
   - `/api/v1/rag/infer-recommendation-mode`
   - `/api/v1/rag/chat-answer`

6. 최종 추천 이유 Markdown 전달
   - DATASET_ONLY/OPENAPI_ONLY/BOTH 모두 `reasonText` 계열 응답을 markdown 문자열로 생성/전달
   - request/response body 스키마 변경 없이 문자열 포맷만 markdown으로 통일

---

## 0326 API 명세 (요청 형식 반영)

아래는 0326 기준 최신 동작 기준이다. (내부 연동 API 포함)

### 1) 내부 데이터셋 추천 생성 API

Header
- API Path: `/api/v1/rag/recommend-datasets`
- Function: `generate_dataset_recommendation`

request parameter

| 파라미터명 | 타입 | 설명 |
| --- | --- | --- |
| `conversationId` | integer \| null | 대화 ID |
| `userId` | integer \| null | 호출 사용자 ID |
| `userTurnId` | integer \| null | Spring Boot가 전달하는 사용자 턴 ID |
| `prompt` | string \| null | 사용자 데이터셋 추천 프롬프트 |
| `message` | string \| null | Spring Boot 메시지 본문 |
| `history` | array | 대화 히스토리 (`role`, `content`) |
| `datasetRecommendationId` | integer \| null | 기존 dataset_recommendations ID 재사용 |
| `topN` | integer \| null | 최종 추천 개수(기본 10, 최대 20) |
| `debugUserTurnId` | integer \| null | 테스트용 userTurnId 대체값 |

response code

| 코드 | 설명 |
| --- | --- |
| `200` | 추천 생성 성공 |
| `400` | 필수 입력 누락/유효성 오류 |
| `404` | 추천 가능한 데이터셋 후보 없음 |
| `422` | 요청 본문 검증 실패 |
| `500` | 내부 처리 오류 |
| `502` | 외부 LLM/Embedding 호출 오류 |

response parameter

| 파라미터명 | 타입 | 설명 |
| --- | --- | --- |
| `status` | integer | 상태 코드 |
| `message` | string | 추가적인 설명(한글) |
| `recommendationId` | integer | dataset recommendation ID |
| `datasetRecommendationId` | integer | dataset recommendation ID |
| `userTurnId` | integer | 사용자 턴 ID |
| `prompt` | string | 입력 프롬프트 |
| `summaryReason` | string | 추천 요약 이유(마크다운 문자열) |
| `reasonText` | string | 추천 요약 이유(마크다운 문자열, 동일 의미) |
| `candidateCount` | integer | LLM 전달 후보 수 |
| `llmModel` | string | 사용 LLM 모델 |
| `recommendedItems` | array | 최종 추천 목록 |
| `recommendedItems[].datasetId` | integer | 추천 데이터셋 ID |
| `recommendedItems[].rank` | integer | 추천 순위 |
| `recommendedItems[].suitabilityScore` | number | 적합도 점수(0~1) |
| `recommendedItems[].reason` | string | 추천 이유 |

success data example

```json
{
  "status": 200,
  "message": "내부 데이터셋 추천을 생성했습니다.",
  "recommendationId": 77,
  "datasetRecommendationId": 77,
  "userTurnId": 1234,
  "prompt": "보행자 탐지 학습용 데이터셋 추천해줘",
  "summaryReason": "## 추천 요약\n- 요청 의도와 태스크 적합도가 높은 데이터셋만 선별했습니다.\n- 접근 제약 조건을 함께 고려했습니다.",
  "reasonText": "## 추천 요약\n- 요청 의도와 태스크 적합도가 높은 데이터셋만 선별했습니다.\n- 접근 제약 조건을 함께 고려했습니다.",
  "candidateCount": 10,
  "llmModel": "gpt-5.2",
  "recommendedItems": [
    {
      "datasetId": 101,
      "rank": 1,
      "suitabilityScore": 0.91,
      "reason": "보행자 탐지와 라벨 구조가 요청 목적에 적합합니다."
    }
  ]
}
```

fail data example

`400`

```json
{
  "status": 400,
  "message": "userTurnId가 필요합니다. Spring 미구현 테스트 시 debugUserTurnId를 전달하세요."
}
```

`404`

```json
{
  "status": 404,
  "message": "추천 가능한 데이터셋 후보를 찾지 못했습니다."
}
```

`422`

```json
{
  "status": 422,
  "message": "요청 본문 검증에 실패했습니다."
}
```

`500`

```json
{
  "status": 500,
  "message": "추천 생성 중 내부 오류가 발생했습니다: 내부 처리 예외"
}
```

`502`

```json
{
  "status": 502,
  "message": "LLM API 호출 실패(status=502): upstream gateway error"
}
```

---

### 2) 내부 OpenAPI 추천 생성 API

Header
- API Path: `/api/v1/rag/recommend-open-apis`
- Function: `recommend_openapi`

request parameter

| 파라미터명 | 타입 | 설명 |
| --- | --- | --- |
| `conversationId` | integer \| null | 대화 ID |
| `userId` | integer \| null | 호출 사용자 ID |
| `userTurnId` | integer \| null | 사용자 턴 ID |
| `debugUserTurnId` | integer \| null | 테스트용 userTurnId 대체값 |
| `prompt` | string \| null | OpenAPI 추천 프롬프트 |
| `message` | string \| null | Spring Boot 메시지 본문 |
| `history` | array | 대화 히스토리 (`role`, `content`) |
| `openapiRecommendationId` | integer \| null | 기존 openapi_recommendations ID 재사용 |

response code

| 코드 | 설명 |
| --- | --- |
| `200` | 추천 생성 성공 |
| `400` | 필수 입력 누락/유효성 오류 |
| `422` | 요청 본문 검증 실패 |
| `500` | 내부 처리 오류 |
| `502` | 외부 LLM/Embedding 호출 오류 |

response parameter

| 파라미터명 | 타입 | 설명 |
| --- | --- | --- |
| `status` | integer | 상태 코드 |
| `message` | string | 추가적인 설명(한글) |
| `recommendationId` | integer | openapi recommendation ID |
| `openapiRecommendationId` | integer | openapi recommendation ID |
| `userTurnId` | integer | 사용자 턴 ID |
| `prompt` | string | 입력 프롬프트 |
| `summaryReason` | string | 추천 요약(마크다운 문자열) |
| `reasonText` | string | 추천 요약(마크다운 문자열, 동일 의미) |
| `candidateCount` | integer | 추천된 API 개수 |
| `llmModel` | string | 사용 LLM 모델 |
| `recommendedItems` | array | 최종 추천 목록 |
| `recommendedItems[].openApiId` | integer | API ID |
| `recommendedItems[].name` | string | API 이름 |
| `recommendedItems[].description` | string \| null | API 설명 |
| `recommendedItems[].provider` | string \| null | 제공자 |
| `recommendedItems[].baseUrl` | string | Base URL |
| `recommendedItems[].docsUrl` | string \| null | 문서 URL |
| `recommendedItems[].authType` | string | 인증 방식 |
| `recommendedItems[].category` | string \| null | 카테고리 |
| `recommendedItems[].tags` | array | 태그 목록 |
| `recommendedItems[].isFree` | boolean \| null | 무료 여부 |
| `recommendedItems[].score` | number | 유사도 점수 |

success data example

```json
{
  "status": 200,
  "message": "Open API 추천을 생성했습니다.",
  "recommendationId": 88,
  "openapiRecommendationId": 88,
  "userTurnId": 1234,
  "prompt": "지도 경로 검색 API 추천해줘",
  "summaryReason": "## 추천 요약\n- 요청 기능과 인증/요금 조건을 기준으로 Open API를 선별했습니다.\n- 구현 전 확인 필요 항목을 함께 정리했습니다.",
  "reasonText": "## 추천 요약\n- 요청 기능과 인증/요금 조건을 기준으로 Open API를 선별했습니다.\n- 구현 전 확인 필요 항목을 함께 정리했습니다.",
  "candidateCount": 2,
  "llmModel": "gpt-5.2",
  "recommendedItems": [
    {
      "openApiId": 11,
      "name": "Kakao Mobility Directions",
      "description": "경로 탐색 API",
      "provider": "Kakao",
      "baseUrl": "https://apis-navi.kakaomobility.com",
      "docsUrl": "https://developers.kakaomobility.com",
      "authType": "API_KEY",
      "category": "지도",
      "tags": ["route", "navigation"],
      "isFree": true,
      "score": 0.84
    }
  ]
}
```

fail data example

`400`

```json
{
  "status": 400,
  "message": "prompt 또는 message 중 하나는 반드시 필요합니다."
}
```

`422`

```json
{
  "status": 422,
  "message": "요청 본문 검증에 실패했습니다."
}
```

`500`

```json
{
  "status": 500,
  "message": "추천 생성 중 오류가 발생했습니다: 내부 처리 예외"
}
```

`502`

```json
{
  "status": 502,
  "message": "LLM API 호출 실패(status=502): upstream gateway error"
}
```

---

### 3) 내부 전체 추천 이유 병합 API

Header
- API Path: `/api/v1/rag/merge-recommendation-reason`
- Function: `merge_recommendation_reasons`

request parameter

| 파라미터명 | 타입 | 설명 |
| --- | --- | --- |
| `conversationId` | integer \| null | 대화 ID |
| `userId` | integer \| null | 호출 사용자 ID |
| `userTurnId` | integer \| null | 사용자 턴 ID |
| `debugUserTurnId` | integer \| null | 테스트용 userTurnId 대체값 |
| `prompt` | string \| null | 사용자 원본 프롬프트 |
| `message` | string \| null | Spring Boot 메시지 본문 |
| `history` | array | 대화 히스토리 (`role`, `content`) |
| `recommendationId` | integer \| null | recommendation ID |
| `datasetRecommendationId` | integer \| null | dataset recommendation ID |
| `openapiRecommendationId` | integer \| null | openapi recommendation ID |
| `datasetReason` | string \| null | 데이터셋 추천 사유 |
| `openapiReason` | string \| null | OpenAPI 추천 사유 |

response code

| 코드 | 설명 |
| --- | --- |
| `200` | 병합 성공 |
| `400` | 입력 파라미터 오류 |
| `422` | 요청 본문 검증 실패 |
| `500` | 내부 처리 오류 |
| `502` | 외부 LLM 호출 오류 |

response parameter

| 파라미터명 | 타입 | 설명 |
| --- | --- | --- |
| `status` | integer | 상태 코드 |
| `message` | string | 추가적인 설명(한글) |
| `recommendationId` | integer | recommendation ID |
| `userTurnId` | integer | 사용자 턴 ID |
| `datasetRecommendationId` | integer | dataset recommendation ID |
| `openapiRecommendationId` | integer | openapi recommendation ID |
| `prompt` | string | 입력 프롬프트 |
| `mergedReasonText` | string | 최종 통합 추천 사유(마크다운 문자열) |
| `llmModel` | string | 사용 LLM 모델 |

success data example

```json
{
  "status": 200,
  "message": "추천 이유 병합을 완료했습니다.",
  "recommendationId": 100,
  "userTurnId": 1234,
  "datasetRecommendationId": 77,
  "openapiRecommendationId": 88,
  "prompt": "지도 기반 유동인구 분석에 맞는 조합 추천",
  "mergedReasonText": "## 최종 추천 요약\n요청 목적에는 유동인구 데이터셋과 경로 탐색 OpenAPI 조합이 적합합니다.\n\n## 유의사항\n- 근거가 제한된 항목은 확인 필요합니다.",
  "llmModel": "gpt-5.2"
}
```

fail data example

`400`

```json
{
  "status": 400,
  "message": "dataset_recommendations 레코드를 찾을 수 없습니다."
}
```

`422`

```json
{
  "status": 422,
  "message": "요청 본문 검증에 실패했습니다."
}
```

`500`

```json
{
  "status": 500,
  "message": "추천 이유 병합 중 내부 오류가 발생했습니다: 내부 처리 예외"
}
```

`502`

```json
{
  "status": 502,
  "message": "LLM API 호출 실패(status=502): upstream gateway error"
}
```

---

### 4) 내부 추천 모드 의도 분류 API (신규)

Header
- API Path: `/api/v1/rag/infer-recommendation-mode`
- Function: `infer_recommendation_mode`

request parameter

| 파라미터명 | 타입 | 설명 |
| --- | --- | --- |
| `conversationId` | integer \| null | 대화 ID |
| `userId` | integer \| null | 호출 사용자 ID |
| `userTurnId` | integer \| null | 사용자 턴 ID |
| `prompt` | string \| null | 의도 판별 대상 프롬프트 |
| `message` | string \| null | Spring Boot 메시지 본문 |
| `history` | array | 대화 히스토리 (`role`, `content`) |

response code

| 코드 | 설명 |
| --- | --- |
| `200` | 모드 판별 성공 |
| `400` | 필수 입력 누락/유효성 오류 |
| `422` | 요청 본문 검증 실패 |
| `500` | 내부 처리 오류 |
| `502` | 외부 LLM 호출 오류 |

response parameter

| 파라미터명 | 타입 | 설명 |
| --- | --- | --- |
| `status` | integer | 상태 코드 |
| `message` | string | 추가적인 설명(한글) |
| `mode` | string | `CHAT_ONLY`/`DATASET_ONLY`/`OPENAPI_ONLY`/`BOTH` |
| `llmModel` | string | 사용 LLM 모델 |

success data example

```json
{
  "status": 200,
  "message": "추천 모드 판별을 완료했습니다.",
  "mode": "CHAT_ONLY",
  "llmModel": "gpt-5.2"
}
```

fail data example

`400`

```json
{
  "status": 400,
  "message": "prompt 또는 message 중 하나는 반드시 필요합니다."
}
```

`422`

```json
{
  "status": 422,
  "message": "요청 본문 검증에 실패했습니다."
}
```

`500`

```json
{
  "status": 500,
  "message": "추천 모드 판별 중 내부 오류가 발생했습니다: 내부 처리 예외"
}
```

`502`

```json
{
  "status": 502,
  "message": "LLM API 타임아웃: upstream timeout"
}
```

---

### 5) 내부 일반 Q&A 답변 생성 API (신규)

Header
- API Path: `/api/v1/rag/chat-answer`
- Function: `generate_chat_answer`

request parameter

| 파라미터명 | 타입 | 설명 |
| --- | --- | --- |
| `conversationId` | integer \| null | 대화 ID |
| `userId` | integer \| null | 호출 사용자 ID |
| `userTurnId` | integer \| null | 사용자 턴 ID |
| `prompt` | string \| null | 채팅 답변 생성 대상 프롬프트 |
| `message` | string \| null | Spring Boot 메시지 본문 |
| `history` | array | 대화 히스토리 (`role`, `content`) |

response code

| 코드 | 설명 |
| --- | --- |
| `200` | 채팅 답변 생성 성공 |
| `400` | 필수 입력 누락/유효성 오류 |
| `422` | 요청 본문 검증 실패 |
| `500` | 내부 처리 오류 |
| `502` | 외부 LLM 호출 오류 |

response parameter

| 파라미터명 | 타입 | 설명 |
| --- | --- | --- |
| `status` | integer | 상태 코드 |
| `message` | string | 추가적인 설명(한글) |
| `answer` | string | 생성된 채팅 답변 |
| `llmModel` | string | 사용 LLM 모델 |

success data example

```json
{
  "status": 200,
  "message": "채팅 응답 생성을 완료했습니다.",
  "answer": "네, 해당 상황에서는 먼저 입력 조건을 분리해서 확인하는 것이 좋습니다.",
  "llmModel": "gpt-5.2"
}
```

fail data example

`400`

```json
{
  "status": 400,
  "message": "prompt 또는 message 중 하나는 반드시 필요합니다."
}
```

`422`

```json
{
  "status": 422,
  "message": "요청 본문 검증에 실패했습니다."
}
```

`500`

```json
{
  "status": 500,
  "message": "채팅 응답 생성 중 내부 오류가 발생했습니다: 내부 처리 예외"
}
```

`502`

```json
{
  "status": 502,
  "message": "LLM API 요청 실패: upstream network error"
}
```

---

## 내부 데이터셋 추천 생성 API

- API 명칭: 내부 데이터셋 추천 생성
- Function: `generateDatasetRecommendation`
- Method: `POST`
- Path: `/api/v1/rag/recommend-datasets`
- 호출 주체: Spring Boot 내부 API(미구현 기간에는 Postman/curl 직접 호출 가능)

### 동작 요약

1. 사용자 프롬프트를 임베딩하여 `dataset_chunk`에서 유사도 `top 50` 후보를 조회
2. 서버에서 가벼운 규칙으로 `top 20` 후보를 압축
3. LLM(`gpt-5.2`)가 최종 추천/랭킹/점수/추천 이유를 생성
4. 결과를 `dataset_recommendation` 테이블에 저장

### 점수 산정 정책

- 최종 `suitability_score`는 **LLM이 생성**한다.
- 프롬프트에 고정 루브릭을 제공해 일관성을 높인다.
  - `0.90 ~ 1.00`: 요구사항 핵심에 매우 적합
  - `0.75 ~ 0.89`: 대체로 적합
  - `0.60 ~ 0.74`: 부분 적합
  - `0.00 ~ 0.59`: 낮은 적합성
- 최종 정렬은 서버에서 `suitabilityScore DESC -> datasetId ASC`로 고정하고 rank를 재부여한다.

### 토큰 절약 전략

- 벡터 검색 `top 50`은 리콜 확보용, LLM 입력은 `top 20`만 전달
- 후보당 긴 원문 대신 압축 카드(`title/도메인/태스크/접근제약/요약`)만 전달
- JSON 강제 출력 + `max_completion_tokens` 제한 (`gpt-5.2` 기본 사용, 필요 시 모델별 옵션 튜닝)
- 추천 이유는 항목당 짧은 한 문장으로 제한

### Header

| Header | Required | Description |
| --- | --- | --- |
| `Content-Type: application/json` | Y | JSON 본문 전송 |
| `X-Triggered-By` | N | 호출 주체 식별자(예: `spring-chat`), 현재 추천 API 로직에서는 읽지 않으며 전달해도 무시 |

### Request Parameter

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `userTurnId` | integer | C | Spring Boot가 전달하는 사용자 turn ID |
| `prompt` | string | Y | 데이터셋 추천 요청 프롬프트 |
| `topN` | integer | N | 최종 추천 개수(기본 10, 최대 20) |
| `debugUserTurnId` | integer | N | Spring 미구현 테스트용 userTurnId 대체값 |

> Required 표기에서 `C`는 조건부 필수(Conditional Required)를 의미한다.
> `userTurnId` 또는 `debugUserTurnId` 중 하나는 반드시 필요하다.

### Request Example (curl)

운영(Spring 연동) 케이스

```bash
curl "http://localhost:8000/api/v1/rag/recommend-datasets" \
  -H "Content-Type: application/json" \
  -d '{
    "userTurnId": 1234,
    "prompt": "보행자 탐지 모델 학습용 한국어 이미지 데이터셋 추천해줘",
    "topN": 5
  }'
```

개발/테스트(Spring 미구현) 케이스

```bash
curl "http://localhost:8000/api/v1/rag/recommend-datasets" \
  -H "Content-Type: application/json" \
  -d '{
    "debugUserTurnId": 1234,
    "prompt": "시계열 예측 연구에 적합한 데이터셋 추천",
    "topN": 5
  }'
```

### Response Code

| Code | Meaning |
| --- | --- |
| `200` | 추천 생성 및 DB 저장 성공 |
| `400` | 필수 파라미터 누락 또는 userTurnId 유효성 오류 |
| `404` | 추천 가능한 후보 데이터셋 없음 |
| `422` | 요청 본문 스키마 검증 실패 |
| `500` | 내부 서버 오류 |
| `502` | 외부 LLM/Embedding API 호출 실패 |

### Response Parameter

#### 200 Success

| Field | Type | Description |
| --- | --- | --- |
| `status` | integer | 상태 코드 |
| `message` | string | 추가 설명(한글) |
| `recommendationId` | integer | `dataset_recommendation.id` |
| `userTurnId` | integer | 사용자 turn ID |
| `prompt` | string | 입력 프롬프트 |
| `summaryReason` | string | 추천 결과 요약 사유 |
| `candidateCount` | integer | LLM에 전달된 후보 수(최대 20) |
| `llmModel` | string | 추천 생성 LLM 모델명 |
| `recommendedItems` | array | 최종 추천 목록 |

`recommendedItems[]` 항목

| Field | Type | Description |
| --- | --- | --- |
| `datasetId` | integer | 추천 데이터셋 ID |
| `rank` | integer | 추천 순위 |
| `suitabilityScore` | number | 적합도 점수(0~1) |
| `reason` | string | 추천 이유(한글) |

#### 4xx/5xx Fail

| Field | Type | Description |
| --- | --- | --- |
| `status` | integer | 상태 코드 |
| `message` | string | 추가 설명(한글) |

### Success Data Example

```json
{
  "status": 200,
  "message": "내부 데이터셋 추천을 생성했습니다.",
  "recommendationId": 41,
  "userTurnId": 1234,
  "prompt": "보행자 탐지 모델 학습용 한국어 이미지 데이터셋이 필요해.",
  "summaryReason": "컴퓨터비전 태스크와 한국어 맥락 적합성이 높은 데이터셋을 우선 추천했습니다.",
  "candidateCount": 20,
"llmModel": "gpt-5.2",
  "recommendedItems": [
    {
      "datasetId": 101,
      "rank": 1,
      "suitabilityScore": 0.932,
      "reason": "보행자 탐지 태스크와 도메인 일치도가 높습니다."
    },
    {
      "datasetId": 205,
      "rank": 2,
      "suitabilityScore": 0.881,
      "reason": "한국어 라벨 메타데이터가 제공되어 활용성이 높습니다."
    }
  ]
}
```

### Fail Data Example

`400`

```json
{
  "status": 400,
  "message": "userTurnId가 필요합니다. Spring 미구현 테스트 시 debugUserTurnId를 전달하세요."
}
```

`404`

```json
{
  "status": 404,
  "message": "추천 가능한 데이터셋 후보를 찾지 못했습니다."
}
```

`422`

```json
{
  "status": 422,
  "message": "요청 본문 검증에 실패했습니다."
}
```

`500`

```json
{
  "status": 500,
  "message": "추천 생성 중 내부 오류가 발생했습니다: 내부 처리 예외"
}
```

`502`

```json
{
  "status": 502,
  "message": "LLM API 호출 실패(status=502): upstream gateway error"
}
```

---

## 내부 전체 추천 이유 생성 API

- API 명칭: 내부 전체 추천 이유 생성
- Function: `mergeRecommendationReasons`
- Method: `POST`
- Path: `/api/v1/rag/merge-recommendation-reason`
- 호출 주체: Spring Boot 공개 채팅 API

### 동작 요약

1. `dataset_recommendation.reason_text`와 `openapi_recommendation.reason_text`를 userTurn 기준으로 조회
2. 필요 시 history를 함께 반영해 LLM(`gpt-5.2`)로 단일 assistant 문장/문단 생성
3. 결과를 `recommendation.merged_reason_text`에 저장하고 응답 반환

### 요청 필드(핵심)

- `userTurnId` 또는 `debugUserTurnId` (둘 중 하나 필수)
- `prompt` 또는 `message` (둘 중 하나 필수)
- `datasetRecommendationId`, `openapiRecommendationId` (미전달 시 userTurn 기준 최신 레코드 사용)
- `datasetReason`, `openapiReason` (미전달 시 DB 저장 reason_text 사용)
- `history` (선택)

### 응답 필드(핵심)

- `recommendationId`
- `datasetRecommendationId`
- `openapiRecommendationId`
- `mergedReasonText`
- `llmModel`

---

## 환경 변수

`.env.example`를 참고해 `.env`를 구성한다.

- `DATABASE_URL`
- `GMS_API_KEY`
- `RECOMMENDATION_EMBEDDING_URL`
- `RECOMMENDATION_CHAT_URL`
- `RECOMMENDATION_EMBEDDING_MODEL`
- `RECOMMENDATION_EMBEDDING_DIMENSIONS`
- `RECOMMENDATION_LLM_MODEL`
- `RECOMMENDATION_VECTOR_TOP_K` (기본 50)
- `RECOMMENDATION_LLM_CANDIDATE_K` (기본 20)
- `RECOMMENDATION_DEFAULT_TOP_N` (기본 10)
- `RECOMMENDATION_TEST_USER_TURN_ID` (Spring 미구현 테스트용)

## DB 검증 예시

추천 저장 결과 확인

```sql
SELECT
  id,
  user_turn_id,
  llm_model,
  status,
  created_at,
  updated_at
FROM dataset_recommendation
ORDER BY id DESC
LIMIT 5;
```

최근 추천의 추천 아이템(JSON) 확인

```sql
SELECT
  id,
  recommended_items_json,
  reason_text
FROM dataset_recommendation
ORDER BY id DESC
LIMIT 1;
```

---

## 0315 수정사항

아래는 2026-03-15 기준으로 dataset/openapi 충돌 정리 및 추천 로직 정합화를 위해 반영한 변경이다.

### 1) 설정/환경변수 통합

- 단일 키 정책 적용: `GEMINI_API_KEY`, `RECOMMENDATION_API_KEY` 제거 후 `GMS_API_KEY` 하나로 통합.
- 반영 파일
  - `api/.env.example`
  - `api/app/core/config.py`
  - `api/app/services/rag_service.py`
  - `api/app/services/dataset_recommendation_service.py`
  - `api/embed_openapi.py`
- `RECOMMENDATION_TEST_USER_TURN_ID`는 비어 있는 문자열(`=`)로 두면 Settings 파싱 에러가 날 수 있어, 미사용 시 미설정(줄 제거) 또는 정수값 사용.

### 2) 충돌 3개 파일 통합 정리

- `api/.env.example`
  - openapi + dataset 설정을 하나의 예시 파일로 통합.
  - `RAG_TOP_K=10`, recommendation 기본 파라미터(`*_TOP_K`, `*_CANDIDATE_K`, `*_MAX_TOKENS` 등) 반영.
- `api/app/core/config.py`
  - 키 필드 단일화(`api_key`) 및 recommendation 기본값 정리.
  - DB URL은 서비스별로 필요 시 `postgresql+asyncpg://` → `postgresql://` 변환 사용.
- `requirements.txt` (repo root)
  - FastAPI + crawler + worker가 공용으로 사용하는 단일 requirements 유지 + 버전 pin 고정.
  - `asyncpg==0.29.0`, `psycopg[binary]==3.2.12`, `httpx==0.28.1`.

### 3) 실제 .env 작성

- 요청받은 값으로 아래 로컬 실행용 파일 생성/채움 완료.
  - `api/.env`
  - `crawler/dataset/.env`
  - `crawler/openapi/.env`

### 4) openapi 크롤러 테스트 적재

- `datagokr` 제외하고 소량 적재 테스트 실행.
  - 실행 소스: `kakao`, `crypto_exchange`
  - 실행 결과: upsert 성공 (`kakao=75`, `crypto_exchange=40` 실행 로그 기준)
  - DB 확인 집계: `KAKAO_DEVELOPERS=58`, `UPBIT=15`, `BITHUMB=13`, `COINONE=12`
    (ON CONFLICT upsert 특성상 실행 건수와 최종 고유 건수는 다를 수 있음)

### 5) dataset 추천 개수 정책 openapi와 정합화

- 목표: 프롬프트에 개수 언급 시 반영, 미언급 시 기본 10, 최대 20.
- 반영 파일
  - `api/app/services/dataset_recommendation_service.py`
    - `_resolve_top_n()` 추가
    - `_extract_count_with_llm()` 추가
    - 최종 추천 개수 계산 로직 교체
  - `api/app/schemas/recommendation.py`
    - `topN` 제한 `le=10` → `le=20`

### 6) 검증 이력

- 설정 파싱 검증: `python -c "from app.core.config import settings; print(settings.app_name)"`
- 문법 검증: `python -m compileall app embed_openapi.py`
- 테스트: `python -m pytest` (현재 테스트 케이스 없음: 0 collected)
- LSP 진단: 변경 파일 기준 error 0 확인

### 7) 실제 실행 커맨드/결과 (재현용)

아래 커맨드는 2026-03-15에 실제 실행한 흐름이다.

환경/의존성 점검

```bash
cd crawler/openapi
python -m pip install -r ../../../requirements.txt
PYTHONPATH=src python -m openapi_ingest --list-sources
```

- 결과: `all, crypto_exchange, datagokr, game, kakao, kis, kobis, naver_map, odsay, tmap, tosspayments` 확인

소량 적재 테스트 (`datagokr` 제외)

```bash
cd crawler/openapi
PYTHONPATH=src python -m openapi_ingest --source kakao
PYTHONPATH=src python -m openapi_ingest --source crypto_exchange
```

- 실행 로그 기준
  - `kakao`: `collected_count=75`, `upserted_count=75`, `failed_count=0`
  - `crypto_exchange`: `collected_count=40`, `upserted_count=40`, `failed_count=0`

DB 확인 쿼리 실행 예시

```bash
cd crawler/openapi
python -c "import os,asyncio,asyncpg; from dotenv import load_dotenv; load_dotenv(); d=os.getenv('DATABASE_URL','').replace('postgresql+asyncpg://','postgresql://');
async def m():
 conn=await asyncpg.connect(d); rows=await conn.fetch(\"SELECT s.source_code, COUNT(*) AS cnt FROM open_api a JOIN openapi_source s ON s.id=a.openapi_source_id WHERE s.source_code IN ('KAKAO_DEVELOPERS','UPBIT','BITHUMB','COINONE') GROUP BY s.source_code ORDER BY s.source_code\"); print('\\n'.join(f'{r[0]}={r[1]}' for r in rows)); await conn.close();
asyncio.run(m())"
```

- DB 집계 결과: `KAKAO_DEVELOPERS=58`, `UPBIT=15`, `BITHUMB=13`, `COINONE=12`
- 참고: 실행 `upserted_count`와 최종 고유 건수는 `ON CONFLICT ... DO UPDATE` 때문에 다를 수 있다.

### 8) 운영/개발 주의사항 체크리스트

- [ ] `.env` 실값(키/토큰)은 로컬 전용으로 사용하고 저장소 커밋/공유 금지
- [ ] `api/.env`에서 `RECOMMENDATION_TEST_USER_TURN_ID`를 비워두지 말 것
  - 미사용이면 줄 자체를 제거
  - 사용이면 정수값 지정
- [ ] `datagokr` 실행 전 `crawler/openapi/.env`의 `DATAGOKR_CSV_PATH`를 실제 CSV 경로로 교체
- [ ] `DATABASE_URL` 스키마 혼용 시, asyncpg/psycopg 경로에서 변환 로직 적용 여부 확인
- [ ] docs 페이지가 404를 반환해도 수집기가 fallback 목록으로 계속 진행하는 소스가 있음(로그 확인 필요)

### 9) 다음 세션 바로 이어서 할 작업(TODO)

1. `datagokr` CSV 경로 설정 후 단독 실행
   - `PYTHONPATH=src python -m openapi_ingest --source datagokr --limit 100 --resume`
2. openapi 나머지 소스 스모크 적재
   - `game`, `kis`, `kobis`, `naver_map`, `odsay`, `tmap`, `tosspayments`
3. API 서버 추천 엔드포인트 실호출 검증
   - `POST /api/v1/rag/recommend-openapi`
   - `POST /api/v1/rag/recommend-datasets` (`topN` 미지정/지정 케이스 모두)
4. 결과 DB 확인
   - `dataset_recommendation` 최신 레코드의 `status`, `reason_text`, `recommended_items_json`
   - `open_api`, `openapi_source` 소스별 건수 변화

---

## 0316 변경사항 (Spring 연동 + Dataset JSON 안정화)

Spring 연동 흐름과 dataset 추천 JSON 파싱 안정화를 함께 반영했다.

### 연동 계약 변경점 (Spring 기준)

- Spring이 `conversation_turn(userTurn)`를 먼저 커밋한 뒤 FastAPI 추천 API를 호출한다.
- 추천 호출 순서는 `recommend-datasets -> recommend-open-apis -> merge-recommendation-reason` 순차 게이트다.
- 선행 단계 실패 시 후속 단계는 호출되지 않는다.

### Dataset 추천 JSON 출력 안정화

`dataset_recommendation_service`에 아래 변경을 반영했다.

1. Structured Output 강화
   - `response_format: json_object` -> `response_format: json_schema + strict=true`
   - `summaryReason`, `recommendedItems` 필드/타입/필수값/개수(topN) 제약을 스키마에 명시

2. 프롬프트 충돌 제거
   - JSON 외 부가 텍스트(코드블록, 서론/결론) 출력 금지 지시를 명확히 강화

3. 파서 내구성 보강
   - 코드블록 제거
   - 첫 JSON 객체 추출 강화
   - 경미한 trailing comma(`,}`/`,]`) 보정 후 파싱

### 호출 순서 (Spring 기준)

```text
1) /api/v1/rag/recommend-datasets
2) /api/v1/rag/recommend-open-apis
3) /api/v1/rag/merge-recommendation-reason
```

### FastAPI 측 유의사항

- `merge-recommendation-reason`는 `datasetRecommendationId`, `openapiRecommendationId`, 각 reason 입력에 의존한다.
- dataset 단계가 실패하면 openapi/merge는 호출되지 않는다(순차 게이트).
- `userTurnId` 기반 조회/검증 로직은 기존 그대로 유지한다.
