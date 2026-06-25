# 리뷰 API

## 목차

- [리뷰 등록](#1-리뷰-등록-post)
- [리뷰 수정](#2-리뷰-수정-put)
- [리뷰 삭제](#3-리뷰-삭제-delete)

---

## 1. 리뷰 등록 `POST`

### Request Parameters

| 파라미터명 | 타입 | 설명 |
|---|---|---|
| `id` | Long | 리소스 ID (Path Variable) |
| `rating` | Integer | 별점 (1~5) |
| `content` | String | 리뷰 내용 |

### Response Codes

| 코드 | 설명 |
|---|---|
| `201` | 리뷰 등록 완료 |
| `400` | 클라이언트 오류 |
| `401` | 인증 실패 |
| `404` | 리소스 없음 |

### Response Parameters

| 파라미터명 | 타입 | 설명 |
|---|---|---|
| `reviewId` | Long | 생성된 리뷰 ID |
| `rating` | Integer | 등록된 별점 |
| `content` | String | 등록된 리뷰 내용 |
| `createdAt` | String | 등록 일시 |

### Success Response Example

**HTTP Status: `201 Created`**

```json
{
  "status": 201,
  "message": "리뷰가 등록되었습니다.",
  "data": {
    "reviewId": 10,
    "rating": 4,
    "content": "응답 속도가 빠르고 안정적입니다.",
    "createdAt": "2025-03-14T09:30:00"
  }
}
```

### Fail Response Examples

**HTTP Status: `400 Bad Request`**

```json
{
  "status": 400,
  "message": "잘못된 요청입니다."
}
```

**HTTP Status: `401 Unauthorized`**

```json
{
  "status": 401,
  "message": "인증이 필요합니다."
}
```

**HTTP Status: `404 Not Found`**

```json
{
  "status": 404,
  "message": "존재하지 않는 리소스입니다."
}
```

---

## 2. 리뷰 수정 `PUT`

### Request Parameters

| 파라미터명 | 타입 | 설명 |
|---|---|---|
| `type` | String | 리소스 타입 (`DATASET` / `OPEN_API`) (Path) |
| `id` | Long | 리소스 ID (Path) |
| `reviewId` | Long | 리뷰 ID (Path) |
| `rating` | Integer | 평점 (1~5) (Body) |
| `content` | String | 리뷰 내용 (Body) |

### Response Codes

| 코드 | 설명 |
|---|---|
| `200` | 요청 정상처리 |
| `400` | 잘못된 평점 입력 |
| `401` | 인증 실패 (토큰 없음/만료) |
| `403` | 본인 리뷰가 아님 |
| `404` | 리뷰를 찾을 수 없음 |

### Response Parameters

| 파라미터명 | 타입 | 설명 |
|---|---|---|
| `id` | Long | 리뷰 ID |
| `rating` | Integer | 수정된 평점 |
| `content` | String | 수정된 리뷰 내용 |
| `createdAt` | String | 최초 작성일 |

### Success Response Example

**HTTP Status: `200 OK`**

```json
{
  "status": 200,
  "message": "리뷰가 수정되었습니다.",
  "data": {
    "id": 10,
    "rating": 5,
    "content": "수정된 리뷰 내용입니다.",
    "createdAt": "2025-03-10T09:00:00"
  }
}
```

### Fail Response Examples

**HTTP Status: `400 Bad Request`**

```json
{
  "status": 400,
  "message": "잘못된 요청입니다."
}
```

**HTTP Status: `401 Unauthorized`**

```json
{
  "status": 401,
  "message": "인증이 필요합니다."
}
```

**HTTP Status: `403 Forbidden`**

```json
{
  "status": 403,
  "message": "접근이 거부되었습니다."
}
```

**HTTP Status: `404 Not Found`**

```json
{
  "status": 404,
  "message": "리소스를 찾을 수 없습니다."
}
```

---

## 3. 리뷰 삭제 `DELETE`

### Request Parameters

| 파라미터명 | 타입 | 설명 |
|---|---|---|
| `type` | String | 리소스 타입 (`DATASET` / `OPEN_API`) (Path) |
| `id` | Long | 리소스 ID (Path) |
| `reviewId` | Long | 리뷰 ID (Path) |

### Response Codes

| 코드 | 설명 |
|---|---|
| `200` | 요청 정상처리 |
| `401` | 인증 실패 (토큰 없음/만료) |
| `403` | 본인 리뷰가 아님 |
| `404` | 리뷰를 찾을 수 없음 |

### Response Parameters

> 삭제 성공 시 `data`는 `null`을 반환합니다.

### Success Response Example

**HTTP Status: `200 OK`**

```json
{
  "status": 200,
  "message": "리뷰가 삭제되었습니다.",
  "data": null
}
```

### Fail Response Examples

**HTTP Status: `401 Unauthorized`**

```json
{
  "status": 401,
  "message": "인증이 필요합니다."
}
```

**HTTP Status: `403 Forbidden`**

```json
{
  "status": 403,
  "message": "접근이 거부되었습니다."
}
```

**HTTP Status: `404 Not Found`**

```json
{
  "status": 404,
  "message": "리소스를 찾을 수 없습니다."
}
```
