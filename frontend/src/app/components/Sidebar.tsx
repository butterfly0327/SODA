import { Search, MessageSquare, Trash2, Users, Bookmark, PanelLeft, ChevronDown, MoreHorizontal, Edit2 } from 'lucide-react';
import { useChatStore } from '../../stores/chatStore';
import type { Conversation } from '../../stores/chatStore';
import { useLocation, useNavigate } from 'react-router';
import { useEffect, useRef, useState } from 'react';
import { BrandLogo } from './BrandLogo';
import { useClickOutside } from '../../hooks/useClickOutside';

interface SidebarProps {
  showTitle?: boolean;
}

export function Sidebar({ showTitle = false }: SidebarProps) {
  const conversations = useChatStore((state) => state.conversations);
  const currentConversationId = useChatStore((state) => state.currentConversationId);
  const isSidebarOpen = useChatStore((state) => state.isSidebarOpen);
  const selectConversation = useChatStore((state) => state.selectConversation);
  const addConversation = useChatStore((state) => state.addConversation);
  const deleteConversation = useChatStore((state) => state.deleteConversation);
  const updateConversationTitle = useChatStore((state) => state.updateConversationTitle);
  const toggleSidebar = useChatStore((state) => state.toggleSidebar);
  const setCurrentConversation = useChatStore((state) => state.setCurrentConversation);

  const [isMyChatExpanded, setIsMyChatExpanded] = useState(true);
  const [conversationMenuOpen, setConversationMenuOpen] = useState<string | null>(null);
  const [editingConversationId, setEditingConversationId] = useState<string | null>(null);
  const [editingConversationTitle, setEditingConversationTitle] = useState('');
  const myChatSectionRef = useRef<HTMLDivElement>(null);
  const editingInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!editingConversationId) {
      return;
    }
    editingInputRef.current?.focus();
    editingInputRef.current?.select();
  }, [editingConversationId]);

  useClickOutside({
    ref: myChatSectionRef,
    enabled: conversationMenuOpen !== null,
    onOutsideClick: () => setConversationMenuOpen(null),
    onEscape: () => setConversationMenuOpen(null),
  });

  const handleNewChat = () => {
    const newConversation: Conversation = {
      id: `conv-${Date.now()}`,
      title: '새 대화',
      messages: [],
      createdAt: Date.now(),
      updatedAt: Date.now(),
    };
    addConversation(newConversation);
    navigate(`/?${new URLSearchParams({ conversationId: newConversation.id }).toString()}`, { replace: true });
  };

  const handleNavigateMenu = (path: string) => {
    setCurrentConversation(null);
    navigate(path);
  };

  const handleDeleteConversationFromMenu = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    deleteConversation(id);
    setConversationMenuOpen(null);
  };

  const handleStartEditConversation = (e: React.MouseEvent, id: string, currentTitle: string) => {
    e.stopPropagation();
    setEditingConversationId(id);
    setEditingConversationTitle(currentTitle);
    setConversationMenuOpen(null);
  };

  const handleSaveConversationTitle = (id: string) => {
    if (editingConversationTitle.trim()) {
      updateConversationTitle(id, editingConversationTitle.trim());
    }
    setEditingConversationId(null);
    setEditingConversationTitle('');
  };

  const handleCancelEditConversation = () => {
    setEditingConversationId(null);
    setEditingConversationTitle('');
  };

  const navigate = useNavigate();
  const location = useLocation();

  const menuItems = [
    { icon: MessageSquare, label: '새 채팅', action: handleNewChat },
    { icon: Search, label: '전체 데이터 탐색', action: () => handleNavigateMenu('/search') },
    { icon: Users, label: '커뮤니티', action: () => handleNavigateMenu('/community') },
    { icon: Bookmark, label: '북마크', action: () => handleNavigateMenu('/bookmark') },
  ];

  const isChatRoute = location.pathname === '/';

  const isMenuItemActive = (label: string) => {
    if (label === '새 채팅') {
      return false;
    }

    if (label === '전체 데이터 탐색') {
      return location.pathname.startsWith('/search');
    }

    if (label === '커뮤니티') {
      return location.pathname.startsWith('/community');
    }

    if (label === '북마크') {
      return location.pathname.startsWith('/bookmark');
    }

    return false;
  };

  const openConversation = (conversationId: string) => {
    selectConversation(conversationId);
    const query = new URLSearchParams({ conversationId });
    navigate(`/?${query.toString()}`);
  };

  // 사이드바가 닫힌 상태 (아이콘만)
  if (!isSidebarOpen) {
    return (
      <div className="w-12 h-full bg-[#e8f4fd] border-r border-border flex flex-col items-center py-3">
        {/* 상단 사이드바 토글 버튼 */}
        <button
          type="button"
          onClick={toggleSidebar}
          className="mb-4 w-8 h-8 rounded-lg flex items-center justify-center cursor-pointer hover:bg-sidebar-accent/50 transition-colors"
          title="사이드바 열기"
          aria-label="사이드바 열기"
        >
          <PanelLeft className="w-5 h-5 text-foreground" />
        </button>

        {/* 메뉴 아이콘들 */}
        <div className="flex flex-col gap-1 w-full px-1.5">
          {menuItems.map((item) => (
            (() => {
              const isActive = isMenuItemActive(item.label);
              return (
            <button
              type="button"
              key={item.label}
              onClick={item.action}
              className={`w-full h-9 flex items-center justify-center rounded-lg cursor-pointer transition-colors group ${
                isActive ? 'bg-[#dfe4ea]' : 'hover:bg-sidebar-accent/50'
              }`}
              title={item.label}
              aria-label={item.label}
            >
              <item.icon className="w-5 h-5 text-foreground" />
            </button>
              );
            })()
          ))}
        </div>
      </div>
    );
  }

  // 사이드바가 열린 상태 (텍스트 포함)
  return (
    <div className="w-64 h-full bg-[#e8f4fd] border-r border-sidebar-border flex flex-col">
      {/* 헤더 */}
      <div className="relative h-13 border-b border-sidebar-border overflow-hidden">
        <button
          type="button"
          onClick={toggleSidebar}
          className="absolute left-3 top-1/2 -translate-y-1/2 p-2 rounded-lg cursor-pointer hover:bg-sidebar-accent/50 transition-colors z-10"
          title="사이드바 닫기"
          aria-label="사이드바 닫기"
        >
          <PanelLeft className="w-5 h-5 text-sidebar-foreground" />
        </button>
        {showTitle && (
          <div className="absolute inset-0 flex items-center justify-center">
            <BrandLogo
              className="h-10 w-auto max-w-[160px] object-contain"
              fallbackClassName="text-lg font-semibold text-sidebar-foreground"
            />
          </div>
        )}
      </div>

      {/* 메뉴 목록 */}
      <div className="flex-1 overflow-y-auto">
        <div className="p-2 space-y-0.5">
          {menuItems.map((item) => (
            (() => {
              const isActive = isMenuItemActive(item.label);
              return (
            <button
              type="button"
              key={item.label}
              onClick={item.action}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg cursor-pointer transition-colors text-left ${
                isActive
                  ? 'bg-[#dfe4ea] text-sidebar-accent-foreground'
                  : 'text-sidebar-foreground hover:bg-sidebar-accent/50'
              }`}
            >
              <item.icon className="w-5 h-5 flex-shrink-0" />
              <span className="text-sm">{item.label}</span>
            </button>
              );
            })()
          ))}
        </div>

        {/* 내 채팅 섹션 */}
            <div
              ref={myChatSectionRef}
              className={conversationMenuOpen !== null ? 'relative z-30 p-2' : 'relative z-0 p-2'}
            >
              {/* 내 채팅 드롭다운 헤더 */}
              <button
                type="button"
                onClick={() => setIsMyChatExpanded(!isMyChatExpanded)}
                className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-muted-foreground cursor-pointer hover:bg-sidebar-accent/50 transition-colors"
              >
                <span className="flex-1 text-left">내 채팅</span>
                <ChevronDown className={`w-4 h-4 transition-transform ${isMyChatExpanded ? 'rotate-180' : ''}`} />
              </button>

              {/* 내 채팅 목록 */}
              {isMyChatExpanded && (
                <div className={conversationMenuOpen !== null ? 'mt-1 space-y-0.5 pointer-events-none' : 'mt-1 space-y-0.5'}>
                  {conversations
                    .map((conversation) => {
                      const isEditing = editingConversationId === conversation.id;
                      
                      return (
                        <div
                          key={conversation.id}
                          className={
                            conversationMenuOpen === conversation.id
                              ? 'group relative z-20 pointer-events-auto rounded-lg bg-sidebar-accent/50'
                              : `group relative z-0 rounded-lg ${isChatRoute ? 'hover:bg-sidebar-accent/50' : ''}`
                           }
                         >
                          {isEditing ? (
                            <div className="w-full flex items-center gap-2 px-3 py-2.5 rounded-lg bg-sidebar-accent/50 hover:bg-sidebar-accent/50">
                              <input
                                type="text"
                                ref={editingInputRef}
                                value={editingConversationTitle}
                                onChange={(e) => setEditingConversationTitle(e.target.value)}
                                onFocus={(e) => e.currentTarget.select()}
                                onKeyDown={(e) => {
                                  if (e.key === 'Enter') {
                                    handleSaveConversationTitle(conversation.id);
                                  } else if (e.key === 'Escape') {
                                    handleCancelEditConversation();
                                  }
                                }}
                                onBlur={() => handleSaveConversationTitle(conversation.id)}
                                className="flex-1 rounded px-2 py-1 text-sm bg-transparent border-0 shadow-none focus:border-0 focus:outline-none focus:ring-0 selection:bg-[#d8ccff] selection:text-black"
                              />
                            </div>
                          ) : (
                            <>
                              <button
                                type="button"
                                onClick={() => {
                                  openConversation(conversation.id);
                                }}
                                 className={`
                                  w-full flex items-center gap-3 px-3 py-2.5 pr-10 rounded-lg cursor-pointer
                                  transition-colors relative text-left
                                 ${
                                   isChatRoute && currentConversationId === conversation.id
                                      ? 'bg-[#dfe4ea] text-sidebar-accent-foreground'
                                      : 'text-sidebar-foreground'
                                   }
                                `}
                              >
                                <div className="flex items-center gap-3 flex-1 min-w-0 text-left">
                                  <span className="flex-1 text-sm truncate text-left">{conversation.title}</span>
                                </div>
                              </button>
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
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      if (conversationMenuOpen === conversation.id) {
                                        setConversationMenuOpen(null);
                                        return;
                                      }
                                      setConversationMenuOpen(conversation.id);
                                    }}
                                    className="p-1 rounded cursor-pointer transition-colors"
                                    aria-label="더보기"
                                  >
                                    <MoreHorizontal className="w-4 h-4" />
                                  </button>
                                  {conversationMenuOpen === conversation.id && (
                                    <div className="absolute right-0 top-full mt-1 w-40 bg-white border border-border shadow-lg rounded-xl overflow-hidden z-50">
                                      <button
                                        type="button"
                                        onClick={(e) => handleStartEditConversation(e, conversation.id, conversation.title)}
                                        className="mx-1 my-1 flex w-[calc(100%-0.5rem)] items-center gap-2 rounded-lg px-3 py-2 text-sm text-left cursor-pointer transition-colors hover:bg-sidebar-accent/50"
                                      >
                                        <Edit2 className="w-3 h-3" />
                                        <span>이름 변경</span>
                                      </button>
                                      <button
                                        type="button"
                                        onClick={(e) => handleDeleteConversationFromMenu(e, conversation.id)}
                                        className="mx-1 mb-1 flex w-[calc(100%-0.5rem)] items-center gap-2 rounded-lg px-3 py-2 text-sm text-left text-destructive cursor-pointer transition-colors hover:bg-sidebar-accent/50"
                                      >
                                        <Trash2 className="w-3 h-3" />
                                        <span>삭제</span>
                                      </button>
                                    </div>
                                  )}
                                </div>
                              </div>
                            </>
                          )}
                        </div>
                      );
                    })}
                </div>
              )}
            </div>
      </div>
    </div>
  );
}
