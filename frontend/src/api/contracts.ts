export interface ApiResponse<TData> {
  status: number;
  message: string;
  data: TData;
}

export interface PaginationMeta {
  page: number;
  pageSize: number;
  totalCount: number;
  totalPages: number;
}

export interface PaginatedResponse<TItem> {
  items: TItem[];
  pagination: PaginationMeta;
}

export interface LoginRequestDto {
  email: string;
  password: string;
}

export interface LoginResponseDto {
  accessToken: string;
  refreshToken?: string;
  user: {
    id: string;
    email: string;
    name: string;
    role?: string;
  };
}

export interface MyProfileResponseDto {
  id: number;
  name: string;
  email: string;
  createdAt: string;
  postCount: number;
  reviewCount: number;
  bookmarkCount: number;
}

export interface MyPostItemResponseDto {
  id: number;
  title: string;
  createdAt: string;
  likeCount: number;
  referenceCount: number;
}

export interface MyPostsPageResponseDto {
  content: MyPostItemResponseDto[];
  totalElements: number;
  totalPages: number;
  page: number;
  size: number;
}

export interface MyReviewItemResponseDto {
  id: number;
  resourceType: 'DATASET' | 'OPEN_API';
  resourceId: number;
  resourceTitle: string;
  rating: number;
  content: string;
  createdAt: string;
}

export interface MyReviewsPageResponseDto {
  content: MyReviewItemResponseDto[];
  totalElements: number;
  totalPages: number;
  page: number;
  size: number;
}

export interface MyBookmarkItemResponseDto {
  bookmarkId: number;
  id: number;
  type: 'DATASET' | 'OPEN_API';
  title: string;
  score: number | null;
  isFree: boolean | null;
  isBookmarked: boolean;
  createdAt: string | null;
  bookmarkedAt: string;
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
}

export interface MyBookmarksPageResponseDto {
  content: MyBookmarkItemResponseDto[];
  totalElements: number;
  totalPages: number;
  page: number;
  size: number;
}

export interface CreateBookmarkRequestDto {
  resourceType: 'DATASET' | 'OPEN_API';
  resourceId: number;
}

export interface CreateBookmarkResponseDto {
  bookmarkId: number;
  resourceType: 'DATASET' | 'OPEN_API';
  resourceId: number;
  bookmarkedAt: string;
}

export interface ChatListRequestDto {
  page?: number;
  pageSize?: number;
}

export interface ChatMessageDto {
  id: string | number;
  role: 'user' | 'assistant' | 'system' | 'USER' | 'ASSISTANT' | 'SYSTEM';
  content: string;
  createdAt?: string;
}

export interface SendMessageRequestDto {
  conversationId?: number;
  message: string;
}

export interface RecommendationSummaryDto {
  id?: number;
  title?: string;
  name?: string;
}

export interface SendMessageAcceptedResponseDto {
  conversationId: number;
  userTurnId: number;
  recommendationId: number;
  status: string;
}

export interface SendMessageResponseDto {
  conversationId: number;
  userTurnId: number;
  assistantTurnId: number;
  assistantMessage: string;
  mergedReason: string;
  datasetRecommendations: RecommendationSummaryDto[];
  openApiRecommendations: RecommendationSummaryDto[];
}

export interface ConversationListItemDto {
  conversationId: number;
  title: string;
  createdAt: string;
  updatedAt: string;
}

export interface ConversationTurnDto {
  turnId: number;
  turnOrder: number;
  role: 'USER' | 'ASSISTANT' | 'SYSTEM';
  content: string;
  responseTimeMs: number | null;
  createdAt: string;
}

export interface RecommendationDetailDto {
  recommendationId: number;
  conversationId?: number;
  userTurnId: number;
  assistantTurnId: number | null;
  status: string;
  mergedReason: string;
  datasetReason?: string;
  openApiReason?: string;
  datasetRecommendations: RecommendationSummaryDto[];
  openApiRecommendations: RecommendationSummaryDto[];
  errorSummary?: string | null;
  updatedAt?: string;
}

export interface ConversationDetailDto {
  conversationId: number;
  title: string;
  turns: ConversationTurnDto[];
  recommendations: RecommendationDetailDto[];
}

export interface CommunityPostDto {
  id: string;
  title: string;
  content: string;
  category: string;
  author: {
    id: string;
    name: string;
  };
  likes: number;
  comments: number;
  views: number;
  createdAt: string;
}

export interface CreateCommunityPostRequestDto {
  title: string;
  content?: string;
  datasetIds?: number[];
  openApiIds?: number[];
}

export interface CreateCommunityPostResponseDto {
  postId: number;
  createdAt: string;
}

export interface UpdateCommunityPostRequestDto {
  title?: string;
  content?: string;
  datasetIds?: number[];
  openApiIds?: number[];
}

export interface UpdateCommunityPostResponseDto {
  postId: number;
  updatedAt: string;
}

export type CommunityPostListSortDto = 'LATEST' | 'VIEW_COUNT' | 'FAVORITE';

export interface GetCommunityPostListRequestDto {
  page?: number;
  size?: number;
  sort?: CommunityPostListSortDto;
  keyword?: string;
}

export interface CommunityPostListItemResponseDto {
  postId: number;
  name: string;
  authorId: number;
  title: string;
  viewCount: number;
  favorite: number;
  createdAt: string;
  updatedAt: string;
}

export interface CommunityPostListPageResponseDto {
  content: CommunityPostListItemResponseDto[];
  page: number;
  size: number;
  totalElements: number;
  totalPages: number;
  sort: CommunityPostListSortDto;
}

export interface CommunityPostReferenceDto {
  id: number;
  name: string;
}

export interface CommunityPostDetailResponseDto {
  postId: number;
  authorId: number;
  name: string;
  title: string;
  content: string;
  viewCount: number;
  favorite: number;
  datasetReferences: CommunityPostReferenceDto[];
  openApiReferences: CommunityPostReferenceDto[];
  createdAt: string;
  updatedAt: string;
}

export interface SearchResourceRequestDto {
  query?: string;
  type?: 'all' | 'dataset' | 'api';
  projectType?: string;
  minScore?: number;
  freeOnly?: boolean;
  sortBy?: 'latest' | 'score';
  page?: number;
  pageSize?: number;
}

export interface SearchResourceItemDto {
  id: string;
  type: 'dataset' | 'api';
  name: string;
  score: number;
  isFree: boolean;
}

export interface ResourceDetailDto {
  id: number;
  type: 'DATASET' | 'OPEN_API';
  title: string;
  score: number | null;
  isFree: boolean | null;
  isBookmarked?: boolean;
  createdAt: string | null;
  datasetDetail: {
    subtitle: string | null;
    descriptionShort: string | null;
    descriptionLong: string | null;
    publisherName: string | null;
    domains: string[];
    tasks: string[];
    modalities: string[];
    tags: string[];
    languages: string[];
    licenseName: string | null;
    licenseUrl: string | null;
    commercialUseAllowed: boolean | null;
    accessType: string | null;
    rowCount: number | null;
    datasetSizeBytes: number | null;
    sourceUpdatedAt: string | null;
    canonicalUrl: string | null;
    landingUrl: string | null;
  } | null;
  openApiDetail: {
    description: string | null;
    provider: string | null;
    baseUrl: string | null;
    docsUrl: string | null;
    authType: string | null;
    category: string | null;
    tags: string[];
    rateLimit: number | null;
    dailyLimit: number | null;
    pricingNote: string | null;
    commercialUse: boolean | null;
    requiresApproval: boolean | null;
    responseFormat: string | null;
    avgResponseTime: number | null;
  } | null;
  reviews?: {
    id: number;
    authorId?: number;
    author?: string | null;
    name?: string | null;
    rating: number;
    content: string;
    createdAt: string | null;
  }[];
}
