import { ArrowLeft, Bookmark, CheckCircle2, Code, Database, ExternalLink, Star } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { resourceApi } from "@/api/resourceApi";
import { reviewApi, type ReviewResourceType } from "@/api/reviewApi";
import type { ResourceDetail } from "@/api/types";
import { useAuthStore } from "../../stores/authStore";
import { useResourceReviewStore } from "../../stores/resourceReviewStore";
import { LoadingState } from "../components/StateView";
import { Layout } from "../components/Layout";
import { useResourceBookmarks } from "@/hooks/useResourceBookmarks";

function normalizeAuthorName(author: string) {
  return author.trim();
}

type ResourceTypeParam = "DATASET" | "OPEN_API";

function normalizeTypeParam(raw: string | null): ResourceTypeParam | null {
  if (!raw) return null;
  const normalized = raw.toLowerCase();
  if (normalized === "dataset" || normalized === "data" || normalized === "datasets") {
    return "DATASET";
  }
  if (normalized === "api" || normalized === "open_api" || normalized === "open-api" || normalized === "openapi") {
    return "OPEN_API";
  }
  if (raw === "DATASET" || raw === "OPEN_API") {
    return raw;
  }
  return null;
}

function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return "-";
  }
  return new Intl.NumberFormat().format(value);
}

function formatMillis(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return "-";
  }
  return `${value}ms`;
}

function formatDate(value: string | null | undefined): string {
  if (!value) return "-";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleDateString();
}

export function ResourceDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);
  const reviews = useResourceReviewStore((state) => state.reviews);
  const upsertReview = useResourceReviewStore((state) => state.upsertReview);
  const removeReview = useResourceReviewStore((state) => state.removeReview);

  const [rating, setRating] = useState(0);
  const [hoverRating, setHoverRating] = useState(0);
  const [reviewText, setReviewText] = useState("");
  const [reviewError, setReviewError] = useState("");
  const [actionError, setActionError] = useState("");
  const [toastMessage, setToastMessage] = useState("");
  const [isToastVisible, setIsToastVisible] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editRating, setEditRating] = useState(0);
  const [editHoverRating, setEditHoverRating] = useState(0);
  const [editText, setEditText] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const [resourceDetail, setResourceDetail] = useState<ResourceDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const {
    bookmarkError,
    clearBookmarkError,
    isBookmarked,
    isBookmarkPending,
    primeResourceBookmark,
    toggleBookmark,
  } = useResourceBookmarks();

  const resourceId = Number(id);
  const isInvalidResourceId = !Number.isFinite(resourceId) || resourceId <= 0;
  const currentAuthorName = useMemo(
    () => normalizeAuthorName(user?.name?.trim() || "Anonymous"),
    [user?.name],
  );

  useEffect(() => {
    let isCancelled = false;

    if (isInvalidResourceId) {
      setIsLoading(false);
      setResourceDetail(null);
      setLoadError("Invalid resource id.");
      return () => {
        isCancelled = true;
      };
    }

    const loadResourceDetail = async () => {
      setIsLoading(true);
      setLoadError(null);

      try {
        const typeParam = normalizeTypeParam(searchParams.get("type"));
        let detail: ResourceDetail | null = null;

        if (typeParam) {
          detail = await resourceApi.getResourceDetail(typeParam, resourceId);
        } else {
          try {
            detail = await resourceApi.getResourceDetail("DATASET", resourceId);
          } catch {
            detail = await resourceApi.getResourceDetail("OPEN_API", resourceId);
          }
        }

        if (!isCancelled) {
          setResourceDetail(detail);
          primeResourceBookmark({
            id: detail.id,
            type: detail.type,
            title: detail.title,
            isBookmarked: detail.isBookmarked,
          });
        }
      } catch (error) {
        if (!isCancelled) {
          console.error("Failed to fetch resource detail:", error);
          setLoadError("Failed to load resource detail.");
        }
      } finally {
        if (!isCancelled) {
          setIsLoading(false);
        }
      }
    };

    void loadResourceDetail();

    return () => {
      isCancelled = true;
    };
  }, [isInvalidResourceId, primeResourceBookmark, resourceId, searchParams]);

  const resourceReviews = useMemo(
    () => (Number.isFinite(resourceId) ? reviews.filter((review) => review.resourceId === resourceId) : []),
    [reviews, resourceId],
  );

  const myReview = useMemo(
    () =>
      resourceReviews.find((review) =>
        user?.id
          ? review.authorId === user.id
          : normalizeAuthorName(review.author) === currentAuthorName,
      ),
    [resourceReviews, currentAuthorName, user?.id],
  );

  const hasMyReview = Boolean(myReview);
  const otherReviews = useMemo(
    () =>
      resourceReviews.filter(
        (review) =>
          !(user?.id
            ? review.authorId === user.id
            : normalizeAuthorName(review.author) === currentAuthorName),
      ),
    [resourceReviews, currentAuthorName, user?.id],
  );

  useEffect(() => {
    if (!myReview) {
      setIsEditing(false);
      setEditRating(0);
      setEditHoverRating(0);
      setEditText("");
      return;
    }
    setEditRating(myReview.rating);
    setEditText(myReview.content);
  }, [myReview?.id]);

  useEffect(() => {
    if (!toastMessage) {
      return;
    }

    setIsToastVisible(true);

    const fadeOutTimer = setTimeout(() => {
      setIsToastVisible(false);
    }, 1800);

    const removeTimer = setTimeout(() => {
      setToastMessage("");
    }, 2000);

    return () => {
      clearTimeout(fadeOutTimer);
      clearTimeout(removeTimer);
    };
  }, [toastMessage]);

  const resolveReviewId = (rawId: string | undefined) => {
    if (!rawId) return null;
    const parsed = Number(rawId);
    return Number.isFinite(parsed) ? parsed : null;
  };

  const handleSubmitReview = async () => {
    if (!resourceDetail) {
      return;
    }

    setReviewError("");
    setActionError("");

    if (rating === 0 || !reviewText.trim()) {
      setReviewError("Please provide a rating and a short review.");
      return;
    }

    const resourceType = resourceDetail.type as ReviewResourceType;

    try {
      setIsSaving(true);
      const response = await reviewApi.createReview(resourceType, resourceDetail.id, {
        rating,
        content: reviewText.trim(),
      });

      upsertReview({
        id: response.reviewId ? String(response.reviewId) : undefined,
        resourceId: resourceDetail.id,
        resourceType: resourceType === "DATASET" ? "dataset" : "api",
        resourceName: resourceDetail.title,
        authorId: user?.id,
        author: currentAuthorName,
        rating: response.rating,
        content: response.content,
        createdAt: response.createdAt ?? undefined,
      });

      setReviewText("");
      setRating(0);
      setHoverRating(0);
      setToastMessage("Review submitted.");
    } catch (error) {
      console.error("Failed to create review:", error);
      setActionError("Failed to submit review. Please try again.");
    } finally {
      setIsSaving(false);
    }
  };

  const handleUpdateReview = async () => {
    if (!resourceDetail || !myReview) {
      return;
    }

    setActionError("");

    if (editRating === 0 || !editText.trim()) {
      setActionError("Please provide a rating and a short review.");
      return;
    }

    const reviewId = resolveReviewId(myReview.id);
    if (!reviewId) {
      setActionError("Invalid review id.");
      return;
    }

    try {
      setIsSaving(true);
      const response = await reviewApi.updateReview(
        resourceDetail.type as ReviewResourceType,
        resourceDetail.id,
        reviewId,
        { rating: editRating, content: editText.trim() },
      );

      upsertReview({
        id: response.reviewId ? String(response.reviewId) : myReview.id,
        resourceId: resourceDetail.id,
        resourceType: resourceDetail.type === "DATASET" ? "dataset" : "api",
        resourceName: resourceDetail.title,
        authorId: user?.id,
        author: currentAuthorName,
        rating: response.rating,
        content: response.content,
        createdAt: response.createdAt ?? undefined,
      });

      setIsEditing(false);
      setToastMessage("Review updated.");
    } catch (error) {
      console.error("Failed to update review:", error);
      setActionError("Failed to update review. Please try again.");
    } finally {
      setIsSaving(false);
    }
  };

  const handleDeleteReview = async () => {
    if (!resourceDetail || !myReview) {
      return;
    }

    const reviewId = resolveReviewId(myReview.id);
    if (!reviewId) {
      setActionError("Invalid review id.");
      return;
    }

    try {
      setIsDeleting(true);
      await reviewApi.deleteReview(
        resourceDetail.type as ReviewResourceType,
        resourceDetail.id,
        reviewId,
      );
      removeReview({
        id: myReview.id,
        resourceId: resourceDetail.id,
        authorId: user?.id,
        author: currentAuthorName,
      });
      setIsEditing(false);
      setToastMessage("Review deleted.");
    } catch (error) {
      console.error("Failed to delete review:", error);
      setActionError("Failed to delete review. Please try again.");
    } finally {
      setIsDeleting(false);
    }
  };

  if (isInvalidResourceId) {
    return (
      <Layout>
        <div className="flex-1 overflow-y-auto">
          <div className="max-w-3xl mx-auto px-8 py-10">
            <div className="rounded-lg border border-red-200 bg-red-50 p-6">
              <p className="mb-2 text-base font-medium text-red-700">Invalid resource id.</p>
              <p className="mb-4 text-sm text-red-600">Please check the link and try again.</p>
              <Button variant="outline" onClick={() => navigate("/search")}>Go to search</Button>
            </div>
          </div>
        </div>
      </Layout>
    );
  }

  if (isLoading) {
    return (
      <Layout>
        <div className="flex-1 flex items-center justify-center">
          <LoadingState title="Loading resource detail..." />
        </div>
      </Layout>
    );
  }

  if (loadError || !resourceDetail) {
    return (
      <Layout>
        <div className="flex-1 overflow-y-auto">
          <div className="max-w-3xl mx-auto px-8 py-10">
            <div className="rounded-lg border border-red-200 bg-red-50 p-6">
              <p className="mb-2 text-base font-medium text-red-700">Failed to load resource.</p>
              <p className="mb-4 text-sm text-red-600">{loadError || "Please try again later."}</p>
              <Button variant="outline" onClick={() => navigate(-1)}>Go back</Button>
            </div>
          </div>
        </div>
      </Layout>
    );
  }

  const isDataset = resourceDetail.type === "DATASET";
  const datasetDetail = resourceDetail.datasetDetail;
  const openApiDetail = resourceDetail.openApiDetail;

  const handleToggleBookmark = async () => {
    if (!resourceDetail) {
      return;
    }

    clearBookmarkError();
    const result = await toggleBookmark({
      id: resourceDetail.id,
      type: resourceDetail.type,
      title: resourceDetail.title,
      isBookmarked: isBookmarked({
        id: resourceDetail.id,
        type: resourceDetail.type,
        isBookmarked: resourceDetail.isBookmarked,
      }),
    });

    if (result) {
      setResourceDetail((previous) =>
        previous
          ? {
              ...previous,
              isBookmarked: result.isBookmarked,
            }
          : previous,
      );
      setToastMessage(result.isBookmarked ? "북마크가 추가되었습니다." : "북마크가 해제되었습니다.");
    }
  };

  return (
    <Layout>
      {toastMessage && (
        <div
          className={`fixed right-6 bottom-6 z-50 flex items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-2.5 text-sm font-medium text-emerald-700 shadow-lg transition-all duration-200 ${
            isToastVisible ? "translate-y-0 opacity-100" : "translate-y-2 opacity-0"
          }`}
        >
          <CheckCircle2 className="h-4 w-4 text-emerald-600" />
          <span>{toastMessage}</span>
        </div>
      )}

      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-5xl px-8 py-8">
          <Button
            onClick={() => navigate(-1)}
            variant="ghost"
            className="mb-6 flex items-center gap-2 text-muted-foreground transition-colors hover:text-foreground"
          >
            <ArrowLeft className="h-4 w-4" />
            <span>Back</span>
          </Button>

          <div className="mb-6 rounded-lg border border-border bg-white p-8">
            <div className="flex items-start gap-6">
              <div
                className={`flex h-16 w-16 flex-shrink-0 items-center justify-center rounded-lg ${
                  isDataset ? "bg-blue-50" : "bg-green-50"
                }`}
              >
                {isDataset ? (
                  <Database className="h-8 w-8 text-blue-600" />
                ) : (
                  <Code className="h-8 w-8 text-green-600" />
                )}
              </div>

              <div className="flex-1">
                {bookmarkError ? (
                  <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
                    {bookmarkError}
                  </div>
                ) : null}
                <div className="mb-4 flex items-start justify-between gap-4">
                  <div>
                    <h1 className="mb-2 text-3xl font-semibold text-foreground">{resourceDetail.title}</h1>
                    <div className="flex items-center gap-2">
                      <span
                        className={`rounded-full px-3 py-1 text-sm font-medium ${
                          isDataset ? "bg-blue-50 text-blue-700" : "bg-green-50 text-green-700"
                        }`}
                      >
                        {isDataset ? "Dataset" : "Open API"}
                      </span>
                      <button
                        type="button"
                        onClick={handleToggleBookmark}
                        disabled={isBookmarkPending({
                          id: resourceDetail.id,
                          type: resourceDetail.type,
                        })}
                        title={
                          isBookmarked({
                            id: resourceDetail.id,
                            type: resourceDetail.type,
                            isBookmarked: resourceDetail.isBookmarked,
                          })
                            ? "북마크 해제"
                            : "북마크 추가"
                        }
                        aria-label={
                          isBookmarked({
                            id: resourceDetail.id,
                            type: resourceDetail.type,
                            isBookmarked: resourceDetail.isBookmarked,
                          })
                            ? "북마크 해제"
                            : "북마크 추가"
                        }
                        className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-border bg-white text-muted-foreground transition-colors hover:bg-muted disabled:opacity-40 disabled:cursor-not-allowed"
                      >
                        <Bookmark
                          className={`h-5 w-5 ${
                            isBookmarked({
                              id: resourceDetail.id,
                              type: resourceDetail.type,
                              isBookmarked: resourceDetail.isBookmarked,
                            })
                              ? "fill-[#4f76df] text-[#4f76df]"
                              : "text-muted-foreground"
                          }`}
                        />
                      </button>
                    </div>
                  </div>
                  <div className="rounded-full bg-[#e8f4fd] px-4 py-2 text-lg font-semibold text-foreground">
                    {resourceDetail.score ?? "-"}
                  </div>
                </div>

                <p className="mb-6 text-muted-foreground">
                  {isDataset
                    ? datasetDetail?.descriptionLong ?? datasetDetail?.descriptionShort ?? "No description available."
                    : openApiDetail?.description ?? "No description available."}
                </p>

                <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
                  {isDataset ? (
                    <>
                      <div>
                        <p className="mb-1 text-sm text-muted-foreground">Publisher</p>
                        <p className="text-base font-semibold text-foreground">
                          {datasetDetail?.publisherName ?? datasetDetail?.subtitle ?? "-"}
                        </p>
                      </div>
                      <div>
                        <p className="mb-1 text-sm text-muted-foreground">Access Type</p>
                        <p className="text-base font-semibold text-foreground">{datasetDetail?.accessType ?? "-"}</p>
                      </div>
                      <div>
                        <p className="mb-1 text-sm text-muted-foreground">Rows</p>
                        <p className="text-base font-semibold text-foreground">{formatNumber(datasetDetail?.rowCount)}</p>
                      </div>
                      <div>
                        <p className="mb-1 text-sm text-muted-foreground">Last Updated</p>
                        <p className="text-base font-semibold text-foreground">{formatDate(datasetDetail?.sourceUpdatedAt)}</p>
                      </div>
                    </>
                  ) : (
                    <>
                      <div>
                        <p className="mb-1 text-sm text-muted-foreground">Category</p>
                        <p className="text-base font-semibold text-foreground">{openApiDetail?.category ?? "-"}</p>
                      </div>
                      <div>
                        <p className="mb-1 text-sm text-muted-foreground">Avg Response</p>
                        <p className="text-base font-semibold text-foreground">{formatMillis(openApiDetail?.avgResponseTime)}</p>
                      </div>
                      <div>
                        <p className="mb-1 text-sm text-muted-foreground">Auth</p>
                        <p className="text-base font-semibold text-foreground">{openApiDetail?.authType ?? "-"}</p>
                      </div>
                      <div>
                        <p className="mb-1 text-sm text-muted-foreground">Daily Limit</p>
                        <p className="text-base font-semibold text-foreground">
                          {openApiDetail?.dailyLimit !== null && openApiDetail?.dailyLimit !== undefined
                            ? `${openApiDetail.dailyLimit}/day`
                            : openApiDetail?.pricingNote ?? "-"}
                        </p>
                      </div>
                    </>
                  )}
                </div>

                <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-2">
                  {isDataset ? (
                    <>
                      <div className="rounded-lg border border-border p-4">
                        <p className="mb-2 text-sm font-medium text-foreground">Tags</p>
                        <p className="text-sm text-muted-foreground">
                          {datasetDetail?.tags?.length ? datasetDetail.tags.join(", ") : "No tags available."}
                        </p>
                      </div>
                      <div className="rounded-lg border border-border p-4">
                        <p className="mb-2 text-sm font-medium text-foreground">License</p>
                        <p className="text-sm text-muted-foreground">{datasetDetail?.licenseName ?? "-"}</p>
                      </div>
                    </>
                  ) : (
                    <>
                      <div className="rounded-lg border border-border p-4">
                        <p className="mb-2 text-sm font-medium text-foreground">Provider</p>
                        <p className="text-sm text-muted-foreground">{openApiDetail?.provider ?? "-"}</p>
                      </div>
                      <div className="rounded-lg border border-border p-4">
                        <p className="mb-2 text-sm font-medium text-foreground">Response Format</p>
                        <p className="text-sm text-muted-foreground">{openApiDetail?.responseFormat ?? "-"}</p>
                      </div>
                    </>
                  )}
                </div>

                <div className="mt-6 flex flex-wrap gap-4 text-sm">
                  {isDataset && datasetDetail?.landingUrl && (
                    <a
                      href={datasetDetail.landingUrl}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-2 text-blue-600 hover:underline"
                    >
                      Open landing page <ExternalLink className="h-4 w-4" />
                    </a>
                  )}
                  {!isDataset && openApiDetail?.docsUrl && (
                    <a
                      href={openApiDetail.docsUrl}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-2 text-blue-600 hover:underline"
                    >
                      Open docs <ExternalLink className="h-4 w-4" />
                    </a>
                  )}
                </div>
              </div>
            </div>
          </div>

          <div className="rounded-lg border border-border bg-white p-8">
            <h2 className="mb-6 text-2xl font-semibold text-foreground">Reviews</h2>

            {!hasMyReview ? (
              <div className="mb-8 rounded-lg border border-border bg-muted/30 p-6">
                <h3 className="mb-4 text-lg font-semibold text-foreground">Write a review</h3>

                <div className="mb-4">
                  <p className="mb-2 text-sm text-muted-foreground">Rating</p>
                  <div className="flex items-center gap-2">
                    {[1, 2, 3, 4, 5].map((starValue) => (
                      <Button
                        key={`review-rating-${starValue}`}
                        variant="ghost"
                        onClick={() => setRating(starValue)}
                        onMouseEnter={() => setHoverRating(starValue)}
                        onMouseLeave={() => setHoverRating(0)}
                        className="transition-colors"
                      >
                        <Star
                          className={`h-8 w-8 ${
                            starValue <= (hoverRating || rating) ? "fill-yellow-400 text-yellow-400" : "text-gray-300"
                          }`}
                        />
                      </Button>
                    ))}
                    {rating > 0 && <span className="ml-2 text-sm text-muted-foreground">{rating}.0</span>}
                  </div>
                </div>

                <div className="mb-4">
                  <p className="mb-2 text-sm text-muted-foreground">Your review</p>
                  <Textarea
                    value={reviewText}
                    onChange={(event) => setReviewText(event.target.value)}
                    placeholder="Share your thoughts about this resource."
                    rows={4}
                    className="w-full resize-none rounded-lg border border-border bg-white px-4 py-3 text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-[#e8f4fd]"
                  />
                </div>

                {reviewError && (
                  <div className="mb-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                    {reviewError}
                  </div>
                )}

                {actionError && (
                  <div className="mb-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                    {actionError}
                  </div>
                )}

                <Button
                  onClick={handleSubmitReview}
                  disabled={isSaving}
                  className="rounded-lg bg-[#e8f4fd] px-6 py-2 font-medium text-foreground transition-colors hover:bg-[#d4eaf7]"
                >
                  {isSaving ? "Saving..." : "Submit review"}
                </Button>
              </div>
            ) : (
              <div className="mb-8 rounded-lg border border-border bg-muted/30 p-6">
                <h3 className="mb-4 text-lg font-semibold text-foreground">My review</h3>

                {!isEditing ? (
                  <div className="space-y-4">
                    <div className="flex items-center gap-2">
                      {[1, 2, 3, 4, 5].map((starValue) => (
                        <Star
                          key={`my-review-star-${starValue}`}
                          className={`h-5 w-5 ${
                            starValue <= (myReview?.rating ?? 0) ? "fill-yellow-400 text-yellow-400" : "text-gray-300"
                          }`}
                        />
                      ))}
                      <span className="text-sm text-muted-foreground">{myReview?.rating ?? 0}.0</span>
                    </div>
                    <p className="text-sm text-muted-foreground">{myReview?.content}</p>
                    <div className="flex items-center gap-2">
                      <Button variant="outline" onClick={() => setIsEditing(true)}>
                        Edit
                      </Button>
                      <Button variant="outline" onClick={handleDeleteReview} disabled={isDeleting}>
                        {isDeleting ? "Deleting..." : "Delete"}
                      </Button>
                    </div>
                    {actionError && (
                      <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                        {actionError}
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="space-y-4">
                    <div>
                      <p className="mb-2 text-sm text-muted-foreground">Rating</p>
                      <div className="flex items-center gap-2">
                        {[1, 2, 3, 4, 5].map((starValue) => (
                          <Button
                            key={`edit-rating-${starValue}`}
                            variant="ghost"
                            onClick={() => setEditRating(starValue)}
                            onMouseEnter={() => setEditHoverRating(starValue)}
                            onMouseLeave={() => setEditHoverRating(0)}
                            className="transition-colors"
                          >
                            <Star
                              className={`h-8 w-8 ${
                                starValue <= (editHoverRating || editRating)
                                  ? "fill-yellow-400 text-yellow-400"
                                  : "text-gray-300"
                              }`}
                            />
                          </Button>
                        ))}
                        {editRating > 0 && <span className="ml-2 text-sm text-muted-foreground">{editRating}.0</span>}
                      </div>
                    </div>

                    <div>
                      <p className="mb-2 text-sm text-muted-foreground">Your review</p>
                      <Textarea
                        value={editText}
                        onChange={(event) => setEditText(event.target.value)}
                        rows={4}
                        className="w-full resize-none rounded-lg border border-border bg-white px-4 py-3 text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-[#e8f4fd]"
                      />
                    </div>

                    {actionError && (
                      <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                        {actionError}
                      </div>
                    )}

                    <div className="flex items-center gap-2">
                      <Button onClick={handleUpdateReview} disabled={isSaving}>
                        {isSaving ? "Saving..." : "Save"}
                      </Button>
                      <Button variant="outline" onClick={() => setIsEditing(false)}>
                        Cancel
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            )}

            <div>
              <h3 className="mb-4 text-lg font-semibold text-foreground">Other reviews</h3>
              <div className="space-y-4">
                {otherReviews.map((review) => (
                  <div key={review.id} className="rounded-lg border border-border p-4">
                    <div className="mb-2 flex items-start justify-between">
                      <div>
                        <p className="font-semibold text-foreground">{review.author}</p>
                        <p className="text-xs text-muted-foreground">{review.createdAt}</p>
                      </div>
                      <div className="flex items-center gap-1">
                        {[1, 2, 3, 4, 5].map((starValue) => (
                          <Star
                            key={`${review.id}-star-${starValue}`}
                            className={`h-4 w-4 ${
                              starValue <= review.rating ? "fill-yellow-400 text-yellow-400" : "text-gray-300"
                            }`}
                          />
                        ))}
                      </div>
                    </div>
                    <p className="text-sm text-muted-foreground">{review.content}</p>
                  </div>
                ))}

                {otherReviews.length === 0 && (
                  <div className="rounded-md border border-border bg-muted/20 px-4 py-3 text-sm text-muted-foreground">
                    No reviews yet.
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
}
