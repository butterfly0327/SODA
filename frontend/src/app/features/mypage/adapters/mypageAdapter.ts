import type { MyPostItemResponseDto, MyReviewItemResponseDto } from "@/api/contracts";

export type MyPagePostCardViewModel = {
  id: string;
  title: string;
  createdAt: string;
  likeCount: number;
  referenceCount: number;
};

export type MyPageReviewCardViewModel = {
  id: string;
  resourceId: number;
  resourceType: "dataset" | "api";
  resourceTypeLabel: "Dataset" | "Open API";
  resourceTitle: string;
  isTitleFallback: boolean;
  rating: number;
  content: string;
  createdAt: string;
};

export function formatMyPageDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");

  return `${year}.${month}.${day}`;
}

export function normalizeApiResourceType(value: "DATASET" | "OPEN_API"): "dataset" | "api" {
  return value === "DATASET" ? "dataset" : "api";
}

export function mapMyPostItemToCard(item: MyPostItemResponseDto): MyPagePostCardViewModel {
  return {
    id: String(item.id),
    title: item.title,
    createdAt: formatMyPageDate(item.createdAt),
    likeCount: item.likeCount,
    referenceCount: item.referenceCount,
  };
}

export function mapMyReviewItemToCard(item: MyReviewItemResponseDto): MyPageReviewCardViewModel {
  const resourceType = normalizeApiResourceType(item.resourceType);
  const normalizedTitle = item.resourceTitle.trim();
  const fallbackTitle = resourceType === "dataset" ? "데이터셋 리소스" : "Open API 리소스";
  const isTitleFallback = normalizedTitle.length === 0;

  return {
    id: String(item.id),
    resourceId: item.resourceId,
    resourceType,
    resourceTypeLabel: resourceType === "dataset" ? "Dataset" : "Open API",
    resourceTitle: isTitleFallback ? fallbackTitle : normalizedTitle,
    isTitleFallback,
    rating: item.rating,
    content: item.content,
    createdAt: formatMyPageDate(item.createdAt),
  };
}
