# MyPage Section Unification Design

## Goal

`My Posts`, `My Reviews`, `My Bookmarks` 3개 섹션의 정보 구조와 시각 스타일을 통일해서, 마이페이지가 API shape 차이 때문에 섹션마다 전혀 다른 화면처럼 보이지 않도록 정리한다.

## Current Problems

### 1. 섹션별 응답 shape 편차가 크다

- `GET /users/me/posts`
  - 현재 `id`, `title`, `createdAt`, `likeCount`만 내려준다.
  - 프론트는 로컬 fallback 데이터와 섞어서 `commentCount`까지 억지로 보정한다.
- `GET /users/me/reviews`
  - `resourceType`, `resourceId`, `resourceTitle`, `rating`, `content`, `createdAt`만 내려준다.
  - 리소스 카드처럼 보이기에는 메타데이터가 적다.
- `GET /users/me/bookmarks`
  - 이미 카드 렌더링용 메타데이터가 풍부하다.
  - 현재 세 섹션 중 가장 정보량이 많고 UI 완성도가 높다.

### 2. 프론트가 API 응답과 로컬 store fallback을 동시에 섞는다

- [MyPage.tsx](C:\Users\SSAFY\Desktop\soda\frontend\src\app\pages\MyPage.tsx)는
  - `posts`
  - `projects.savedResources`
  - `resourceReviews`
  와 API 응답을 동시에 섞어 사용한다.
- 이 구조 때문에
  - 섹션별 데이터 shape가 더 달라지고
  - API 기준 UX가 아니라 “fallback이 우연히 채운 값” 기준 UX가 된다.

### 3. UI 컴포넌트 재사용 기준이 없다

- 게시글: 단순 리스트 버튼
- 리뷰: 리뷰 전용 리스트 + 우측 패널
- 북마크: 리소스 카드형
- 같은 마이페이지 내부인데도 레이아웃, 정보 배치, 액션 위치가 모두 다르다.

## Approaches

### A. 프론트만 정리

- API는 그대로 두고
- 프론트에서 부족한 값은 숨기거나 fallback으로 맞춘다.

장점:
- 작업량이 가장 적다.

단점:
- API와 화면의 책임이 계속 꼬인다.
- 로컬 fallback 구조가 유지된다.
- 섹션별 모양은 비슷해질 수 있어도 정보 밀도 차이는 남는다.

### B. API를 카드 기준으로 확장하고, 프론트는 섹션 공통 레이아웃으로 통일한다

- `My Posts`, `My Reviews`, `My Bookmarks`를 모두 “카드 렌더링 가능한 응답”으로 맞춘다.
- 프론트는 공통 카드 shell + 섹션별 body를 쓴다.
- 마이페이지는 API만 신뢰하고 로컬 fallback은 제거하거나 최소화한다.

장점:
- 구조가 가장 자연스럽다.
- 프론트와 백엔드 책임이 명확하다.
- 발표 전 품질 개선 대비 작업량이 적절하다.

단점:
- 백엔드 DTO/서비스 수정이 필요하다.

### C. 마이페이지 전용 통합 endpoint를 새로 만든다

- `GET /users/me/overview` 같은 새 API로 세 섹션을 한 번에 내려준다.

장점:
- 완전히 통합된 shape 설계가 가능하다.

단점:
- 범위가 커진다.
- 기존 API들과 중복이 생긴다.
- 발표 전 변경량 대비 이득이 작다.

## Recommendation

### 추천안: B

- 기존 endpoint는 유지한다.
- 각 endpoint 응답을 “카드 렌더링 가능한 최소 메타데이터” 기준으로 확장한다.
- 프론트는 공통 section/card shell을 만들고, 섹션별 body만 다르게 둔다.
- `MyPage`는 API 응답을 1차 source of truth로 쓰고 로컬 fallback 의존도를 줄인다.

이 방식이 현재 북마크 작업과도 가장 잘 맞는다.

## Target UX

### 공통 원칙

- 세 섹션 모두 같은 카드 표면(`surface`)과 spacing, 액션 배치 규칙을 사용한다.
- 카드 상단은 제목 + 보조 메타 + 우측 액션으로 통일한다.
- 카드 하단은 섹션별 CTA를 둔다.
- 빈 상태, 오류 상태, 페이지네이션 위치를 통일한다.

### My Posts

- 제목
- 작성일
- 좋아요 수
- 댓글 수
- 필요 시 카테고리
- CTA: `게시글 보기`

### My Reviews

- 대상 리소스 제목
- 리소스 타입 배지
- 평점
- 리뷰 본문 2줄 미리보기
- 작성일
- CTA: `리소스 보기`
  - 데스크탑: 우측 상세 패널
  - 모바일: 오버레이 패널

### My Bookmarks

- 현재 리소스 카드 기준 유지
- 도메인/공개 상태/상용 사용/비용/태그 표시
- CTA: `상세보기`
- 북마크 토글 유지

## Backend Design

### Posts

현재 [MyPostResponse.java](C:\Users\SSAFY\Desktop\soda\backend\src\main\java\ssafy\E105\domain\user\dto\response\MyPostResponse.java)는 너무 얇다.

확장 후보:

- `commentCount`
- `category` 또는 `referenceCount`
- 필요 시 `updatedAt`

최소 권장:

```json
{
  "id": 1,
  "title": "게시글 제목",
  "createdAt": "...",
  "likeCount": 3,
  "commentCount": 5
}
```

### Reviews

현재 [MyReviewResponse.java](C:\Users\SSAFY\Desktop\soda\backend\src\main\java\ssafy\E105\domain\user\dto\response\MyReviewResponse.java)는 카드 렌더링에는 충분하지만, 리소스 문맥이 조금 약하다.

최소 권장:

- 현 구조 유지
- 필요하면 `resourceCreatedAt` 정도만 추가 검토

즉 우선은:

```json
{
  "id": 10,
  "resourceType": "DATASET",
  "resourceId": 123,
  "resourceTitle": "리소스 이름",
  "rating": 4,
  "content": "리뷰 내용",
  "createdAt": "..."
}
```

### Bookmarks

- 현재 확장된 bookmark 응답 구조를 유지한다.
- 목록 카드에 필요한 메타데이터는 이미 충분하다.

## Frontend Design

### 1. Section shell 분리

`MyPage` 안에서 세 섹션을 인라인으로 직접 그리지 말고, 아래 계층으로 분리한다.

- `MyPageSection`
  - 제목/설명/빈 상태/오류/페이지네이션 공통
- `MyPostCard`
- `MyReviewCard`
- `ResourceCard` (기존 bookmark/resource용)

### 2. API-only 기준으로 재정리

`MyPage`는 아래 로컬 fallback 의존도를 제거 또는 축소한다.

- `posts`
- `projects.savedResources`
- `resourceReviews`

발표 기준으로는 API 응답을 신뢰하는 편이 낫다.

### 3. 상세 패널 통일

- 리뷰와 북마크 리소스는 같은 `RecommendationDetailPanel` UX를 사용한다.
- 게시글은 커뮤니티 상세 페이지로 이동한다.

## Data Flow

### Posts

1. `GET /users/me/posts`
2. 응답을 `MyPostCardViewModel[]`로 변환
3. 카드 렌더
4. `게시글 보기` 클릭 시 `/community/:id` 이동

### Reviews

1. `GET /users/me/reviews`
2. 응답을 `MyReviewCardViewModel[]`로 변환
3. 카드 렌더
4. `리소스 보기` 클릭 시 상세 API 호출 후 우측 패널 표시

### Bookmarks

1. `GET /users/me/bookmarks`
2. 응답을 `ResourceCardViewModel[]`로 변환
3. 카드 렌더
4. `상세보기` 클릭 시 우측 패널 표시
5. 북마크 토글 시 목록 보정

## Error Handling

- API 실패 시 각 섹션별 에러 메시지 노출은 유지하되 스타일을 통일한다.
- 인증 만료는 기존 auth 흐름을 그대로 따른다.
- 패널 상세 조회 실패 시 카드 기본 정보는 유지하고 패널만 fallback 상태를 보여준다.

## Testing

### Backend

- posts 응답에 `commentCount` 포함 여부 테스트
- reviews/bookmarks 응답 회귀 테스트

### Frontend

- `MyPage` 섹션별 view model adapter 테스트
- 북마크/리뷰 패널 열기 테스트
- `npm run build`

### Browser

- My Posts / My Reviews / My Bookmarks 진입
- 섹션 카드 spacing/배지/버튼 위치 일관성 확인
- 리뷰/북마크 상세 패널 확인
- 게시글 상세 이동 확인

## Scope Decision

이번 작업 범위:

- 마이페이지 3개 섹션 카드형 통일
- posts/reviews API 최소 확장
- 프론트 fallback 구조 정리

이번 작업 범위 제외:

- 새 endpoint 추가
- 커뮤니티 상세 side panel 신설
- bookmark/review 외의 새로운 상세 API 개편
