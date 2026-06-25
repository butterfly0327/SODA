import { apiClient } from './client';
import type { ApiResponse } from './contracts';
import type { ResourceDetail } from './types';

type ResourceTypeParam = 'DATASET' | 'OPEN_API';

export const resourceApi = {
  getResourceDetail: async (type: ResourceTypeParam, id: number): Promise<ResourceDetail> => {
    const response = await apiClient.get<ApiResponse<ResourceDetail>>(`/resources/${type}/${id}`);
    return response.data.data;
  },
};
