# Bookmark Page Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 북마크 페이지를 카드형 UX로 완성하고 기존 북마크 조회/삭제 API를 이용해 목록 조회와 해제를 안정적으로 처리한다.

**Architecture:** `BookmarkPage`는 조회·필터·페이지네이션·삭제 상태를 관리하고, API 응답은 북마크 카드 전용 adapter를 통해 공용 카드 view model로 변환한다. 카드 렌더링은 검색 결과와 톤을 맞춘 공용 카드 컴포넌트 계층으로 분리하며, 토글은 `DELETE /bookmarks/{bookmarkId}`만 사용한다.

**Tech Stack:** React, TypeScript, React Router, Axios API client, existing shadcn/ui components

---

### Task 1: 북마크 카드 view model과 adapter 추가

**Files:**
- Create: `C:\Users\SSAFY\Desktop\soda\frontend\src\app\lib\bookmarkPageAdapter.ts`
- Modify: `C:\Users\SSAFY\Desktop\soda\frontend\src\types\recommendation.ts`
- Test: `C:\Users\SSAFY\Desktop\soda\frontend\src\app\lib\bookmarkPageAdapter.test.ts`

**Step 1: Write the failing test**

테스트 케이스:
- `DATASET` 북마크 응답이 dataset 카드 view model로 변환된다
- `OPEN_API` 북마크 응답이 api 카드 view model로 변환된다
- `bookmarkId`, `resourceId`, `resourceType`, `bookmarkedAt`가 보존된다

**Step 2: Run test to verify it fails**

Run:
```bash
node --test --experimental-strip-types frontend/src/app/lib/bookmarkPageAdapter.test.ts
```

Expected:
- FAIL because adapter file does not exist

**Step 3: Write minimal implementation**

구현 내용:
- 북마크 API 응답을 카드 렌더링용 구조로 변환
- `bookmarkId`와 `resourceId`를 분리 유지
- dataset/api별 기본 메타 표시 문자열 준비

**Step 4: Run test to verify it passes**

Run:
```bash
node --test --experimental-strip-types frontend/src/app/lib/bookmarkPageAdapter.test.ts
```

Expected:
- PASS

**Step 5: Commit**

Do not commit yet without user approval.

### Task 2: 북마크 전용 카드 컴포넌트 추가

**Files:**
- Create: `C:\Users\SSAFY\Desktop\soda\frontend\src\app\components\ResourceBookmarkCard.tsx`
- Modify: `C:\Users\SSAFY\Desktop\soda\frontend\src\app\components\SearchResult.tsx`

**Step 1: Write the failing component expectations**

테스트 없이 구현하더라도 아래 조건을 코드 기준으로 만족시킨다:
- 타입 배지 표시
- 제목/평점/요금/북마크 등록일 표시
- 상세보기 버튼
- 북마크 해제 버튼
- dataset/api 카드 레이아웃 차이 최소화

**Step 2: Implement minimal component**

구현 내용:
- 검색 결과 카드 톤을 유지하되 검색 전용 정보 제거
- `bookmarked` 상태는 항상 `true`
- 액션은 `onOpenDetail`, `onRemoveBookmark`

**Step 3: Smoke-check in page after integration**

Run after Task 3 integration:
```bash
npm run build
```

Expected:
- component type errors 없음

**Step 4: Commit**

Do not commit yet without user approval.

### Task 3: BookmarkPage를 카드형 페이지로 재구성

**Files:**
- Modify: `C:\Users\SSAFY\Desktop\soda\frontend\src\app\pages\BookmarkPage.tsx`
- Modify: `C:\Users\SSAFY\Desktop\soda\frontend\src\api\userApi.ts`

**Step 1: Add state for delete handling**

필요 상태:
- `isLoading`
- `loadError`
- `deleteError`
- `isRemovingBookmarkId`
- fetched `content`
- `totalCount`
- `totalPages`
- `currentPage`

**Step 2: Integrate adapter**

구현 내용:
- `userApi.getMyBookmarks(...)` 결과를 카드 view model로 변환
- 기존 필터/검색/페이지네이션 로직 유지

**Step 3: Wire open detail navigation**

구현 내용:
- `resourceId`와 `resourceType`로 `/resource/:id?type=dataset|api` 이동

**Step 4: Wire bookmark removal**

구현 내용:
- `bookmarkApi.deleteBookmark(bookmarkId)` 호출
- 성공 시 현재 목록에서 제거
- `404`면 이미 삭제된 것으로 간주하고 제거
- `401/403`는 메시지 분리

**Step 5: Add page correction**

구현 내용:
- 마지막 카드 삭제 후 현재 페이지가 비면 이전 페이지로 이동
- `totalElements`, `totalPages` 보정

**Step 6: Run build**

Run:
```bash
npm run build
```

Expected:
- PASS

**Step 7: Commit**

Do not commit yet without user approval.

### Task 4: 북마크 토글 UX를 기존 화면과 맞추기

**Files:**
- Modify: `C:\Users\SSAFY\Desktop\soda\frontend\src\app\pages\BookmarkPage.tsx`
- Modify: `C:\Users\SSAFY\Desktop\soda\frontend\src\app\components\ResourceBookmarkCard.tsx`

**Step 1: Align button semantics**

구현 내용:
- `aria-label="북마크 해제"`
- tooltip/title 정리
- 아이콘 활성 상태 고정

**Step 2: Add loading protection**

구현 내용:
- 같은 카드 연속 클릭 방지
- 삭제 중 버튼 disable

**Step 3: Display empty state after removal**

구현 내용:
- 북마크가 0개가 되면 empty state 표시

**Step 4: Run build**

Run:
```bash
npm run build
```

Expected:
- PASS

**Step 5: Commit**

Do not commit yet without user approval.

### Task 5: 브라우저 smoke test

**Files:**
- No new source files required

**Step 1: Open bookmark page**

Check:
- 페이지 진입 가능
- 필터/검색 입력 표시

**Step 2: Validate card rendering**

Check:
- dataset/api 카드가 타입별로 보인다
- 제목/메타 정보/상세보기 버튼이 보인다

**Step 3: Validate bookmark removal**

Check:
- 카드의 북마크 버튼 클릭 시 해제된다
- 목록에서 즉시 제거된다
- 페이지가 비는 경우 보정된다

**Step 4: Validate navigation**

Check:
- 상세보기 버튼 클릭 시 상세 페이지 이동

**Step 5: Final verification**

Run:
```bash
npm run build
```

Expected:
- PASS

**Step 6: Commit**

Do not commit yet without user approval.
