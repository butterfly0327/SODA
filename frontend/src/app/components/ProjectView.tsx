import { ArrowLeft, Database, Code, MessageSquare } from 'lucide-react';
import { useChatStore } from '../../stores/chatStore';
import type { ComparisonItem } from '../../stores/chatStore';
import { useNavigate } from 'react-router';
import { ProjectConversationsSection } from './project/ProjectConversationsSection';
import { ProjectComparisonsSection } from './project/ProjectComparisonsSection';

interface ProjectViewProps {
  projectId: string;
  onBack: () => void;
  onNewChat: (projectId: string) => void;
}

export function ProjectView({ projectId, onBack, onNewChat }: ProjectViewProps) {
  const projects = useChatStore((state) => state.projects);
  const conversations = useChatStore((state) => state.conversations);
  const selectConversation = useChatStore((state) => state.selectConversation);
  const currentConversationId = useChatStore((state) => state.currentConversationId);
  const deleteConversation = useChatStore((state) => state.deleteConversation);
  const removeProjectComparison = useChatStore((state) => state.removeProjectComparison);
  const updateConversationTitle = useChatStore((state) => state.updateConversationTitle);
  const navigate = useNavigate();

  const openConversation = (conversationId: string) => {
    const query = new URLSearchParams({ conversationId });
    navigate(`/?${query.toString()}`);
  };
  const project = projects.find(p => p.id === projectId);
  const projectConversations = conversations
    .filter((conversation) => conversation.projectId === projectId)
    .sort((a, b) => b.updatedAt - a.updatedAt);

  if (!project) return null;

  const comparisonItems = (project.comparisons ?? []).map((comparison, index): ComparisonItem => {
    if (typeof comparison === 'string') {
      return {
        id: `legacy-${project.id}-${index}`,
        name: comparison,
        type: 'dataset',
        addedAt: 0,
      };
    }

    return comparison;
  });

  const handleDeleteConversation = (id: string) => {
    deleteConversation(id);
  };

  const handleRenameConversation = (id: string, title: string) => {
    updateConversationTitle(id, title);
  };

  const handleDeleteComparison = (comparisonId: string) => {
    removeProjectComparison(project.id, comparisonId);
  };

  return (
    <div className="p-2">
      {/* 뒤로 가기 버튼 */}
      <button
        type="button"
        onClick={onBack}
        className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-sidebar-accent transition-colors text-left mb-4"
      >
        <ArrowLeft className="w-4 h-4 text-sidebar-foreground" />
        <span className="text-sm text-sidebar-foreground">프로젝트 목록</span>
      </button>

      {/* 프로젝트 이름 */}
      <div className="px-3 py-2 mb-4">
        <div className="text-xs text-muted-foreground mb-1">프로젝트</div>
        <div className="text-lg font-semibold text-foreground">{project.name}</div>
      </div>

      {/* 새 채팅 버튼 */}
      <button
        type="button"
        onClick={() => onNewChat(projectId)}
        className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg bg-[#e8f4fd] hover:bg-[#d4eaf7] transition-colors text-left mb-4"
      >
        <MessageSquare className="w-4 h-4 text-foreground" />
        <span className="text-sm font-medium text-foreground">새 채팅</span>
      </button>

      <ProjectConversationsSection
        conversations={projectConversations}
        currentConversationId={currentConversationId}
        onOpenConversation={(conversationId) => {
          selectConversation(conversationId);
          openConversation(conversationId);
        }}
        onDeleteConversation={handleDeleteConversation}
        onRenameConversation={handleRenameConversation}
      />

      {/* 북마크 */}
      <div className="mb-4">
        <div className="px-3 py-2 text-xs text-muted-foreground font-medium">북마크</div>
        {project.savedResources && project.savedResources.length > 0 ? (
          <div className="space-y-1">
            {project.savedResources.map((resource, index) => (
              <button
                type="button"
                key={`${resource.type}-${resource.name}`}
                className="w-full flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-sidebar-accent/50 transition-colors text-left"
              >
                {resource.type === 'dataset' ? (
                  <Database className="w-3.5 h-3.5 text-blue-600 flex-shrink-0" />
                ) : (
                  <Code className="w-3.5 h-3.5 text-green-600 flex-shrink-0" />
                )}
                <span className="text-sm text-sidebar-foreground">- {resource.name}</span>
              </button>
            ))}
          </div>
        ) : (
          <div className="px-3 py-2 text-xs text-muted-foreground italic">
            북마크가 없습니다
          </div>
        )}
      </div>

      <ProjectComparisonsSection
        comparisons={comparisonItems}
        onDeleteComparison={handleDeleteComparison}
      />

    </div>
  );
}
