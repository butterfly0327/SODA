import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { chatService } from '@/services/chatService';
import { useChatStore } from '@/stores/chatStore';
import type { Message } from '@/stores/chatStore';
import { buildConversationTitle, isGenericConversationTitle } from '@/utils/conversationTitle';

export const useChat = () => {
  const addConversation = useChatStore((state) => state.addConversation);
  const addMessage = useChatStore((state) => state.addMessage);
  const upsertConversation = useChatStore((state) => state.upsertConversation);
  const updateConversationTitle = useChatStore((state) => state.updateConversationTitle);
  const getCurrentConversation = useChatStore((state) => state.getCurrentConversation);
  const replaceConversationId = useChatStore((state) => state.replaceConversationId);
  const setLoading = useChatStore((state) => state.setLoading);
  const [error, setError] = useState<string | null>(null);
  const [pendingConversationId, setPendingConversationId] = useState<string | null>(null);

  const sendMessageMutation = useMutation({
    mutationFn: async (content: string) => {
      const existingConversation = getCurrentConversation();

      const currentConversation =
        existingConversation ?? {
          id: `temp-${Date.now()}`,
          title: buildConversationTitle(content),
          messages: [],
          createdAt: Date.now(),
          updatedAt: Date.now(),
          projectId: null,
        };

      if (!existingConversation) {
        addConversation(currentConversation);
      }

      setPendingConversationId(currentConversation.id);

      if (currentConversation.messages.length === 0 && isGenericConversationTitle(currentConversation.title)) {
        updateConversationTitle(currentConversation.id, buildConversationTitle(content));
      }

      const userMessage: Message = {
        id: `msg-${Date.now()}-user`,
        role: 'user',
        content,
        timestamp: Date.now(),
      };
      addMessage(currentConversation.id, userMessage);

      const response = await chatService.sendMessage({
        conversationId: existingConversation?.id ?? null,
        message: content,
      });

      return {
        previousConversationId: currentConversation.id,
        ...response,
      };
    },
    onMutate: () => {
      setLoading(true);
      setError(null);
    },
    onSuccess: (data) => {
      if (data.previousConversationId !== data.conversationId) {
        replaceConversationId(data.previousConversationId, data.conversationId);
      }

      if (data.hydratedConversation) {
        upsertConversation(data.hydratedConversation);
      } else if (data.content) {
        const assistantMessage: Message = {
          id: `msg-${Date.now()}-assistant`,
          role: 'assistant',
          content: data.content,
          timestamp: Date.now(),
          searchResult: data.searchResult,
        };
        addMessage(data.conversationId, assistantMessage);
      }

      setLoading(false);
      setPendingConversationId(null);
    },
    onError: (err) => {
      setError(err instanceof Error ? err.message : '메시지 전송에 실패했습니다.');
      setLoading(false);
      setPendingConversationId(null);
    },
  });

  return {
    sendMessage: sendMessageMutation.mutate,
    sendMessageAsync: sendMessageMutation.mutateAsync,
    isLoading: sendMessageMutation.isPending,
    pendingConversationId,
    error,
  };
};
