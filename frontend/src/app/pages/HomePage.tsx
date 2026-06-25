import { useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate, useSearchParams } from 'react-router';
import { Layout } from '../components/Layout';
import { MessageInput } from '../components/MessageInput';
import { Message } from '../components/Message';
import { RecommendationDetailPanel } from '@/app/features/recommendation-detail/components/RecommendationDetailPanel';
import { useHomeBookmarks } from '@/app/features/home/hooks/useHomeBookmarks';
import { useHomeConversationSync } from '@/app/features/home/hooks/useHomeConversationSync';
import { HomeIntroSection } from '../components/HomeIntroSection';
import { HOME_INTRO_EXAMPLES, HOME_INTRO_FOOTER_NOTE, HOME_INTRO_TITLE } from '../lib/introContent';
import { resourceApi } from '@/api/resourceApi';
import { mapResourceDetailToResultCard } from '../lib/chatResourceAdapter';
import { useChatStore } from '../../stores/chatStore';
import { useAuthStore } from '../../stores/authStore';
import { useChat } from '../../hooks/useChat';
import type { ResultCard } from '@/types/recommendation';
import { useResizableDetailPanel } from '@/app/shared/hooks/useResizableDetailPanel';
import sodabotImage from '@/assets/images/sodabot.png';

export function HomePage() {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const conversationIdFromQuery = searchParams.get('conversationId');
  const locationState = location.state as { resetHome?: boolean; draftConversationId?: string } | null;
  const resetHomeRequested = locationState?.resetHome === true;
  const draftConversationId = locationState?.draftConversationId ?? null;

  const conversations = useChatStore((state) => state.conversations);
  const projects = useChatStore((state) => state.projects);
  const currentProjectId = useChatStore((state) => state.currentProjectId);
  const currentConversationId = useChatStore((state) => state.currentConversationId);
  const upsertConversation = useChatStore((state) => state.upsertConversation);
  const addProject = useChatStore((state) => state.addProject);
  const toggleProjectSavedResource = useChatStore((state) => state.toggleProjectSavedResource);
  const addProjectComparison = useChatStore((state) => state.addProjectComparison);
  const selectConversation = useChatStore((state) => state.selectConversation);
  const getCurrentConversation = useChatStore((state) => state.getCurrentConversation);
  const setCurrentProject = useChatStore((state) => state.setCurrentProject);
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  const { sendMessageAsync, isLoading, pendingConversationId } = useChat();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const shouldAutoScrollRef = useRef(true);
  const previousMessageCountRef = useRef(0);
  const previousConversationIdRef = useRef<string | null>(null);
  const {
    selectedDetail,
    setSelectedDetail,
    panelWidth,
    startResizing,
    isNarrowViewport,
    closeDetail,
  } = useResizableDetailPanel<ResultCard>();

  const currentConversation = getCurrentConversation();
  const {
    bookmarkError,
    canBookmark,
    canCompare,
    isBookmarked,
    handleToggleBookmark,
  } = useHomeBookmarks({
    isAuthenticated,
    projects,
    currentProjectId,
    currentConversationProjectId: currentConversation?.projectId ?? null,
    addProject,
    setCurrentProject,
    toggleProjectSavedResource,
  });
  const isCurrentConversationLoading =
    isLoading &&
    currentConversation !== null &&
    pendingConversationId === currentConversation.id;

  useHomeConversationSync({
    conversationIdFromQuery,
    draftConversationId,
    resetHomeRequested,
    conversations,
    currentConversationId,
    navigateHome: () => navigate('/', { replace: true, state: null }),
    selectConversation,
    upsertConversation,
  });

  useEffect(() => {
    const container = scrollContainerRef.current;
    const currentMessageCount = currentConversation?.messages.length ?? 0;
    const previousMessageCount = previousMessageCountRef.current;

    if (!container) {
      previousMessageCountRef.current = currentMessageCount;
      return;
    }

    const hasNewMessage = currentMessageCount > previousMessageCount;
    previousMessageCountRef.current = currentMessageCount;

    if (!hasNewMessage || !shouldAutoScrollRef.current) {
      return;
    }

    container.scrollTo({
      top: container.scrollHeight,
      behavior: previousMessageCount === 0 ? 'auto' : 'smooth',
    });
  }, [currentConversation?.messages]);

  useEffect(() => {
    shouldAutoScrollRef.current = true;
    previousMessageCountRef.current = currentConversation?.messages.length ?? 0;
  }, [currentConversation?.messages.length]);

  useEffect(() => {
    const hasConversationChanged = previousConversationIdRef.current !== currentConversationId;
    const hasNoMessages = (currentConversation?.messages.length ?? 0) === 0;

    if (hasConversationChanged || currentConversationId === null || hasNoMessages) {
      setSelectedDetail(null);
    }

    previousConversationIdRef.current = currentConversationId;
  }, [currentConversationId, currentConversation?.messages.length, setSelectedDetail]);

  const openConversationOnHome = (conversationId: string) => {
    const query = new URLSearchParams({ conversationId });
    navigate(`/?${query.toString()}`);
  };

  const handlePromptSubmit = async (text: string) => {
    try {
      const result = await sendMessageAsync(text);
      if (result.conversationId !== currentConversationId) {
        openConversationOnHome(result.conversationId);
      }
    } catch {
      // useChat manages the visible error state
    }
  };

  const handleMessageListScroll = () => {
    const container = scrollContainerRef.current;
    if (!container) {
      return;
    }

    const distanceFromBottom = container.scrollHeight - container.scrollTop - container.clientHeight;
    shouldAutoScrollRef.current = distanceFromBottom < 120;
  };

  const showIntro = !currentConversation || currentConversation.messages.length === 0;

  const handleOpenDetail = async (result: ResultCard) => {
    setSelectedDetail(result);

    if (typeof result.id !== 'number') {
      return;
    }

    try {
      const detail = await resourceApi.getResourceDetail(
        result.type === 'dataset' ? 'DATASET' : 'OPEN_API',
        result.id,
      );

      setSelectedDetail((prev) => {
        if (prev?.id !== result.id) {
          return prev;
        }

        return {
          ...mapResourceDetailToResultCard(detail, result.type, {
            recommendationScore: prev.rawRecommendationScore ?? prev.score,
            currentScore: prev.score,
            reason: prev.reasons?.[0],
            rank: prev.rank,
            bookmarkId: prev.bookmarkId ?? null,
            isBookmarked: prev.isBookmarked,
          }),
          reasons: prev.reasons,
        } as ResultCard;
      });
    } catch (error) {
      console.error('Failed to fetch details', error);
    }
  };

  const handleAddComparison = (result: ResultCard) => {
    const targetProjectId = currentConversation?.projectId ?? currentProjectId;
    if (!targetProjectId) {
      return;
    }

    addProjectComparison(targetProjectId, {
      name: result.name,
      type: result.type,
    });
  };

  return (
    <Layout showHeader={Boolean(currentConversation?.id)}>
      <main className="flex-1 flex flex-col overflow-hidden">
        {showIntro ? (
          <HomeIntroSection
            onSubmitPrompt={handlePromptSubmit}
            isLoading={isCurrentConversationLoading}
            title={HOME_INTRO_TITLE}
            examples={HOME_INTRO_EXAMPLES}
            footerNote={HOME_INTRO_FOOTER_NOTE}
          />
        ) : (
          <div className="flex-1 min-h-0 flex">
            <div className="flex-1 min-w-0 flex flex-col">
                <div
                  ref={scrollContainerRef}
                  onScroll={handleMessageListScroll}
                  className="flex-1 overflow-y-auto pb-32"
                >
                {bookmarkError && (
                  <div className="mx-auto mt-4 max-w-2xl rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                    {bookmarkError}
                  </div>
                )}
                {currentConversation.messages.map((message) => (
                  <Message
                    key={message.id}
                    message={message}
                    onOpenDetail={handleOpenDetail}
                    onAddComparison={handleAddComparison}
                    onToggleBookmark={handleToggleBookmark}
                    isBookmarked={isBookmarked}
                    canBookmark={canBookmark}
                    canCompare={canCompare}
                  />
                ))}

                {isCurrentConversationLoading && (
                  <div className="w-full" aria-live="polite">
                    <div className="max-w-2xl mx-auto px-4 sm:px-12 py-6 flex items-center gap-4">
                      <div className="w-8 h-8 flex items-center justify-center flex-shrink-0">
                        <img src={sodabotImage} alt="SODA bot" className="h-full w-full object-contain" />
                      </div>
                      <div className="flex items-center gap-1">
                           <div
                             className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce"
                             style={{ animationDelay: '0ms' }}
                           />
                          <div
                            className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce"
                            style={{ animationDelay: '150ms' }}
                          />
                           <div
                             className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce"
                             style={{ animationDelay: '300ms' }}
                           />
                      </div>
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>

              <MessageInput onSubmitMessage={handlePromptSubmit} isLoading={isCurrentConversationLoading} />
            </div>

            {selectedDetail && !isNarrowViewport && (
              <>
                <button
                  type="button"
							className="w-1 cursor-col-resize bg-border/60 hover:bg-[#dfe4ea] transition-colors"
                  onPointerDown={startResizing}
                  aria-label="상세 패널 너비 조절"
                />
                <div style={{ width: `${panelWidth}px` }} className="min-w-[320px] max-w-[760px] h-full">
                  <RecommendationDetailPanel data={selectedDetail} onClose={closeDetail} reviewMode="readOnly" />
                </div>
              </>
            )}
          </div>
        )}

        {selectedDetail && isNarrowViewport && (
          <div className="fixed inset-0 z-50 bg-black/30">
            <button
              type="button"
              onClick={closeDetail}
              aria-label="상세 패널 닫기"
              className="absolute inset-0"
            />
            <div className="absolute inset-y-0 right-0 z-10 w-full max-w-[440px] bg-white shadow-2xl">
              <RecommendationDetailPanel data={selectedDetail} onClose={closeDetail} reviewMode="readOnly" />
            </div>
          </div>
        )}
      </main>
    </Layout>
  );
}
