import type { Message as MessageType } from '../../stores/chatStore';
import { ChatSearchResultsAttachment } from './ChatSearchResultsAttachment';
import { RecommendationMarkdown } from './RecommendationMarkdown';
import type { ResultCard, SearchResultData } from '@/types/recommendation';
import sodabotImage from '@/assets/images/sodabot.png';

interface MessageProps {
  message: MessageType;
  onOpenDetail?: (result: ResultCard) => void;
  onAddComparison?: (result: ResultCard) => void;
  onToggleBookmark?: (result: ResultCard) => void;
  isBookmarked?: (result: ResultCard) => boolean;
  canBookmark?: boolean;
  canCompare?: boolean;
}

function buildAssistantDisplayContent(message: MessageType) {
  if (!message.content) {
    return isSearchResultData(message.searchResult) ? message.searchResult.analysis : '';
  }

  if (!isSearchResultData(message.searchResult)) {
    return message.content;
  }

  return message.searchResult.analysis || message.content;
}

function isSearchResultData(value: unknown): value is SearchResultData {
  if (!value || typeof value !== 'object') {
    return false;
  }

  const maybe = value as Partial<SearchResultData>;
  return Array.isArray(maybe.results) && typeof maybe.analysis === 'string' && typeof maybe.recommendations === 'number';
}

export function Message({
  message,
  onOpenDetail,
  onAddComparison,
  onToggleBookmark,
  isBookmarked,
  canBookmark,
  canCompare,
}: MessageProps) {
  const isUser = message.role === 'user';
  const displayContent = buildAssistantDisplayContent(message);

  // 사용자 메시지는 오른쪽 정렬
  if (isUser) {
    return (
      <div className="w-full px-4 sm:px-12 py-3">
        <div className="max-w-2xl mx-auto flex justify-end">
          <div 
            className="inline-block px-5 py-3 rounded-3xl max-w-[80%] bg-[#e8f4fd] text-[#1F1F1F]"
          >
            <div className="whitespace-pre-wrap break-words">
              {message.content}
            </div>
          </div>
        </div>
      </div>
    );
  }

  // AI 응답은 왼쪽 정렬 (아바타 포함)
  return (
    <div className="w-full px-4 sm:px-12 py-3">
      <div className="max-w-2xl mx-auto flex gap-3">
        {/* 아바타 */}
        <div className="w-8 h-8 flex items-center justify-center flex-shrink-0">
          <img src={sodabotImage} alt="SODA bot" className="h-full w-full object-contain" />
        </div>

        {/* 메시지 내용 */}
        <div className="flex-1 min-w-0 overflow-x-hidden overflow-y-visible">
          {displayContent ? (
            <div className="break-words leading-relaxed">
              <RecommendationMarkdown content={displayContent} />
            </div>
          ) : null}

          {isSearchResultData(message.searchResult) ? (
            <ChatSearchResultsAttachment
              data={message.searchResult}
              onOpenDetail={onOpenDetail}
              onAddComparison={onAddComparison}
              onToggleBookmark={onToggleBookmark}
              isBookmarked={isBookmarked}
              canBookmark={canBookmark}
              canCompare={canCompare}
            />
          ) : null}
        </div>
      </div>
    </div>
  );
}
