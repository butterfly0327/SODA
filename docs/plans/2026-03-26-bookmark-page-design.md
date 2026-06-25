# Bookmark Page Design

## 1. Goal

신설된 북마크 페이지에서 기존 북마크 조회 API를 사용해 사용자가 저장한 `Dataset` / `Open API`를 카드형 UI로 보여주고, 같은 페이지 안에서 북마크 해제까지 처리한다.

## 2. Current Context

관련 코드:

- [C:\Users\SSAFY\Desktop\soda\frontend\src\app\pages\BookmarkPage.tsx](C:\Users\SSAFY\Desktop\soda\frontend\src\app\pages\BookmarkPage.tsx)
- [C:\Users\SSAFY\Desktop\soda\frontend\src\app\components\SearchResult.tsx](C:\Users\SSAFY\Desktop\soda\frontend\src\app\components\SearchResult.tsx)
- [C:\Users\SSAFY\Desktop\soda\frontend\src\app\pages\MyPage.tsx](C:\Users\SSAFY\Desktop\soda\frontend\src\app\pages\MyPage.tsx)
- [C:\Users\SSAFY\Desktop\soda\frontend\src\api\userApi.ts](C:\Users\SSAFY\Desktop\soda\frontend\src\api\userApi.ts)
- [C:\Users\SSAFY\Desktop\soda\frontend\src\api\bookmarkApi.ts](C:\Users\SSAFY\Desktop\soda\frontend\src\api\bookmarkApi.ts)
- [C:\Users\SSAFY\Desktop\soda\backend\src\main\java\ssafy\E105\domain\user\service\UserService.java](C:\Users\SSAFY\Desktop\soda\backend\src\main\java\ssafy\E105\domain\user\service\UserService.java)
- [C:\Users\SSAFY\Desktop\soda\backend\src\main\java\ssafy\E105\domain\bookmark\service\BookmarkService.java](C:\Users\SSAFY\Desktop\soda\backend\src\main\java\ssafy\E105\domain\bookmark\service\BookmarkService.java)

현재 상태:

- 북마크 페이지 라우트는 이미 존재한다.
- 북마크 목록 API는 이미 존재한다.
- 북마크 추가/삭제 API도 이미 존재한다.
- `BookmarkPage`는 현재 리스트형 UI와 필터/페이지네이션 골격을 이미 갖고 있다.
- `SearchResult`는 카드형 UI를 이미 제공하지만 검색 결과 문맥에 강하게 묶여 있다.

## 3. API Understanding

### 3.1 북마크 조회

프론트:

- [C:\Users\SSAFY\Desktop\soda\frontend\src\api\userApi.ts](C:\Users\SSAFY\Desktop\soda\frontend\src\api\userApi.ts)
  - `GET /users/me/bookmarks`

응답 필드:

- `id`
- `resourceType`
- `resourceId`
- `resourceTitle`
- `score`
- `isFree`
- `bookmarkedAt`

백엔드 구현:

- [C:\Users\SSAFY\Desktop\soda\backend\src\main\java\ssafy\E105\domain\user\service\UserService.java](C:\Users\SSAFY\Desktop\soda\backend\src\main\java\ssafy\E105\domain\user\service\UserService.java)

지원 필터:

- `keyword`
- `type`
- `freeOnly`
- `page`
- `size`

### 3.2 북마크 등록/삭제

프론트:

- [C:\Users\SSAFY\Desktop\soda\frontend\src\api\bookmarkApi.ts](C:\Users\SSAFY\Desktop\soda\frontend\src\api\bookmarkApi.ts)

엔드포인트:

- `POST /bookmarks`
- `DELETE /bookmarks/{bookmarkId}`

백엔드 구현:

- [C:\Users\SSAFY\Desktop\soda\backend\src\main\java\ssafy\E105\domain\bookmark\service\BookmarkService.java](C:\Users\SSAFY\Desktop\soda\backend\src\main\java\ssafy\E105\domain\bookmark\service\BookmarkService.java)

삭제는 `bookmarkId` 기준이다.

즉 북마크 페이지에서 해제를 하려면 `resourceId`가 아니라 목록 API에서 내려온 `id`를 그대로 들고 있어야 한다.

## 4. Options

### Option A. BookmarkPage만 카드형으로 개별 구현

장점:

- 변경 범위가 좁다.
- 현재 페이지 상태 로직을 거의 그대로 유지할 수 있다.

단점:

- 검색 결과 카드와 UI가 쉽게 벌어진다.
- 북마크 버튼, 배지, 메타 정보 렌더링 로직이 중복된다.

### Option B. SearchResult를 북마크 페이지에서 그대로 재사용

장점:

- 카드형 UI를 빠르게 맞출 수 있다.

단점:

- 검색 결과 전용 컨텍스트(`analysis`, `recommendation reasons`, `compare`)가 섞여 있다.
- 북마크 API 응답에 없는 필드를 억지로 채워야 한다.
- 북마크 페이지 필터/정렬과 중복 구조가 생긴다.

### Option C. 카드 컴포넌트를 공용화하고 BookmarkPage는 북마크 데이터만 관리

장점:

- 검색 결과와 북마크 페이지 간 UI 일관성이 좋다.
- 북마크 API 응답 구조에 맞는 북마크 전용 view model을 가질 수 있다.
- 향후 마이페이지 북마크 탭도 같은 카드로 맞출 수 있다.

단점:

- Option A보다 작업량은 조금 더 있다.

## 5. Decision

`Option C`를 채택한다.

즉:

- `BookmarkPage`는 조회/필터/페이지네이션/삭제 상태를 관리한다.
- 카드 렌더링은 검색 결과와 시각 톤을 맞춘 공용 카드 계층으로 정리한다.
- 검색 결과 전용 요소는 제외한다.

## 6. Target UX

### 6.1 페이지 구성

- 페이지 제목
- 북마크 검색창
- 타입 필터: 전체 / Dataset / Open API
- 무료만 보기
- 총 개수 / 현재 범위
- 카드형 목록
- 페이지네이션

### 6.2 카드 구성

Dataset / Open API 공통:

- 타입 배지
- 제목
- 평점
- 요금 정보
- 북마크 등록 시각
- 상세보기 버튼
- 북마크 토글 버튼

제외:

- 비교하기
- 추천 이유
- 검색 분석 문구

## 7. Data Flow

1. 페이지 진입 시 `GET /users/me/bookmarks`
2. 검색어/필터/페이지 변경 시 목록 재조회
3. 응답 `content`를 북마크 카드용 view model로 변환
4. 카드에서 상세보기 클릭 시 `/resource/:id?type=...` 이동
5. 카드에서 북마크 해제 클릭 시 `DELETE /bookmarks/{bookmarkId}`
6. 성공 시 현재 목록과 총 개수를 즉시 갱신

## 8. Bookmark Toggle Behavior

북마크 페이지에서는 토글의 의미가 사실상 "해제"다.

정책:

- 카드의 북마크 아이콘은 기본적으로 활성 상태로 보인다.
- 클릭 시 북마크 해제 API 호출
- 성공 시 현재 리스트에서 제거

오류 처리:

- `401`: 로그인 만료 메시지
- `403`: 권한 오류 메시지
- `404`: 이미 삭제된 북마크로 간주하고 목록에서 제거
- 기타: 일반 삭제 실패 메시지

페이지 보정:

- 마지막 아이템 삭제 후 현재 페이지가 비면 이전 페이지로 이동
- `totalElements`와 `totalPages`를 함께 보정

## 9. Architecture

권장 구조:

- `BookmarkPage`
  - fetch state
  - filter state
  - pagination state
  - bookmark delete action
- `bookmarkPageAdapter`
  - API 응답 -> 카드 view model 변환
- `ResourceBookmarkCard` 또는 유사한 공용 카드 컴포넌트
  - dataset/api 타입별 메타 정보 표시
  - 상세보기 / 북마크 토글

## 10. Risks

- `SearchResult`를 그대로 재사용하면 검색 전용 문맥이 너무 섞인다.
- `bookmarkId`와 `resourceId`를 혼동하면 삭제가 깨진다.
- 삭제 후 페이지 보정을 안 하면 빈 페이지에 머무를 수 있다.
- 조회 실패/삭제 실패 메시지를 분리하지 않으면 UX가 불명확해진다.

## 11. Success Criteria

- 북마크 페이지에서 목록이 카드형으로 보인다.
- 검색/필터/무료 옵션/페이지네이션이 유지된다.
- 상세보기 이동이 된다.
- 카드의 북마크 버튼으로 해제가 된다.
- 해제 즉시 화면에서 카드가 사라진다.
- 마지막 카드 삭제 시 페이지 상태가 깨지지 않는다.
