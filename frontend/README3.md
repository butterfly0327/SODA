# 2026-03-22 회고

오늘은 커뮤니티 기능 안정화와 인증 흐름 정합화에 집중했다. 특히 `수정/삭제` API와 `로그아웃` 처리에서 사용자 경험이 끊기지 않도록 개선했다.

## 1) 게시글 수정 시 로그인 만료 이슈

### 문제
- 게시글 수정 버튼 클릭/수정 제출 시 `로그인이 만료되었습니다`가 발생하며 흐름이 끊겼다.
- 수정 API와 백엔드 명세 간 불일치(메서드/응답 처리)가 있었다.

### 해결방식
- 수정 API를 백엔드 명세(`PATCH /api/v1/posts/{postId}`)에 맞췄다.
- 수정 응답을 `void`로 버리지 않고 `{ postId, updatedAt }` 타입으로 받아 상세 이동에 활용했다.
- `401/403/404/400` 상태코드별 에러 분기를 명확히 나눴다.

### 코드
```ts
// frontend/src/api/postApi.ts
updatePost: async (postId, payload) => {
  const response = await apiClient.patch(`/posts/${postId}`, payload);
  return response.data.data; // { postId, updatedAt }
}
```

```ts
// frontend/src/app/pages/CommunityWritePage.tsx
if (status === 401) {
  await logout();
  navigate('/login', { replace: true });
  return;
}
```

## 2) 로그아웃 API 미연결 이슈

### 문제
- 기존 로그아웃은 로컬 상태만 정리했고, 서버 로그아웃 API 호출이 없었다.
- 네트워크 실패 시 사용자 입장에서 로그아웃 완료 여부가 불명확했다.

### 해결방식
- `POST /api/v1/auth/logout` 호출을 추가했다.
- 서버 응답 성공/실패와 무관하게 로컬 토큰/인증 상태를 정리하는 fail-safe로 구현했다.
- 네비게이션/설정/마이페이지 로그아웃 호출부를 `await logout()`로 통일했다.

### 코드
```ts
// frontend/src/api/authApi.ts
export const authApi = {
  logout: async () => {
    await apiClient.post('/auth/logout');
  },
};
```

```ts
// frontend/src/stores/authStore.ts
logout: async () => {
  try {
    await authApi.logout();
  } finally {
    clearAuthState();
  }
}
```

## 3) 게시글 삭제 실패 UX 불일치

### 문제
- 삭제 실패 시 `404`는 목록 이동+토스트, `400`은 상세 페이지 에러 표시로 UX가 달랐다.

### 해결방식
- `400`도 `404`와 동일하게 목록으로 이동하고 토스트를 표시하도록 통일했다.
- `401/403/404` 처리도 정책에 맞게 정리했다.
- 삭제 진행 중 체크박스/취소/삭제 버튼 비활성화로 중복 입력을 방지했다.

### 코드
```ts
// frontend/src/app/pages/CommunityDetailPage.tsx
if (status === 400) {
  navigate('/community', {
    replace: true,
    state: { toastMessage: message || '잘못된 요청입니다.' },
  });
  return;
}
```

```ts
// frontend/src/app/pages/CommunityDetailPage.tsx
if (status === 401) {
  await logout();
  navigate('/login', { replace: true });
  return;
}
```

## 오늘의 정리
- API 명세 정합화는 단순 호출 성공보다 "응답 타입/상태코드 분기/후속 UX"까지 포함해야 안정적이다.
- 인증 관련 로직은 화면별 예외 처리보다 공통 정책(`logout + redirect`)으로 통일할수록 유지보수가 쉬워진다.

# 2026-03-29 회고

오늘은 검색/북마크/커뮤니티/마이페이지/채팅 카드 UI를 일관되게 맞추고, Search 상세 사이드바의 리뷰 표시 이슈(이름/날짜/런타임 에러)를 프론트에서 안정화했다.

## 1) Search 상세 사이드바 리뷰가 안 보이거나 익명으로 보이는 이슈

### 문제
- Search 상세 패널에서 서버 리뷰가 있어도 목록 노출이 누락되는 경우가 있었다.
- 일부 응답에서 작성자 필드가 `author`가 아니라 `name`으로 내려와 `익명`으로 표시되었다.

### 해결방식
- 리뷰 매핑에서 작성자 fallback을 `author -> name -> 익명` 순서로 보강했다.
- 상세 패널 리뷰 렌더 경로를 정리해 full/readOnly 모드 모두에서 일관되게 표시되도록 수정했다.

### 코드
```ts
// frontend/src/app/lib/resourceSearchApi.ts
author: review.author?.trim() || review.name?.trim() || "익명"
```

```ts
// frontend/src/app/components/RecommendationDetailPanel.tsx
const visibleReviews = canManageReviews
  ? activeReviews.filter((review) => !isMyReviewEntry(review))
  : activeReviews;
```

## 2) RecommendationDetailPanel 런타임 에러(`trim` of undefined)

### 문제
- `normalizeAuthorName`가 `author.trim()`을 직접 호출해서 `author`가 `undefined`인 경우 크래시가 발생했다.

### 해결방식
- `normalizeAuthorName`를 nullable-safe로 변경하고, 서버 리뷰 매핑에서도 author 기본값을 보강했다.

### 코드
```ts
// frontend/src/app/components/RecommendationDetailPanel.tsx
function normalizeAuthorName(author: string | null | undefined) {
  return (author ?? "").trim();
}
```

## 3) 리뷰 날짜 가독성 개선

### 문제
- 리뷰 날짜가 원본 ISO 문자열로 그대로 표시되어 가독성이 떨어졌다.
- 잘못된 문자열이 들어오면 `Invalid Date`가 보일 가능성이 있었다.

### 해결방식
- 리뷰 목록/내 리뷰 날짜 모두 `formatDate(...)`를 사용하도록 통일했다.
- 포맷 함수에서 유효하지 않은 날짜를 안전하게 처리하도록 보강했다.

### 코드
```ts
// frontend/src/app/components/RecommendationDetailPanel.tsx
if (Number.isNaN(parsed.getTime())) {
  return dateString;
}
```

## 4) UI 디테일 정리 (커뮤니티 글쓰기/채팅 카드/마이페이지)

### 문제
- 커뮤니티 글쓰기 페이지 버튼/검색 입력 스타일이 페이지 간 불일치했다.
- 채팅 카드 메타 영역 정렬, 북마크 아이콘 동작, 점수/추천순위 배치가 어색했다.
- 마이페이지 `My Posts`, `My Reviews` 날짜 표기에 마침표 형식이 누락되었다.

### 해결방식
- 커뮤니티 글쓰기 페이지의 토글/검색/액션 버튼 스타일을 통일하고, 검색창 placeholder/높이를 정리했다.
- 채팅 카드에서 메타 정렬과 북마크 아이콘 인터랙션을 정리하고 점수 배치 구조를 개선했다.
- 마이페이지 카드의 날짜 말미에 `.`을 일관되게 적용했다.

## 오늘의 정리
- 리뷰 데이터는 "타입 정의 -> 매핑 -> 렌더" 3단계 중 하나만 어긋나도 UI 신뢰도가 크게 떨어진다.
- 디자인 통일 작업은 컴포넌트 단위 공통화(variant/class 재사용)로 접근할수록 회귀가 적고 유지보수가 쉽다.
