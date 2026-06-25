import { apiClient } from "./client";
import type { ApiResponse } from "./contracts";

export type ReviewResourceType = "DATASET" | "OPEN_API";

export interface ReviewRequest {
  rating: number;
  content: string;
}

export interface ReviewResponse {
  id?: number;
  reviewId?: number;
  rating: number;
  content: string;
  createdAt: string | null;
}

function resolveReviewId(response: ReviewResponse): number | null {
  if (typeof response.reviewId === "number") return response.reviewId;
  if (typeof response.id === "number") return response.id;
  return null;
}

export const reviewApi = {
  createReview: async (type: ReviewResourceType, resourceId: number, payload: ReviewRequest) => {
    const response = await apiClient.post<ApiResponse<ReviewResponse>>(
      `/resources/${type}/${resourceId}/reviews`,
      payload,
    );
    const data = response.data.data;
    return {
      ...data,
      reviewId: resolveReviewId(data),
    };
  },

  updateReview: async (type: ReviewResourceType, resourceId: number, reviewId: number, payload: ReviewRequest) => {
    const response = await apiClient.put<ApiResponse<ReviewResponse>>(
      `/resources/${type}/${resourceId}/reviews/${reviewId}`,
      payload,
    );
    const data = response.data.data;
    return {
      ...data,
      reviewId: resolveReviewId(data),
    };
  },

  deleteReview: async (type: ReviewResourceType, resourceId: number, reviewId: number) => {
    await apiClient.delete<ApiResponse<null>>(`/resources/${type}/${resourceId}/reviews/${reviewId}`);
  },
};
