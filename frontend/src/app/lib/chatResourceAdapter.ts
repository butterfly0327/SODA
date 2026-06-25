import type {
  ChatResourceBatchItem,
  ChatResourceDetailDto,
  ChatResourceTypeParam,
} from '@/api/chatResourceApi';
import type { ResourceDetail } from '@/api/types';
import type { ResultCard } from '@/types/recommendation';

export type ChatRecommendationType = 'dataset' | 'api';

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

function formatBytes(value: number | null | undefined): string | undefined {
  if (value === null || value === undefined || value <= 0) {
    return undefined;
  }

  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let size = value;
  let unitIndex = 0;

  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex += 1;
  }

  const rounded = size >= 10 || unitIndex === 0 ? Math.round(size) : Math.round(size * 10) / 10;
  return `${rounded}${units[unitIndex]}`;
}

export function normalizeRecommendationScore(value: number | undefined) {
  if (value === undefined) {
    return undefined;
  }

  if (value >= 0 && value <= 1) {
    return Math.round(value * 1000) / 10;
  }

  return value;
}

export function toChatResourceType(type: ChatRecommendationType): ChatResourceTypeParam {
  return type === 'dataset' ? 'DATASET' : 'OPEN_API';
}

export function mapChatBatchItem(
  resourceType: ChatRecommendationType,
  resourceId: number,
  recommendationScore: number,
  rank: number,
): ChatResourceBatchItem {
  return {
    resourceType: toChatResourceType(resourceType),
    resourceId,
    recommendationScore,
    rank,
  };
}

export function mapChatBatchCardToResultCard(card: {
  id: number;
  name: string;
  type: ChatResourceTypeParam;
  updatedAt: string;
  isFree: boolean;
  sourceName: string | null;
  recommendationScore: number;
}): ResultCard {
  const normalizedScore = normalizeRecommendationScore(card.recommendationScore);

  if (card.type === 'DATASET') {
    return {
      id: card.id,
      type: 'dataset',
      name: card.name,
      score: normalizedScore,
      rawRecommendationScore: card.recommendationScore,
      rank: card.rank,
      updatedAt: card.updatedAt,
      isFree: card.isFree,
      source: card.sourceName ?? undefined,
      lastUpdate: card.updatedAt,
    };
  }

  return {
    id: card.id,
    type: 'api',
    name: card.name,
    score: normalizedScore,
    rawRecommendationScore: card.recommendationScore,
    rank: card.rank,
    updatedAt: card.updatedAt,
    isFree: card.isFree,
    provider: card.sourceName ?? undefined,
  };
}

export function mapChatResourceDetailToResultCard(
  detail: ChatResourceDetailDto,
  type: ChatRecommendationType,
  reason?: string,
): ResultCard {
  const normalizedScore = normalizeRecommendationScore(detail.recommendationScore);

  if (type === 'dataset') {
    return {
      id: detail.id,
      type,
      name: detail.name,
      score: normalizedScore,
      rawRecommendationScore: detail.recommendationScore,
      updatedAt: detail.updatedAt,
      isFree: detail.isFree,
      source: detail.sourceName ?? undefined,
      descriptionLong: detail.datasetDetail?.descriptionLong ?? undefined,
      domains: detail.datasetDetail?.classification ?? undefined,
      tags: detail.datasetDetail?.tags ?? undefined,
      languages: detail.datasetDetail?.languages ?? undefined,
      licenseName: detail.datasetDetail?.licenseName ?? undefined,
      taskMatch: normalizedScore,
      rowCount: detail.datasetDetail?.rowCount ?? undefined,
      sampleCount: formatCompactNumber(detail.datasetDetail?.rowCount),
      lastUpdate: detail.updatedAt,
      datasetSizeBytes: detail.datasetDetail?.datasetSizeBytes ?? undefined,
      dataSize: formatBytes(detail.datasetDetail?.datasetSizeBytes),
      metrics: detail.datasetDetail?.metrics ?? undefined,
      schemaJson: detail.datasetDetail?.schemaJson ?? undefined,
      canonicalUrl: detail.originUrl ?? undefined,
      reasons: reason ? [reason] : [],
    };
  }

  return {
    id: detail.id,
    type,
    name: detail.name,
      score: normalizedScore,
      rawRecommendationScore: detail.recommendationScore,
      updatedAt: detail.updatedAt,
      isFree: detail.isFree,
    provider: detail.sourceName ?? undefined,
    description: detail.openApiDetail?.description ?? undefined,
    docsUrl: detail.originUrl ?? undefined,
    category: detail.openApiDetail?.category ?? undefined,
    tags: detail.openApiDetail?.tags ?? undefined,
    rateLimit: detail.openApiDetail?.rateLimit ?? undefined,
    responseTime: formatMillis(detail.openApiDetail?.avgResponseTime),
    responseFormat: detail.openApiDetail?.responseFormat ?? undefined,
    auth: detail.openApiDetail?.authType ?? undefined,
    freeQuota: formatDailyLimit(detail.openApiDetail?.dailyLimit),
    pricingNote: detail.openApiDetail?.pricingNote ?? undefined,
    availability: detail.openApiDetail?.responseFormat ?? undefined,
    responseSchema: detail.openApiDetail?.responseSchema ?? undefined,
    reasons: reason ? [reason] : [],
  };
}

export function mapResourceDetailToResultCard(
  detail: ResourceDetail,
  type: ChatRecommendationType,
  options: {
    recommendationScore?: number;
    currentScore?: number;
    reason?: string;
    rank?: number;
    bookmarkId?: number | null;
    isBookmarked?: boolean;
  } = {},
): ResultCard {
  const resolvedScore = normalizeRecommendationScore(
    options.recommendationScore ?? detail.score ?? options.currentScore,
  );

  if (type === 'dataset') {
    return {
      id: detail.id,
      type,
      name: detail.title,
      score: resolvedScore,
      rawRecommendationScore: options.recommendationScore,
      rank: options.rank,
      updatedAt: detail.createdAt ?? undefined,
      isFree: detail.isFree ?? undefined,
      isBookmarked: detail.isBookmarked ?? options.isBookmarked,
      bookmarkId: options.bookmarkId,
      source: detail.datasetDetail?.publisherName ?? undefined,
      subtitle: detail.datasetDetail?.subtitle ?? undefined,
      descriptionShort: detail.datasetDetail?.descriptionShort ?? undefined,
      descriptionLong: detail.datasetDetail?.descriptionLong ?? undefined,
      domains: detail.datasetDetail?.domains ?? undefined,
      tasks: detail.datasetDetail?.tasks ?? undefined,
      modalities: detail.datasetDetail?.modalities ?? undefined,
      tags: detail.datasetDetail?.tags ?? undefined,
      languages: detail.datasetDetail?.languages ?? undefined,
      licenseName: detail.datasetDetail?.licenseName ?? undefined,
      licenseUrl: detail.datasetDetail?.licenseUrl ?? undefined,
      commercialUseAllowed: detail.datasetDetail?.commercialUseAllowed ?? undefined,
      reliability: detail.datasetDetail?.accessType ?? undefined,
      rowCount: detail.datasetDetail?.rowCount ?? undefined,
      sampleCount: formatCompactNumber(detail.datasetDetail?.rowCount),
      lastUpdate: detail.datasetDetail?.sourceUpdatedAt ?? detail.createdAt ?? undefined,
      datasetSizeBytes: detail.datasetDetail?.datasetSizeBytes ?? undefined,
      schemaJson: detail.datasetDetail?.schemaJson ?? undefined,
      dataSize: formatBytes(detail.datasetDetail?.datasetSizeBytes),
      canonicalUrl:
        detail.datasetDetail?.canonicalUrl ?? detail.datasetDetail?.landingUrl ?? undefined,
      landingUrl: detail.datasetDetail?.landingUrl ?? undefined,
      reviews: detail.reviews?.map((review) => ({
        id: review.id,
        authorId: typeof review.authorId === 'number' ? String(review.authorId) : undefined,
        author: review.name,
        rating: review.rating,
        content: review.content,
        createdAt: review.createdAt,
      })),
      reasons: options.reason ? [options.reason] : [],
    };
  }

  return {
    id: detail.id,
    type,
    name: detail.title,
    score: resolvedScore,
    rawRecommendationScore: options.recommendationScore,
    rank: options.rank,
    updatedAt: detail.createdAt ?? undefined,
    isFree: detail.isFree ?? undefined,
    isBookmarked: detail.isBookmarked ?? options.isBookmarked,
    bookmarkId: options.bookmarkId,
    provider: detail.openApiDetail?.provider ?? undefined,
    description: detail.openApiDetail?.description ?? undefined,
    baseUrl: detail.openApiDetail?.baseUrl ?? undefined,
    docsUrl: detail.openApiDetail?.docsUrl ?? undefined,
    category: detail.openApiDetail?.category ?? undefined,
    tags: detail.openApiDetail?.tags ?? undefined,
    rateLimit: detail.openApiDetail?.rateLimit ?? undefined,
    responseTime: formatMillis(detail.openApiDetail?.avgResponseTime),
    responseFormat: detail.openApiDetail?.responseFormat ?? undefined,
    auth: detail.openApiDetail?.authType ?? undefined,
    freeQuota: formatDailyLimit(detail.openApiDetail?.dailyLimit),
    pricingNote: detail.openApiDetail?.pricingNote ?? undefined,
    commercialUse: detail.openApiDetail?.commercialUse ?? undefined,
    requiresApproval: detail.openApiDetail?.requiresApproval ?? undefined,
    availability: detail.openApiDetail?.responseFormat ?? undefined,
    reviews: detail.reviews?.map((review) => ({
      id: review.id,
      authorId: typeof review.authorId === 'number' ? String(review.authorId) : undefined,
      author: review.name,
      rating: review.rating,
      content: review.content,
      createdAt: review.createdAt,
    })),
    reasons: options.reason ? [options.reason] : [],
  };
}
