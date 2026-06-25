import type { ApiResponse } from "@/api/contracts";
import type { ResourceDetail } from "@/api/types";
import type { ResultCard } from "@/types/recommendation";

export type ResourceListItem = {
  id: number;
  bookmarkId?: number | null;
  type: "DATASET" | "OPEN_API";
  title: string;
  score: number | null;
  isFree: boolean | null;
  isBookmarked?: boolean;
  createdAt: string | null;
  datasetMeta: {
    publisherName: string | null;
    sourceUpdatedAt: string | null;
    sampleCount: number | null;
    domains: string[] | null;
    accessType: string | null;
    commercialUseAllowed: boolean | null;
    tags: string[] | null;
  } | null;
  openApiMeta: {
    provider: string | null;
    category: string | null;
    avgResponseTime: number | null;
    authType: string | null;
    dailyLimit: number | null;
    responseFormat: string | null;
    commercialUse: boolean | null;
    tags: string[] | null;
  } | null;
};

type ResourceListResponse = {
  totalCount: number;
  items: ResourceListItem[];
};

export type SearchResourceCard = ResultCard & {
  projectType?: string;
};

function formatCompactNumber(value: number | null | undefined): string | undefined {
  if (value === null || value === undefined) {
    return undefined;
  }

  if (value >= 1000000) {
    return `${Math.round(value / 100000) / 10}M`;
  }

  if (value >= 1000) {
    return `${Math.round(value / 100) / 10}K`;
  }

  return `${value}`;
}

function formatMillis(value: number | null | undefined): string | undefined {
  if (value === null || value === undefined) {
    return undefined;
  }

  return `${Math.round(value * 1000)}ms`;
}

function formatDailyLimit(value: number | null | undefined): string | undefined {
  if (value === null || value === undefined) {
    return undefined;
  }

  return `${value.toLocaleString()}/day`;
}

function mapDetailReviews(detail: ResourceDetail) {
  return detail.reviews?.map((review) => ({
    id: review.id,
    authorId: typeof review.authorId === "number" ? String(review.authorId) : undefined,
    author: review.author?.trim() || review.name?.trim() || "익명",
    rating: review.rating,
    content: review.content,
    createdAt: review.createdAt,
  }));
}

export function getResourceListRequest() {
  return {
    url: "/resources",
    params: {
      type: "ALL" as const,
      sort: "SCORE" as const,
    },
  };
}

export function mapResourceItem(item: ResourceListItem): SearchResourceCard {
  if (item.type === "DATASET") {
    return {
      id: item.id,
      bookmarkId: item.bookmarkId ?? null,
      type: "dataset",
      name: item.title,
      source: item.datasetMeta?.publisherName ?? "Unknown",
      projectType: "기타",
      taskMatch: 0,
      score: item.score ?? 0,
      classCount: 0,
      sampleCount: formatCompactNumber(item.datasetMeta?.sampleCount) ?? "N/A",
      missingRate: 0,
      domains: item.datasetMeta?.domains ?? [],
      tags: item.datasetMeta?.tags ?? [],
      commercialUseAllowed: item.datasetMeta?.commercialUseAllowed ?? null,
      reliability: item.datasetMeta?.accessType ?? "-",
      lastUpdate: item.datasetMeta?.sourceUpdatedAt ?? "",
      isFree: item.isFree ?? false,
      isBookmarked: item.isBookmarked ?? false,
    };
  }

    return {
      id: item.id,
      bookmarkId: item.bookmarkId ?? null,
      type: "api",
      name: item.title,
      category: item.openApiMeta?.category ?? "General",
      provider: item.openApiMeta?.provider ?? undefined,
      projectType: "기타",
      score: item.score ?? 0,
      responseTime: formatMillis(item.openApiMeta?.avgResponseTime) ?? "N/A",
      auth: item.openApiMeta?.authType ?? "Unknown",
      freeQuota: formatDailyLimit(item.openApiMeta?.dailyLimit) ?? "N/A",
      responseFormat: item.openApiMeta?.responseFormat ?? undefined,
      commercialUse: item.openApiMeta?.commercialUse ?? null,
      tags: item.openApiMeta?.tags ?? [],
      availability: item.openApiMeta?.responseFormat ?? "N/A",
      isFree: item.isFree ?? false,
      isBookmarked: item.isBookmarked ?? false,
    };
}

export function mapResourceListResponse(
  response: ApiResponse<ResourceListResponse>,
): SearchResourceCard[] {
  return response.data.items.map(mapResourceItem);
}

export function buildResourceDetailPath(resource: Pick<SearchResourceCard, "type" | "id">) {
  const type = resource.type === "dataset" ? "DATASET" : "OPEN_API";
  return `/resources/${type}/${resource.id}`;
}

export function mergeResourceDetail(
  resource: SearchResourceCard,
  detail: ResourceDetail,
): SearchResourceCard {
  if (resource.type === "dataset") {
    return {
      ...resource,
      name: detail.title,
      score: detail.score ?? resource.score ?? 0,
      isFree: detail.isFree ?? resource.isFree ?? false,
      subtitle: detail.datasetDetail?.subtitle ?? resource.subtitle,
      descriptionShort:
        detail.datasetDetail?.descriptionShort ?? resource.descriptionShort,
      descriptionLong:
        detail.datasetDetail?.descriptionLong ?? resource.descriptionLong,
      source: detail.datasetDetail?.publisherName ?? resource.source,
      domains: detail.datasetDetail?.domains ?? resource.domains,
      tasks: detail.datasetDetail?.tasks ?? resource.tasks,
      modalities: detail.datasetDetail?.modalities ?? resource.modalities,
      tags: detail.datasetDetail?.tags ?? resource.tags,
      languages: detail.datasetDetail?.languages ?? resource.languages,
      licenseName:
        detail.datasetDetail?.licenseName ?? resource.licenseName,
      licenseUrl: detail.datasetDetail?.licenseUrl ?? resource.licenseUrl,
      commercialUseAllowed:
        detail.datasetDetail?.commercialUseAllowed ?? resource.commercialUseAllowed,
      taskMatch: detail.score ?? resource.taskMatch,
      rowCount: detail.datasetDetail?.rowCount ?? resource.rowCount,
      sampleCount:
        formatCompactNumber(detail.datasetDetail?.rowCount) ?? resource.sampleCount,
      reliability: detail.datasetDetail?.accessType ?? resource.reliability,
      lastUpdate:
        detail.datasetDetail?.sourceUpdatedAt ?? detail.createdAt ?? resource.lastUpdate,
      isBookmarked: detail.isBookmarked ?? resource.isBookmarked ?? false,
      datasetSizeBytes:
        detail.datasetDetail?.datasetSizeBytes ?? resource.datasetSizeBytes,
      schemaJson: detail.datasetDetail?.schemaJson ?? resource.schemaJson,
      canonicalUrl:
        detail.datasetDetail?.canonicalUrl ?? resource.canonicalUrl,
      landingUrl: detail.datasetDetail?.landingUrl ?? resource.landingUrl,
      reviews: mapDetailReviews(detail) ?? resource.reviews,
    };
  }

  return {
    ...resource,
    name: detail.title,
    score: detail.score ?? resource.score ?? 0,
    isFree: detail.isFree ?? resource.isFree ?? false,
    description: detail.openApiDetail?.description ?? resource.description,
    provider: detail.openApiDetail?.provider ?? resource.provider,
    baseUrl: detail.openApiDetail?.baseUrl ?? resource.baseUrl,
    docsUrl: detail.openApiDetail?.docsUrl ?? resource.docsUrl,
    category: detail.openApiDetail?.category ?? resource.category,
    tags: detail.openApiDetail?.tags ?? resource.tags,
    rateLimit: detail.openApiDetail?.rateLimit ?? resource.rateLimit,
    responseTime:
      formatMillis(detail.openApiDetail?.avgResponseTime) ?? resource.responseTime,
    auth: detail.openApiDetail?.authType ?? resource.auth,
    freeQuota:
      formatDailyLimit(detail.openApiDetail?.dailyLimit) ?? resource.freeQuota,
    pricingNote: detail.openApiDetail?.pricingNote ?? resource.pricingNote,
    isBookmarked: detail.isBookmarked ?? resource.isBookmarked ?? false,
    commercialUse: detail.openApiDetail?.commercialUse ?? resource.commercialUse,
    requiresApproval:
      detail.openApiDetail?.requiresApproval ?? resource.requiresApproval,
    availability: detail.openApiDetail?.responseFormat ?? resource.availability,
    reviews: mapDetailReviews(detail) ?? resource.reviews,
  };
}
