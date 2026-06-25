import { MoreVertical, Trash2, Pencil } from 'lucide-react';
import { useChatStore } from '../../stores/chatStore';
import { useState, useRef, useEffect } from 'react';
import { useLocation } from 'react-router';
import { useClickOutside } from '../../hooks/useClickOutside';
import { RenameConversationModal } from './header/RenameConversationModal';

export function Header() {
  const isSidebarOpen = useChatStore((state) => state.isSidebarOpen);
  const toggleSidebar = useChatStore((state) => state.toggleSidebar);
  const getCurrentConversation = useChatStore((state) => state.getCurrentConversation);
  const deleteConversation = useChatStore((state) => state.deleteConversation);
  const updateConversationTitle = useChatStore((state) => state.updateConversationTitle);
  const { pathname, search } = useLocation();
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [isRenameModalOpen, setIsRenameModalOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  
  const currentConversation = getCurrentConversation();
  const canUseConversationActions = Boolean(currentConversation?.id);
  const headerTitle = canUseConversationActions ? currentConversation.title : 'SODA';

  useClickOutside({
    ref: menuRef,
    enabled: isMenuOpen,
    onOutsideClick: () => setIsMenuOpen(false),
  });

  useEffect(() => {
    const locationKey = `${pathname}${search}`;
    if (!locationKey) {
      return;
    }

    setIsMenuOpen(false);
    setIsRenameModalOpen(false);
  }, [pathname, search]);

  const handleRenameClick = () => {
    setIsRenameModalOpen(true);
  };

  const handleRenameConfirm = (nextTitle: string) => {
    if (currentConversation?.id) {
      updateConversationTitle(currentConversation.id, nextTitle);
      setIsRenameModalOpen(false);
    }
  };

  return (
    <>
      <header className="h-13 border-b border-border bg-background flex items-center justify-between px-6">
        {/* 왼쪽: 채팅방 이름 */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <h1 className="text-base font-semibold text-foreground">
              {headerTitle}
            </h1>
          </div>
        </div>

        {/* 오른쪽: 더보기 */}
        <div className="flex items-center gap-3">
          {/* 세로 점 3개 */}
          <div className="relative" ref={menuRef}>
            <button
              type="button"
              onClick={() => {
                if (!canUseConversationActions) {
                  return;
                }
                setIsMenuOpen(!isMenuOpen);
              }}
              disabled={!canUseConversationActions}
              className="p-1.5 cursor-pointer hover:bg-muted rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <MoreVertical className="w-5 h-5 text-foreground" />
            </button>
            
            {/* 드롭다운 메뉴 */}
            {isMenuOpen && canUseConversationActions && (
              <div className="absolute right-0 top-full mt-1 w-40 bg-white border border-border shadow-lg rounded-xl overflow-hidden z-50">
                <button 
                  type="button"
                  onClick={() => {
                    setIsMenuOpen(false);
                    handleRenameClick();
                  }}
                  className="mx-1 my-1 flex w-[calc(100%-0.5rem)] items-center gap-2 rounded-lg px-3 py-2 text-sm text-left cursor-pointer transition-colors hover:bg-sidebar-accent/50"
                >
                  <Pencil className="w-3 h-3" />
                  <span>이름 변경</span>
                </button>
                <button 
                  type="button"
                  onClick={() => {
                    setIsMenuOpen(false);
                    if (currentConversation?.id) {
                      deleteConversation(currentConversation.id);
                    }
                  }}
                  className="mx-1 mb-1 flex w-[calc(100%-0.5rem)] items-center gap-2 rounded-lg px-3 py-2 text-sm text-left text-destructive cursor-pointer transition-colors hover:bg-sidebar-accent/50"
                >
                  <Trash2 className="w-3 h-3" />
                  <span>삭제</span>
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      {isRenameModalOpen && (
        <RenameConversationModal
          initialTitle={currentConversation?.title ?? ''}
          onClose={() => setIsRenameModalOpen(false)}
          onConfirm={handleRenameConfirm}
        />
      )}
    </>
  );
}
