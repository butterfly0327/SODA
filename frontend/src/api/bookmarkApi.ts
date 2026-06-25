import { apiClient } from './client';
import type { ApiResponse } from './contracts';
import type { CreateBookmarkRequest, CreateBookmarkResponse } from './types';

export const bookmarkApi = {
  createBookmark: async (
    payload: CreateBookmarkRequest,
  ): Promise<CreateBookmarkResponse> => {
    const response = await apiClient.post<ApiResponse<CreateBookmarkResponse>>(
      '/bookmarks',
      payload,
    );

    return response.data.data;
  },

  deleteBookmark: async (bookmarkId: number): Promise<void> => {
    await apiClient.delete<ApiResponse<null>>(`/bookmarks/${bookmarkId}`);
  },
};
