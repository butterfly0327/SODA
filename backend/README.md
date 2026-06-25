# Chat/Conversation API Guide (MVP)

## 1) 채팅 메시지 전송 및 추천 생성

### Header
- `Authorization: Bearer <accessToken>`
- `Content-Type: application/json`

### request parameter
- Body
  - `conversationId` (Long, optional): 없으면 신규 대화 생성, 있으면 기존 대화 이어쓰기
  - `message` (String, required): 사용자 질문

### response code
- `200`: 채팅 메시지 저장 + 추천 생성 + assistant 턴 저장 성공
- `400`: 잘못된 요청(메시지 누락/공백, 잘못된 conversationId)
- `401`: 인증 실패
- `403`: 본인 대화가 아닌 경우
- `404`: 대화를 찾을 수 없는 경우
- `502`: FastAPI 내부 연동 실패

### response parameter
- `status` (int): HTTP 상태 코드
- `message` (String): 처리 결과 설명
- `data` (Object)
  - `conversationId` (Long)
  - `userTurnId` (Long)
  - `assistantTurnId` (Long)
  - `assistantMessage` (String)
  - `mergedReason` (String)
  - `datasetRecommendations` (JSON)
  - `openApiRecommendations` (JSON)

### success data example
```json
{
  "status": 200,
  "message": "채팅 메시지 전송 및 추천 생성이 완료되었습니다.",
  "data": {
    "conversationId": 12,
    "userTurnId": 101,
    "assistantTurnId": 102,
    "assistantMessage": "요청하신 조건에 맞는 데이터셋과 Open API를 추천드립니다.",
    "mergedReason": "질문 맥락을 기준으로 데이터셋과 Open API를 함께 고려한 통합 추천입니다.",
    "datasetRecommendations": [
      {
        "id": 88,
        "title": "기상 데이터셋"
      }
    ],
    "openApiRecommendations": [
      {
        "id": 33,
        "name": "날씨 예보 API"
      }
    ]
  }
}
```

### fail data example
```json
{
  "status": 400,
  "message": "메시지는 비어 있을 수 없습니다."
}
```

```json
{
  "status": 401,
  "message": "유효하지 않은 사용자입니다."
}
```

```json
{
  "status": 403,
  "message": "해당 대화에 접근할 수 없습니다."
}
```

```json
{
  "status": 404,
  "message": "대화를 찾을 수 없습니다."
}
```

```json
{
  "status": 502,
  "message": "추천 서버와 통신에 실패했습니다."
}
```

---

## 2) 대화 목록 조회

### Header
- `Authorization: Bearer <accessToken>`

### request parameter
- Query Parameter: 없음

### response code
- `200`: 목록 조회 성공
- `401`: 인증 실패

### response parameter
- `status` (int)
- `message` (String)
- `data` (Array)
  - `conversationId` (Long)
  - `title` (String)
  - `createdAt` (String, ISO datetime)
  - `updatedAt` (String, ISO datetime)

### success data example
```json
{
  "status": 200,
  "message": "대화 목록 조회가 완료되었습니다.",
  "data": [
    {
      "conversationId": 12,
      "title": "날씨 예측 모델 추천",
      "createdAt": "2026-03-12T11:20:10",
      "updatedAt": "2026-03-12T11:24:53"
    }
  ]
}
```

### fail data example
```json
{
  "status": 401,
  "message": "유효하지 않은 사용자입니다."
}
```

---

## 3) 대화 상세 조회

### Header
- `Authorization: Bearer <accessToken>`

### request parameter
- Path Variable
  - `conversationId` (Long, required)

### response code
- `200`: 상세 조회 성공
- `401`: 인증 실패
- `403`: 본인 대화가 아닌 경우
- `404`: 대화를 찾을 수 없는 경우

### response parameter
- `status` (int)
- `message` (String)
- `data` (Object)
  - `conversationId` (Long)
  - `title` (String)
  - `turns` (Array)
    - `turnId` (Long)
    - `turnOrder` (int)
    - `role` (String)
    - `content` (String)
    - `responseTimeMs` (int|null)
    - `createdAt` (String)
  - `recommendations` (Array)
    - `recommendationId` (Long)
    - `userTurnId` (Long)
    - `assistantTurnId` (Long|null)
    - `status` (String)
    - `mergedReason` (String)
    - `datasetReason` (String)
    - `openApiReason` (String)
    - `datasetRecommendations` (JSON)
    - `openApiRecommendations` (JSON)

### success data example
```json
{
  "status": 200,
  "message": "대화 상세 조회가 완료되었습니다.",
  "data": {
    "conversationId": 12,
    "title": "날씨 예측 모델 추천",
    "turns": [
      {
        "turnId": 101,
        "turnOrder": 1,
        "role": "USER",
        "content": "기상 데이터 분석용 리소스를 추천해줘",
        "responseTimeMs": null,
        "createdAt": "2026-03-12T11:20:10"
      },
      {
        "turnId": 102,
        "turnOrder": 2,
        "role": "ASSISTANT",
        "content": "요청하신 조건에 맞는 데이터셋과 Open API를 추천드립니다.",
        "responseTimeMs": 742,
        "createdAt": "2026-03-12T11:20:11"
      }
    ],
    "recommendations": [
      {
        "recommendationId": 55,
        "userTurnId": 101,
        "assistantTurnId": 102,
        "status": "SUCCESS",
        "mergedReason": "데이터 가용성과 활용 목적을 기준으로 통합 추천했습니다.",
        "datasetReason": "시계열 기반 기상 데이터셋이 적합합니다.",
        "openApiReason": "실시간 예보 조회가 가능한 API를 우선 추천합니다.",
        "datasetRecommendations": [
          {
            "id": 88,
            "title": "기상 데이터셋"
          }
        ],
        "openApiRecommendations": [
          {
            "id": 33,
            "name": "날씨 예보 API"
          }
        ]
      }
    ]
  }
}
```

### fail data example
```json
{
  "status": 401,
  "message": "유효하지 않은 사용자입니다."
}
```

```json
{
  "status": 403,
  "message": "해당 대화에 접근할 수 없습니다."
}
```

```json
{
  "status": 404,
  "message": "대화를 찾을 수 없습니다."
}
```

## 4) 대화 삭제

### Header
- `Authorization: Bearer <accessToken>`

### request parameter
- Path Variable
  - `conversationId` (Long, required)

### response code
- `200`: 삭제 성공
- `401`: 인증 실패
- `403`: 본인 대화가 아닌 경우
- `404`: 대화를 찾을 수 없는 경우

### response parameter
- `status` (int)
- `message` (String)
- `data` (null)

### success data example
```json
{
  "status": 200,
  "message": "대화 삭제가 완료되었습니다.",
  "data": null
}
```

### fail data example
```json
{
  "status": 401,
  "message": "유효하지 않은 사용자입니다."
}
```

```json
{
  "status": 403,
  "message": "해당 대화에 접근할 수 없습니다."
}
```

```json
{
  "status": 404,
  "message": "대화를 찾을 수 없습니다."
}
```

---

## 0316 변경사항 (연동 안정화)

채팅 전송 API(`POST /v1/chat/messages`)의 FastAPI 연동 안정화를 위해 아래 항목을 반영했다.

### 핵심 변경

1. 커밋 경계 분리(After-commit)
   - 1차 트랜잭션: `conversation`, `userTurn` 저장 후 커밋
   - 커밋 이후: FastAPI 추천 API 호출
   - 2차 트랜잭션: 추천/assistant/recommendation 저장

2. 추천 API 호출 순서 변경(순차 게이트)
   - `recommend-datasets` 성공 후 `recommend-open-apis` 호출
   - 두 단계 모두 성공 시 `merge-recommendation-reason` 호출
   - 선행 단계 실패 시 후속 단계는 호출하지 않음

3. Spring WebClient 타임아웃 상향
   - FastAPI 연동 응답 타임아웃을 `15초 -> 180초`로 상향
   - 장시간 추론 구간에서 Spring이 먼저 타임아웃으로 끊는 문제를 완화

### 호출 흐름

```text
POST /v1/chat/messages
  -> [Tx-1] conversation/userTurn 저장 + commit
  -> [After commit] FastAPI #1(recommend-datasets)
  -> [After #1 success] FastAPI #2(recommend-open-apis)
  -> [After #1,#2 success] FastAPI #3(merge-recommendation-reason)
  -> [Tx-2] dataset/openapi/recommendation/assistantTurn 저장
  -> API 응답 반환
```

### 실패 처리

- #1 실패 시 #2/#3은 호출하지 않는다.
- #2 실패 시 #3은 호출하지 않는다.
- 실패 시 기존과 동일하게 FastAPI 연동 실패(`502`)로 응답한다.

### 반영 파일

- `backend/src/main/java/ssafy/E105/domain/chat/service/ChatService.java`
- `backend/src/main/java/ssafy/E105/global/config/WebClientConfig.java`

---

## 0317 수정사항 (게시판 API 추가)

### 1) 게시글 작성

| 구분 | 내용 |
|---|---|
| Header | `Authorization: Bearer <accessToken>`, `Content-Type: application/json` |
| API Path | `POST /api/v1/posts` |
| request parameter | Body: `title`(String, required), `content`(String, optional), `datasetIds`(Long[], optional), `openApiIds`(Long[], optional) |
| response code | `201` 생성 성공, `400` 잘못된 요청, `401` 인증 실패 |
| response parameter | `status`(int), `message`(String), `data.postId`(Long), `data.createdAt`(String) |
| success data example | ```json
{
  "status": 201,
  "message": "게시글이 등록되었습니다.",
  "data": {
    "postId": 101,
    "createdAt": "2026-03-17T14:10:00"
  }
}
``` |
| fail data example | ```json
{
  "status": 400,
  "message": "게시글 제목은 필수입니다."
}
```
```json
{
  "status": 401,
  "message": "유효하지 않은 토큰입니다."
}
``` |

### 2) 게시글 목록 조회

| 구분 | 내용 |
|---|---|
| Header | `Content-Type: application/json` |
| API Path | `GET /api/v1/posts` |
| request parameter | Query: `page`(int, default 0), `size`(int, default 10), `sort`(LATEST\|VIEW_COUNT\|FAVORITE, default LATEST) |
| response code | `200` 조회 성공, `400` 잘못된 요청 |
| response parameter | `status`(int), `message`(String), `data.content[].postId`, `data.content[].authorId`, `data.content[].name`(작성자 이름), `data.content[].title`, `data.content[].viewCount`, `data.content[].favorite`, `data.content[].createdAt`, `data.content[].updatedAt`, `data.page`, `data.size`, `data.totalElements`, `data.totalPages`, `data.sort` |
| success data example | ```json
{
  "status": 200,
  "message": "게시글 목록 조회가 완료되었습니다.",
  "data": {
    "content": [
      {
        "postId": 101,
        "authorId": 7,
        "name": "홍길동",
        "title": "기상 데이터 분석 팁 공유",
        "viewCount": 55,
        "favorite": 8,
        "createdAt": "2026-03-17T14:10:00",
        "updatedAt": "2026-03-17T14:10:00"
      }
    ],
    "page": 0,
    "size": 10,
    "totalElements": 1,
    "totalPages": 1,
    "sort": "LATEST"
  }
}
``` |
| fail data example | ```json
{
  "status": 400,
  "message": "잘못된 요청입니다."
}
``` |

### 3) 게시글 상세 조회

| 구분 | 내용 |
|---|---|
| Header | `Content-Type: application/json` |
| API Path | `GET /api/v1/posts/{postId}` |
| request parameter | Path: `postId`(Long, required), Query: `increaseViewCount`(boolean, default true) |
| response code | `200` 조회 성공, `404` 게시글 없음 |
| response parameter | `status`(int), `message`(String), `data.postId`, `data.authorId`, `data.name`(작성자 이름), `data.title`, `data.content`, `data.viewCount`, `data.favorite`, `data.datasetReferences[]`, `data.openApiReferences[]`, `data.createdAt`, `data.updatedAt` |
| success data example | ```json
{
  "status": 200,
  "message": "게시글 상세 조회가 완료되었습니다.",
  "data": {
    "postId": 101,
    "authorId": 7,
    "name": "홍길동",
    "title": "기상 데이터 분석 팁 공유",
    "content": "데이터 전처리 순서를 공유합니다.",
    "viewCount": 56,
    "favorite": 8,
    "datasetReferences": [
      {
        "id": 88,
        "name": "기상 데이터셋"
      }
    ],
    "openApiReferences": [
      {
        "id": 33,
        "name": "날씨 예보 API"
      }
    ],
    "createdAt": "2026-03-17T14:10:00",
    "updatedAt": "2026-03-17T14:15:00"
  }
}
``` |
| fail data example | ```json
{
  "status": 404,
  "message": "게시글을 찾을 수 없습니다."
}
``` |

### 4) 게시글 수정

| 구분 | 내용 |
|---|---|
| Header | `Authorization: Bearer <accessToken>`, `Content-Type: application/json` |
| API Path | `PATCH /api/v1/posts/{postId}` |
| request parameter | Path: `postId`(Long, required), Body: `title`(String, optional), `content`(String, optional), `datasetIds`(Long[], optional), `openApiIds`(Long[], optional) |
| response code | `200` 수정 성공, `400` 잘못된 요청, `401` 인증 실패, `403` 권한 없음, `404` 게시글 없음 |
| response parameter | `status`(int), `message`(String), `data.postId`(Long), `data.updatedAt`(String) |
| success data example | ```json
{
  "status": 200,
  "message": "게시글 수정이 완료되었습니다.",
  "data": {
    "postId": 101,
    "updatedAt": "2026-03-17T14:20:00"
  }
}
``` |
| fail data example | ```json
{
  "status": 400,
  "message": "게시글 제목은 필수입니다."
}
```
```json
{
  "status": 401,
  "message": "유효하지 않은 토큰입니다."
}
```
```json
{
  "status": 403,
  "message": "본인이 작성한 게시글만 수정/삭제할 수 있습니다."
}
```
```json
{
  "status": 404,
  "message": "게시글을 찾을 수 없습니다."
}
``` |

### 5) 게시글 삭제

| 구분 | 내용 |
|---|---|
| Header | `Authorization: Bearer <accessToken>` |
| API Path | `DELETE /api/v1/posts/{postId}` |
| request parameter | Path: `postId`(Long, required) |
| response code | `200` 삭제 성공, `401` 인증 실패, `403` 권한 없음, `404` 게시글 없음 |
| response parameter | `status`(int), `message`(String), `data`(null) |
| success data example | ```json
{
  "status": 200,
  "message": "게시글 삭제가 완료되었습니다.",
  "data": null
}
``` |
| fail data example | ```json
{
  "status": 401,
  "message": "유효하지 않은 토큰입니다."
}
```
```json
{
  "status": 403,
  "message": "본인이 작성한 게시글만 수정/삭제할 수 있습니다."
}
```
```json
{
  "status": 404,
  "message": "게시글을 찾을 수 없습니다."
}
``` |

---

## 0318 수정사항 (Hibernate 설정 및 게시글 API 검증)

### 변경 사항

| 구분 | 내용 |
|---|---|
| Hibernate 설정 | `backend/src/main/resources/application.yml`의 `spring.jpa.properties.hibernate`에 `globally_quoted_identifiers: true` 추가 |
| 실행 환경 설정 | `backend/.env`에 `SPRING_JPA_HIBERNATE_DDL_AUTO=none` 추가 |
| 적용 목적 | PostgreSQL에서 `user` 테이블 식별자 충돌(`from user ...`)을 피하기 위해 Hibernate가 식별자를 인용(`"user"`)하도록 설정 |

### 검증 결과 (Docker + .env)

| 항목 | 결과 |
|---|---|
| Spring Boot 기동 | 성공 (`docker-compose.dev` + `backend/.env`) |
| DB 연결 | 성공 (`HikariPool connection` 확인) |
| 게시글 작성 API | 성공 (`POST /api/v1/posts` -> 201) |
| 게시글 목록 조회 API | 성공 (`GET /api/v1/posts` -> 200) |
| 게시글 상세 조회 API | 성공 (`GET /api/v1/posts/{postId}` -> 200, `view_count` 증가 확인) |
| 게시글 수정 API | 성공 (`PATCH /api/v1/posts/{postId}` -> 200) |
| 게시글 삭제 API | 성공 (`DELETE /api/v1/posts/{postId}` -> 200, 소프트 삭제 확인) |

### 참고

| 구분 | 내용 |
|---|---|
| 영향 범위 | `globally_quoted_identifiers`는 Hibernate가 생성하는 SQL 식별자에 적용되며, `nativeQuery=true` 쿼리에는 직접 적용되지 않음 |
| 주의 사항 | `SPRING_JPA_HIBERNATE_DDL_AUTO=none` 설정 시 스키마 검증(`validate`)은 수행되지 않으므로, 스키마 불일치는 런타임에서 발견될 수 있음 |

---

## 0319 북마크 api추천

### 1) 북마크 추가

#### 1. Header
- `Authorization: Bearer <accessToken>`
- `Content-Type: application/json`

#### 2. request parameter

| 파라미터명 | 타입 | 설명 |
|---|---|---|
| `resourceType` | String (`DATASET` \| `OPEN_API`) | 북마크 대상 리소스 타입 |
| `resourceId` | Long | 북마크 대상 리소스 ID |

#### 3. response code

| 코드 | 설명 |
|---|---|
| `201` | 북마크 생성 성공 |
| `400` | 잘못된 요청 값 (resourceType/resourceId 누락 또는 형식 오류) |
| `401` | 인증 실패 또는 유효하지 않은 사용자 |
| `404` | 대상 리소스를 찾을 수 없음 |
| `409` | 이미 북마크한 리소스 |

#### 4. response parameter

| 파라미터명 | 타입 | 설명 |
|---|---|---|
| `status` | int | HTTP 상태 코드 |
| `message` | String | 처리 결과 메시지 |
| `data.bookmarkId` | Long | 생성된 북마크 ID |
| `data.resourceType` | String | 북마크된 리소스 타입 |
| `data.resourceId` | Long | 북마크된 리소스 ID |
| `data.bookmarkedAt` | String (ISO datetime) | 북마크 생성 시각 |

#### 5. success data example

```json
{
  "status": 201,
  "message": "북마크가 등록되었습니다.",
  "data": {
    "bookmarkId": 101,
    "resourceType": "DATASET",
    "resourceId": 88,
    "bookmarkedAt": "2026-03-19T15:30:00"
  }
}
```

#### 6. fail data example

```json
{
  "status": 400,
  "message": "잘못된 요청입니다."
}
```

```json
{
  "status": 401,
  "message": "유효하지 않은 사용자입니다."
}
```

```json
{
  "status": 404,
  "message": "존재하지 않는 리소스입니다."
}
```

---

```json
{
  "status": 409,
  "message": "이미 북마크한 리소스입니다."
}
```

### 2) 북마크 삭제

#### 1. Header
- `Authorization: Bearer <accessToken>`

#### 2. request parameter

| 파라미터명 | 타입 | 설명 |
|---|---|---|
| `bookmarkId` | Long (Path Variable) | 삭제할 북마크 ID |

#### 3. response code

| 코드 | 설명 |
|---|---|
| `200` | 북마크 삭제 성공(소프트 삭제) |
| `401` | 인증 실패 또는 유효하지 않은 사용자 |
| `403` | 본인 북마크가 아님 |
| `404` | 북마크를 찾을 수 없음 |

#### 4. response parameter

| 파라미터명 | 타입 | 설명 |
|---|---|---|
| `status` | int | HTTP 상태 코드 |
| `message` | String | 처리 결과 메시지 |
| `data` | null | 삭제 API는 본문 데이터 없음 |

#### 5. success data example

```json
{
  "status": 200,
  "message": "북마크 삭제가 완료되었습니다.",
  "data": null
}
```

#### 6. fail data example

```json
{
  "status": 401,
  "message": "유효하지 않은 사용자입니다."
}
```

```json
{
  "status": 403,
  "message": "본인이 등록한 북마크만 삭제할 수 있습니다."
}
```

```json
{
  "status": 404,
  "message": "북마크를 찾을 수 없습니다."
}
```

---

## 0320 수정사항 (채팅 카드/상세 조회 API 명세 추가)

> 본 항목은 채팅 결과 화면 전용 API 명세 초안입니다.
> 기존 `/api/v1/resources*` 계약과 분리된 `chat-resources` 전용 계약을 기준으로 작성했습니다.
> 외부 호출 경로는 `/api/v1/chat-resources/*`를 기준으로 작성했으며, nginx에서 `/api` prefix 제거 후 백엔드 내부 `/v1/chat-resources/*`로 라우팅되는 전제를 따릅니다.

### 공통 규약

| 구분 | 내용 |
|---|---|
| Base Path | 외부 `/api/v1/chat-resources` / 내부 `/v1/chat-resources` |
| Header | `Authorization: Bearer <accessToken>`, `Content-Type: application/json` |
| 응답 형식 | `ApiResponse<T>` (`status`, `message`, `data`) |
| 점수 정책 | `recommendationScore`만 반환 (리뷰 점수 미반환) |
| 출처 정책 | `sourceName`만 반환 (`dataset_sources.source_name` / `openapi_sources.source_name`) |

### 1) 채팅 추천 카드 배치 조회

| 구분 | 내용 |
|---|---|
| API Path | 외부 `POST /api/v1/chat-resources/cards/batch` / 내부 `POST /v1/chat-resources/cards/batch` |
| 목적 | 채팅 추천 카드 렌더링용 공통 필드 일괄 조회 |
| request parameter | Body: `items`(Array, required), `items[].resourceType`(String: `DATASET`\|`OPEN_API`, required), `items[].resourceId`(Long, required), `items[].recommendationScore`(Double, required), `items[].rank`(Integer, optional) |
| response code | `200` 조회 성공(부분 실패 포함), `400` 잘못된 요청, `401` 인증 실패, `403` 권한 없음, `500` 서버 오류 |
| 카드 반환 정책 | dataset/openapi 공통 필드만 반환. 타입 전용 필드(`metrics`, `authType`, `category` 등) 미반환 |

#### response parameter

| 파라미터명 | 타입 | 설명 |
|---|---|---|
| `status` | int | HTTP 상태 코드 |
| `message` | String | 처리 결과 메시지 |
| `data.cards` | Array | 카드 결과 목록(요청 순서 기준) |
| `data.cards[].id` | Long | 리소스 ID |
| `data.cards[].name` | String | 이름(`datasets.title` / `open_apis.name`) |
| `data.cards[].type` | String | `DATASET` / `OPEN_API` |
| `data.cards[].updatedAt` | String | 최근 업데이트일 (`datasets.updated_at` / `open_apis.updated_at`) |
| `data.cards[].isFree` | Boolean | 무료 여부 (dataset은 `payment_required` 반전) |
| `data.cards[].sourceName` | String | 출처 사이트명 |
| `data.cards[].recommendationScore` | Double | 추천 생성 점수 |
| `data.cards[].rank` | Integer\|null | 요청 rank 값(선택) |
| `data.errors` | Array | 조회 실패 항목 목록 |
| `data.errors[].resourceType` | String | 실패 타입 |
| `data.errors[].resourceId` | Long | 실패 ID |
| `data.errors[].code` | String | 오류 코드 (`RESOURCE_NOT_FOUND` 등) |
| `data.errors[].message` | String | 오류 메시지 |

#### success data example

```json
{
  "status": 200,
  "message": "채팅 카드 배치 조회가 완료되었습니다.",
  "data": {
    "cards": [
      {
        "id": 101,
        "name": "서울시 공공데이터",
        "type": "DATASET",
        "updatedAt": "2026-03-15T12:30:00",
        "isFree": true,
        "sourceName": "서울열린데이터광장",
        "recommendationScore": 0.932,
        "rank": 1
      },
      {
        "id": 55,
        "name": "Weather API",
        "type": "OPEN_API",
        "updatedAt": "2026-03-11T08:10:00",
        "isFree": false,
        "sourceName": "공공데이터포털",
        "recommendationScore": 0.874,
        "rank": 2
      }
    ],
    "errors": []
  }
}
```

#### fail data example

```json
{
  "status": 400,
  "message": "잘못된 요청입니다."
}
```

```json
{
  "status": 401,
  "message": "유효하지 않은 토큰입니다."
}
```

---

### 2) 채팅 추천 상세 조회

| 구분 | 내용 |
|---|---|
| API Path | 외부 `GET /api/v1/chat-resources/{resourceType}/{resourceId}` / 내부 `GET /v1/chat-resources/{resourceType}/{resourceId}` |
| 목적 | 카드 클릭 시 우측 상세 패널 데이터 조회 |
| request parameter | Path: `resourceType`(String: `DATASET`\|`OPEN_API`, required), `resourceId`(Long, required), Query: `recommendationScore`(Double, required) |
| response code | `200` 조회 성공, `400` 잘못된 요청, `401` 인증 실패, `403` 권한 없음, `404` 리소스 없음, `500` 서버 오류 |
| originUrl 규칙 | dataset: `datasets.landing_url`, openapi: `open_apis.docs_url` |

#### response parameter (공통)

| 파라미터명 | 타입 | 설명 |
|---|---|---|
| `status` | int | HTTP 상태 코드 |
| `message` | String | 처리 결과 메시지 |
| `data.id` | Long | 리소스 ID |
| `data.name` | String | 리소스명 |
| `data.type` | String | `DATASET` / `OPEN_API` |
| `data.updatedAt` | String | 최근 업데이트일 |
| `data.isFree` | Boolean | 무료 여부 |
| `data.sourceName` | String | 출처 사이트명 |
| `data.recommendationScore` | Double | 추천 생성 점수 |
| `data.originUrl` | String | 원 주소 (`landing_url` / `docs_url`) |
| `data.datasetDetail` | Object\|null | dataset 전용 상세 |
| `data.openApiDetail` | Object\|null | openapi 전용 상세 |

#### response parameter (`datasetDetail`)

| 파라미터명 | 타입 | 설명 |
|---|---|---|
| `descriptionLong` | String | 긴 설명 (`datasets.description_long`) |
| `schemaJson` | JSON | 스키마 (`datasets.schema_json`) |
| `datasetSizeBytes` | Long | 용량 |
| `rowCount` | Long | 행 수 |
| `metrics` | JSON | 지표 (`datasets.metrics_json`) |
| `licenseName` | String | 라이선스명 |
| `classification` | String[] | 분류 (`datasets.domains` 매핑) |
| `tags` | String[] | 태그 |
| `languages` | String[] | 언어 |

> dataset detail 제외 필드: `descriptionShort`, `licenseUrl`, `tasks`

#### response parameter (`openApiDetail`)

| 파라미터명 | 타입 | 설명 |
|---|---|---|
| `description` | String | 설명 |
| `authType` | String | 인증 방식 |
| `category` | String | 카테고리 |
| `tags` | String[] | 태그 |
| `rateLimit` | Integer | 초당 제한 |
| `dailyLimit` | Integer | 일일 제한 |
| `pricingNote` | String | 과금 메모 |
| `responseFormat` | String | 응답 형식 |
| `avgResponseTime` | Double | 평균 응답 시간 |
| `responseSchema` | JSON | 응답 스키마 |

> openapi detail 제외 필드: `baseUrl`, `docsUrl` (직접 필드 미노출, `originUrl`만 제공)

#### success data example (dataset)

```json
{
  "status": 200,
  "message": "채팅 상세 조회가 완료되었습니다.",
  "data": {
    "id": 101,
    "name": "서울시 공공데이터",
    "type": "DATASET",
    "updatedAt": "2026-03-15T12:30:00",
    "isFree": true,
    "sourceName": "서울열린데이터광장",
    "recommendationScore": 0.932,
    "originUrl": "https://data.seoul.go.kr/data/...",
    "datasetDetail": {
      "descriptionLong": "긴 설명 ...",
      "schemaJson": { "fields": [] },
      "datasetSizeBytes": 123456789,
      "rowCount": 450000,
      "metrics": {
        "downloadCount": 120340,
        "viewCount": 987654
      },
      "licenseName": "CC BY 4.0",
      "classification": ["교통", "도시"],
      "tags": ["버스", "정류장"],
      "languages": ["ko"]
    },
    "openApiDetail": null
  }
}
```

#### success data example (openapi)

```json
{
  "status": 200,
  "message": "채팅 상세 조회가 완료되었습니다.",
  "data": {
    "id": 55,
    "name": "Weather API",
    "type": "OPEN_API",
    "updatedAt": "2026-03-11T08:10:00",
    "isFree": false,
    "sourceName": "공공데이터포털",
    "recommendationScore": 0.874,
    "originUrl": "https://www.data.go.kr/data/....do",
    "datasetDetail": null,
    "openApiDetail": {
      "description": "날씨 조회 API",
      "authType": "API_KEY",
      "category": "기상",
      "tags": ["날씨", "기온"],
      "rateLimit": 10,
      "dailyLimit": 10000,
      "pricingNote": "일부 유료 플랜 존재",
      "responseFormat": "JSON",
      "avgResponseTime": 220.5,
      "responseSchema": { "type": "object" }
    }
  }
}
```

#### fail data example

```json
{
  "status": 404,
  "message": "존재하지 않는 리소스입니다."
}
```

---

### 0320 적용 기준 요약

| 항목 | 적용 내용 |
|---|---|
| 카드 필드 | 공통 필드만 반환 |
| 출처 | `sourceName`만 반환 |
| 점수 | `recommendationScore`만 반환 |
| OpenAPI 최근 업데이트일 | `open_apis.updated_at` 고정 |
| 원 주소 | dataset=`landing_url`, openapi=`docs_url` |
| dataset detail | `metrics` 포함, `classification(domains)` 사용, `tasks`/`descriptionShort`/`licenseUrl` 제외 |
| openapi detail | `baseUrl`/`docsUrl` 직접 필드 제외 (`originUrl`만 사용) |

---

## 0321 수정사항 (채팅 최적화)

> 본 항목은 채팅 요청-응답을 동기 완료형에서 비동기 처리형으로 전환하기 위한 API 명세 초안입니다.
> 외부 호출 경로는 `/api/v1/*`를 기준으로 작성했으며, nginx에서 `/api` prefix 제거 후 백엔드 내부 `/v1/*`로 라우팅되는 전제를 따릅니다.

### 공통 규약

| 구분 | 내용 |
|---|---|
| Base Path | `/api/v1` |
| Header | `Authorization: Bearer <accessToken>`, `Content-Type: application/json` |
| 응답 형식 | `ApiResponse<T>` (`status`, `message`, `data`) |
| 상태값 | `PENDING` / `RUNNING` / `SUCCESS` / `FAILED` |
| 상태 조회 방식 | `recommendationId` 기반 폴링 |

### 1) 새로 추가된 API 명세

#### 1-1) 추천 상태 조회

| 구분 | 내용 |
|---|---|
| API Path | `GET /api/v1/recommendations/{recommendationId}` |
| 목적 | 추천 생성 진행 상태 및 최종 결과 조회 |
| request parameter | Path: `recommendationId`(Long, required) |
| response code | `200` 조회 성공, `401` 인증 실패, `403` 권한 없음, `404` 추천 작업 없음, `500` 서버 오류 |
| 조회 정책 | `RUNNING`/`PENDING` 시 결과 필드는 `null` 또는 빈 배열, `SUCCESS`/`FAILED` 시 결과 또는 오류 정보 반환 |

##### response parameter

| 파라미터명 | 타입 | 설명 |
|---|---|---|
| `status` | int | HTTP 상태 코드 |
| `message` | String | 처리 결과 메시지 |
| `data.recommendationId` | Long | 추천 작업 ID |
| `data.conversationId` | Long | 대화 ID |
| `data.userTurnId` | Long | 사용자 턴 ID |
| `data.assistantTurnId` | Long\|null | assistant 턴 ID(완료 전 null) |
| `data.status` | String | `PENDING` / `RUNNING` / `SUCCESS` / `FAILED` |
| `data.mergedReason` | String\|null | 병합 추천 사유 |
| `data.datasetRecommendations` | JSON | dataset 추천 목록 |
| `data.openApiRecommendations` | JSON | openapi 추천 목록 |
| `data.errorSummary` | String\|null | 실패 요약 사유 |
| `data.updatedAt` | String | 상태 최종 변경 시각 |

##### success data example (RUNNING)

```json
{
  "status": 200,
  "message": "추천 상태 조회가 완료되었습니다.",
  "data": {
    "recommendationId": 9001,
    "conversationId": 12,
    "userTurnId": 101,
    "assistantTurnId": null,
    "status": "RUNNING",
    "mergedReason": null,
    "datasetRecommendations": [],
    "openApiRecommendations": [],
    "errorSummary": null,
    "updatedAt": "2026-03-21T15:10:03"
  }
}
```

##### success data example (SUCCESS)

```json
{
  "status": 200,
  "message": "추천 상태 조회가 완료되었습니다.",
  "data": {
    "recommendationId": 9001,
    "conversationId": 12,
    "userTurnId": 101,
    "assistantTurnId": 102,
    "status": "SUCCESS",
    "mergedReason": "질문 맥락을 기준으로 데이터셋과 Open API를 통합 추천했습니다.",
    "datasetRecommendations": [
      {
        "datasetId": 88,
        "rank": 1,
        "suitabilityScore": 0.932,
        "reason": "시계열 기상 분석 목적에 적합합니다."
      }
    ],
    "openApiRecommendations": [
      {
        "openApiId": 33,
        "name": "날씨 예보 API",
        "score": 0.874
      }
    ],
    "errorSummary": null,
    "updatedAt": "2026-03-21T15:10:08"
  }
}
```

##### fail data example

```json
{
  "status": 404,
  "message": "추천 작업을 찾을 수 없습니다."
}
```

---

### 2) 수정된 API 명세

#### 2-1) 채팅 메시지 전송 (`POST /api/v1/chat/messages`)

| 구분 | 기존 | 변경 |
|---|---|---|
| 처리 방식 | 동기 완료 후 응답 | 작업 접수 즉시 응답 |
| 성공 코드 | `200` | `202` |
| 응답 의미 | 추천 결과 포함 최종 응답 | 추천 생성 시작 응답 |

##### 변경 후 response parameter

| 파라미터명 | 타입 | 설명 |
|---|---|---|
| `status` | int | HTTP 상태 코드 |
| `message` | String | 처리 결과 메시지 |
| `data.conversationId` | Long | 대화 ID |
| `data.userTurnId` | Long | 사용자 턴 ID |
| `data.recommendationId` | Long | 추천 상태 조회 ID |
| `data.status` | String | 초기 상태(`PENDING`) |

##### success data example

```json
{
  "status": 202,
  "message": "채팅 메시지가 접수되었습니다. 추천 생성이 진행 중입니다.",
  "data": {
    "conversationId": 12,
    "userTurnId": 101,
    "recommendationId": 9001,
    "status": "PENDING"
  }
}
```

#### 2-2) 대화 상세 조회 (`GET /api/v1/conversations/{conversationId}`)

| 구분 | 기존 | 변경 |
|---|---|---|
| 추천 상태 해석 | 완료 데이터 중심 | 진행 중 상태(`PENDING`/`RUNNING`) 노출 |
| `assistantTurnId` | 대부분 존재 | 진행 중에는 `null` 허용 |
| 추천 목록 | 완료 목록 중심 | 진행 중에는 빈 배열/부분 데이터 허용 |

##### 변경 후 응답 정책

- `recommendations[].status`가 `RUNNING`/`PENDING`이면 `assistantTurnId`는 `null`일 수 있다.
- `recommendations[].status`가 `FAILED`이면 `mergedReason`는 `null`일 수 있고, 오류 요약 정보를 우선 노출한다.
- 프론트는 상세 조회 단독으로 완료를 단정하지 않고, 상태 조회 API와 함께 사용한다.

---

### 3) 전체 플로우 명세

| 단계 | 처리 주체 | 동작 | DB 상태 |
|---|---|---|---|
| 1 | Frontend | `POST /api/v1/chat/messages` 호출 | - |
| 2 | Backend (TX-1) | `conversation`, `user_turn` 저장 + recommendation 계열 레코드 선생성 | `PENDING` |
| 3 | Backend | `202` + `recommendationId` 즉시 반환 | `PENDING` |
| 4 | Backend Worker | FastAPI 추천 3단계 호출(dataset/openapi/merge) 시작 전/초기에 `RUNNING` 전환 | `RUNNING` |
| 5 | Backend (TX-2) | 성공 시 assistant turn 생성/연결 + 추천 결과 저장 | `SUCCESS` |
| 6 | Backend (TX-2) | 실패 시 오류 요약 저장 | `FAILED` |
| 7 | Frontend | `GET /api/v1/recommendations/{recommendationId}` 폴링 | 상태 기반 UI 전환 |

#### 상태 전이 규칙

`PENDING` -> `RUNNING` -> `SUCCESS` or `FAILED`

#### 핵심 동작 원칙

- 요청 스레드는 추천 생성 완료까지 블로킹하지 않는다.
- `POST /chat/messages` 즉시 응답 시점의 `data.status`는 `PENDING`이며, 워커가 작업을 시작하면 `RUNNING`으로 전이될 수 있다.
- 최종 결과 렌더링은 `recommendationId` 상태 조회 결과를 기준으로 한다.
- `SUCCESS`가 되기 전에는 assistant 메시지/카드가 없거나 부분 데이터일 수 있다.

---

### 4) 프론트 이용 명세

#### 권장 호출 순서

1. 사용자 메시지 전송: `POST /api/v1/chat/messages`
2. 응답에서 `recommendationId` 확보
3. 1~2초 간격 상태 폴링: `GET /api/v1/recommendations/{recommendationId}`
4. `SUCCESS` 수신 시 채팅 메시지/추천 카드 렌더링
5. 카드 상세 필요 시 `GET /api/v1/chat-resources/{resourceType}/{resourceId}?recommendationScore=...` 호출
6. 카드 다건 렌더링 시 `POST /api/v1/chat-resources/cards/batch` 호출

#### 폴링 종료 조건

| 조건 | 처리 |
|---|---|
| `status=SUCCESS` | 폴링 중단, 결과 렌더링 |
| `status=FAILED` | 폴링 중단, 실패 메시지 노출 + 재시도 버튼 |
| 최대 대기시간 초과 | 폴링 중단, "처리 지연" 안내 후 수동 재조회 제공 |

#### UI/상태 처리 권장안

- `RUNNING`: 입력창/전송 버튼 중복 제출 방지 + 진행 배너 표시
- `FAILED`: `errorSummary`를 사용자 친화 메시지로 매핑
- 새로고침/재진입: `conversationId` 기반으로 진행 중 recommendation을 재조회해 상태 복원

---

## 0322 보완사항 (채팅 운영 안정화)

> 본 항목은 0321 비동기 채팅 구조를 실제 운영 트래픽/장애 상황에서 안정적으로 유지하기 위한 보완 명세입니다.
> 본 항목은 범위를 `#3 history/요청 크기 제어`, `#4 finalize 보장/상태 고착 방지`로 한정합니다.

### 보완 목표

| 구분 | 목표 |
|---|---|
| #3 | 대화가 길어져도 FastAPI 요청 크기/처리시간이 비정상적으로 증가하지 않도록 상한을 강제한다. |
| #4 | 추천 상태가 `RUNNING`에서 고착되지 않도록 최종 상태(`SUCCESS`/`FAILED`) 기록 보장 장치를 둔다. |

### 1) 보완 항목 #3 - history 무제한 누적으로 인한 처리량 저하 방지

#### 문제 정의

- 현재 채팅 history는 과거 턴 전체를 누적한 뒤 FastAPI 3개 호출(dataset/openapi/merge)에 전달된다.
- 호출은 블로킹(`.block()`) 기반이며 timeout이 길어(180초) 워커 점유 시간이 증가할 수 있다.
- 결과적으로 동시 요청 증가 시 워커 풀 포화 -> 큐 적체 -> 작업 거절 가능성이 높아진다.

#### 증상 시나리오

| 시나리오 | 예상 증상 |
|---|---|
| 긴 대화(턴 수/문자 수 증가) | 직렬화/전송 비용 증가, FastAPI 응답 지연 증가 |
| 피크 트래픽 | executor queue 적체, 일부 요청 지연 또는 거절 |
| 외부 API 일시 지연 | 대기 작업 누적, 후속 요청 처리량 감소 |

#### 대응 방안 (구현 순서)

1. **P0 - history 상한 강제**
   - 최근 N턴만 포함(예: 최근 10턴)
   - 총 payload 문자/바이트 상한 추가(초과 시 앞부분 축약)
   - 단일 메시지 최대 길이 제한(초과 시 truncate 또는 validation 실패)
2. **P1 - 호출별 context 경량화**
   - 3개 FastAPI 호출 모두에 full history를 전달하지 않고, merge 외 호출은 축약 context 사용
   - 동일 history를 다중 호출에 반복 전달하는 비용 최소화
3. **P2 - 백프레셔/운영 가드**
   - executor 포화 임계치 기반 제한(요청 수락 제어)
   - 거절 시 사용자/프론트에 재시도 가능한 명확한 상태 메시지 제공

#### 수용 기준 (Acceptance)

- 대화 길이 증가 시에도 요청 payload가 설정 상한을 넘지 않는다.
- 피크 상황에서 queue 포화가 발생해도 무제한 지연 대신 통제된 실패/재시도 흐름을 제공한다.
- 운영 대시보드에서 history 크기/큐 적체 지표를 추적할 수 있다.

### 2) 보완 항목 #4 - finalize 실패 시 상태 고착 방지

#### 문제 정의

- 비동기 플로우는 `RUNNING` 전이 후 `finalize(success/failure)`에서 최종 상태를 기록한다.
- finalize 단계 자체가 실패하면 경고 로그만 남고 종료될 수 있어, `RUNNING` 상태가 장시간 남을 수 있다.
- executor 거절 경로와 일반 비동기 예외 경로의 finalize 예외 처리 방식이 비대칭이다.

#### 증상 시나리오

| 시나리오 | 예상 증상 |
|---|---|
| DB 일시 장애/트랜잭션 실패 | 최종 상태 미기록, `RUNNING` 고착 |
| executor 거절 직후 finalize 실패 | 사용자 실패 응답 대비 DB 상태 불일치 |
| 장애 후 재시작 | 일부 recommendation이 종결되지 않은 상태로 잔존 |

#### 대응 방안 (구현 순서)

1. **P0 - finalize 실패 재처리 가능화**
   - finalize 실패를 로그-only로 끝내지 않고 재처리 트리거(재시도 대상)로 남긴다.
   - executor 거절 경로도 동일한 finalize 예외 처리 정책으로 통일한다.
2. **P1 - stale RUNNING 정리 배치**
   - `RUNNING`이 임계 시간(예: 5분/10분) 이상 지속되면 강제 `FAILED` 전이하는 정리 작업 추가
   - 오류 요약(`errorSummary`)에 만료/복구 사유를 명시
3. **P2 - 관측성 강화**
   - finalize 실패 건수, stale RUNNING 건수, 강제 종료 건수를 메트릭으로 노출
   - 임계치 초과 시 운영 알림 연동

#### 수용 기준 (Acceptance)

- 일정 시간 이상 `RUNNING` 상태가 무기한 유지되지 않는다.
- finalize 실패 발생 시 후속 재처리 루트가 존재하며, 상태 불일치가 자동으로 수렴된다.
- 운영자가 로그/메트릭만으로 고착 원인과 복구 여부를 추적할 수 있다.

### 우선순위 및 적용 범위

| 우선순위 | 항목 | 이유 |
|---|---|---|
| 즉시 | #3 P0, #4 P0 | 사용자 체감 지연/고착을 직접 줄이는 최소 안전장치 |
| 단기 | #3 P1, #4 P1 | 구조적 비용 절감 및 자동 복구 |
| 중기 | #3 P2, #4 P2 | 운영 가시성/예방 자동화 강화 |

### 적용 후 기대 효과

- 긴 대화와 피크 트래픽에서도 추천 처리 품질이 급격히 저하되지 않는다.
- 비동기 처리 실패 시에도 상태가 최종적으로 수렴해 사용자/DB 간 불일치가 줄어든다.
- 운영자는 재현이 어려운 간헐 장애를 지표 기반으로 조기 탐지/복구할 수 있다.

---

### 0322 실제 보완 사항

> 아래 항목은 본 문서의 0322 보완 계획 중 즉시 적용(P0) 범위를 실제 코드에 반영한 내용입니다.

#### 반영 범위

| 구분 | 적용 여부 | 실제 반영 내용 |
|---|---|---|
| #3 P0 | 적용 완료 | 입력 메시지 길이 상한, history 턴 수/턴별 길이/총 길이 상한 적용 |
| #4 P0 | 적용 완료 | finalize 실패 처리 공통화 및 재시도(2회) + executor 거절 경로 예외 처리 대칭화 |
| #3 P1/P2 | 미적용 | 호출별 context 경량화/백프레셔 정책 고도화는 후속 검토 |
| #4 P1/P2 | 미적용 | stale RUNNING 정리 배치/메트릭 알림은 후속 검토 |

#### 실제 코드 변경 상세

1. **#3 P0 적용 - 요청 payload 상한 강제**
   - `validateMessage()`에서 공백 trim 후 최대 길이(2000자) 초과 시 `INVALID_CHAT_MESSAGE` 처리
   - `buildHistory()`에 아래 상한을 적용
     - 최근 턴만 유지: 최대 10턴(`MAX_HISTORY_TURNS`)
     - 턴별 content 상한: 1000자(`MAX_HISTORY_ITEM_CONTENT_LENGTH`)
     - history 전체 content 총합 상한: 12000자(`MAX_HISTORY_TOTAL_CONTENT_LENGTH`)
   - 상한 초과 시 후행 content를 축약해 FastAPI 요청 본문이 무제한 증가하지 않도록 제어

2. **#4 P0 적용 - finalize 실패 처리 강건화**
   - `finalizeFailureWithRetry(...)` 공통 헬퍼 도입
   - 실패 finalize를 2회까지 재시도(`FINALIZE_FAILURE_RETRY_COUNT=2`)하고, 시도별 경고 로그를 남기도록 변경
   - `RejectedExecutionException` 경로도 동일 헬퍼를 사용하도록 변경해, 일반 비동기 예외 경로와 finalize 예외 처리 정책을 통일

#### 반영 파일

| 파일 | 변경 요약 |
|---|---|
| `backend/src/main/java/ssafy/E105/domain/chat/service/ChatService.java` | #3 P0 상한 로직 + #4 P0 finalize 재시도/대칭 처리 |

#### 적용 후 확인 포인트

- 긴 대화에서 FastAPI 요청이 과도하게 비대해지지 않는지(`history` 상한 준수)
- executor 거절/비동기 예외 시 recommendation 상태가 `FAILED`로 수렴하는지
- `finalize` 실패 로그 발생 시 재시도 로그가 남고, 상태 고착 건이 감소하는지

#### 추가 질문(후속 질문) 시 이전 추천 전달 방식

아래 내용은 "첫 질문 이후 사용자가 추가 질문을 보낼 때" 서버가 어떤 데이터를 다시 보내는지에 대한 실제 구현 기준 설명이다.

1) 매 턴마다 추천 ID는 새로 만든다.

- 후속 질문이 들어오면, 서버는 이번 턴 전용으로 아래 3개 레코드를 새로 선생성한다.
  - `datasetRecommendationId`
  - `openapiRecommendationId`
  - `recommendationId`
- 즉, 이전 턴의 추천 ID를 재사용하지 않는다.

2) 이전 추천 "카드 JSON 전체"를 다시 보내지는 않는다.

- 후속 질문 호출 시 FastAPI로 전달되는 것은
  - 이번 사용자 메시지(`message`)
  - 대화 히스토리(`history`: role/content 텍스트 배열)
  - 이번 턴에 새로 만든 recommendation 계열 ID들
- 이전 턴의 `recommendedItems` JSON 전체를 그대로 재전송하지는 않는다.

3) `history`에는 무엇이 들어가나?

- `history`는 카드 데이터가 아니라 "대화 텍스트"다.
- 각 항목은 아래 형태다.

```json
{
  "role": "USER | ASSISTANT",
  "content": "대화 문장"
}
```

- 현재 정책상 최근 10턴, 턴당 최대 1000자, 전체 최대 12000자까지만 전달한다.

4) FastAPI에서 `history`를 실제로 쓰는 단계

- `recommend-datasets`, `recommend-open-apis`:
  - 스키마로는 `history`를 받지만, 현재 추천 계산 로직에서는 사용하지 않는다.
- `merge-recommendation-reason`:
  - `history`를 실제로 사용한다.
  - 최근 일부(history[-8:])를 LLM 프롬프트에 넣어 최종 병합 응답 문장을 생성한다.

5) 한 줄 요약

- 후속 질문 시에는 "이전 추천 결과 JSON을 통째로 재전송"하는 방식이 아니라,
  "이전 대화 텍스트(history) + 이번 턴 신규 recommendation ID"를 전달하는 방식이다.

---

## 프론트 연동 참고 사항

> 이 섹션은 프론트엔드 개발자가 채팅 생성(없을 시 생성) + 추천 생성(비동기) 플로우를 구현할 때 필요한 실무 정보를 한 번에 확인할 수 있도록 작성했다.
> 기준 코드는 `ChatController`, `ChatService`, 관련 DTO/Entity이다.

### 1) 먼저 알아야 할 핵심 요약

- 채팅 전송은 **동기 완료형이 아니라 비동기 접수형**이다.
- `POST /api/v1/chat/messages` 성공 시 HTTP `202` + `recommendationId`를 즉시 받고, 결과는 `GET /api/v1/recommendations/{recommendationId}`로 폴링한다.
- `conversationId`를 보내지 않으면 백엔드가 대화를 새로 만들고, 보내면 해당 대화에 이어서 턴을 추가한다.
- 추천 상태는 `PENDING -> RUNNING -> SUCCESS | FAILED`로 전이한다.
- `SUCCESS` 전까지 `assistantTurnId`는 `null`일 수 있고, 추천 목록은 빈 배열/부분 데이터일 수 있다.

### 2) 실제 API 엔드포인트(외부/내부)

| 목적 | 외부 경로(프론트 호출) | 내부 경로(백엔드) | 메서드 |
|---|---|---|---|
| 메시지 전송(접수) | `/api/v1/chat/messages` | `/v1/chat/messages` | `POST` |
| 추천 상태 조회 | `/api/v1/recommendations/{recommendationId}` | `/v1/recommendations/{recommendationId}` | `GET` |
| 대화 목록 | `/api/v1/conversations` | `/v1/conversations` | `GET` |
| 대화 상세 | `/api/v1/conversations/{conversationId}` | `/v1/conversations/{conversationId}` | `GET` |
| 대화 삭제 | `/api/v1/conversations/{conversationId}` | `/v1/conversations/{conversationId}` | `DELETE` |

### 3) 식별자(ID) 관계를 정확히 이해하기

- `conversationId`: 대화방 단위 식별자
- `userTurnId`: 사용자 발화 턴 식별자(요청마다 새로 생김)
- `assistantTurnId`: 추천 완료 후 생성되는 assistant 턴 식별자(`SUCCESS` 전에는 `null` 가능)
- `recommendationId`: 상태 폴링 키(프론트가 반드시 보관해야 함)
- `datasetRecommendationId`, `openApiRecommendationId`: 내부 처리용(프론트 직접 사용 X)

프론트 저장 권장:

- 최소 저장 키: `conversationId`, `recommendationId`, `userTurnId`
- 화면 갱신/재진입 복구 시: `conversationId`로 상세 조회 + 필요 시 `recommendationId` 상태 재조회

### 4) 채팅 전송 요청/응답 계약

#### 4-1) 요청

```json
{
  "conversationId": 12,
  "message": "기상 데이터 분석에 쓸 데이터셋/오픈API 추천해줘"
}
```

- `conversationId` 생략 또는 `null`이면 신규 대화 생성
- `message`는 필수, 공백 불가
- 서버에서 입력 길이 상한을 검증한다(현재 2000자)

#### 4-2) 성공 응답 (`202 Accepted`)

```json
{
  "status": 202,
  "message": "채팅 메시지가 접수되었습니다. 추천 생성이 진행 중입니다.",
  "data": {
    "conversationId": 12,
    "userTurnId": 101,
    "recommendationId": 9001,
    "status": "PENDING"
  }
}
```

응답 헤더:

- `Location: /v1/recommendations/{recommendationId}`

프론트 동작:

1. `conversationId`, `recommendationId`, `userTurnId`를 상태/스토리지에 즉시 저장
2. 입력창은 중복 전송 방지 상태로 전환
3. 상태 폴링 시작

### 5) 추천 상태 조회 계약

#### 5-1) 요청

- `GET /api/v1/recommendations/{recommendationId}`

#### 5-2) 응답 핵심 필드

| 필드 | 설명 |
|---|---|
| `recommendationId` | 현재 상태 조회 대상 |
| `conversationId` | 연결된 대화 ID |
| `userTurnId` | 연결된 사용자 턴 ID |
| `assistantTurnId` | 완료 전 `null` 가능 |
| `status` | `PENDING`/`RUNNING`/`SUCCESS`/`FAILED` |
| `mergedReason` | 성공 시 주 응답 문장(없을 수도 있음) |
| `datasetRecommendations` | dataset 추천 JSON |
| `openApiRecommendations` | openapi 추천 JSON |
| `errorSummary` | 실패 요약 |
| `updatedAt` | 상태 변경 시각 |

### 6) 프론트 권장 상태머신(UI)

| 백엔드 상태 | 프론트 표시 | 입력 가능 여부 | 다음 행동 |
|---|---|---|---|
| `PENDING` | "요청 접수" 스피너 | 비활성 권장 | 1~2초 후 재조회 |
| `RUNNING` | "추천 생성 중" 진행 상태 | 비활성 권장 | 1~2초 폴링 유지 |
| `SUCCESS` | assistant 메시지 + 카드 렌더링 | 활성 | 폴링 종료 |
| `FAILED` | 오류 배너 + 재시도 버튼 | 활성 | 폴링 종료 |

권장 폴링 정책:

- 기본: 1~2초 간격
- 최대 대기: 60~120초(서비스 정책에 맞춰 조정)
- 최대 대기 초과 시: "지연 중" 안내 + 수동 재조회 버튼

### 7) 전체 시퀀스(프론트 기준)

```text
사용자 입력
  -> POST /api/v1/chat/messages
      <- 202 + conversationId + userTurnId + recommendationId
  -> (poll) GET /api/v1/recommendations/{recommendationId}
      <- PENDING/RUNNING 반복
      <- SUCCESS 이면 결과 렌더링
      <- FAILED 이면 오류 렌더링
  -> 필요 시 GET /api/v1/conversations/{conversationId}로 전체 히스토리 동기화
```

### 8) conversationId 없는 경우 vs 있는 경우

#### A. conversationId 없음(신규 대화)

- 서버가 conversation 생성
- 사용자 턴 생성
- recommendation 3종(통합/dataset/openapi) `PENDING` 생성
- `202`로 `conversationId` 반환

#### B. conversationId 있음(기존 대화)

- 서버가 해당 대화 소유권 검증
- 턴 오더 계산 후 사용자 턴 추가
- recommendation 3종 `PENDING` 생성
- `202` 반환

### 9) 백엔드 내부 처리(프론트 이해용)

백엔드는 접수 후 별도 실행기에서 추천 파이프라인을 수행한다.

1. 상태 `RUNNING` 전환
2. FastAPI `recommend-datasets` 호출
3. FastAPI `recommend-open-apis` 호출
4. FastAPI `merge-recommendation-reason` 호출
5. 성공 시 assistant 턴 생성 + recommendation `SUCCESS`
6. 실패 시 recommendation `FAILED` + `errorSummary` 저장

참고로 백엔드에는 다음 제약이 있다.

- history 전달 최대 턴 수/길이 상한(과도한 payload 방지)
- 비동기 큐 포화 시 즉시 실패 처리 가능
- finalize 실패 시 재시도 로직 존재

### 10) 오류 코드 매핑(프론트 처리 지침)

| HTTP | 주요 코드/상황 | 프론트 권장 처리 |
|---|---|---|
| `400` | `INVALID_CHAT_MESSAGE`, `INVALID_CONVERSATION_ID`, `INVALID_INPUT` | 입력 검증 메시지 표시 |
| `401` | `INVALID_USER`, `INVALID_TOKEN` | 로그인 만료 처리/재인증 |
| `403` | `CONVERSATION_FORBIDDEN`, `RECOMMENDATION_FORBIDDEN` | 접근 불가 안내 + 목록 화면 유도 |
| `404` | `CONVERSATION_NOT_FOUND`, `RECOMMENDATION_NOT_FOUND` | 존재하지 않는 리소스 안내 |
| `502` | `FASTAPI_SERVER_ERROR` | "추천 서버 지연/실패" 안내 + 재시도 |

### 11) 중복 전송/재시도 전략 (프론트 필수)

- 백엔드에 idempotency key 계약이 없으므로, 프론트에서 중복 전송을 적극 방지해야 한다.
- 전송 버튼 연타 방지(로딩 중 비활성)
- 네트워크 타임아웃으로 재시도할 때는 이전 `recommendationId` 존재 여부를 먼저 확인
- 같은 메시지를 자동 재발송하지 말고 사용자 의도 확인 후 재시도

### 12) 새로고침/재진입 복구 전략

권장 복구 순서:

1. 저장해둔 `conversationId`가 있으면 대화 상세 조회
2. 화면에 진행 중 추천(`PENDING`/`RUNNING`)이 있으면 해당 `recommendationId`로 상태 조회 재개
3. 완료(`SUCCESS`/`FAILED`)된 항목은 폴링 중단

### 13) 프론트 구현 체크리스트

- [ ] `POST /chat/messages` 성공 시 `202`를 정상 플로우로 처리
- [ ] `Location` 헤더 또는 `data.recommendationId`를 폴링 키로 저장
- [ ] 상태값 4종(`PENDING`, `RUNNING`, `SUCCESS`, `FAILED`) 분기 구현
- [ ] `assistantTurnId == null` 상태를 오류로 취급하지 않음
- [ ] `FAILED`에서 `errorSummary` 우선 노출 + 재시도 UX 제공
- [ ] 대화 상세 화면은 `GET /conversations/{id}`와 상태 조회 결과를 함께 반영
- [ ] 중복 전송 방지(버튼 비활성, in-flight request 관리)

### 14) 연동 시 자주 놓치는 포인트

- `POST /chat/messages`는 최종 추천 결과를 즉시 반환하지 않는다.
- `SUCCESS` 전에는 카드가 비어 있어도 정상이다.
- `conversationId` 없이 보내면 매번 새 대화가 생긴다.
- 추천 실패(`FAILED`)도 대화 자체는 남는다(대화 목록/상세에서 확인 가능).

### 15) 코드 기준 참조 경로

- `backend/src/main/java/ssafy/E105/domain/chat/controller/ChatController.java`
- `backend/src/main/java/ssafy/E105/domain/chat/service/ChatService.java`
- `backend/src/main/java/ssafy/E105/domain/chat/dto/request/SendChatMessageRequest.java`
- `backend/src/main/java/ssafy/E105/domain/chat/dto/response/SendChatMessageAcceptedResponse.java`
- `backend/src/main/java/ssafy/E105/domain/chat/dto/response/RecommendationStatusResponse.java`
- `backend/src/main/java/ssafy/E105/domain/chat/dto/response/ConversationDetailResponse.java`
- `backend/src/main/java/ssafy/E105/domain/chat/dto/response/RecommendationDetailResponse.java`
- `backend/src/main/java/ssafy/E105/global/exception/ErrorCode.java`

---

## 0324 API 정리 (채팅 관련 전체)

> 아래 명세는 프론트 외부 호출 기준(`/api/v1/...`)으로 작성했습니다. 백엔드 내부 매핑은 `/v1/...`입니다.

### 1) 채팅 메시지 전송 (비동기 접수)

#### Header
- `Authorization: Bearer <accessToken>`
- `Content-Type: application/json`

#### apipath
- `POST /api/v1/chat/messages` (내부: `POST /v1/chat/messages`)

#### description
- 사용자 메시지를 접수하고 추천 작업을 비동기로 시작합니다.
- 성공 시 최종 추천 결과가 아니라 `recommendationId`를 즉시 반환합니다.

#### request parameter

| 파라미터명 | 타입 | 설명 |
|---|---|---|
| `conversationId` | Long\|null | 기존 대화 ID(없으면 신규 대화 생성) |
| `message` | String | 사용자 입력 메시지(필수, 공백 불가) |

#### response code

| 코드 | 설명 |
|---|---|
| `202` | 메시지 접수 및 추천 생성 시작 |
| `400` | 잘못된 요청(메시지 공백/잘못된 입력) |
| `401` | 인증 실패 |
| `403` | 본인 대화가 아님 |
| `404` | 대화를 찾을 수 없음 |
| `502` | 추천 서버(FastAPI) 연동 실패 |

#### response parameter

| 파라미터명 | 타입 | 설명 |
|---|---|---|
| `status` | int | HTTP 상태 코드 |
| `message` | String | 처리 결과 메시지 |
| `data.conversationId` | Long | 대화 ID |
| `data.userTurnId` | Long | 사용자 턴 ID |
| `data.recommendationId` | Long | 추천 상태 조회 ID |
| `data.status` | String | 초기 상태(`PENDING`) |

#### success data example

```json
{
  "status": 202,
  "message": "채팅 메시지가 접수되었습니다. 추천 생성이 진행 중입니다.",
  "data": {
    "conversationId": 12,
    "userTurnId": 101,
    "recommendationId": 9001,
    "status": "PENDING"
  }
}
```

#### fail data example

```json
{
  "status": 400,
  "message": "메시지는 비어 있을 수 없습니다."
}
```

```json
{
  "status": 401,
  "message": "유효하지 않은 사용자입니다."
}
```

```json
{
  "status": 403,
  "message": "해당 대화에 접근할 수 없습니다."
}
```

```json
{
  "status": 404,
  "message": "대화를 찾을 수 없습니다."
}
```

```json
{
  "status": 502,
  "message": "추천 서버와 통신에 실패했습니다."
}
```

### 2) 추천 상태 조회

#### Header
- `Authorization: Bearer <accessToken>`

#### apipath
- `GET /api/v1/recommendations/{recommendationId}` (내부: `GET /v1/recommendations/{recommendationId}`)

#### description
- 추천 작업의 진행 상태(`PENDING/RUNNING/SUCCESS/FAILED`)와 결과를 조회합니다.

#### request parameter

| 파라미터명 | 타입 | 설명 |
|---|---|---|
| `recommendationId` | Long (Path) | 추천 작업 ID |

#### response code

| 코드 | 설명 |
|---|---|
| `200` | 조회 성공 |
| `400` | 잘못된 추천 ID |
| `401` | 인증 실패 |
| `403` | 본인 추천 작업이 아님 |
| `404` | 추천 작업을 찾을 수 없음 |

#### response parameter

| 파라미터명 | 타입 | 설명 |
|---|---|---|
| `status` | int | HTTP 상태 코드 |
| `message` | String | 처리 결과 메시지 |
| `data.recommendationId` | Long | 추천 작업 ID |
| `data.conversationId` | Long | 대화 ID |
| `data.userTurnId` | Long | 사용자 턴 ID |
| `data.assistantTurnId` | Long\|null | assistant 턴 ID |
| `data.status` | String | `PENDING` / `RUNNING` / `SUCCESS` / `FAILED` |
| `data.mergedReason` | String\|null | 병합 추천 사유 |
| `data.datasetRecommendations` | JSON | 데이터셋 추천 목록(JSON) |
| `data.openApiRecommendations` | JSON | Open API 추천 목록(JSON) |
| `data.errorSummary` | String\|null | 실패 요약 |
| `data.updatedAt` | String (ISO datetime) | 마지막 상태 변경 시각 |

#### success data example

```json
{
  "status": 200,
  "message": "추천 상태 조회가 완료되었습니다.",
  "data": {
    "recommendationId": 9001,
    "conversationId": 12,
    "userTurnId": 101,
    "assistantTurnId": null,
    "status": "RUNNING",
    "mergedReason": null,
    "datasetRecommendations": [],
    "openApiRecommendations": [],
    "errorSummary": null,
    "updatedAt": "2026-03-24T10:10:00"
  }
}
```

#### fail data example

```json
{
  "status": 400,
  "message": "잘못된 요청입니다."
}
```

```json
{
  "status": 401,
  "message": "유효하지 않은 사용자입니다."
}
```

```json
{
  "status": 403,
  "message": "해당 추천 작업에 접근할 수 없습니다."
}
```

```json
{
  "status": 404,
  "message": "추천 작업을 찾을 수 없습니다."
}
```

### 3) 대화 목록 조회

#### Header
- `Authorization: Bearer <accessToken>`

#### apipath
- `GET /api/v1/conversations` (내부: `GET /v1/conversations`)

#### description
- 로그인 사용자의 대화 목록을 최근 수정일 기준으로 조회합니다.

#### request parameter

| 파라미터명 | 타입 | 설명 |
|---|---|---|
| 없음 | - | Query/Body 파라미터 없음 |

#### response code

| 코드 | 설명 |
|---|---|
| `200` | 조회 성공 |
| `401` | 인증 실패 |

#### response parameter

| 파라미터명 | 타입 | 설명 |
|---|---|---|
| `status` | int | HTTP 상태 코드 |
| `message` | String | 처리 결과 메시지 |
| `data[]` | Array | 대화 목록 |
| `data[].conversationId` | Long | 대화 ID |
| `data[].title` | String | 대화 제목 |
| `data[].createdAt` | String (ISO datetime) | 생성 시각 |
| `data[].updatedAt` | String (ISO datetime) | 수정 시각 |

#### success data example

```json
{
  "status": 200,
  "message": "대화 목록 조회가 완료되었습니다.",
  "data": [
    {
      "conversationId": 12,
      "title": "기상 데이터 추천",
      "createdAt": "2026-03-24T09:00:00",
      "updatedAt": "2026-03-24T09:01:30"
    }
  ]
}
```

#### fail data example

```json
{
  "status": 401,
  "message": "유효하지 않은 사용자입니다."
}
```

### 4) 대화 상세 조회

#### Header
- `Authorization: Bearer <accessToken>`

#### apipath
- `GET /api/v1/conversations/{conversationId}` (내부: `GET /v1/conversations/{conversationId}`)

#### description
- 특정 대화의 턴 목록과 추천 결과 목록을 조회합니다.

#### request parameter

| 파라미터명 | 타입 | 설명 |
|---|---|---|
| `conversationId` | Long (Path) | 조회할 대화 ID |

#### response code

| 코드 | 설명 |
|---|---|
| `200` | 조회 성공 |
| `401` | 인증 실패 |
| `403` | 본인 대화가 아님 |
| `404` | 대화를 찾을 수 없음 |

#### response parameter

| 파라미터명 | 타입 | 설명 |
|---|---|---|
| `status` | int | HTTP 상태 코드 |
| `message` | String | 처리 결과 메시지 |
| `data.conversationId` | Long | 대화 ID |
| `data.title` | String | 대화 제목 |
| `data.turns[]` | Array | 대화 턴 목록 |
| `data.turns[].turnId` | Long | 턴 ID |
| `data.turns[].turnOrder` | Integer | 턴 순서 |
| `data.turns[].role` | String | `USER` / `ASSISTANT` |
| `data.turns[].content` | String | 턴 본문 |
| `data.turns[].responseTimeMs` | Integer\|null | 응답 시간(ms) |
| `data.turns[].createdAt` | String (ISO datetime) | 생성 시각 |
| `data.recommendations[]` | Array | 추천 상세 목록 |
| `data.recommendations[].recommendationId` | Long | 추천 ID |
| `data.recommendations[].userTurnId` | Long | 사용자 턴 ID |
| `data.recommendations[].assistantTurnId` | Long\|null | assistant 턴 ID |
| `data.recommendations[].status` | String | 추천 상태 |
| `data.recommendations[].mergedReason` | String\|null | 병합 사유 |
| `data.recommendations[].datasetReason` | String\|null | 데이터셋 사유 |
| `data.recommendations[].openApiReason` | String\|null | Open API 사유 |
| `data.recommendations[].datasetRecommendations` | JSON | 데이터셋 추천 JSON |
| `data.recommendations[].openApiRecommendations` | JSON | Open API 추천 JSON |
| `data.recommendations[].errorSummary` | String\|null | 실패 요약 |

#### success data example

```json
{
  "status": 200,
  "message": "대화 상세 조회가 완료되었습니다.",
  "data": {
    "conversationId": 12,
    "title": "기상 데이터 추천",
    "turns": [
      {
        "turnId": 101,
        "turnOrder": 1,
        "role": "USER",
        "content": "기상 데이터 추천해줘",
        "responseTimeMs": null,
        "createdAt": "2026-03-24T09:00:00"
      }
    ],
    "recommendations": [
      {
        "recommendationId": 9001,
        "userTurnId": 101,
        "assistantTurnId": null,
        "status": "RUNNING",
        "mergedReason": null,
        "datasetReason": null,
        "openApiReason": null,
        "datasetRecommendations": [],
        "openApiRecommendations": [],
        "errorSummary": null
      }
    ]
  }
}
```

#### fail data example

```json
{
  "status": 401,
  "message": "유효하지 않은 사용자입니다."
}
```

```json
{
  "status": 403,
  "message": "해당 대화에 접근할 수 없습니다."
}
```

```json
{
  "status": 404,
  "message": "대화를 찾을 수 없습니다."
}
```

### 5) 대화 삭제

#### Header
- `Authorization: Bearer <accessToken>`

#### apipath
- `DELETE /api/v1/conversations/{conversationId}` (내부: `DELETE /v1/conversations/{conversationId}`)

#### description
- 대화를 소프트 삭제 처리합니다.

#### request parameter

| 파라미터명 | 타입 | 설명 |
|---|---|---|
| `conversationId` | Long (Path) | 삭제할 대화 ID |

#### response code

| 코드 | 설명 |
|---|---|
| `200` | 삭제 성공 |
| `401` | 인증 실패 |
| `403` | 본인 대화가 아님 |
| `404` | 대화를 찾을 수 없음 |

#### response parameter

| 파라미터명 | 타입 | 설명 |
|---|---|---|
| `status` | int | HTTP 상태 코드 |
| `message` | String | 처리 결과 메시지 |
| `data` | null | 삭제 API 본문 데이터 없음 |

#### success data example

```json
{
  "status": 200,
  "message": "대화 삭제가 완료되었습니다.",
  "data": null
}
```

#### fail data example

```json
{
  "status": 401,
  "message": "유효하지 않은 사용자입니다."
}
```

```json
{
  "status": 403,
  "message": "해당 대화에 접근할 수 없습니다."
}
```

```json
{
  "status": 404,
  "message": "대화를 찾을 수 없습니다."
}
```

### 6) 채팅 추천 카드 배치 조회

#### Header
- `Authorization: Bearer <accessToken>`
- `Content-Type: application/json`

#### apipath
- `POST /api/v1/chat-resources/cards/batch` (내부: `POST /v1/chat-resources/cards/batch`)

#### description
- 추천 결과 카드 렌더링용 공통 정보를 다건 조회합니다.
- 일부 리소스가 없어도 `200`으로 응답하고 `data.errors`에 실패 항목을 담습니다.

#### request parameter

| 파라미터명 | 타입 | 설명 |
|---|---|---|
| `items` | Array | 조회 대상 목록(필수) |
| `items[].resourceType` | String | `DATASET` / `OPEN_API` |
| `items[].resourceId` | Long | 리소스 ID |
| `items[].recommendationScore` | Double | 추천 점수 |
| `items[].rank` | Integer\|null | 카드 순위(선택) |

#### response code

| 코드 | 설명 |
|---|---|
| `200` | 조회 성공(부분 실패 포함) |
| `400` | 잘못된 요청 |
| `401` | 인증 실패 |

#### response parameter

| 파라미터명 | 타입 | 설명 |
|---|---|---|
| `status` | int | HTTP 상태 코드 |
| `message` | String | 처리 결과 메시지 |
| `data.cards[]` | Array | 카드 목록 |
| `data.cards[].id` | Long | 리소스 ID |
| `data.cards[].name` | String | 리소스명 |
| `data.cards[].type` | String | `DATASET` / `OPEN_API` |
| `data.cards[].updatedAt` | String | 업데이트 시각 |
| `data.cards[].isFree` | Boolean | 무료 여부 |
| `data.cards[].sourceName` | String\|null | 출처명 |
| `data.cards[].recommendationScore` | Double | 추천 점수 |
| `data.cards[].rank` | Integer\|null | 순위 |
| `data.errors[]` | Array | 개별 실패 항목 |
| `data.errors[].resourceType` | String | 실패 리소스 타입 |
| `data.errors[].resourceId` | Long | 실패 리소스 ID |
| `data.errors[].code` | String | 오류 코드 |
| `data.errors[].message` | String | 오류 메시지 |

#### success data example

```json
{
  "status": 200,
  "message": "채팅 카드 배치 조회가 완료되었습니다.",
  "data": {
    "cards": [
      {
        "id": 88,
        "name": "기상 데이터셋",
        "type": "DATASET",
        "updatedAt": "2026-03-24T09:30:00",
        "isFree": true,
        "sourceName": "공공데이터포털",
        "recommendationScore": 0.93,
        "rank": 1
      }
    ],
    "errors": [
      {
        "resourceType": "OPEN_API",
        "resourceId": 999999,
        "code": "RESOURCE_NOT_FOUND",
        "message": "존재하지 않는 리소스입니다."
      }
    ]
  }
}
```

#### fail data example

```json
{
  "status": 400,
  "message": "잘못된 요청입니다."
}
```

```json
{
  "status": 401,
  "message": "유효하지 않은 사용자입니다."
}
```

### 7) 채팅 추천 상세 조회

#### Header
- `Authorization: Bearer <accessToken>`

#### apipath
- `GET /api/v1/chat-resources/{resourceType}/{resourceId}?recommendationScore={score}`
- (내부: `GET /v1/chat-resources/{resourceType}/{resourceId}`)

#### description
- 카드 클릭 시 리소스 상세 정보를 조회합니다.
- `resourceType`에 따라 `datasetDetail` 또는 `openApiDetail` 중 하나만 채워집니다.

#### request parameter

| 파라미터명 | 타입 | 설명 |
|---|---|---|
| `resourceType` | String (Path) | `DATASET` / `OPEN_API` |
| `resourceId` | Long (Path) | 리소스 ID |
| `recommendationScore` | Double (Query) | 추천 점수 |

#### response code

| 코드 | 설명 |
|---|---|
| `200` | 조회 성공 |
| `400` | 잘못된 요청 |
| `401` | 인증 실패 |
| `404` | 리소스를 찾을 수 없음 |

#### response parameter

| 파라미터명 | 타입 | 설명 |
|---|---|---|
| `status` | int | HTTP 상태 코드 |
| `message` | String | 처리 결과 메시지 |
| `data.id` | Long | 리소스 ID |
| `data.name` | String | 이름 |
| `data.type` | String | `DATASET` / `OPEN_API` |
| `data.updatedAt` | String | 업데이트 시각 |
| `data.isFree` | Boolean | 무료 여부 |
| `data.sourceName` | String\|null | 출처명 |
| `data.recommendationScore` | Double | 추천 점수 |
| `data.originUrl` | String\|null | 원문 URL |
| `data.datasetDetail` | Object\|null | 데이터셋 상세 |
| `data.openApiDetail` | Object\|null | Open API 상세 |

#### success data example

```json
{
  "status": 200,
  "message": "채팅 상세 조회가 완료되었습니다.",
  "data": {
    "id": 88,
    "name": "기상 데이터셋",
    "type": "DATASET",
    "updatedAt": "2026-03-24T09:30:00",
    "isFree": true,
    "sourceName": "공공데이터포털",
    "recommendationScore": 0.93,
    "originUrl": "https://www.data.go.kr/data/15000444/fileData.do",
    "datasetDetail": {
      "descriptionLong": "기상 관련 분석용 데이터셋입니다.",
      "schemaJson": {
        "columns": []
      },
      "datasetSizeBytes": 1234567,
      "rowCount": 10000,
      "metrics": {
        "downloadCount": 100
      },
      "licenseName": "공공누리",
      "classification": ["기상"],
      "tags": ["날씨"],
      "languages": ["ko"]
    },
    "openApiDetail": null
  }
}
```

#### fail data example

```json
{
  "status": 400,
  "message": "잘못된 요청입니다."
}
```

```json
{
  "status": 401,
  "message": "유효하지 않은 사용자입니다."
}
```

```json
{
  "status": 404,
  "message": "존재하지 않는 리소스입니다."
}
```

---

## 프론트 연동 안내

### 목적
- 채팅 관련 API를 프론트에서 안정적으로 연동하기 위한 표준 호출 순서/상태 처리/예외 처리 기준을 제공합니다.

### 기본 흐름
1. `POST /api/v1/chat/messages` 호출
2. `202` 응답에서 `conversationId`, `userTurnId`, `recommendationId` 저장
3. `GET /api/v1/recommendations/{recommendationId}` 폴링(1~2초 간격)
4. `SUCCESS` 시 카드 목록 렌더링, `FAILED` 시 실패 메시지 노출
5. 카드 목록 렌더링은 `POST /api/v1/chat-resources/cards/batch` 사용
6. 카드 클릭 상세는 `GET /api/v1/chat-resources/{resourceType}/{resourceId}` 사용
7. 새로고침/재진입 시 `GET /api/v1/conversations/{conversationId}`로 상태 복구

### 상태값 기준 UI 정책
| 상태 | 의미 | 프론트 처리 |
|---|---|---|
| `PENDING` | 요청 접수 완료, 작업 대기 | 로딩 표시 유지 + 폴링 |
| `RUNNING` | 추천 생성 중 | 로딩 표시 유지 + 폴링 |
| `SUCCESS` | 추천 완료 | 폴링 종료 + 카드/상세 활성 |
| `FAILED` | 추천 실패 | 폴링 종료 + 실패 메시지/재시도 버튼 |

### 프론트 저장 권장 키
| 키 | 용도 |
|---|---|
| `conversationId` | 대화 복구 기준 |
| `recommendationId` | 상태 폴링 키 |
| `userTurnId` | 요청-응답 추적 |
| `lastStatus` | 화면 복구/중복 렌더링 방지 |

### 에러 처리 가이드
| HTTP | 대표 원인 | 프론트 권장 처리 |
|---|---|---|
| `400` | 입력값/형식 오류 | 입력값 검증 메시지 표시 |
| `401` | 인증 실패/만료 | 로그인 갱신 또는 재로그인 유도 |
| `403` | 본인 리소스 아님 | 접근 불가 안내 후 목록 이동 |
| `404` | 대화/추천/리소스 없음 | 대상 없음 안내 |
| `502` | 추천 서버 연동 실패 | 일시 장애 안내 + 재시도 |

### 폴링/재시도 권장값
- 폴링 간격: 1~2초
- 최대 폴링 시간: 60~120초
- 타임아웃 초과 시: "처리가 지연되고 있습니다" 안내 + 수동 재조회 버튼
- 중복 전송 방지: 전송 버튼 비활성 + in-flight 요청 재전송 차단

### 구현 체크리스트
- [ ] `POST /chat/messages`의 `202`를 성공으로 처리
- [ ] `recommendationId` 수신 즉시 폴링 시작
- [ ] 상태 4종(`PENDING`, `RUNNING`, `SUCCESS`, `FAILED`) 분기 구현
- [ ] `FAILED` 시 `message`/`errorSummary` 우선 노출
- [ ] 카드 목록은 `cards/batch` 응답 기준으로 통일
- [ ] 새로고침 시 `conversationId` 기반으로 복구

---

## 0326 수정사항

### 변경 배경

- 추천 결과가 요청 개수에 맞춰 강제로 채워지면서 저품질 후보가 노출되는 문제를 줄이고, LLM 토큰 사용량을 절감하기 위해 추천 개수/점수 정책을 조정했다.

### 반영 요약

| 구분 | 변경 전 | 0326 변경 후 |
|---|---|---|
| 기본 추천 개수 | 미지정 시 기본 5 | 미지정 시 기본 10 |
| 최대 추천 개수 | 최대 10 | 최대 20 |
| 저점수 차단 | 없음 | 점수 60점 이하(`<=60`) 결과 제외 |
| 결과 개수 정책 | 요청 N을 강제로 채우는 경향 | 요청 N은 상한(최대치), 통과한 결과만 `0..N` 반환 |
| Open API 요약 LLM 호출 | 후보가 있으면 호출 | 임계치 필터 후 후보가 없으면 요약 LLM 호출 생략 |
| 추천 실행 트리거 | 모든 프롬프트에서 추천 파이프라인 실행 | LLM 의도분류 결과에 따라 `CHAT_ONLY/DATASET_ONLY/OPENAPI_ONLY/BOTH` 자동 분기 |
| 최종 추천 이유 포맷 | 일반 텍스트 중심 | 최종 추천 이유를 markdown 문자열로 생성/전달 |

### 상세 반영 내용

1. 추천 개수 정책 상향
   - 기본 개수: 5 -> 10
   - 최대 개수: 10 -> 20

2. 데이터셋 추천 품질 게이트 적용
   - `suitabilityScore` 기준 60점 이하 항목 제거
   - LLM 출력에서 부족한 개수를 filler로 강제 보완하던 로직 제거
   - LLM에 "정확히 N개" 반환 강제를 제거하고 "최대 N개" 반환으로 변경

3. Open API 추천 품질 게이트 및 토큰 절감
   - 검색 점수 필터(`<=60` 제외) 적용 후 후보가 없으면 LLM 요약 호출 생략
   - Open API 컨텍스트(description/tag) 길이 축소로 LLM 입력 토큰 절감

4. 임계치 설정값 환경변수화
   - `RECOMMENDATION_SCORE_THRESHOLD_ENABLED` 추가
   - `RECOMMENDATION_MIN_SCORE_100` 추가(기본 60)

5. 프롬프트 기반 LLM 의도 분기 추가(모드 선택 UI 없이 동작)
   - Spring `POST /chat/messages` 계약은 그대로 유지한 채 내부 라우팅만 변경
   - FastAPI 내부 엔드포인트 `/infer-recommendation-mode`, `/chat-answer` 추가
   - `CHAT_ONLY` 판정 시 dataset/openapi 추천 호출 없이 일반 Q&A 답변만 생성
   - `DATASET_ONLY`, `OPENAPI_ONLY`, `BOTH`는 기존 추천 경로 유지

6. 최종 추천 이유 markdown 전달
   - dataset/openapi/merge reason 생성 지시를 markdown 허용 형태로 조정
   - merge 단계의 markdown 금지/제거 후처리를 제거해 markdown 구조 보존
   - 외부 API request/response 스키마 변경 없이 문자열 포맷만 markdown으로 통일

### 반영 파일

| 파일 | 변경 요약 |
|---|---|
| `data-platform/api/app/core/config.py` | 추천 임계치 설정(`recommendation_score_threshold_enabled`, `recommendation_min_score_100`) 추가 |
| `data-platform/api/app/services/dataset_recommendation_service.py` | 저점수 필터, 강제 N 채움 제거, LLM 출력 스키마를 "최대 N개"로 변경, 후보 축소 로직 개선 |
| `data-platform/api/app/services/rag_service.py` | Open API 점수 필터 및 필터 후 빈 후보 시 LLM 호출 스킵, 입력 컨텍스트 경량화 |
| `data-platform/api/app/services/openapi_recommendation_service.py` | 빈 추천 결과도 정상 저장/반환 가능하도록 처리 |
| `data-platform/api/app/schemas/recommendation.py` | dataset `topN` 최대치/설명 업데이트(최대 20, 기본 10) |
| `data-platform/api/app/services/chat_intent_service.py` | LLM 의도분류(`CHAT_ONLY/...`) 및 채팅 전용 답변 생성 서비스 추가 |
| `data-platform/api/app/api/v1/endpoints/rag.py` | 내부 라우팅용 `/infer-recommendation-mode`, `/chat-answer` 엔드포인트 추가 |
| `backend/src/main/java/ssafy/E105/domain/chat/service/ChatService.java` | LLM 의도분류 기반 분기 및 CHAT_ONLY 경로 처리 추가(외부 API 계약 변경 없음) |
| `data-platform/api/app/services/merge_recommendation_service.py` | 최종 병합 reason markdown 허용/보존 및 검증 로직 보정 |
| `data-platform/api/.env.example` | 신규 환경변수 및 기본값 반영 |
| `data-platform/api/README.md` | 추천 개수 정책 문서값 동기화 |

### API/프론트 영향 포인트

- `recommendedItems`는 요청한 N보다 적게 반환될 수 있다(품질 기준 통과분만 반환).
- 모든 후보가 임계치 이하인 경우, 추천 목록이 빈 배열로 반환될 수 있다.
- 점수 필터 활성화 여부는 환경변수로 제어 가능하다.
- `POST /chat/messages`의 request/response body 및 경로는 변경되지 않는다.
- `mergedReason`/`assistantMessage`는 markdown 문자열을 포함할 수 있다.
