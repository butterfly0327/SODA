import { apiClient } from './client';
import type { ApiResponse } from './contracts';
import type {
  ConversationDetail,
  ConversationListItem,
  SendChatMessageAcceptedResponse,
  SendChatMessageRequest,
  SendChatMessageResponse,
} from './types';

export const chatApi = {
  sendMessage: async (
    request: SendChatMessageRequest,
  ): Promise<SendChatMessageAcceptedResponse | SendChatMessageResponse> => {
    const response = await apiClient.post<
      ApiResponse<SendChatMessageAcceptedResponse | SendChatMessageResponse>
    >('/chat/messages', request);
    return response.data.data;
  },

  getConversations: async (): Promise<ConversationListItem[]> => {
    const response = await apiClient.get<ApiResponse<ConversationListItem[]>>('/conversations');
    return response.data.data;
  },

  getConversationDetail: async (conversationId: number): Promise<ConversationDetail> => {
    const response = await apiClient.get<ApiResponse<ConversationDetail>>(`/conversations/${conversationId}`);
    return response.data.data;
  },
};
