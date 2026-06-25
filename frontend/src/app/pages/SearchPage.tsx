import { Layout } from '../components/Layout';
import { Search, ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { EmptyState } from '../components/StateView';
import { RecommendationDetailPanel } from '@/app/features/recommendation-detail/components/RecommendationDetailPanel';
import { ResourceCard } from '../components/ResourceCard';
import type { ResultCard } from '@/types/recommendation';
import { apiClient } from '@/api/client';
import {
  buildResourceDetailPath,
  mergeResourceDetail,
} from '../lib/resourceSearchApi';
import { buildSearchResourceCardModel } from '../lib/resourceCardAdapter';
import { useResourceBookmarks } from '@/hooks/useResourceBookmarks';
import { useResizableDetailPanel } from '@/app/shared/hooks/useResizableDetailPanel';
import { SEARCH_PAGE_SIZE, useSearchResources } from '@/app/features/search/hooks/useSearchResources';

export function SearchPage() {
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const {
    bookmarkError,
    clearBookmarkError,
    isBookmarked,
    isBookmarkPending,
    primeResourceBookmark,
    toggleBookmark,
  } = useResourceBookmarks();
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
    currentPage,
    setCurrentPage,
    isAllFilterActive,
    selectedFilterLabels,
    toggleTypeFilter,
    togglePriceFilter,
    sortedResources,
    visibleTotalCount,
    totalPages,
  } = useSearchResources({
    primeResourceBookmark,
  });

  const activeFilterClass =
    'bg-[#4f76df] border border-[#4f76df] text-white hover:bg-[#4f76df] hover:text-white';
  const inactiveFilterClass =
    'bg-white border border-border text-muted-foreground hover:bg-muted hover:text-muted-foreground';
  // 페이지 변경 시 스크롤 최상단 이동
  useEffect(() => {
    void currentPage;
    scrollContainerRef.current?.scrollTo({ top: 0, behavior: 'smooth' });
  }, [currentPage]);

  // 페이지네이션 계산
  // 서버 페이지네이션이므로 현재 리소스(sortedResources)가 곧 화면에 보여줄 리소스입니다.
  const currentResources = sortedResources;

  const pageStart = Math.max(0, currentPage - 2);
  const pageEnd = Math.min(totalPages, pageStart + 5);
  const pageNumbers = Array.from({ length: Math.max(0, pageEnd - pageStart) }, (_, index) => pageStart + index);

  const handleOpenDetail = async (resource: ResultCard) => {
    // 우선 리스트의 정보를 보여주고,
    setSelectedDetail(resource);

    // 상세 정보를 API로 가져와서 업데이트 (RecommendationDetailPanel 연동)
    try {
      const endpoint = buildResourceDetailPath(resource);
      const response = await apiClient.get(endpoint);
      if (response.data?.data) {
        const merged = mergeResourceDetail(resource as any, response.data.data) as ResultCard;
        primeResourceBookmark(merged);
        setSelectedDetail((prev) => (prev?.id === resource.id ? merged : prev));
      }
    } catch (e) {
      console.error('Failed to fetch details', e);
    }
  };

  const handleToggleBookmark = async (resource: ResultCard) => {
    clearBookmarkError();
    await toggleBookmark(resource);
  };

  return (
    <Layout>
      {/* 메인 콘텐츠 */}
      <main className="flex-1 flex flex-col overflow-hidden">
        <div className="flex-1 min-h-0 flex">
          <div ref={scrollContainerRef} className="flex-1 min-w-0 overflow-y-auto">
            <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8">
          {/* 페이지 제목 */}
          <div className="mb-6">
            <h1 className="mb-6 text-3xl font-bold text-foreground">전체 데이터 탐색</h1>
            <p className="text-muted-foreground">서비스에서 제공하는 모든 데이터셋과 Open API를 탐색하세요</p>
          </div>

          {/* 검색창 */}
          <div className="mb-6">
            <label htmlFor="search-query" className="sr-only">
              검색어 입력
            </label>
            <div className="relative">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
              <Input
                id="search-query"
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

          {/* 필터 버튼 */}
          <div className="mb-6 flex flex-wrap items-center gap-2">
            <Button
              onClick={() => {
                setSelectedTypes([]);
                setSelectedPriceFilters([]);
                setCurrentPage(0);
              }}
              variant="outline"
              className={`cursor-pointer rounded-lg px-4 py-2 text-sm transition-colors ${
                isAllFilterActive ? activeFilterClass : inactiveFilterClass
              }`}
            >
              전체
            </Button>

            <div className="flex flex-wrap items-center gap-2">
              <Button
                onClick={() => toggleTypeFilter('dataset')}
                variant="outline"
                className={`cursor-pointer rounded-lg px-4 py-2 text-sm transition-colors ${
                  selectedTypes.includes('dataset') ? activeFilterClass : inactiveFilterClass
                }`}
              >
                Dataset
              </Button>
              <Button
                onClick={() => toggleTypeFilter('api')}
                variant="outline"
                className={`cursor-pointer rounded-lg px-4 py-2 text-sm transition-colors ${
                  selectedTypes.includes('api') ? activeFilterClass : inactiveFilterClass
                }`}
              >
                Open API
              </Button>
              <Button
                onClick={() => togglePriceFilter('free')}
                variant="outline"
                className={`cursor-pointer rounded-lg px-4 py-2 text-sm transition-colors ${
                  selectedPriceFilters.includes('free') ? activeFilterClass : inactiveFilterClass
                }`}
              >
                무료
              </Button>
              <Button
                onClick={() => togglePriceFilter('paid')}
                variant="outline"
                className={`cursor-pointer rounded-lg px-4 py-2 text-sm transition-colors ${
                  selectedPriceFilters.includes('paid') ? activeFilterClass : inactiveFilterClass
                }`}
              >
                유료
              </Button>
            </div>

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

          {/* 결과 개수 */}
          <div className="mb-4">
              <p className="text-sm text-muted-foreground">
                총 <span className="font-semibold text-foreground">{visibleTotalCount}</span>개의 리소스 중 {visibleTotalCount > 0 ? currentPage * SEARCH_PAGE_SIZE + 1 : 0} - {Math.min((currentPage + 1) * SEARCH_PAGE_SIZE, visibleTotalCount)}
              </p>
            </div>

          {bookmarkError ? (
            <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
              {bookmarkError}
            </div>
          ) : null}

          {/* 리소스 목록 */}
          <div className="grid grid-cols-1 gap-4">
            {!isLoading && sortedResources.length === 0 ? (
              <EmptyState
                title="검색 결과가 없습니다."
                description="필터를 조정하거나 다른 키워드로 검색해 보세요."
              />
            ) : (
              currentResources.map((resource) => (
                <ResourceCard
                  key={`${resource.type}-${resource.id}`}
                  data={buildSearchResourceCardModel(resource, {
                    isBookmarked: isBookmarked(resource),
                    isBookmarkPending: isBookmarkPending(resource),
                  })}
                  variant="search"
                  onOpenDetail={() => handleOpenDetail(resource as ResultCard)}
                  onToggleBookmark={() => {
                    void handleToggleBookmark(resource);
                  }}
                />
              ))
            )}
            </div>

            {/* 페이지네이션 */}
            {visibleTotalCount > 0 && totalPages >= 1 && (
              <div className="mt-8 flex flex-wrap items-center justify-center gap-1">
                <Button
                  variant="outline"
                  disabled={currentPage === 0}
                  onClick={() => setCurrentPage(0)}
                  className={`h-8 w-8 cursor-pointer rounded-lg border border-border bg-white p-0 hover:bg-white ${
                    currentPage === 0
                      ? 'text-muted-foreground/50 hover:text-muted-foreground/50'
                      : 'text-muted-foreground hover:text-muted-foreground'
                  }`}
                >
                  <ChevronsLeft className="w-3.5 h-3.5" />
                </Button>
                <Button
                  variant="outline"
                  disabled={currentPage === 0}
                  onClick={() => setCurrentPage((prev) => Math.max(0, prev - 1))}
                  className={`h-8 w-8 cursor-pointer rounded-lg border border-border bg-white p-0 hover:bg-white ${
                    currentPage === 0
                      ? 'text-muted-foreground/50 hover:text-muted-foreground/50'
                      : 'text-muted-foreground hover:text-muted-foreground'
                  }`}
                >
                  <ChevronLeft className="w-3.5 h-3.5" />
                </Button>
                {pageNumbers.map((pageNumber) => (
                  <Button
                    key={pageNumber}
                    onClick={() => setCurrentPage(pageNumber)}
                    variant={pageNumber === currentPage ? 'default' : 'outline'}
                    className={
                      pageNumber === currentPage
                        ? 'h-8 w-8 cursor-pointer rounded-lg border border-[#4f76df] bg-[#4f76df] p-0 text-xs text-white hover:bg-[#4f76df]'
                        : 'h-8 w-8 cursor-pointer rounded-lg border border-border bg-white p-0 text-xs text-foreground hover:bg-white hover:text-foreground'
                    }
                  >
                    {pageNumber + 1}
                  </Button>
                ))}
                <Button
                  variant="outline"
                  disabled={currentPage >= totalPages - 1}
                  onClick={() => setCurrentPage((prev) => Math.min(totalPages - 1, prev + 1))}
                  className={`h-8 w-8 cursor-pointer rounded-lg border border-border bg-white p-0 hover:bg-white ${
                    currentPage >= totalPages - 1
                      ? 'text-muted-foreground/50 hover:text-muted-foreground/50'
                      : 'text-muted-foreground hover:text-muted-foreground'
                  }`}
                >
                  <ChevronRight className="w-3.5 h-3.5" />
                </Button>
                <Button
                  variant="outline"
                  disabled={currentPage >= totalPages - 1}
                  onClick={() => setCurrentPage(Math.max(0, totalPages - 1))}
                  className={`h-8 w-8 cursor-pointer rounded-lg border border-border bg-white p-0 hover:bg-white ${
                    currentPage >= totalPages - 1
                      ? 'text-muted-foreground/50 hover:text-muted-foreground/50'
                      : 'text-muted-foreground hover:text-muted-foreground'
                  }`}
                >
                  <ChevronsRight className="w-3.5 h-3.5" />
                </Button>
              </div>
            )}
          </div>
        </div>

          {selectedDetail && !isNarrowViewport && (
            <>
              <button
                type="button"
                className={`w-1 cursor-col-resize transition-colors focus-visible:outline-none ${
                  isResizing ? 'bg-[#dfe4ea]' : 'bg-border/60 hover:bg-[#dfe4ea] focus-visible:bg-[#dfe4ea]'
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
            <div className="absolute inset-y-0 right-0 w-full max-w-[440px] bg-white shadow-2xl">
              <RecommendationDetailPanel data={selectedDetail} onClose={closeDetail} />
            </div>
          </div>
        )}
      </main>
    </Layout>
  );
}
