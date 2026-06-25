import { Edit2, MoreHorizontal, Trash2 } from 'lucide-react';
import { useRef, useState } from 'react';
import type { Conversation } from '../../../stores/chatStore';
import { useClickOutside } from '../../../hooks/useClickOutside';

const RECENT_CONVERSATION_PREVIEW_COUNT = 4;

interface ProjectConversationsSectionProps {
  conversations: Conversation[];
  currentConversationId: string | null;
  onOpenConversation: (conversationId: string) => void;
  onDeleteConversation: (conversationId: string) => void;
  onRenameConversation: (conversationId: string, title: string) => void;
}

export function ProjectConversationsSection({
  conversations,
  currentConversationId,
  onOpenConversation,
  onDeleteConversation,
  onRenameConversation,
}: ProjectConversationsSectionProps) {
  const sectionRef = useRef<HTMLDivElement>(null);
  const [conversationMenuOpen, setConversationMenuOpen] = useState<string | null>(null);
  const [editingConversationId, setEditingConversationId] = useState<string | null>(null);
  const [editingConversationTitle, setEditingConversationTitle] = useState('');
  const [showAllRecentConversations, setShowAllRecentConversations] = useState(false);

  useClickOutside({
    ref: sectionRef,
    enabled: conversationMenuOpen !== null,
    onOutsideClick: () => setConversationMenuOpen(null),
    onEscape: () => setConversationMenuOpen(null),
  });

  const visibleProjectConversations = showAllRecentConversations
    ? conversations
    : conversations.slice(0, RECENT_CONVERSATION_PREVIEW_COUNT);

  const handleStartEditConversation = (
    e: React.MouseEvent,
    id: string,
    currentTitle: string
  ) => {
    e.stopPropagation();
    setEditingConversationId(id);
    setEditingConversationTitle(currentTitle);
    setConversationMenuOpen(null);
  };

  const handleSaveConversationTitle = (id: string) => {
    if (editingConversationTitle.trim()) {
      onRenameConversation(id, editingConversationTitle.trim());
    }
    setEditingConversationId(null);
    setEditingConversationTitle('');
  };

  const handleCancelEditConversation = () => {
    setEditingConversationId(null);
    setEditingConversationTitle('');
  };

  return (
    <div ref={sectionRef} className={conversationMenuOpen !== null ? 'relative z-30 mb-4' : 'relative z-0 mb-4'}>
      <div className="px-3 py-2 text-xs text-muted-foreground font-medium">최근 대화</div>
      {conversations.length > 0 ? (
        <div className={conversationMenuOpen !== null ? 'space-y-1 pointer-events-none' : 'space-y-1'}>
          {visibleProjectConversations.map((conversation) => {
            const isEditing = editingConversationId === conversation.id;

            return (
              <div
                key={conversation.id}
                className={conversationMenuOpen === conversation.id ? 'relative z-20 pointer-events-auto' : 'relative z-0'}
              >
                {isEditing ? (
                  <div className="w-full flex items-center gap-2 px-3 py-2.5 bg-white/50 rounded-lg">
                    <input
                      type="text"
                      value={editingConversationTitle}
                      onChange={(e) => setEditingConversationTitle(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                          handleSaveConversationTitle(conversation.id);
                        } else if (e.key === 'Escape') {
                          handleCancelEditConversation();
                        }
                      }}
                      onBlur={() => handleSaveConversationTitle(conversation.id)}
                      className="flex-1 text-sm bg-white border border-border rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-[#e8f4fd]"
                      autoFocus
                    />
                  </div>
                ) : (
                  <div
                    role="button"
                    tabIndex={0}
                    onClick={() => {
                      setConversationMenuOpen(null);
                      onOpenConversation(conversation.id);
                    }}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        setConversationMenuOpen(null);
                        onOpenConversation(conversation.id);
                      }
                    }}
                    className={`
                      w-full flex items-center gap-3 px-3 py-2.5 pr-10 rounded-lg group
                      transition-colors relative cursor-pointer
                      ${
                        currentConversationId === conversation.id
                          ? 'bg-white/70 text-sidebar-accent-foreground'
                          : 'hover:bg-sidebar-accent/50 text-sidebar-foreground'
                      }
                    `}
                  >
                    <div className="flex items-center gap-3 flex-1 min-w-0 text-left">
                      <span className="flex-1 text-sm truncate text-left">{conversation.title}</span>
                    </div>
                    <div
                      className={`absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1 transition-opacity ${
                        conversationMenuOpen === conversation.id
                          ? 'z-50 opacity-100'
                          : 'z-10 opacity-0 group-hover:opacity-100'
                      }`}
                    >
                      <div className="relative">
                        <button
                          type="button"
                          onMouseDown={(e) => e.stopPropagation()}
                          onClick={(e) => {
                            e.stopPropagation();
                            setConversationMenuOpen(
                              conversationMenuOpen === conversation.id ? null : conversation.id
                            );
                          }}
                          className="p-1 hover:bg-sidebar-accent rounded transition-colors"
                          aria-label="더보기"
                        >
                          <MoreHorizontal className="w-4 h-4" />
                        </button>
                        {conversationMenuOpen === conversation.id && (
                          <div className="absolute right-0 top-full mt-1 w-40 bg-white border border-border shadow-lg rounded-lg overflow-hidden z-50">
                            <button
                              type="button"
                              onMouseDown={(e) => e.stopPropagation()}
                              onClick={(e) =>
                                handleStartEditConversation(e, conversation.id, conversation.title)
                              }
                              className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-muted transition-colors text-left"
                            >
                              <Edit2 className="w-3 h-3" />
                              <span>이름 변경</span>
                            </button>
                            <button
                              type="button"
                              onMouseDown={(e) => e.stopPropagation()}
                              onClick={(e) => {
                                e.stopPropagation();
                                onDeleteConversation(conversation.id);
                                setConversationMenuOpen(null);
                              }}
                              className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-muted transition-colors text-left text-destructive"
                            >
                              <Trash2 className="w-3 h-3" />
                              <span>삭제</span>
                            </button>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })}

          {conversations.length > RECENT_CONVERSATION_PREVIEW_COUNT && (
            <button
              type="button"
              onClick={() => setShowAllRecentConversations((prev) => !prev)}
              className="w-full px-3 py-2 text-sm text-muted-foreground text-left hover:text-foreground transition-colors"
            >
              {showAllRecentConversations ? '접기' : '... 더 보기'}
            </button>
          )}
        </div>
      ) : (
        <div className="px-3 py-2 text-xs text-muted-foreground italic">아직 대화가 없습니다</div>
      )}
    </div>
  );
}
