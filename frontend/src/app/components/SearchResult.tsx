import { Bookmark } from 'lucide-react';
import { useState } from 'react';

interface DatasetCard {
  id?: number;
  type: 'dataset';
  score: number;
  name: string;
  source: string;
  projectType?: string;
  taskMatch: number;
  classCount: number;
  sampleCount: string;
  missingRate: number;
  reliability: 'High' | 'Medium' | 'Low';
  lastUpdate: string;
  isFree?: boolean;
  reasons?: string[]; // 추천 이유
}

interface APICard {
  id?: number;
  type: 'api';
  score: number;
  name: string;
  category: string;
  projectType?: string;
  responseTime: string;
  auth: string;
  freeQuota: string;
  availability: string;
  isFree?: boolean;
  reasons?: string[]; // 추천 이유
}

export type ResultCard = DatasetCard | APICard;

export interface SearchResultData {
  projectType: string;
  totalCandidates: number;
  recommendations: number;
  analysis: string;
  results: ResultCard[];
  searchQuery?: string; // 검색어 추가
}

interface SearchResultProps {
  data: SearchResultData;
  onOpenDetail?: (result: ResultCard) => void;
  onAddComparison?: (result: ResultCard) => void;
  onToggleBookmark?: (result: ResultCard) => void;
  isBookmarked?: (result: ResultCard) => boolean;
  canBookmark?: boolean;
  canCompare?: boolean;
}

export function SearchResult({
  data,
  onOpenDetail,
  onAddComparison,
  onToggleBookmark,
  isBookmarked,
  canBookmark = true,
  canCompare = true,
}: SearchResultProps) {
  const [filterType, setFilterType] = useState<'all' | 'dataset' | 'api'>('all');
  const [sortBy, setSortBy] = useState<'score' | 'latest'>('score');

  const filteredResults = data.results.filter((result) => {
    if (filterType === 'all') return true;
    return result.type === filterType;
  });

  const getReliabilityColor = (reliability: 'High' | 'Medium' | 'Low') => {
    switch (reliability) {
      case 'High':
        return 'bg-green-100 text-green-700 border-green-300';
      case 'Medium':
        return 'bg-yellow-100 text-yellow-700 border-yellow-300';
      case 'Low':
        return 'bg-red-100 text-red-700 border-red-300';
    }
  };

  const parseLastUpdate = (value: string | undefined) => {
    if (!value) {
      return 0;
    }

    const numeric = value.replace(/[^0-9]/g, '');
    return Number(numeric || 0);
  };

  const sortedResults = [...filteredResults].sort((a, b) => {
    if (sortBy === 'score') {
      return b.score - a.score;
    }

    if (a.type === 'dataset' && b.type === 'dataset') {
      return parseLastUpdate(b.lastUpdate) - parseLastUpdate(a.lastUpdate);
    }

    return b.score - a.score;
  });

  return (
    <div className="w-full">
      {/* 검색어 강조 영역 */}
      {data.searchQuery && (
        <div className="mb-6">
          <h2 className="text-2xl font-semibold text-foreground mb-2">
            '{data.searchQuery}'에 대한 추천 결과
          </h2>
          <p className="text-sm text-muted-foreground">
            {data.analysis}
          </p>
        </div>
      )}

      {/* 필터 영역 */}
      <div className="flex items-center gap-3 mb-6 flex-wrap">
        <div className="flex items-center gap-2 bg-white border border-border rounded-lg p-1">
          <button
            onClick={() => setFilterType('all')}
            className={`px-4 py-1.5 rounded-md text-sm transition-colors ${
              filterType === 'all'
                ? 'bg-[#e8f4fd] text-foreground font-medium'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            전체
          </button>
          <button
            onClick={() => setFilterType('dataset')}
            className={`px-4 py-1.5 rounded-md text-sm transition-colors ${
              filterType === 'dataset'
                ? 'bg-[#e8f4fd] text-foreground font-medium'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            데이터셋
          </button>
          <button
            onClick={() => setFilterType('api')}
            className={`px-4 py-1.5 rounded-md text-sm transition-colors ${
              filterType === 'api'
                ? 'bg-[#e8f4fd] text-foreground font-medium'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            Open API
          </button>
        </div>

        <select
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value as 'score' | 'latest')}
          className="px-4 py-2 bg-white border border-border rounded-lg text-sm"
        >
          <option value="score">적합도순</option>
          <option value="latest">최신순</option>
        </select>
      </div>

      {/* 결과 카드 목록 */}
      <div className="grid gap-4">
        {sortedResults.map((result) => (
          <div key={`${result.type}-${result.name}`}>
            {result.type === 'dataset' ? (
              <DatasetCardComponent
                data={result}
                onOpenDetail={onOpenDetail}
                onAddComparison={onAddComparison}
                onToggleBookmark={onToggleBookmark}
                isBookmarked={isBookmarked}
                canBookmark={canBookmark}
                canCompare={canCompare}
              />
            ) : (
              <APICardComponent
                data={result}
                onOpenDetail={onOpenDetail}
                onAddComparison={onAddComparison}
                onToggleBookmark={onToggleBookmark}
                isBookmarked={isBookmarked}
                canBookmark={canBookmark}
                canCompare={canCompare}
              />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function DatasetCardComponent({
  data,
  onOpenDetail,
  onAddComparison,
  onToggleBookmark,
  isBookmarked,
  canBookmark,
  canCompare,
}: {
  data: Extract<ResultCard, { type: 'dataset' }>;
  onOpenDetail?: (result: ResultCard) => void;
  onAddComparison?: (result: ResultCard) => void;
  onToggleBookmark?: (result: ResultCard) => void;
  isBookmarked?: (result: ResultCard) => boolean;
  canBookmark: boolean;
  canCompare: boolean;
}) {
  const getScoreBadge = (score?: number) => {
    if (score === undefined) return { label: '추천', color: 'bg-blue-100 text-blue-700 border-blue-300' };
    if (score >= 90) return { label: 'High', color: 'bg-green-100 text-green-700 border-green-300' };
    if (score >= 70) return { label: 'Medium', color: 'bg-yellow-100 text-yellow-700 border-yellow-300' };
    return { label: 'Low', color: 'bg-gray-100 text-gray-700 border-gray-300' };
  };

  const scoreBadge = getScoreBadge(data.score);

  const bookmarked = isBookmarked?.(data) ?? false;

  return (
    <div className="bg-white border border-border rounded-xl p-5 hover:shadow-md transition-shadow">
      {/* 헤더: 타입 태그 + 점수 배지 */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="px-2.5 py-1 bg-blue-100 text-blue-700 text-xs font-medium rounded-md border border-blue-200">
            Dataset
          </span>
          <button
            type="button"
            onClick={() => onToggleBookmark?.(data)}
            disabled={!canBookmark}
            title={canBookmark ? '북마크 토글' : '프로젝트를 선택하면 북마크할 수 있어요'}
            className="p-1.5 rounded-md hover:bg-muted transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            aria-label={bookmarked ? '북마크 해제' : '북마크 추가'}
          >
            <Bookmark className={`w-4 h-4 ${bookmarked ? 'fill-yellow-400 text-yellow-400' : 'text-muted-foreground'}`} />
          </button>
        </div>
        <span className={`px-2.5 py-1 text-xs font-medium rounded-md border ${scoreBadge.color}`}>{scoreBadge.label}</span>
      </div>

      {/* 제목 */}
      <h3 className="text-lg font-semibold text-foreground mb-1">{data.name}</h3>
      <div className="text-sm text-muted-foreground mb-3">{data.source ?? '출처 정보 없음'}</div>

      {/* 추천 이유 */}
      {data.reasons && data.reasons.length > 0 && (
        <div className="mb-4 bg-blue-50/50 rounded-lg p-3 border border-blue-100">
          <div className="text-xs font-medium text-foreground mb-2">추천 이유</div>
          <ul className="space-y-1">
            {data.reasons.map((reason, idx) => (
              <li key={idx} className="text-sm text-muted-foreground flex items-start">
                <span className="mr-2">•</span>
                <span>{reason}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* 핵심 정보만 표시 */}
      <div className="grid grid-cols-2 gap-x-4 gap-y-2 mb-4">
        {data.taskMatch !== undefined && (
          <div className="text-sm">
            <span className="text-muted-foreground">태스크 일치도:</span>
            <span className="ml-2 font-medium text-foreground">{data.taskMatch}%</span>
          </div>
        )}
        {data.sampleCount && (
          <div className="text-sm">
            <span className="text-muted-foreground">샘플 수:</span>
            <span className="ml-2 font-medium text-foreground">{data.sampleCount}</span>
          </div>
        )}
      </div>

      {/* 액션 버튼 */}
      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => onOpenDetail?.(data)}
          className="px-4 py-2 bg-[#e8f4fd] text-foreground rounded-lg text-sm font-medium hover:bg-blue-200 transition-colors"
        >
          상세보기
        </button>
        <button
          type="button"
          onClick={() => onAddComparison?.(data)}
          disabled={!canCompare}
          title={canCompare ? '비교 목록에 추가' : '프로젝트를 선택하면 비교할 수 있어요'}
          className="px-4 py-2 border border-border text-foreground rounded-lg text-sm font-medium hover:bg-muted transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
        >
          비교하기
        </button>
      </div>
    </div>
  );
}

function APICardComponent({
  data,
  onOpenDetail,
  onAddComparison,
  onToggleBookmark,
  isBookmarked,
  canBookmark,
  canCompare,
}: {
  data: Extract<ResultCard, { type: 'api' }>;
  onOpenDetail?: (result: ResultCard) => void;
  onAddComparison?: (result: ResultCard) => void;
  onToggleBookmark?: (result: ResultCard) => void;
  isBookmarked?: (result: ResultCard) => boolean;
  canBookmark: boolean;
  canCompare: boolean;
}) {
  const getScoreBadge = (score?: number) => {
    if (score === undefined) return { label: '추천', color: 'bg-blue-100 text-blue-700 border-blue-300' };
    if (score >= 90) return { label: 'High', color: 'bg-green-100 text-green-700 border-green-300' };
    if (score >= 70) return { label: 'Medium', color: 'bg-yellow-100 text-yellow-700 border-yellow-300' };
    return { label: 'Low', color: 'bg-gray-100 text-gray-700 border-gray-300' };
  };

  const scoreBadge = getScoreBadge(data.score);

  const bookmarked = isBookmarked?.(data) ?? false;

  return (
    <div className="bg-white border border-border rounded-xl p-5 hover:shadow-md transition-shadow">
      {/* 헤더: 타입 태그 + 점수 배지 */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="px-2.5 py-1 bg-green-100 text-green-700 text-xs font-medium rounded-md border border-green-200">
            Open API
          </span>
          <button
            type="button"
            onClick={() => onToggleBookmark?.(data)}
            disabled={!canBookmark}
            title={canBookmark ? '북마크 토글' : '프로젝트를 선택하면 북마크할 수 있어요'}
            className="p-1.5 rounded-md hover:bg-muted transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            aria-label={bookmarked ? '북마크 해제' : '북마크 추가'}
          >
            <Bookmark className={`w-4 h-4 ${bookmarked ? 'fill-yellow-400 text-yellow-400' : 'text-muted-foreground'}`} />
          </button>
        </div>
        <span className={`px-2.5 py-1 text-xs font-medium rounded-md border ${scoreBadge.color}`}>{scoreBadge.label}</span>
      </div>

      {/* 제목 */}
      <h3 className="text-lg font-semibold text-foreground mb-1">{data.name}</h3>
      <div className="text-sm text-muted-foreground mb-3">Category: {data.category ?? '미분류'}</div>

      {/* 추천 이유 */}
      {data.reasons && data.reasons.length > 0 && (
        <div className="mb-4 bg-green-50/50 rounded-lg p-3 border border-green-100">
          <div className="text-xs font-medium text-foreground mb-2">추천 이유</div>
          <ul className="space-y-1">
            {data.reasons.map((reason, idx) => (
              <li key={idx} className="text-sm text-muted-foreground flex items-start">
                <span className="mr-2">•</span>
                <span>{reason}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* 핵심 정보만 표시 */}
      <div className="grid grid-cols-2 gap-x-4 gap-y-2 mb-4">
        {data.responseTime && (
          <div className="text-sm">
            <span className="text-muted-foreground">응답 속도:</span>
            <span className="ml-2 font-medium text-foreground">{data.responseTime}</span>
          </div>
        )}
        {data.freeQuota && (
          <div className="text-sm">
            <span className="text-muted-foreground">무료 호출:</span>
            <span className="ml-2 font-medium text-foreground">{data.freeQuota}</span>
          </div>
        )}
      </div>

      {/* 액션 버튼 */}
      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => onOpenDetail?.(data)}
          className="px-4 py-2 bg-[#e8f4fd] text-foreground rounded-lg text-sm font-medium hover:bg-blue-200 transition-colors"
        >
          상세보기
        </button>
        <button
          type="button"
          onClick={() => onAddComparison?.(data)}
          disabled={!canCompare}
          title={canCompare ? '비교 목록에 추가' : '프로젝트를 선택하면 비교할 수 있어요'}
          className="px-4 py-2 border border-border text-foreground rounded-lg text-sm font-medium hover:bg-muted transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
        >
          비교하기
        </button>
      </div>
    </div>
  );
}
