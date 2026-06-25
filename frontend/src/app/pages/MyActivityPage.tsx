import { Navbar } from '../components/Navbar';
import { Sidebar } from '../components/Sidebar';
import { Activity, MessageSquare, ThumbsUp, Edit, Trash2 } from 'lucide-react';
import { useState } from 'react';
import { Button } from '@/components/ui/button';

interface ActivityItem {
  id: string;
  type: 'chat' | 'post' | 'comment' | 'like';
  title: string;
  description: string;
  timestamp: string;
  category?: string;
}

export function MyActivityPage() {
  const [filter, setFilter] = useState<'all' | 'chat' | 'post' | 'comment' | 'like'>('all');

  // 임시 활동 데이터
  const activities: ActivityItem[] = [
    {
      id: '1',
      type: 'chat',
      title: '새로운 채팅 시작',
      description: 'React 프로젝트 구조에 대한 질문',
      timestamp: '2시간 전',
      category: '내 채팅',
    },
    {
      id: '2',
      type: 'post',
      title: '커뮤니티 게시글 작성',
      description: 'Tailwind CSS 활용 팁 공유',
      timestamp: '5시간 전',
      category: '커뮤니티',
    },
    {
      id: '3',
      type: 'comment',
      title: '댓글 작성',
      description: 'React Query 사용법에 대한 의견 추가',
      timestamp: '1일 전',
      category: '커뮤니티',
    },
    {
      id: '4',
      type: 'like',
      title: '좋아요 표시',
      description: 'Zustand vs Redux 비교 글',
      timestamp: '1일 전',
      category: '커뮤니티',
    },
    {
      id: '5',
      type: 'chat',
      title: '채팅 이름 변경',
      description: 'Atomic Design 패턴 → 디자인 시스템 구축',
      timestamp: '2일 전',
      category: '내 채팅',
    },
    {
      id: '6',
      type: 'post',
      title: '커뮤니티 게시글 작성',
      description: 'Layer-based 아키텍처 적용 경험',
      timestamp: '3일 전',
      category: '커뮤니티',
    },
  ];

  const filteredActivities = filter === 'all' 
    ? activities 
    : activities.filter(activity => activity.type === filter);

  const getActivityIcon = (type: string) => {
    switch (type) {
      case 'chat':
        return <MessageSquare className="w-5 h-5 text-blue-500" />;
      case 'post':
        return <Edit className="w-5 h-5 text-green-500" />;
      case 'comment':
        return <MessageSquare className="w-5 h-5 text-purple-500" />;
      case 'like':
        return <ThumbsUp className="w-5 h-5 text-pink-500" />;
      default:
        return <Activity className="w-5 h-5 text-gray-500" />;
    }
  };

  const getActivityTypeLabel = (type: string) => {
    switch (type) {
      case 'chat':
        return '채팅';
      case 'post':
        return '게시글';
      case 'comment':
        return '댓글';
      case 'like':
        return '좋아요';
      default:
        return '활동';
    }
  };

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-background">
      <Navbar />
      
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        
        <div className="flex-1 overflow-y-auto">
          <div className="max-w-5xl mx-auto px-6 py-8">
            {/* 페이지 헤더 */}
            <div className="mb-8">
              <div className="flex items-center gap-3 mb-2">
                <Activity className="w-8 h-8 text-foreground" />
                <h1 className="text-3xl font-bold text-foreground">My Activity</h1>
              </div>
              <p className="text-muted-foreground">최근 활동 내역을 확인하세요</p>
            </div>

            {/* 필터 버튼 */}
            <div className="flex gap-2 mb-6 flex-wrap">
              {[
                { value: 'all', label: '전체' },
                { value: 'chat', label: '채팅' },
                { value: 'post', label: '게시글' },
                { value: 'comment', label: '댓글' },
                { value: 'like', label: '좋아요' },
              ].map((item) => (
                <Button
                  key={item.value}
                  onClick={() => setFilter(item.value as any)}
                  variant="outline"
                  className={`
                    px-4 py-2 rounded-lg font-medium text-sm transition-colors
                    ${
                      filter === item.value
                        ? 'bg-[#e8f4fd] text-foreground'
                        : 'bg-white border border-border text-muted-foreground hover:bg-muted'
                    }
                  `}
                >
                  {item.label}
                </Button>
              ))}
            </div>

            {/* 활동 목록 */}
            <div className="space-y-3">
              {filteredActivities.length > 0 ? (
                filteredActivities.map((activity) => (
                  <div
                    key={activity.id}
                    className="bg-white border border-border rounded-lg p-5 hover:shadow-md transition-shadow"
                  >
                    <div className="flex items-start gap-4">
                      {/* 아이콘 */}
                      <div className="flex-shrink-0 mt-1">
                        {getActivityIcon(activity.type)}
                      </div>

                      {/* 내용 */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-xs font-medium text-muted-foreground bg-muted px-2 py-0.5 rounded">
                            {getActivityTypeLabel(activity.type)}
                          </span>
                          {activity.category && (
                            <span className="text-xs text-muted-foreground">
                              • {activity.category}
                            </span>
                          )}
                        </div>
                        <h3 className="font-semibold text-foreground mb-1">
                          {activity.title}
                        </h3>
                        <p className="text-sm text-muted-foreground mb-2">
                          {activity.description}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {activity.timestamp}
                        </p>
                      </div>

                      {/* 더보기 버튼 (선택적) */}
                      <Button variant="ghost" className="flex-shrink-0 p-1 hover:bg-muted rounded transition-colors opacity-0 group-hover:opacity-100 h-auto">
                        <Trash2 className="w-4 h-4 text-muted-foreground" />
                      </Button>
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-center py-16">
                  <Activity className="w-16 h-16 text-muted-foreground mx-auto mb-4 opacity-50" />
                  <p className="text-muted-foreground">활동 내역이 없습니다</p>
                </div>
              )}
            </div>

            {/* 더 불러오기 버튼 */}
            {filteredActivities.length > 0 && (
              <div className="mt-8 text-center">
                <Button variant="outline" className="px-6 py-2.5 rounded-lg border border-border text-foreground hover:bg-muted transition-colors font-medium">
                  더 불러오기
                </Button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
