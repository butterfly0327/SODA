import { useState } from "react";
import { Search } from "lucide-react";

import { BOOKMARK_PAGE_SIZE, useBookmarkPageData } from "@/app/features/bookmark/hooks/useBookmarkPageData";
import { buildResourceDetailPath, mergeResourceDetail } from "@/app/lib/resourceSearchApi";
import { buildSearchResourceCardModel } from "@/app/lib/resourceCardAdapter";
import { apiClient } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useResourceBookmarks } from "@/hooks/useResourceBookmarks";
import type { ResultCard } from "@/types/recommendation";
import { Layout } from "../components/Layout";
import { PagePagination } from "../components/PagePagination";
import { RecommendationDetailPanel } from "@/app/features/recommendation-detail/components/RecommendationDetailPanel";
import { useResizableDetailPanel } from "@/app/shared/hooks/useResizableDetailPanel";
import { ResourceCard } from "../components/ResourceCard";
import { EmptyState, ErrorState, LoadingState } from "../components/StateView";

export function BookmarkPage() {
  const { seedBookmarks, markBookmarkRemoved, isBookmarked, primeResourceBookmark } = useResourceBookmarks();
  const {
    selectedDetail,
    setSelectedDetail,
    panelWidth,
    isResizing,
    startResizing,
    isNarrowViewport,
    closeDetail,
  } = useResizableDetailPanel<ResultCard>();

  const {
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
  } = useBookmarkPageData({
    seedBookmarks,
    markBookmarkRemoved,
    onRemovedFromSelectedDetail: (bookmark) => {
      setSelectedDetail((previous) =>
        previous?.id === bookmark.id && previous?.type === bookmark.type ? null : previous,
      );
    },
  });

  const activeFilterClass =
    "bg-[#4f76df] border border-[#4f76df] text-white hover:bg-[#4f76df] hover:text-white";
  const inactiveFilterClass =
    "bg-white border border-border text-muted-foreground hover:bg-muted hover:text-muted-foreground";

  const handleOpenDetail = async (bookmark: ResultCard) => {
    setSelectedDetail(bookmark);

    try {
      const endpoint = buildResourceDetailPath(bookmark);
      const detailResponse = await apiClient.get(endpoint);
      if (detailResponse.data?.data) {
        const merged = mergeResourceDetail(bookmark, detailResponse.data.data);
        primeResourceBookmark(merged);
        setSelectedDetail((previous) => (previous?.id === bookmark.id ? merged : previous));
      }
    } catch (error) {
      console.error("Failed to fetch bookmark detail:", error);
    }
  };

  return (
    <Layout>
      <main className="flex-1 flex flex-col overflow-hidden">
        <div className="flex-1 min-h-0 flex">
          <div className="flex-1 min-w-0 overflow-y-auto">
            <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8">
              <div className="mb-6">
                <h1 className="mb-6 text-2xl font-bold text-foreground">북마크</h1>
                <p className="text-muted-foreground">저장한 데이터셋과 Open API를 빠르게 확인하세요</p>
              </div>

              <div className="mb-6">
                <label htmlFor="bookmark-query" className="sr-only">
                  북마크 검색어 입력
                </label>
                <div className="relative">
                  <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
                  <Input
                    id="bookmark-query"
                    type="text"
                    placeholder="키워드를 검색하세요"
                    value={searchQuery}
                    onChange={(event) => {
                      setSearchQuery(event.target.value);
                      setCurrentPage(0);
                    }}
                    className="w-full pl-12 pr-4 py-3 border border-border rounded-lg bg-white text-foreground placeholder:text-muted-foreground focus:outline-none focus-visible:outline-none focus-visible:ring-0 focus-visible:ring-transparent focus-visible:border-border"
                  />
                </div>
              </div>

              <div className="mb-6 flex flex-wrap items-center gap-2">
                <Button
                  onClick={() => {
                    setSelectedTypes([]);
                    setSelectedPriceFilters([]);
                    setCurrentPage(0);
                  }}
                  variant="outline"
                  className={`cursor-pointer px-4 py-2 rounded-lg text-sm transition-colors ${
                    isAllFilterActive ? activeFilterClass : inactiveFilterClass
                  }`}
                >
                  전체
                </Button>
                <Button
                  onClick={() => toggleTypeFilter("dataset")}
                  variant="outline"
                  className={`cursor-pointer px-4 py-2 rounded-lg text-sm transition-colors ${
                    selectedTypes.includes("dataset") ? activeFilterClass : inactiveFilterClass
                  }`}
                >
                  Dataset
                </Button>
                <Button
                  onClick={() => toggleTypeFilter("api")}
                  variant="outline"
                  className={`cursor-pointer px-4 py-2 rounded-lg text-sm transition-colors ${
                    selectedTypes.includes("api") ? activeFilterClass : inactiveFilterClass
                  }`}
                >
                  Open API
                </Button>
                <Button
                  onClick={() => togglePriceFilter("free")}
                  variant="outline"
                  className={`cursor-pointer px-4 py-2 rounded-lg text-sm transition-colors ${
                    selectedPriceFilters.includes("free") ? activeFilterClass : inactiveFilterClass
                  }`}
                >
                  무료
                </Button>
                <Button
                  onClick={() => togglePriceFilter("paid")}
                  variant="outline"
                  className={`cursor-pointer px-4 py-2 rounded-lg text-sm transition-colors ${
                    selectedPriceFilters.includes("paid") ? activeFilterClass : inactiveFilterClass
                  }`}
                >
                  유료
                </Button>
              </div>

              {selectedFilterLabels.length > 0 && (
                <div className="mb-4 flex flex-wrap items-center gap-2">
                  <span className="text-xs text-muted-foreground">선택됨:</span>
                  {selectedFilterLabels.map((label) => (
                    <span
                      key={label}
                      className="inline-flex items-center rounded-full bg-[#e8f4fd] px-2.5 py-1 text-xs font-medium text-[#2b6ea6]"
                    >
                      {label}
                    </span>
                  ))}
                </div>
              )}

              <div className="mb-4">
                <p className="text-sm text-muted-foreground">
                  총 <span className="font-semibold text-foreground">{totalCount}</span>개의 북마크 중{" "}
                  {totalCount > 0 ? currentPage * BOOKMARK_PAGE_SIZE + 1 : 0} -{" "}
                  {Math.min((currentPage + 1) * BOOKMARK_PAGE_SIZE, totalCount)}
                </p>
              </div>

              {actionError ? (
                <div className="mb-4">
                  <ErrorState
                    title="북마크 작업을 완료하지 못했습니다."
                    description={actionError}
                    className="p-4"
                  />
                </div>
              ) : null}

              {loadError ? (
                <ErrorState title="북마크를 불러오지 못했습니다." description={loadError} />
              ) : (
                <div className="grid grid-cols-1 gap-4">
                  {isLoading ? (
                    <LoadingState
                      title="북마크를 불러오는 중입니다."
                      description="저장한 리소스를 준비하고 있습니다."
                    />
                  ) : currentResources.length === 0 ? (
                    <EmptyState
                      title="북마크한 리소스가 없습니다."
                      description="검색 결과나 상세 페이지에서 북마크를 추가해보세요."
                    />
                  ) : (
                    currentResources.map((bookmark) => (
                      <ResourceCard
                        key={`${bookmark.type}-${bookmark.id}`}
                        data={buildSearchResourceCardModel(bookmark, {
                          isBookmarked: isBookmarked(bookmark),
                          isBookmarkPending: removingBookmarkId === bookmark.bookmarkId,
                        })}
                        variant="bookmark"
                        onOpenDetail={() => handleOpenDetail(bookmark)}
                        onToggleBookmark={() => {
                          void handleRemoveBookmark(bookmark);
                        }}
                      />
                    ))
                  )}
                </div>
              )}

              <PagePagination
                currentPage={currentPage}
                totalPages={safeTotalPages}
                totalItems={totalCount}
                variant="community"
                onPageChange={setCurrentPage}
              />
            </div>
          </div>

          {selectedDetail && !isNarrowViewport && (
            <>
              <button
                type="button"
                className={`w-1 cursor-col-resize transition-colors focus-visible:outline-none ${
                  isResizing ? "bg-[#dfe4ea]" : "bg-border/60 hover:bg-[#dfe4ea] focus-visible:bg-[#dfe4ea]"
                }`}
                onPointerDown={startResizing}
                aria-label="상세 패널 너비 조절"
              />
              <div style={{ width: `${panelWidth}px` }} className="min-w-[320px] max-w-[760px] h-full">
                <RecommendationDetailPanel data={selectedDetail} onClose={closeDetail} />
              </div>
            </>
          )}
        </div>

        {selectedDetail && isNarrowViewport && (
          <div className="fixed inset-0 z-50">
            <button
              type="button"
              className="absolute inset-0 bg-black/30"
              onClick={closeDetail}
              aria-label="상세 패널 닫기"
            />
            <div
              className="absolute inset-y-0 right-0 w-full max-w-[440px] bg-white shadow-2xl"
            >
              <RecommendationDetailPanel data={selectedDetail} onClose={closeDetail} />
            </div>
          </div>
        )}
      </main>
    </Layout>
  );
}
