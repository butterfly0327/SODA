import { useEffect, useMemo, useState } from "react";

import { bookmarkApi } from "@/api/bookmarkApi";
import type { MyBookmarkItemResponseDto } from "@/api/contracts";
import { userApi } from "@/api/userApi";
import type {
  MyBookmarksPage,
  MyPostsPage,
  MyProfile,
  MyReviewsPage,
} from "@/api/types";
import { getApiErrorInfo } from "@/app/shared/lib/apiError";
import {
  formatMyPageDate,
  mapMyPostItemToCard,
  mapMyReviewItemToCard,
} from "@/app/features/mypage/adapters/mypageAdapter";

export const MY_PAGE_SIZE = 10;

type UseMyPageDataOptions = {
  isAuthenticated: boolean;
  fallbackName?: string | null;
  fallbackEmail?: string | null;
  onRemovedFromSelectedDetail: (bookmark: MyBookmarkItemResponseDto) => void;
};

function getSafeTotalPages(totalPages: number, totalElements: number, size: number) {
  const safeSize = size > 0 ? size : MY_PAGE_SIZE;
  const computedPages = Math.max(1, Math.ceil(Math.max(0, totalElements) / safeSize));
  return Math.max(totalPages, computedPages);
}

export function useMyPageData({
  isAuthenticated,
  fallbackName,
  fallbackEmail,
  onRemovedFromSelectedDetail,
}: UseMyPageDataOptions) {
  const [postsPageIndex, setPostsPageIndex] = useState(0);
  const [reviewsPageIndex, setReviewsPageIndex] = useState(0);
  const [bookmarksPageIndex, setBookmarksPageIndex] = useState(0);

  const [profile, setProfile] = useState<MyProfile | null>(null);
  const [profileError, setProfileError] = useState<string | null>(null);
  const [myPostsPage, setMyPostsPage] = useState<MyPostsPage | null>(null);
  const [myPostsError, setMyPostsError] = useState<string | null>(null);
  const [myReviewsPage, setMyReviewsPage] = useState<MyReviewsPage | null>(null);
  const [myReviewsError, setMyReviewsError] = useState<string | null>(null);
  const [myBookmarksPage, setMyBookmarksPage] = useState<MyBookmarksPage | null>(null);
  const [myBookmarksError, setMyBookmarksError] = useState<string | null>(null);
  const [removingBookmarkId, setRemovingBookmarkId] = useState<number | null>(null);

  useEffect(() => {
    if (!isAuthenticated) {
      setProfile(null);
      setProfileError(null);
      setMyPostsPage(null);
      setMyPostsError(null);
      setMyReviewsPage(null);
      setMyReviewsError(null);
      setMyBookmarksPage(null);
      setMyBookmarksError(null);
      setPostsPageIndex(0);
      setReviewsPageIndex(0);
      setBookmarksPageIndex(0);
      return;
    }

    let cancelled = false;

    const fetchProfile = async () => {
      try {
        const profileResult = await userApi.getMyProfile();
        if (cancelled) return;
        setProfile(profileResult);
        setProfileError(null);
      } catch {
        if (cancelled) return;
        setProfileError("프로필 정보를 불러오지 못했습니다.");
      }
    };

    void fetchProfile();

    return () => {
      cancelled = true;
    };
  }, [isAuthenticated]);

  useEffect(() => {
    if (!isAuthenticated) {
      return;
    }

    let cancelled = false;

    const fetchMyPosts = async () => {
      try {
        const result = await userApi.getMyPosts(postsPageIndex, MY_PAGE_SIZE);
        if (cancelled) return;
        setMyPostsPage(result);
        setMyPostsError(null);
      } catch {
        if (cancelled) return;
        setMyPostsError("내 게시글 목록을 불러오지 못했습니다.");
      }
    };

    void fetchMyPosts();

    return () => {
      cancelled = true;
    };
  }, [isAuthenticated, postsPageIndex]);

  useEffect(() => {
    if (!isAuthenticated) {
      return;
    }

    let cancelled = false;

    const fetchMyReviews = async () => {
      try {
        const result = await userApi.getMyReviews(reviewsPageIndex, MY_PAGE_SIZE);
        if (cancelled) return;
        setMyReviewsPage(result);
        setMyReviewsError(null);
      } catch {
        if (cancelled) return;
        setMyReviewsError("내 리뷰 목록을 불러오지 못했습니다.");
      }
    };

    void fetchMyReviews();

    return () => {
      cancelled = true;
    };
  }, [isAuthenticated, reviewsPageIndex]);

  useEffect(() => {
    if (!isAuthenticated) {
      return;
    }

    let cancelled = false;

    const fetchMyBookmarks = async () => {
      try {
        const result = await userApi.getMyBookmarks(bookmarksPageIndex, MY_PAGE_SIZE);
        if (cancelled) return;
        setMyBookmarksPage(result);
        setMyBookmarksError(null);
      } catch {
        if (cancelled) return;
        setMyBookmarksError("내 북마크 목록을 불러오지 못했습니다.");
      }
    };

    void fetchMyBookmarks();

    return () => {
      cancelled = true;
    };
  }, [bookmarksPageIndex, isAuthenticated]);

  const visiblePosts = useMemo(
    () => (myPostsPage?.content ?? []).map(mapMyPostItemToCard),
    [myPostsPage],
  );
  const visibleReviews = useMemo(
    () => (myReviewsPage?.content ?? []).map(mapMyReviewItemToCard),
    [myReviewsPage],
  );
  const visibleBookmarks = useMemo(() => myBookmarksPage?.content ?? [], [myBookmarksPage]);

  const displayName = profile?.name?.trim() || fallbackName?.trim() || "";
  const displayEmail = profile?.email || fallbackEmail || "ssafy@ssafy.com";
  const displayCreatedAt = profile?.createdAt
    ? formatMyPageDate(profile.createdAt)
    : "가입일 정보 없음";
  const displayPostCount = profile?.postCount ?? myPostsPage?.totalElements ?? 0;
  const displayReviewCount = profile?.reviewCount ?? myReviewsPage?.totalElements ?? 0;
  const displayBookmarkCount = profile?.bookmarkCount ?? myBookmarksPage?.totalElements ?? 0;

  const effectivePostsTotalElements = Math.max(
    myPostsPage?.totalElements ?? 0,
    typeof displayPostCount === "number" ? displayPostCount : 0,
  );
  const effectiveReviewsTotalElements = Math.max(
    myReviewsPage?.totalElements ?? 0,
    typeof displayReviewCount === "number" ? displayReviewCount : 0,
  );
  const effectiveBookmarksTotalElements = Math.max(
    myBookmarksPage?.totalElements ?? 0,
    typeof displayBookmarkCount === "number" ? displayBookmarkCount : 0,
  );

  const myPostsTotalPages = myPostsPage
    ? getSafeTotalPages(myPostsPage.totalPages, effectivePostsTotalElements, myPostsPage.size)
    : 1;
  const myReviewsTotalPages = myReviewsPage
    ? getSafeTotalPages(
        myReviewsPage.totalPages,
        effectiveReviewsTotalElements,
        myReviewsPage.size,
      )
    : 1;
  const myBookmarksTotalPages = myBookmarksPage
    ? getSafeTotalPages(
        myBookmarksPage.totalPages,
        effectiveBookmarksTotalElements,
        myBookmarksPage.size,
      )
    : 1;

  const myPostsCurrentPage = myPostsPage?.page ?? postsPageIndex;
  const myReviewsCurrentPage = myReviewsPage?.page ?? reviewsPageIndex;
  const myBookmarksCurrentPage = myBookmarksPage?.page ?? bookmarksPageIndex;

  const handleRemoveBookmark = async (bookmark: MyBookmarkItemResponseDto) => {
    if (removingBookmarkId !== null) {
      return;
    }

    setMyBookmarksError(null);
    setRemovingBookmarkId(bookmark.bookmarkId);

    try {
      await bookmarkApi.deleteBookmark(bookmark.bookmarkId);

      const isLastItemOnPage = visibleBookmarks.length === 1;
      const nextPageIndex =
        isLastItemOnPage && bookmarksPageIndex > 0 ? bookmarksPageIndex - 1 : bookmarksPageIndex;
      const refreshed = await userApi.getMyBookmarks(nextPageIndex, MY_PAGE_SIZE);

      setMyBookmarksPage(refreshed);
      setBookmarksPageIndex(nextPageIndex);
      onRemovedFromSelectedDetail(bookmark);
    } catch (error) {
      const { status, message } = getApiErrorInfo(error);

      if (status === 401) {
        setMyBookmarksError(message || "로그인이 만료되었습니다. 다시 로그인해주세요.");
      } else if (status === 403) {
        setMyBookmarksError(message || "본인이 등록한 북마크만 삭제할 수 있습니다.");
      } else if (status === 404) {
        const nextPageIndex =
          visibleBookmarks.length === 1 && bookmarksPageIndex > 0
            ? bookmarksPageIndex - 1
            : bookmarksPageIndex;
        const refreshed = await userApi.getMyBookmarks(nextPageIndex, MY_PAGE_SIZE);
        setMyBookmarksPage(refreshed);
        setBookmarksPageIndex(nextPageIndex);
        onRemovedFromSelectedDetail(bookmark);
        setMyBookmarksError(message || "이미 삭제되었거나 존재하지 않는 북마크입니다.");
      } else {
        setMyBookmarksError("북마크 삭제 중 오류가 발생했습니다.");
      }
    } finally {
      setRemovingBookmarkId(null);
    }
  };

  return {
    profileError,
    myPostsError,
    myReviewsError,
    myBookmarksError,
    postsPageIndex,
    setPostsPageIndex,
    reviewsPageIndex,
    setReviewsPageIndex,
    bookmarksPageIndex,
    setBookmarksPageIndex,
    visiblePosts,
    visibleReviews,
    visibleBookmarks,
    displayName,
    displayEmail,
    displayCreatedAt,
    displayPostCount,
    displayReviewCount,
    displayBookmarkCount,
    effectivePostsTotalElements,
    effectiveReviewsTotalElements,
    effectiveBookmarksTotalElements,
    myPostsCurrentPage,
    myReviewsCurrentPage,
    myBookmarksCurrentPage,
    myPostsTotalPages,
    myReviewsTotalPages,
    myBookmarksTotalPages,
    removingBookmarkId,
    handleRemoveBookmark,
  };
}
