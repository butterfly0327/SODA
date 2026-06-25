import { apiClient } from './client';
import type { ApiResponse } from './contracts';

export type ChatResourceTypeParam = 'DATASET' | 'OPEN_API';

export interface ChatResourceBatchItem {
  resourceType: ChatResourceTypeParam;
  resourceId: number;
  recommendationScore: number;
  rank: number;
}

interface ChatResourceCardDto {
  id: number;
  name: string;
  type: ChatResourceTypeParam;
  updatedAt: string;
  isFree: boolean;
  sourceName: string | null;
  recommendationScore: number;
  rank: number;
}

interface ChatResourceItemErrorDto {
  resourceType: ChatResourceTypeParam;
  resourceId: number;
  code: string;
  message: string;
}

interface ChatResourceCardsBatchResponseDto {
  cards: ChatResourceCardDto[];
  errors: ChatResourceItemErrorDto[];
}

interface ChatResourceDatasetDetailDto {
  descriptionLong: string | null;
  schemaJson: unknown;
  datasetSizeBytes: number | null;
  rowCount: number | null;
  metrics: unknown;
  licenseName: string | null;
  classification: string[];
  tags: string[];
  languages: string[];
}

interface ChatResourceOpenApiDetailDto {
  description: string | null;
  authType: string | null;
  category: string | null;
  tags: string[];
  rateLimit: number | null;
  dailyLimit: number | null;
  pricingNote: string | null;
  responseFormat: string | null;
  avgResponseTime: number | null;
  responseSchema: unknown;
}

export interface ChatResourceDetailDto {
  id: number;
  name: string;
  type: ChatResourceTypeParam;
  updatedAt: string;
  isFree: boolean;
  sourceName: string | null;
  recommendationScore: number;
  originUrl: string | null;
  datasetDetail: ChatResourceDatasetDetailDto | null;
  openApiDetail: ChatResourceOpenApiDetailDto | null;
}

export const chatResourceApi = {
  getCardsBatch: async (items: ChatResourceBatchItem[]): Promise<ChatResourceCardsBatchResponseDto> => {
    const response = await apiClient.post<ApiResponse<ChatResourceCardsBatchResponseDto>>(
      '/chat-resources/cards/batch',
      { items },
    );
    return response.data.data;
  },

  getResourceDetail: async (
    type: ChatResourceTypeParam,
    id: number,
    recommendationScore: number,
  ): Promise<ChatResourceDetailDto> => {
    const response = await apiClient.get<ApiResponse<ChatResourceDetailDto>>(
      `/chat-resources/${type}/${id}`,
      {
        params: { recommendationScore },
      },
    );
    return response.data.data;
  },
};
