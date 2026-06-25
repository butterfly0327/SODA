# MyPage Section Unification Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** MyPage의 `My Posts`, `My Reviews`, `My Bookmarks` 섹션을 공통 카드형 UX로 통일하고, API 응답도 카드 렌더링 기준으로 정리한다.

**Architecture:** 백엔드는 posts/reviews/bookmarks 응답을 카드 렌더링 가능한 최소 메타데이터 기준으로 확장한다. 프론트는 `MyPage` 인라인 렌더링을 줄이고, 공통 section shell과 섹션별 카드 컴포넌트로 분리한다. API 응답을 source of truth로 사용하고 로컬 fallback 의존도를 낮춘다.

**Tech Stack:** Spring Boot, React, TypeScript, Zustand, Vite, JUnit, Node test

---

### Task 1: Posts 응답 계약 확장

**Files:**
- Modify: `C:\Users\SSAFY\Desktop\soda\backend\src\main\java\ssafy\E105\domain\user\dto\response\MyPostResponse.java`
- Modify: `C:\Users\SSAFY\Desktop\soda\backend\src\main\java\ssafy\E105\domain\user\service\UserService.java`
- Test: `C:\Users\SSAFY\Desktop\soda\backend\src\test\java\ssafy\E105\domain\user\service\UserServiceMyPageSectionTest.java`

**Step 1: Write the failing test**

- `getMyPosts()` 응답에 `commentCount`가 포함되는 테스트를 추가한다.

**Step 2: Run test to verify it fails**

Run:

```powershell
.\gradlew.bat test --tests "ssafy.E105.domain.user.service.UserServiceMyPageSectionTest"
```

**Step 3: Write minimal implementation**

- `MyPostResponse`에 `commentCount` 추가
- `UserService#getMyPosts()`에서 `PostEntity`의 댓글 수를 매핑

**Step 4: Run test to verify it passes**

같은 테스트를 다시 실행한다.

**Step 5: Commit**

```bash
git add backend/src/main/java/ssafy/E105/domain/user/dto/response/MyPostResponse.java backend/src/main/java/ssafy/E105/domain/user/service/UserService.java backend/src/test/java/ssafy/E105/domain/user/service/UserServiceMyPageSectionTest.java
git commit -m "feat: expand my posts response for card metadata"
```

### Task 2: Reviews 응답 계약 점검 및 보강

**Files:**
- Modify: `C:\Users\SSAFY\Desktop\soda\backend\src\main\java\ssafy\E105\domain\user\dto\response\MyReviewResponse.java`
- Modify: `C:\Users\SSAFY\Desktop\soda\backend\src\main\java\ssafy\E105\domain\user\service\UserService.java`
- Test: `C:\Users\SSAFY\Desktop\soda\backend\src\test\java\ssafy\E105\domain\user\service\UserServiceMyPageSectionTest.java`

**Step 1: Write the failing test**

- 리뷰 응답이 마이페이지 카드 렌더링에 필요한 최소 필드(`resourceType`, `resourceId`, `resourceTitle`, `rating`, `content`, `createdAt`)를 모두 유지하는 테스트를 명시한다.

**Step 2: Run test to verify it fails or guards current behavior**

Run:

```powershell
.\gradlew.bat test --tests "ssafy.E105.domain.user.service.UserServiceMyPageSectionTest"
```

**Step 3: Write minimal implementation**

- 필요한 필드가 빠져 있다면 DTO/매핑을 보강한다.
- 현재 shape로 충분하면 테스트만 추가하고 DTO는 유지한다.

**Step 4: Run test to verify it passes**

같은 테스트를 다시 실행한다.

**Step 5: Commit**

```bash
git add backend/src/main/java/ssafy/E105/domain/user/dto/response/MyReviewResponse.java backend/src/main/java/ssafy/E105/domain/user/service/UserService.java backend/src/test/java/ssafy/E105/domain/user/service/UserServiceMyPageSectionTest.java
git commit -m "test: lock my reviews response shape for mypage cards"
```

### Task 3: MyPage 프론트 fallback 구조 정리

**Files:**
- Modify: `C:\Users\SSAFY\Desktop\soda\frontend\src\app\pages\MyPage.tsx`
- Modify: `C:\Users\SSAFY\Desktop\soda\frontend\src\api\contracts.ts`
- Modify: `C:\Users\SSAFY\Desktop\soda\frontend\src\api\types.ts`
- Test: `C:\Users\SSAFY\Desktop\soda\frontend\src\app\lib\mypageAdapter.test.ts`

**Step 1: Write the failing test**

- API 응답만으로 게시글/리뷰/북마크 카드 view model이 생성되는 테스트를 추가한다.

**Step 2: Run test to verify it fails**

Run:

```powershell
node --test --experimental-strip-types frontend/src/app/lib/mypageAdapter.test.ts
```

**Step 3: Write minimal implementation**

- `contracts.ts`에 확장된 posts/reviews shape 반영
- `MyPage`에서 `posts`, `projects`, `resourceReviews` fallback 의존도를 줄이고 API 응답 기준으로 렌더링

**Step 4: Run test to verify it passes**

같은 테스트를 다시 실행한다.

**Step 5: Commit**

```bash
git add frontend/src/app/pages/MyPage.tsx frontend/src/api/contracts.ts frontend/src/api/types.ts frontend/src/app/lib/mypageAdapter.test.ts
git commit -m "refactor: make mypage sections api-driven"
```

### Task 4: 공통 section shell과 카드 컴포넌트 분리

**Files:**
- Create: `C:\Users\SSAFY\Desktop\soda\frontend\src\app\components\mypage\MyPageSection.tsx`
- Create: `C:\Users\SSAFY\Desktop\soda\frontend\src\app\components\mypage\MyPostCard.tsx`
- Create: `C:\Users\SSAFY\Desktop\soda\frontend\src\app\components\mypage\MyReviewCard.tsx`
- Modify: `C:\Users\SSAFY\Desktop\soda\frontend\src\app\pages\MyPage.tsx`

**Step 1: Write the failing test**

- `MyPage`가 섹션별 공통 레이아웃을 사용하는 스냅샷/렌더 테스트를 추가한다.

**Step 2: Run test to verify it fails**

Run:

```powershell
node --test --experimental-strip-types frontend/src/app/lib/mypageAdapter.test.ts
```

**Step 3: Write minimal implementation**

- 공통 section wrapper 생성
- posts/reviews는 전용 카드 컴포넌트 생성
- bookmarks는 기존 `ResourceCard` 재사용

**Step 4: Run test to verify it passes**

테스트와 빌드를 다시 실행한다.

**Step 5: Commit**

```bash
git add frontend/src/app/components/mypage frontend/src/app/pages/MyPage.tsx
git commit -m "feat: unify mypage section cards"
```

### Task 5: 상세 패널 동작 통일

**Files:**
- Modify: `C:\Users\SSAFY\Desktop\soda\frontend\src\app\pages\MyPage.tsx`
- Modify: `C:\Users\SSAFY\Desktop\soda\frontend\src\app\lib\resourceSearchApi.ts`

**Step 1: Write the failing test**

- 리뷰 카드 클릭 시 상세 패널이 열리고, 게시글 카드는 커뮤니티 상세로 이동하는 흐름을 검증하는 테스트를 추가한다.

**Step 2: Run test to verify it fails**

Run:

```powershell
node --test --experimental-strip-types frontend/src/app/lib/mypageAdapter.test.ts
```

**Step 3: Write minimal implementation**

- 리뷰/북마크는 같은 상세 패널 사용
- 게시글은 기존처럼 커뮤니티 상세로 이동

**Step 4: Run test to verify it passes**

같은 테스트를 다시 실행한다.

**Step 5: Commit**

```bash
git add frontend/src/app/pages/MyPage.tsx frontend/src/app/lib/resourceSearchApi.ts
git commit -m "feat: align mypage detail actions"
```

### Task 6: 검증

**Files:**
- Verify only

**Step 1: Run backend tests**

```powershell
.\gradlew.bat test --tests "ssafy.E105.domain.user.service.UserServiceMyPageSectionTest"
```

**Step 2: Run frontend tests**

```powershell
node --test --experimental-strip-types frontend/src/app/lib/mypageAdapter.test.ts
```

**Step 3: Run build**

```powershell
cd frontend
npm run build
```

**Step 4: Browser verification**

- My Posts / My Reviews / My Bookmarks 진입
- 카드 레이아웃 통일 확인
- 게시글 상세 이동 확인
- 리뷰/북마크 상세 패널 확인

**Step 5: Commit if verification changes were needed**

```bash
git add .
git commit -m "chore: finalize mypage section unification"
```
