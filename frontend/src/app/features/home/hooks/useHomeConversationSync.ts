import { useEffect, useRef } from "react";

import { chatService } from "@/services/chatService";
import type { Conversation } from "@/stores/chatStore";
import { useChatStore } from "@/stores/chatStore";

type UseHomeConversationSyncOptions = {
  conversationIdFromQuery: string | null;
  draftConversationId: string | null;
  resetHomeRequested: boolean;
  conversations: Conversation[];
  currentConversationId: string | null;
  navigateHome: () => void;
  selectConversation: (id: string | null) => void;
  upsertConversation: (conversation: Conversation) => void;
};

export function useHomeConversationSync({
  conversationIdFromQuery,
  draftConversationId,
  resetHomeRequested,
  conversations,
  currentConversationId,
  navigateHome,
  selectConversation,
  upsertConversation,
}: UseHomeConversationSyncOptions) {
  const hydratedServerConversationIdsRef = useRef(new Set<string>());
  const hydratingServerConversationIdsRef = useRef(new Set<string>());

  useEffect(() => {
    if (draftConversationId) {
      const draftConversation = conversations.find((conv) => conv.id === draftConversationId);
      if (draftConversation) {
        selectConversation(draftConversationId);
      }
      navigateHome();
      return;
    }

    if (resetHomeRequested) {
      selectConversation(null);
      navigateHome();
      return;
    }

    if (conversationIdFromQuery) {
      const existingConversation = useChatStore
        .getState()
        .conversations.find((conv) => conv.id === conversationIdFromQuery);
      const parsedConversationId = Number(conversationIdFromQuery);
      const isServerConversationId = Number.isFinite(parsedConversationId);

      if (!isServerConversationId) {
        if (existingConversation) {
          if (currentConversationId !== conversationIdFromQuery) {
            selectConversation(conversationIdFromQuery);
          }
          return;
        }

        navigateHome();
        return;
      }

      if (existingConversation) {
        if (currentConversationId !== conversationIdFromQuery) {
          selectConversation(conversationIdFromQuery);
        }

        if (existingConversation.messages.length > 0) {
          hydratedServerConversationIdsRef.current.add(conversationIdFromQuery);
          return;
        }
      }

      if (
        hydratingServerConversationIdsRef.current.has(conversationIdFromQuery) ||
        hydratedServerConversationIdsRef.current.has(conversationIdFromQuery)
      ) {
        return;
      }

      let isCancelled = false;
      hydratingServerConversationIdsRef.current.add(conversationIdFromQuery);

      const loadConversation = async () => {
        try {
          const hydratedConversation = await chatService.hydrateConversation(conversationIdFromQuery);

          if (isCancelled) {
            return;
          }

          upsertConversation(hydratedConversation);
          hydratedServerConversationIdsRef.current.add(hydratedConversation.id);
          selectConversation(hydratedConversation.id);
        } catch {
          if (isCancelled) {
            return;
          }

          hydratedServerConversationIdsRef.current.delete(conversationIdFromQuery);
          selectConversation(null);
          navigateHome();
        } finally {
          hydratingServerConversationIdsRef.current.delete(conversationIdFromQuery);
        }
      };

      void loadConversation();

      return () => {
        isCancelled = true;
        hydratingServerConversationIdsRef.current.delete(conversationIdFromQuery);
      };
    }

    if (currentConversationId) {
      return;
    }

    selectConversation(null);
  }, [
    conversationIdFromQuery,
    conversations,
    currentConversationId,
    draftConversationId,
    navigateHome,
    resetHomeRequested,
    selectConversation,
    upsertConversation,
  ]);
}
