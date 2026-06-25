import { Star, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import type { ResultCard } from "@/types/recommendation";
import { Textarea } from "@/components/ui/textarea";
import { reviewApi, type ReviewResourceType } from "@/api/reviewApi";
import { useAuthStore } from "../../stores/authStore";
import { useResourceReviewStore } from "../../stores/resourceReviewStore";

interface RecommendationDetailPanelProps {
  data: ResultCard;
  onClose: () => void;
  reviewMode?: 'full' | 'readOnly';
}

function normalizeAuthorName(author: string | null | undefined) {
  return (author ?? "").trim();
}

function formatDate(dateString: string | null | undefined): string {
  if (!dateString) return "-";
  const parsed = new Date(dateString);
  if (Number.isNaN(parsed.getTime())) {
    return dateString;
  }

  return parsed.toLocaleDateString("ko-KR", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit"
  });
}

function splitDescriptionParagraphs(text: string | null | undefined): string[] {
  if (!text) return [];

  const normalized = text.replace(/\r\n/g, "\n").trim();
  if (!normalized) return [];

  const explicitParagraphs = normalized
    .split(/\n\s*\n/)
    .map((part) => part.trim())
    .filter(Boolean);

  if (explicitParagraphs.length > 1) {
    return explicitParagraphs;
  }

  return normalized
    .split(/(?<=[.!?])\s+(?=[A-Z가-힣0-9"'“‘])/)
    .reduce<string[]>((paragraphs, sentence) => {
      const trimmed = sentence.trim();
      if (!trimmed) return paragraphs;

      const current = paragraphs[paragraphs.length - 1];
      if (!current) {
        paragraphs.push(trimmed);
        return paragraphs;
      }

      if (current.length >= 120) {
        paragraphs.push(trimmed);
      } else {
        paragraphs[paragraphs.length - 1] = `${current} ${trimmed}`;
      }
      return paragraphs;
    }, []);
}

interface SchemaColumn {
  name: string;
  unit?: string;
  data_type?: string;
  max_length?: string;
  description?: string;
}

function parseSchemaColumns(schemaJson: unknown): SchemaColumn[] {
  if (!schemaJson) {
    return [];
  }

  let parsed: unknown = schemaJson;

  if (typeof schemaJson === 'string') {
    try {
      parsed = JSON.parse(schemaJson);
    } catch {
      return [];
    }
  }

  if (!parsed || typeof parsed !== 'object') {
    return [];
  }

  const columns = (parsed as { columns?: unknown }).columns;
  if (!Array.isArray(columns)) {
    return [];
  }

  return columns
    .filter((column): column is Record<string, unknown> => Boolean(column) && typeof column === 'object')
    .map((column) => ({
      name: typeof column.name === 'string' ? column.name : '-',
      unit: typeof column.unit === 'string' ? column.unit : undefined,
      data_type: typeof column.data_type === 'string' ? column.data_type : undefined,
      max_length:
        typeof column.max_length === 'string' || typeof column.max_length === 'number'
          ? String(column.max_length)
          : undefined,
      description: typeof column.description === 'string' ? column.description : undefined,
    }))
    .filter((column) => column.name !== '-');
}

function DetailRow({
  label,
  value,
}: {
  label: string;
  value: React.ReactNode;
}) {
  const normalizedLabel = label.replace(/:\s*$/, "");

  return (
    <div className="grid grid-cols-[108px_minmax(0,1fr)] gap-x-4 items-start px-3 py-2 text-sm leading-6">
      <span className="font-medium text-gray-700">{normalizedLabel}</span>
      <div className="min-w-0 break-words border-l border-border/60 pl-4 text-gray-900">{value}</div>
    </div>
  );
}

function DetailBlock({ children }: { children: React.ReactNode }) {
  return <div className="space-y-3 pt-3">{children}</div>;
}

function DetailTable({ children }: { children: React.ReactNode }) {
  return <div className="overflow-hidden rounded-md border border-border/60 divide-y divide-border/60">{children}</div>;
}

export function RecommendationDetailPanel({
  data,
  onClose,
  reviewMode = 'full',
}: RecommendationDetailPanelProps) {
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
  const [deletedReviewIds, setDeletedReviewIds] = useState<string[]>([]);
  const [expandedDescription, setExpandedDescription] = useState(false);
  const [expandedSchema, setExpandedSchema] = useState(false);
  const [expandedCreators, setExpandedCreators] = useState(false);

  const resourceId = typeof data.id === "number" ? data.id : null;
  const normalizeAuthorId = (value: string | number | undefined | null) => {
    if (value === undefined || value === null) {
      return undefined;
    }
    return String(value);
  };

  const currentAuthorName = useMemo(
    () => normalizeAuthorName(user?.name?.trim() || "익명"),
    [user?.name],
  );

  const resourceReviews = useMemo(() => {
    if (resourceId === null) {
      return [];
    }
    return reviews.filter((review) => review.resourceId === resourceId);
  }, [reviews, resourceId]);

  const serverReviews = useMemo(() => {
    if (resourceId === null || !data.reviews || data.reviews.length === 0) {
      return [];
    }

    return data.reviews
      .map((review) => ({
        id: String(review.id),
        resourceId,
        resourceType: data.type,
        resourceName: data.name,
        author: review.author?.trim() || review.name?.trim() || "익명",
        authorId: normalizeAuthorId(review.authorId),
        rating: review.rating,
        content: review.content,
        createdAt: review.createdAt ?? '-',
      }))
      .filter((review) => !deletedReviewIds.includes(review.id));
  }, [data.name, data.reviews, data.type, deletedReviewIds, resourceId]);

  useEffect(() => {
    setDeletedReviewIds([]);
  }, [resourceId, data.type]);

  const isCurrentUserReview = (review: { authorId?: string; author: string }) => {
    const byId =
      user?.id !== undefined &&
      review.authorId !== undefined &&
      normalizeAuthorId(review.authorId) === normalizeAuthorId(user.id);
    const byName = normalizeAuthorName(review.author) === currentAuthorName;
    return Boolean(byId || byName);
  };

  const readOnlyReviews = useMemo(() => {
    if (resourceId === null) {
      return [];
    }

    const myLocalReview = resourceReviews.find((review) => isCurrentUserReview(review));

    if (!myLocalReview) {
      return serverReviews.length > 0 ? serverReviews : resourceReviews;
    }

    const merged = serverReviews.filter((review) => !isCurrentUserReview(review));
    merged.push(myLocalReview);
    return merged;
  }, [resourceId, resourceReviews, reviewMode, serverReviews, user?.id]);

  const activeReviews = readOnlyReviews;

  const myReview = useMemo(
    () => activeReviews.find((review) => isCurrentUserReview(review)),
    [activeReviews, user?.id],
  );

  const isMyReviewEntry = (review: (typeof activeReviews)[number]) => {
    if (myReview?.id && review.id) {
      return review.id === myReview.id;
    }

    if (myReview?.authorId !== undefined && review.authorId !== undefined) {
      return normalizeAuthorId(review.authorId) === normalizeAuthorId(myReview.authorId);
    }

    return normalizeAuthorName(review.author) === normalizeAuthorName(myReview?.author ?? "");
  };

  const hasMyReview = Boolean(myReview);
  const canCreateReview = reviewMode === 'full';
  const canManageMyReview = hasMyReview;
  const visibleReviews = canManageMyReview
    ? activeReviews.filter((review) => !isMyReviewEntry(review))
    : activeReviews;
  const reviewCount = visibleReviews.length + (hasMyReview ? 1 : 0);
  const averageRating = useMemo(() => {
    const ratedReviews = activeReviews.filter(
      (review) => typeof review.rating === 'number' && Number.isFinite(review.rating),
    );

    if (ratedReviews.length === 0) {
      return null;
    }

    const total = ratedReviews.reduce((sum, review) => sum + review.rating, 0);
    return total / ratedReviews.length;
  }, [activeReviews]);
  const panelResetKey = `${data.type}-${resourceId ?? "none"}`;
  const descriptionParagraphs = useMemo(
    () => splitDescriptionParagraphs((data as any).descriptionLong),
    [data],
  );
  const apiDescriptionParagraphs = useMemo(
    () => splitDescriptionParagraphs((data as any).description),
    [data],
  );
  const schemaColumns = useMemo(
    () => parseSchemaColumns((data as any).schemaJson),
    [data],
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
  }, [myReview]);

  useEffect(() => {
    void panelResetKey;
    setRating(0);
    setHoverRating(0);
    setReviewText("");
    setReviewError("");
    setToastMessage("");
    setActionError("");
    setExpandedDescription(false);
  }, [panelResetKey]);

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

  const toReviewType = (type: "dataset" | "api"): ReviewResourceType =>
    type === "dataset" ? "DATASET" : "OPEN_API";

  const resolveReviewId = (rawId: string | undefined) => {
    if (!rawId) return null;
    const parsed = Number(rawId);
    return Number.isFinite(parsed) ? parsed : null;
  };

  const getErrorMessage = (error: unknown): string => {
    if (error instanceof Error) {
      const axiosError = error as any;
      const status = axiosError?.response?.status;
      const message = axiosError?.response?.data?.message;
      
      switch (status) {
        case 400:
          return message || "잘못된 요청입니다.";
        case 401:
          return "인증이 필요합니다.";
        case 403:
          return "접근이 거부되었습니다. (본인 리뷰만 수정/삭제 가능)";
        case 404:
          return "리소스를 찾을 수 없습니다.";
        case 500:
          return "서버 오류가 발생했습니다.";
        default:
          return message || "요청 처리 중 오류가 발생했습니다.";
      }
    }
    return "요청 처리 중 오류가 발생했습니다.";
  };

  const handleSubmitReview = async () => {
    if (resourceId === null) {
      return;
    }

    setReviewError("");
    setActionError("");

    if (rating < 1 || rating > 5 || !reviewText.trim()) {
      setReviewError("1~5점 사이의 별점과 리뷰를 입력해주세요.");
      return;
    }

    try {
      setIsSaving(true);
      const response = await reviewApi.createReview(toReviewType(data.type), resourceId, {
        rating,
        content: reviewText.trim(),
      });

      upsertReview({
        id: response.reviewId ? String(response.reviewId) : undefined,
        resourceId,
        resourceType: data.type,
        resourceName: data.name,
        authorId: user?.id,
        author: currentAuthorName,
        rating: response.rating,
        content: response.content,
        createdAt: response.createdAt ?? undefined,
      });

      setReviewText("");
      setRating(0);
      setHoverRating(0);
      setToastMessage("리뷰가 작성되었습니다.");
    } catch (error) {
      console.error("Failed to create review:", error);
      setActionError(getErrorMessage(error));
    } finally {
      setIsSaving(false);
    }
  };

  const handleUpdateReview = async () => {
    if (!myReview || resourceId === null) {
      return;
    }

    setActionError("");

    if (editRating < 1 || editRating > 5 || !editText.trim()) {
      setActionError("1~5점 사이의 별점과 리뷰를 입력해주세요.");
      return;
    }

    const reviewId = resolveReviewId(myReview.id);
    if (!reviewId) {
      setActionError("유효하지 않은 리뷰 ID입니다.");
      return;
    }

    try {
      setIsSaving(true);
      const response = await reviewApi.updateReview(
        toReviewType(data.type),
        resourceId,
        reviewId,
        { rating: editRating, content: editText.trim() },
      );

      upsertReview({
        id: response.reviewId ? String(response.reviewId) : myReview.id,
        resourceId,
        resourceType: data.type,
        resourceName: data.name,
        authorId: user?.id,
        author: currentAuthorName,
        rating: response.rating,
        content: response.content,
        createdAt: response.createdAt ?? undefined,
      });

      setIsEditing(false);
      setToastMessage("리뷰가 수정되었습니다.");
    } catch (error) {
      console.error("Failed to update review:", error);
      setActionError(getErrorMessage(error));
    } finally {
      setIsSaving(false);
    }
  };

  const handleDeleteReview = async () => {
    if (!myReview || resourceId === null) {
      return;
    }

    const reviewId = resolveReviewId(myReview.id);
    if (!reviewId) {
      setActionError("리뷰 ID가 올바르지 않습니다.");
      return;
    }

    try {
      setIsDeleting(true);
      await reviewApi.deleteReview(toReviewType(data.type), resourceId, reviewId);
      setDeletedReviewIds((previous) =>
        previous.includes(myReview.id) ? previous : [...previous, myReview.id],
      );
      removeReview({
        id: myReview.id,
        resourceId,
        authorId: user?.id,
        author: currentAuthorName,
      });
      setIsEditing(false);
      setToastMessage("리뷰가 삭제되었습니다.");
    } catch (error) {
      console.error("Failed to delete review:", error);
      setActionError(getErrorMessage(error));
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <aside className="h-full bg-white overflow-y-auto">
      {toastMessage && (
        <div className="fixed right-6 bottom-6 z-50 p-3 bg-emerald-100 border border-emerald-300 rounded">
          <span>{toastMessage}</span>
        </div>
      )}

      {/* 헤더 */}
      <div className="p-4 border-b flex items-center justify-between">
        <h3 className="font-semibold">상세 정보</h3>
        <button type="button" onClick={onClose} className="text-lg">
          ✕
        </button>
      </div>

      {/* 메인 콘텐츠 */}
      <div className="p-4 space-y-3">
        <div>
          <strong>{data.name}</strong>
          <div className="text-sm text-gray-600">
            {data.type === "dataset" ? data.source ?? "제공처 미상" : data.provider ?? "제공처 미상"}
          </div>
        </div>

        {/* DATASET 전용 정보 */}
        {data.type === "dataset" && (
          <DetailBlock>
            {(data as any).canonicalUrl && (
              <div className="text-sm border-b pb-2">
                <span className="font-medium mr-1">URL:</span>
                <a href={(data as any).canonicalUrl} target="_blank" rel="noreferrer" className="text-blue-600 hover:underline break-all">
                  {(data as any).canonicalUrl}
                </a>
              </div>
            )}

            {(data as any).descriptionLong && (
              <div>
                <button
                  type="button"
                  onClick={() => setExpandedDescription(!expandedDescription)}
                  className="text-xs font-medium text-blue-600 cursor-pointer"
                >
                  {expandedDescription ? "▼" : "▶"} 상세 설명
                </button>
                {expandedDescription && (
                  <div className="mt-2 space-y-3 text-sm leading-7 text-gray-800">
                    {descriptionParagraphs.map((paragraph, index) => (
                      <p key={`${panelResetKey}-description-${index}`}>{paragraph}</p>
                    ))}
                  </div>
                )}
              </div>
            )}

            <DetailTable>
              {(data as any).rowCount !== undefined && (
                <DetailRow label="행 수:" value={(data as any).rowCount?.toLocaleString()} />
              )}

              {(data as any).lastUpdate && (
                <DetailRow label="업데이트:" value={formatDate((data as any).lastUpdate)} />
              )}

              {(data as any).domains && (data as any).domains.length > 0 && (
                <DetailRow label="도메인:" value={(data as any).domains.join(", ")} />
              )}

              {(data as any).tasks && (data as any).tasks.length > 0 && (
                <DetailRow label="작업:" value={(data as any).tasks.join(", ")} />
              )}

              {(data as any).modalities && (data as any).modalities.length > 0 && (
                <DetailRow label="형식:" value={(data as any).modalities.join(", ")} />
              )}

              {(data as any).tags && (data as any).tags.length > 0 && (
                <DetailRow label="태그:" value={(data as any).tags.join(", ")} />
              )}

              {(data as any).reliability && (
                <DetailRow label="공개 상태:" value={(data as any).reliability} />
              )}

              {(data as any).loginRequired !== undefined && (
                <DetailRow label="로그인 필요:" value={(data as any).loginRequired ? "예" : "아니오"} />
              )}

              {(data as any).approvalRequired !== undefined && (
                <DetailRow label="승인 필요:" value={(data as any).approvalRequired ? "예" : "아니오"} />
              )}

              {data.isFree !== undefined && (
                <DetailRow label="비용:" value={data.isFree ? "무료" : "유료"} />
              )}

              {(data as any).isRestricted !== undefined && (
                <DetailRow label="제한 있음:" value={(data as any).isRestricted ? "예" : "아니오"} />
              )}

              {(data as any).licenseName && (
                <DetailRow label="라이선스:" value={(data as any).licenseName} />
              )}
              {(data as any).commercialUseAllowed !== undefined && (
                <DetailRow label="상용 사용:" value={(data as any).commercialUseAllowed ? "가능" : "불가능"} />
              )}

              {(data as any).languages && (data as any).languages.length > 0 && (
                <DetailRow label="언어:" value={(data as any).languages.join(", ")} />
              )}

              {(data as any).metrics?.viewCount !== undefined && (
                <DetailRow label="조회수:" value={(data as any).metrics.viewCount} />
              )}
              {(data as any).metrics?.requestCount !== undefined && (
                <DetailRow label="요청수:" value={(data as any).metrics.requestCount} />
              )}

              {(data as any).sourceVersion && <DetailRow label="데이터 버전:" value={(data as any).sourceVersion} />}
              {(data as any).sourceCreatedAt && <DetailRow label="원본 생성:" value={formatDate((data as any).sourceCreatedAt)} />}
              {(data as any).sourceUpdatedAt && <DetailRow label="원본 수정:" value={formatDate((data as any).sourceUpdatedAt)} />}
              {(data as any).createdAt && <DetailRow label="메타데이터 수정:" value={formatDate((data as any).createdAt)} />}
            </DetailTable>

            {(data as any).creators && Array.isArray((data as any).creators) && (data as any).creators.length > 0 && (
              <div>
                <button
                  type="button"
                  onClick={() => setExpandedCreators(!expandedCreators)}
                  className="text-xs font-medium text-blue-600 cursor-pointer"
                >
                  {expandedCreators ? "▼" : "▶"} 제작자 정보 ({(data as any).creators.length})
                </button>
                {expandedCreators && (
                  <div className="ml-2 space-y-1">
                    {(data as any).creators.map((creator: any) => (
                      <div
                        key={`${creator.name}-${creator.role ?? ""}-${creator.phone ?? ""}`}
                        className="text-sm"
                      >
                        <div className="font-medium">{creator.name}</div>
                        <div className="text-xs">{creator.role}</div>
                        {creator.phone && <div className="text-xs">📞 {creator.phone}</div>}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {schemaColumns.length > 0 && (
              <div className="space-y-2">
                <h4 className="font-semibold">스키마 정보</h4>
                <div className="overflow-hidden rounded-md border border-border/60">
                  <div className="grid grid-cols-[1.1fr_1.6fr_0.8fr_1fr_0.8fr] gap-x-4 border-b border-border/60 bg-muted/30 px-3 py-2 text-xs font-semibold text-gray-700">
                    <span>컬럼명</span>
                    <span>설명</span>
                    <span>단위</span>
                    <span>타입</span>
                    <span>최대 길이</span>
                  </div>
                  <div className="divide-y divide-border/60">
                    {schemaColumns.map((column, index) => (
                      <div key={`${column.name}-${index}`} className="px-3 py-2 text-sm">
                        <div className="grid grid-cols-[1.1fr_1.6fr_0.8fr_1fr_0.8fr] gap-x-4 text-gray-900">
                          <span className="font-medium break-words">{column.name}</span>
                          <span className="break-words text-gray-600">{column.description ?? '-'}</span>
                          <span className="break-words">{column.unit ?? '-'}</span>
                          <span className="break-words">{column.data_type ?? '-'}</span>
                          <span className="break-words">{column.max_length ?? '-'}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

          </DetailBlock>
        )}

        {/* OPEN_API 전용 정보 */}
        {data.type === "api" && (
          <DetailBlock>
            {(data as any).docsUrl && (
              <div className="text-sm border-b pb-2">
                <span className="font-medium mr-1">URL:</span>
                <a href={(data as any).docsUrl} target="_blank" rel="noreferrer" className="text-blue-600 hover:underline break-all">
                  {(data as any).docsUrl}
                </a>
              </div>
            )}

            {(data as any).description && (
              <div className="space-y-3 text-sm leading-7 text-gray-800">
                {apiDescriptionParagraphs.map((paragraph, index) => (
                  <p key={`${panelResetKey}-api-description-${index}`}>
                    {index === 0 ? <><span className="font-medium text-gray-700">설명:</span> {paragraph}</> : paragraph}
                  </p>
                ))}
              </div>
            )}

            <DetailTable>
              {data.isFree !== undefined && (
                <DetailRow label="비용:" value={data.isFree ? "무료" : "유료"} />
              )}

              {(data as any).auth && <DetailRow label="인증 방식:" value={(data as any).auth} />}
              {(data as any).category && <DetailRow label="카테고리:" value={(data as any).category} />}
              {(data as any).availability && <DetailRow label="응답 형식:" value={(data as any).availability} />}

              {(data as any).tags && (data as any).tags.length > 0 && (
                <DetailRow label="태그:" value={(data as any).tags.join(", ")} />
              )}

              {(data as any).pricingNote && (
                <DetailRow label="가격 정책:" value={<div className="whitespace-pre-wrap">{(data as any).pricingNote}</div>} />
              )}

              {(data as any).commercialUse !== undefined && (
                <DetailRow label="상용 사용:" value={(data as any).commercialUse ? "가능" : "불가능"} />
              )}

              {(data as any).requiresApproval !== undefined && (
                <DetailRow label="승인 필요:" value={(data as any).requiresApproval ? "필요" : "불필요"} />
              )}
            </DetailTable>
          </DetailBlock>
        )}

        {/* 평균 평점 */}
        {averageRating !== null && (
          <div className="rounded-md border border-border/60 bg-white px-3 py-3">
            <div className="flex items-center gap-3">
              <span className="text-sm font-medium text-gray-700">평균 평점</span>
              <div className="flex items-center gap-1">
                {[1, 2, 3, 4, 5].map((starValue) => (
                  <Star
                    key={`average-rating-${starValue}`}
                    className={`h-4 w-4 ${
                      starValue <= Math.round(averageRating)
                        ? 'fill-[#4f76df] text-[#4f76df]'
                        : 'text-slate-300'
                    }`}
                  />
                ))}
              </div>
              <span className="text-sm text-gray-900">{averageRating.toFixed(1)}점</span>
              <span className="text-xs text-gray-500">({reviewCount}개 리뷰)</span>
            </div>
          </div>
        )}

        {/* 리뷰 섹션 */}
        {resourceId !== null && (
          <div className="pt-3 border-t space-y-2">
            <h4 className="font-semibold">리뷰 ({reviewCount})</h4>

            {canCreateReview && !hasMyReview ? (
              <div className="p-3 border rounded space-y-3">
                <div>
                  <div className="text-xs font-medium mb-1.5">별점</div>
                  <div className="mt-1 flex gap-1.5">
                    {[1, 2, 3, 4, 5].map((starValue) => (
                      <button
                        type="button"
                        key={`review-rating-${starValue}`}
                        onClick={() => setRating(starValue)}
                        onMouseEnter={() => setHoverRating(starValue)}
                        onMouseLeave={() => setHoverRating(0)}
                        className="cursor-pointer"
                      >
                        <Star
                          className={`h-6 w-6 ${
                            starValue <= (hoverRating || rating)
                              ? "fill-[#4f76df] text-[#4f76df]"
                              : "text-slate-300"
                          }`}
                        />
                      </button>
                    ))}
                    {rating > 0 && <span className="text-xs ml-2">{rating}.0점</span>}
                  </div>
                </div>

                <div>
                  <div className="text-xs font-medium mb-1.5">리뷰 내용</div>
                  <Textarea
                    value={reviewText}
                    onChange={(e) => setReviewText(e.target.value)}
                    placeholder="리뷰를 작성해주세요"
                    rows={3}
                    className="mt-1 w-full border rounded bg-[#f9fafc] px-2 py-1 text-sm focus-visible:ring-0 focus-visible:border-input"
                  />
                </div>

                {reviewError && <div className="text-sm text-red-600">{reviewError}</div>}
                {actionError && <div className="text-sm text-red-600">{actionError}</div>}

                <button
                  type="button"
                  onClick={handleSubmitReview}
                  disabled={isSaving}
                  className="mt-1 w-full cursor-pointer px-2 py-1 bg-blue-600 text-white rounded text-sm"
                >
                  {isSaving ? "제출 중..." : "리뷰 제출"}
                </button>
              </div>
            ) : canManageMyReview ? (
              <div className="p-3 border rounded space-y-3">
                {!isEditing ? (
                  <>
                    <div className="text-sm">
                      <div className="font-medium flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="flex items-center gap-1 text-[#4f76df]">
                            {[1, 2, 3, 4, 5].map((starValue) => (
                              <Star
                                key={`my-review-star-${starValue}`}
                                className={`h-4 w-4 ${
                                  starValue <= (myReview?.rating ?? 0)
                                    ? "fill-[#4f76df]"
                                    : "text-slate-300"
                                }`}
                              />
                            ))}
                          </span>
                        </div>
                        <span className="text-xs text-gray-500">{formatDate(myReview?.createdAt)}</span>
                      </div>
                      <p className="text-sm">{myReview?.content}</p>
                    </div>
                    <div className="flex gap-1">
                      <button type="button" onClick={() => setIsEditing(true)} className="text-xs px-2 py-1 border rounded cursor-pointer">수정</button>
                      <button type="button" onClick={handleDeleteReview} disabled={isDeleting} className="text-xs px-2 py-1 border rounded cursor-pointer">
                        {isDeleting ? "삭제 중..." : "삭제"}
                      </button>
                    </div>
                    {actionError && <div className="text-sm text-red-600">{actionError}</div>}
                  </>
                ) : (
                  <>
                    <div>
                      <div className="text-xs font-medium mb-1.5">별점</div>
                      <div className="mt-1 flex gap-1.5">
                        {[1, 2, 3, 4, 5].map((starValue) => (
                          <button
                            type="button"
                            key={`edit-rating-${starValue}`}
                            onClick={() => setEditRating(starValue)}
                            onMouseEnter={() => setEditHoverRating(starValue)}
                            onMouseLeave={() => setEditHoverRating(0)}
                            className="cursor-pointer"
                          >
                            <Star
                              className={`h-6 w-6 ${
                                starValue <= (editHoverRating || editRating)
                                  ? "fill-[#4f76df] text-[#4f76df]"
                                  : "text-slate-300"
                              }`}
                            />
                          </button>
                        ))}
                        {editRating > 0 && <span className="text-xs ml-2">{editRating}.0점</span>}
                      </div>
                    </div>

                    <div>
                      <div className="text-xs font-medium mb-1.5">리뷰 내용</div>
                      <Textarea
                        value={editText}
                        onChange={(e) => setEditText(e.target.value)}
                        rows={3}
                        className="mt-1 w-full border rounded bg-[#f9fafc] px-2 py-1 text-sm focus-visible:ring-0 focus-visible:border-input"
                      />
                    </div>

                    {actionError && <div className="text-sm text-red-600">{actionError}</div>}

                    <div className="flex gap-1">
                      <button type="button" onClick={handleUpdateReview} disabled={isSaving} className="text-xs px-2 py-1 bg-blue-600 text-white rounded">
                        {isSaving ? "저장 중..." : "저장"}
                      </button>
                      <button type="button" onClick={() => setIsEditing(false)} className="text-xs px-2 py-1 border rounded">취소</button>
                    </div>
                  </>
                )}
              </div>
            ) : null}

            {visibleReviews.length > 0 && (
              <div className="space-y-2">
                {visibleReviews.map((review) => (
                  <div key={review.id} className="p-2 border rounded space-y-2">
                    <div className="font-medium flex items-center justify-between text-sm">
                      <span>{review.author}</span>
                      <span className="text-xs text-gray-500">{formatDate(review.createdAt)}</span>
                    </div>
                    <div className="mt-1 text-sm">
                      <span className="flex items-center gap-1 text-[#4f76df]">
                        {[1, 2, 3, 4, 5].map((starValue) => (
                          <Star
                            key={`${review.id}-star-${starValue}`}
                            className={`h-4 w-4 ${starValue <= review.rating ? "fill-[#4f76df]" : "text-slate-300"}`}
                          />
                        ))}
                      </span>
                    </div>
                    <p className="mt-1 text-sm">{review.content}</p>
                  </div>
                ))}
              </div>
            )}

            {visibleReviews.length === 0 && (
              <div className="text-sm text-gray-500">
                {canManageMyReview || canCreateReview ? "다른 사용자 리뷰가 없습니다." : "아직 리뷰가 없습니다."}
              </div>
            )}
          </div>
        )}
      </div>
    </aside>
  );
}
