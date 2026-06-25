import { apiClient } from './client';
import type { ApiResponse } from './contracts';
import type { MyBookmarksPage, MyPostsPage, MyProfile, MyReviewsPage } from './types';

type GetMyBookmarksParams = {
  keyword?: string;
  type?: 'DATASET' | 'OPEN_API';
  freeOnly?: boolean;
};

export const userApi = {
  getMyProfile: async (): Promise<MyProfile> => {
    const response = await apiClient.get<ApiResponse<MyProfile>>('/users/me');
    return response.data.data;
  },

  getMyPosts: async (page = 0, size = 10): Promise<MyPostsPage> => {
    const response = await apiClient.get<ApiResponse<MyPostsPage>>('/users/me/posts', {
      params: { page, size },
    });
    return response.data.data;
  },

  getMyReviews: async (page = 0, size = 10): Promise<MyReviewsPage> => {
    const response = await apiClient.get<ApiResponse<MyReviewsPage>>('/users/me/reviews', {
      params: { page, size },
    });
    return response.data.data;
  },

  getMyBookmarks: async (
    page = 0,
    size = 10,
    filters?: GetMyBookmarksParams,
  ): Promise<MyBookmarksPage> => {
    const response = await apiClient.get<ApiResponse<MyBookmarksPage>>('/users/me/bookmarks', {
      params: {
        page,
        size,
        keyword: filters?.keyword,
        type: filters?.type,
        freeOnly: filters?.freeOnly,
      },
    });
    return response.data.data;
  },

  deleteMyAccount: async (): Promise<string> => {
    const response = await apiClient.delete<ApiResponse<null>>('/users/me');
    return response.data.message;
  },
};
