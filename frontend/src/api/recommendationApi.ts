import { apiClient } from './client';
import type { ApiResponse } from './contracts';
import type { RecommendationDetail } from './types';

export const recommendationApi = {
  getRecommendation: async (recommendationId: number): Promise<RecommendationDetail> => {
    const response = await apiClient.get<ApiResponse<RecommendationDetail>>(
      `/recommendations/${recommendationId}`,
    );
    return response.data.data;
  },
};
