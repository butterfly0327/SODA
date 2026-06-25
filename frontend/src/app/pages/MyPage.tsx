import {
  Bookmark,
  Calendar,
  Mail,
  MessageSquare,
  Star,
  User,
} from "lucide-react";
import axios from "axios";
import { useState } from "react";
import { useNavigate } from "react-router";

import { apiClient } from "@/api/client";
import type { MyBookmarkItemResponseDto } from "@/api/contracts";
import { Button } from "@/components/ui/button";
import type { ResultCard } from "@/types/recommendation";
import { useAuthStore } from "@/stores/authStore";
import { useResizableDetailPanel } from "@/app/shared/hooks/useResizableDetailPanel";
import { RecommendationDetailPanel } from "@/app/features/recommendation-detail/components/RecommendationDetailPanel";
import { Layout } from "../components/Layout";
import { PagePagination } from "../components/PagePagination";
import { ResourceCard } from "../components/ResourceCard";
import { MyPageSection } from "../components/mypage/MyPageSection";
import { MyPostCard } from "../components/mypage/MyPostCard";
import { MyReviewCard } from "../components/mypage/MyReviewCard";
import { mapBookmarkItemToResultCard } from "@/app/features/bookmark/adapters/bookmarkPageAdapter";
import { MY_PAGE_SIZE, useMyPageData } from "@/app/features/mypage/hooks/useMyPageData";
import {
  buildResourceDetailPath,
  mergeResourceDetail,
} from "../lib/resourceSearchApi";
import { buildSearchResourceCardModel } from "../lib/resourceCardAdapter";
import { beginSsafyLoginFlow } from "../lib/ssafyLoginFlow";

export function MyPage() {
  const user = useAuthStore((state) => state.user);
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const logout = useAuthStore((state) => state.logout);
  const navigate = useNavigate();

  const [activeTab, setActiveTab] = useState<"posts" | "reviews" | "bookmarks">("posts");
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [isDeleteConfirmChecked, setIsDeleteConfirmChecked] = useState(false);
  const [isDeletingAccount, setIsDeletingAccount] = useState(false);
  const [deleteAccountError, setDeleteAccountError] = useState<string | null>(null);

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
  } = useMyPageData({
    isAuthenticated,
    fallbackName: user?.name,
    fallbackEmail: user?.email,
    onRemovedFromSelectedDetail: (bookmark) => {
      setSelectedDetail((previous) =>
        previous?.id === bookmark.id &&
        previous?.type === (bookmark.type === "DATASET" ? "dataset" : "api")
          ? null
          : previous,
      );
    },
  });


  const handleWithdrawal = async () => {
    if (isDeletingAccount) return;

    setDeleteAccountError(null);
    setIsDeletingAccount(true);

    try {
      await userApi.deleteMyAccount();
      setShowDeleteModal(false);
      setIsDeleteConfirmChecked(false);
      const setJustWithdrew = useAuthStore.getState().setJustWithdrew;
      setJustWithdrew(true);
      await logout();
      navigate("/", { replace: true });
    } catch (error) {
      if (axios.isAxiosError(error)) {
        const status = error.response?.status;
        if (status === 401 || status === 404) {
          await logout();
          beginSsafyLoginFlow("/mypage");
          return;
        }

        setDeleteAccountError(
          error.response?.data?.message ?? "회원 탈퇴 처리에 실패했습니다. 잠시 후 다시 시도해주세요.",
        );
        return;
      }

      setDeleteAccountError("회원 탈퇴 처리에 실패했습니다. 잠시 후 다시 시도해주세요.");
    } finally {
      setIsDeletingAccount(false);
    }
  };

  const handleOpenResourceDetail = async (resource: ResultCard) => {
    setSelectedDetail(resource);

    try {
      const endpoint = buildResourceDetailPath(resource);
      const response = await apiClient.get(endpoint);
      if (response.data?.data) {
        setSelectedDetail((previous) =>
          previous?.id === resource.id && previous?.type === resource.type
            ? (mergeResourceDetail(previous, response.data.data) as ResultCard)
            : previous,
        );
      }
    } catch {
      // Keep base card in panel if detail fetch fails.
    }
  };

  const handleOpenReviewDetail = (review: (typeof visibleReviews)[number]) => {
    const baseResource: ResultCard =
      review.resourceType === "dataset"
        ? {
            id: review.resourceId,
            type: "dataset",
            name: review.resourceTitle,
            score: review.rating,
          }
        : {
            id: review.resourceId,
            type: "api",
            name: review.resourceTitle,
            score: review.rating,
          };

    void handleOpenResourceDetail(baseResource);
  };

  return (
    <Layout>
      <main className="flex min-h-0 flex-1 overflow-hidden">
        <div className="flex-1 overflow-y-auto">
          <div className="mx-auto max-w-4xl px-6 py-8">
            <h1 className="mb-6 text-2xl font-bold text-foreground">My Page</h1>
            {profileError && (
              <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
                {profileError}
              </div>
            )}
            {myPostsError && (
              <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
                {myPostsError}
              </div>
            )}
            {myReviewsError && (
              <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
                {myReviewsError}
              </div>
            )}
            {myBookmarksError && (
              <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
                {myBookmarksError}
              </div>
            )}
            {deleteAccountError && (
              <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                {deleteAccountError}
              </div>
            )}

            <div className="relative mb-6 rounded-xl border border-border bg-white p-6 shadow-sm">
              <div className="absolute bottom-6 right-6">
                <Button
                  onClick={() => {
                    setDeleteAccountError(null);
                    setIsDeleteConfirmChecked(false);
                    setShowDeleteModal(true);
                  }}
                  variant="ghost"
                  className="cursor-pointer rounded-lg px-2 py-1 text-sm text-red-500 transition-colors hover:bg-sidebar-accent/50 hover:text-red-500"
                >
                  회원 탈퇴
                </Button>
              </div>

              <div className="flex items-start gap-5">
                <div className="flex h-16 w-16 flex-shrink-0 items-center justify-center rounded-full bg-[#e8f4fd]">
                  <User className="h-8 w-8 text-foreground" />
                </div>

                <div className="flex flex-col gap-1">
                  <h2 className="text-xl font-semibold text-foreground">{displayName}</h2>
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Mail className="h-4 w-4" />
                    <span>{displayEmail}</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Calendar className="h-4 w-4" />
                    <span>가입일: {displayCreatedAt}</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-3">
              <div className="rounded-xl border border-border bg-white p-4 shadow-sm">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#e8f4fd]">
                    <MessageSquare className="h-5 w-5 text-foreground" />
                  </div>
                  <div>
                    <p className="text-2xl font-semibold text-foreground">{displayPostCount}개</p>
                    <p className="text-sm text-muted-foreground">작성한 게시글</p>
                  </div>
                </div>
              </div>
              <div className="rounded-xl border border-border bg-white p-4 shadow-sm">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#e8f4fd]">
                    <Star className="h-5 w-5 text-foreground" />
                  </div>
                  <div>
                    <p className="text-2xl font-semibold text-foreground">{displayReviewCount}개</p>
                    <p className="text-sm text-muted-foreground">작성한 리뷰</p>
                  </div>
                </div>
              </div>
              <div className="rounded-xl border border-border bg-white p-4 shadow-sm">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#e8f4fd]">
                    <Bookmark className="h-5 w-5 text-foreground" />
                  </div>
                  <div>
                    <p className="text-2xl font-semibold text-foreground">{displayBookmarkCount}개</p>
                    <p className="text-sm text-muted-foreground">북마크</p>
                  </div>
                </div>
              </div>
            </div>

            <div className="mb-6 flex gap-6 border-b border-border">
              <Button
                onClick={() => setActiveTab("posts")}
                variant="ghost"
                className={`cursor-pointer relative pb-3 text-sm font-medium transition-colors ${
                  activeTab === "posts"
                    ? "rounded-lg bg-[#dfe4ea] text-foreground hover:bg-[#dfe4ea] hover:text-foreground"
                    : "text-muted-foreground hover:bg-sidebar-accent/50 hover:text-foreground"
                }`}
              >
                My Posts
                {activeTab === "posts" && (
                  <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#e8f4fd]" />
                )}
              </Button>
              <Button
                onClick={() => setActiveTab("reviews")}
                variant="ghost"
                className={`cursor-pointer relative pb-3 text-sm font-medium transition-colors ${
                  activeTab === "reviews"
                    ? "rounded-lg bg-[#dfe4ea] text-foreground hover:bg-[#dfe4ea] hover:text-foreground"
                    : "text-muted-foreground hover:bg-sidebar-accent/50 hover:text-foreground"
                }`}
              >
                My Reviews
                {activeTab === "reviews" && (
                  <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#e8f4fd]" />
                )}
              </Button>
              <Button
                onClick={() => setActiveTab("bookmarks")}
                variant="ghost"
                className={`cursor-pointer relative pb-3 text-sm font-medium transition-colors ${
                  activeTab === "bookmarks"
                    ? "rounded-lg bg-[#dfe4ea] text-foreground hover:bg-[#dfe4ea] hover:text-foreground"
                    : "text-muted-foreground hover:bg-sidebar-accent/50 hover:text-foreground"
                }`}
              >
                My Bookmarks
                {activeTab === "bookmarks" && (
                  <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#e8f4fd]" />
                )}
              </Button>
            </div>

            {activeTab === "posts" && (
              <MyPageSection
                itemsCount={visiblePosts.length}
                emptyMessage="내가 작성한 게시글이 없습니다."
                pagination={
                  <PagePagination
                    currentPage={myPostsCurrentPage}
                    totalPages={myPostsTotalPages}
                    totalItems={effectivePostsTotalElements}
                    alwaysShow
                    variant="community"
                    onPageChange={setPostsPageIndex}
                  />
                }
              >
                {visiblePosts.map((post) => (
                  <MyPostCard
                    key={post.id}
                    data={post}
                    onOpen={() => navigate(`/community/${post.id}`)}
                  />
                ))}
              </MyPageSection>
            )}

            {activeTab === "reviews" && (
              <MyPageSection
                itemsCount={visibleReviews.length}
                emptyMessage="내가 작성한 리뷰가 없습니다."
                pagination={
                  <PagePagination
                    currentPage={myReviewsCurrentPage}
                    totalPages={myReviewsTotalPages}
                    totalItems={effectiveReviewsTotalElements}
                    alwaysShow
                    variant="community"
                    onPageChange={setReviewsPageIndex}
                  />
                }
              >
                {visibleReviews.map((review) => (
                  <MyReviewCard
                    key={review.id}
                    data={review}
                    onOpen={() => handleOpenReviewDetail(review)}
                  />
                ))}
              </MyPageSection>
            )}

            {activeTab === "bookmarks" && (
              <MyPageSection
                itemsCount={visibleBookmarks.length}
                emptyMessage="아직 북마크한 리소스가 없습니다."
                pagination={
                  <PagePagination
                    currentPage={myBookmarksCurrentPage}
                    totalPages={myBookmarksTotalPages}
                    totalItems={effectiveBookmarksTotalElements}
                    alwaysShow
                    variant="community"
                    onPageChange={setBookmarksPageIndex}
                  />
                }
              >
                {visibleBookmarks.map((bookmark) => {
                  const resource = mapBookmarkItemToResultCard(bookmark);
                  const cardModel = buildSearchResourceCardModel(resource, {
                    isBookmarked: true,
                    isBookmarkPending: removingBookmarkId === bookmark.bookmarkId,
                  });

                  return (
                    <ResourceCard
                      key={bookmark.bookmarkId}
                      data={cardModel}
                      variant="mypage"
                      onOpenDetail={() => void handleOpenResourceDetail(resource)}
                      onToggleBookmark={() => void handleRemoveBookmark(bookmark)}
                    />
                  );
                })}
              </MyPageSection>
            )}
          </div>
        </div>

        {selectedDetail && !isNarrowViewport && (
          <>
            <div
              className={`w-1 cursor-col-resize transition-colors ${
                isResizing ? "bg-[#dfe4ea]" : "bg-border/60 hover:bg-[#dfe4ea]"
              }`}
              onPointerDown={startResizing}
            />
            <div
              style={{ width: `${panelWidth}px` }}
              className="min-w-[320px] max-w-[760px] border-l border-border bg-white"
            >
              <RecommendationDetailPanel
                data={selectedDetail}
                onClose={closeDetail}
                reviewMode="readOnly"
              />
            </div>
          </>
        )}
      </main>

      {selectedDetail && isNarrowViewport && (
        <div className="fixed inset-0 z-50">
          <button
            type="button"
            className="absolute inset-0 bg-black/30"
            onClick={closeDetail}
            aria-label="상세 패널 닫기"
          />
          <div className="absolute inset-y-0 right-0 w-full max-w-[440px] bg-white shadow-2xl">
            <RecommendationDetailPanel
              data={selectedDetail}
              onClose={closeDetail}
              reviewMode="readOnly"
            />
          </div>
        </div>
      )}

      {showDeleteModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4">
          <div className="w-full max-w-[320px] rounded-[16px] bg-white px-5 pb-5 pt-6 shadow-[0_14px_30px_rgba(15,23,42,0.16)]">
            <div className="mb-4 flex justify-center">
              <div className="flex h-8 w-8 items-center justify-center rounded-full border border-[#f5c8cf] bg-[#fff5f6]">
                <div className="flex h-5 w-5 items-center justify-center rounded-full border border-[#efb0ba] bg-white">
                  <span className="text-[14px] font-bold leading-none text-[#e57373]">!</span>
                </div>
              </div>
            </div>

            <h3 className="text-center text-[18px] font-bold tracking-[-0.01em] text-[#111827]">
              회원 탈퇴
            </h3>

            <p className="mt-2.5 text-center text-[13px] leading-relaxed text-[#6b7280]">
              계정을 삭제하시겠습니까?
              <br />
              삭제된 계정은 다시 복구할 수 없습니다.
            </p>

            <label className="mt-4 flex cursor-pointer items-center gap-2.5 rounded-lg border border-border bg-white px-3 py-2 text-[13px] text-[#374151]">
              <input
                type="checkbox"
                checked={isDeleteConfirmChecked}
                onChange={(event) => setIsDeleteConfirmChecked(event.target.checked)}
                className="h-4 w-4 rounded border-border text-[#E57373] focus:outline-none focus-visible:ring-0"
              />
              <span>위 내용을 확인했고, 회원 탈퇴에 동의합니다.</span>
            </label>

            <div className="mt-5 grid grid-cols-2 gap-2.5">
              <Button
                onClick={() => {
                  if (isDeletingAccount) return;
                  setIsDeleteConfirmChecked(false);
                  setShowDeleteModal(false);
                }}
                disabled={isDeletingAccount}
                className="h-10 rounded-lg border-0 bg-[#eceef1] text-[14px] font-medium text-[#111827] hover:bg-[#e4e7eb]"
              >
                취소
              </Button>
              <Button
                onClick={() => void handleWithdrawal()}
                disabled={isDeletingAccount || !isDeleteConfirmChecked}
                className="h-10 rounded-lg border-0 bg-[#E57373] text-[14px] font-medium text-white hover:bg-[#db6c6c]"
              >
                탈퇴하기
              </Button>
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
}
