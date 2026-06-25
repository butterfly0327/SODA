import { useEffect, useMemo, useState } from "react";

import { bookmarkApi } from "@/api/bookmarkApi";
import { userApi } from "@/api/userApi";
import type { MyBookmarksPage } from "@/api/types";
import { getApiErrorInfo } from "@/app/shared/lib/apiError";
import type { ResultCard } from "@/types/recommendation";
import { mapBookmarkItemToResultCard } from "@/app/features/bookmark/adapters/bookmarkPageAdapter";

export const BOOKMARK_PAGE_SIZE = 20;

type BookmarkTypeFilter = "dataset" | "api";
type BookmarkPriceFilter = "free" | "paid";

type UseBookmarkPageDataOptions = {
  seedBookmarks: (items: MyBookmarksPage["content"]) => void;
  markBookmarkRemoved: (payload: { id: number; type: "dataset" | "api" }) => void;
  onRemovedFromSelectedDetail: (resource: ResultCard) => void;
};

export function useBookmarkPageData({
  seedBookmarks,
  markBookmarkRemoved,
  onRemovedFromSelectedDetail,
}: UseBookmarkPageDataOptions) {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedTypes, setSelectedTypes] = useState<BookmarkTypeFilter[]>([]);
  const [selectedPriceFilters, setSelectedPriceFilters] = useState<BookmarkPriceFilter[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [allBookmarks, setAllBookmarks] = useState<ResultCard[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [currentPage, setCurrentPage] = useState(0);
  const [removingBookmarkId, setRemovingBookmarkId] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;

    const fetchBookmarks = async () => {
      setIsLoading(true);
      setLoadError(null);
      setActionError(null);

      try {
        const normalizedKeyword = searchQuery.trim();
        const filterType =
          selectedTypes.length === 1
            ? selectedTypes[0] === "dataset"
              ? "DATASET"
              : "OPEN_API"
            : undefined;
        const freeOnly =
          selectedPriceFilters.length === 1
            ? selectedPriceFilters[0] === "free"
            : undefined;

        const pageResult = await userApi.getMyBookmarks(currentPage, BOOKMARK_PAGE_SIZE, {
          keyword: normalizedKeyword || undefined,
          type: filterType,
          freeOnly,
        });
        if (cancelled) {
          return;
        }

        seedBookmarks(pageResult.content);
        const bookmarkResults = pageResult.content.map(mapBookmarkItemToResultCard);
        setAllBookmarks(bookmarkResults);
        setTotalCount(pageResult.totalElements ?? 0);
        setTotalPages(pageResult.totalPages ?? 0);
      } catch {
        if (!cancelled) {
          setLoadError("북마크 목록을 불러오지 못했습니다. 잠시 후 다시 시도해주세요.");
          setAllBookmarks([]);
          setTotalCount(0);
          setTotalPages(0);
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    };

    void fetchBookmarks();

    return () => {
      cancelled = true;
    };
  }, [currentPage, searchQuery, selectedPriceFilters, selectedTypes, seedBookmarks]);

  const currentResources = useMemo(() => allBookmarks, [allBookmarks]);
  const safeTotalPages = Math.max(1, totalPages);
  const isAllFilterActive =
    selectedTypes.length === 0 && selectedPriceFilters.length === 0;
  const selectedFilterLabels = [
    ...selectedTypes.map((type) => (type === "dataset" ? "Dataset" : "Open API")),
    ...selectedPriceFilters.map((price) => (price === "free" ? "무료" : "유료")),
  ];

  const normalizeAllFilters = (
    nextTypes: BookmarkTypeFilter[],
    nextPrices: BookmarkPriceFilter[],
  ) => {
    const isEveryFilterSelected =
      nextTypes.length === 2 && nextPrices.length === 2;

    if (isEveryFilterSelected) {
      return {
        types: [] as BookmarkTypeFilter[],
        prices: [] as BookmarkPriceFilter[],
      };
    }

    return {
      types: nextTypes,
      prices: nextPrices,
    };
  };

  const toggleTypeFilter = (type: BookmarkTypeFilter) => {
    const nextTypes = selectedTypes.includes(type)
      ? selectedTypes.filter((value) => value !== type)
      : [...selectedTypes, type];
    const normalizedFilters = normalizeAllFilters(nextTypes, selectedPriceFilters);
    setSelectedTypes(normalizedFilters.types);
    setSelectedPriceFilters(normalizedFilters.prices);
    setCurrentPage(0);
  };

  const togglePriceFilter = (price: BookmarkPriceFilter) => {
    const nextPrices = selectedPriceFilters.includes(price)
      ? selectedPriceFilters.filter((value) => value !== price)
      : [...selectedPriceFilters, price];
    const normalizedFilters = normalizeAllFilters(selectedTypes, nextPrices);
    setSelectedTypes(normalizedFilters.types);
    setSelectedPriceFilters(normalizedFilters.prices);
    setCurrentPage(0);
  };

  const handleRemoveBookmark = async (bookmark: ResultCard) => {
    if (
      removingBookmarkId !== null ||
      typeof bookmark.bookmarkId !== "number" ||
      typeof bookmark.id !== "number"
    ) {
      return;
    }

    setActionError(null);
    setRemovingBookmarkId(bookmark.bookmarkId);

    const wasLastItemOnPage = currentResources.length === 1;

    try {
      await bookmarkApi.deleteBookmark(bookmark.bookmarkId);

      const nextTotalCount = Math.max(0, totalCount - 1);
      const nextTotalPages =
        nextTotalCount === 0 ? 0 : Math.ceil(nextTotalCount / BOOKMARK_PAGE_SIZE);

      setAllBookmarks((previous) =>
        previous.filter((item) => item.bookmarkId !== bookmark.bookmarkId),
      );
      setTotalCount(nextTotalCount);
      setTotalPages(nextTotalPages);
      markBookmarkRemoved({
        id: bookmark.id,
        type: bookmark.type,
      });
      onRemovedFromSelectedDetail(bookmark);

      if (wasLastItemOnPage && currentPage > 0) {
        setCurrentPage((previous) => Math.max(0, previous - 1));
      }
    } catch (error) {
      const { status, message } = getApiErrorInfo(error);

      if (status === 401) {
        setActionError(message || "로그인이 만료되었습니다. 다시 로그인해주세요.");
      } else if (status === 403) {
        setActionError(message || "본인이 등록한 북마크만 삭제할 수 있습니다.");
      } else if (status === 404) {
        const nextTotalCount = Math.max(0, totalCount - 1);
        const nextTotalPages =
          nextTotalCount === 0 ? 0 : Math.ceil(nextTotalCount / BOOKMARK_PAGE_SIZE);

        setAllBookmarks((previous) =>
          previous.filter((item) => item.bookmarkId !== bookmark.bookmarkId),
        );
        setTotalCount(nextTotalCount);
        setTotalPages(nextTotalPages);
        markBookmarkRemoved({
          id: bookmark.id,
          type: bookmark.type,
        });
        onRemovedFromSelectedDetail(bookmark);
        if (wasLastItemOnPage && currentPage > 0) {
          setCurrentPage((previous) => Math.max(0, previous - 1));
        }
        setActionError(message || "이미 삭제되었거나 존재하지 않는 북마크입니다.");
      } else {
        setActionError("북마크 해제에 실패했습니다. 잠시 후 다시 시도해주세요.");
      }
    } finally {
      setRemovingBookmarkId(null);
    }
  };

  return {
    searchQuery,
    setSearchQuery,
    selectedTypes,
    selectedPriceFilters,
    isLoading,
    loadError,
    actionError,
    currentResources,
    totalCount,
    safeTotalPages,
    currentPage,
    setCurrentPage,
    removingBookmarkId,
    isAllFilterActive,
    selectedFilterLabels,
    toggleTypeFilter,
    togglePriceFilter,
    handleRemoveBookmark,
    setSelectedTypes,
    setSelectedPriceFilters,
  };
}
