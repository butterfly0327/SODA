import { apiClient } from './client';
import type { ApiResponse } from './contracts';

export const authApi = {
  logout: async (): Promise<void> => {
    await apiClient.post<ApiResponse<null>>('/auth/logout');
  },
};
