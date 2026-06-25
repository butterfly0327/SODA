import { Bookmark, Code, Database } from 'lucide-react';
import type { ResultCard, SearchResultData } from '@/types/recommendation';

interface ChatSearchResultsAttachmentProps {
  data: SearchResultData;
  onOpenDetail?: (result: ResultCard) => void;
  onAddComparison?: (result: ResultCard) => void;
  onToggleBookmark?: (result: ResultCard) => void;
  isBookmarked?: (result: ResultCard) => boolean;
  canBookmark?: boolean;
  canCompare?: boolean;
}

function compareByScoreDesc(a: ResultCard, b: ResultCard) {
  return (b.score ?? 0) - (a.score ?? 0);
}

export function ChatSearchResultsAttachment({ data, ...actions }: ChatSearchResultsAttachmentProps) {
  const datasets = data.results
    .filter((result): result is Extract<ResultCard, { type: 'dataset' }> => result.type === 'dataset')
    .sort(compareByScoreDesc);
  const apis = data.results
    .filter((result): result is Extract<ResultCard, { type: 'api' }> => result.type === 'api')
    .sort(compareByScoreDesc);

  return (
    <div className="mt-5 space-y-5 pb-2">
      {datasets.length > 0 && (
        <section className="space-y-3">
          <h3 className="text-sm font-semibold text-foreground">추천 데이터셋</h3>
          <div className="grid gap-4">
            {datasets.map((result) => (
              <DatasetAttachmentCard key={`dataset-${result.id ?? result.name}`} result={result} {...actions} />
            ))}
          </div>
        </section>
      )}

      {apis.length > 0 && (
        <section className="space-y-3">
          <h3 className="text-sm font-semibold text-foreground">추천 Open API</h3>
          <div className="grid gap-4">
            {apis.map((result) => (
              <ApiAttachmentCard key={`api-${result.id ?? result.name}`} result={result} {...actions} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

function renderScoreBadge(score?: number) {
  if (score === undefined) {
    return '추천';
  }

  return `${Math.round(score)}점`;
}

function renderMetaValue(value: string | number | undefined, fallback = '-') {
  if (value === undefined || value === null || value === '') {
    return fallback;
  }

  return `${value}`;
}

function renderDateValue(value: string | undefined, fallback = '-') {
  if (!value) {
    return fallback;
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return fallback;
  }

  const year = date.getFullYear();
  const month = `${date.getMonth() + 1}`.padStart(2, '0');
  const day = `${date.getDate()}`.padStart(2, '0');
  return `${year}. ${month}. ${day}.`;
}

function DatasetAttachmentCard(props: {
  result: Extract<ResultCard, { type: 'dataset' }>;
  onOpenDetail?: (result: ResultCard) => void;
  onAddComparison?: (result: ResultCard) => void;
  onToggleBookmark?: (result: ResultCard) => void;
  isBookmarked?: (result: ResultCard) => boolean;
  canBookmark?: boolean;
  canCompare?: boolean;
}) {
  const { result, ...actions } = props;
  const bookmarked = actions.isBookmarked?.(result) ?? false;

  return (
    <div
      className={`rounded-xl border border-border bg-white p-6 shadow-md transition-shadow hover:shadow-lg ${
        actions.onOpenDetail ? 'cursor-pointer' : ''
      }`}
      role={actions.onOpenDetail ? 'button' : undefined}
      tabIndex={actions.onOpenDetail ? 0 : undefined}
      onClick={actions.onOpenDetail ? () => actions.onOpenDetail?.(result) : undefined}
      onKeyDown={
        actions.onOpenDetail
          ? (event) => {
              if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                actions.onOpenDetail?.(result);
              }
            }
          : undefined
      }
    >
      <div className="flex items-start gap-4">
        <div className="w-12 h-12 rounded-lg flex items-center justify-center flex-shrink-0 ds-resource-dataset-icon">
          <Database className="w-6 h-6" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="mb-2 grid grid-cols-[minmax(0,1fr)_auto] items-start gap-3">
            <div className="min-w-0">
              <h3 className="text-lg font-semibold text-foreground mb-1 break-words leading-snug">{result.name}</h3>
              <div className="flex items-center gap-3 text-sm text-muted-foreground flex-wrap">
                <span>출처: {renderMetaValue(result.source, '정보 없음')}</span>
              </div>
            </div>
            <div className="flex items-center gap-2 self-start whitespace-nowrap pl-2">
              <button
                type="button"
                onClick={(event) => {
                  event.stopPropagation();
                  actions.onToggleBookmark?.(result);
                }}
                onKeyDown={(event) => {
                  event.stopPropagation();
                  if (event.key === ' ') {
                    event.preventDefault();
                  }
                }}
                disabled={!actions.canBookmark}
                className="rounded-md p-2.5 cursor-pointer disabled:cursor-pointer disabled:opacity-40"
                aria-label={bookmarked ? '북마크 해제' : '북마크 추가'}
                title={bookmarked ? '북마크 해제' : '북마크 추가'}
              >
                <Bookmark className={`h-5 w-5 ${bookmarked ? 'fill-[#4f76df] text-[#4f76df]' : 'text-muted-foreground'}`} />
              </button>
            </div>
          </div>

          <div className={`mt-4 grid grid-cols-2 gap-4 ${result.rank ? 'md:grid-cols-5' : 'md:grid-cols-4'}`}>
            <div className="flex flex-col items-start text-left">
              <p className="mb-1 text-xs text-muted-foreground">타입</p>
              <p className="text-sm font-semibold text-foreground">데이터셋</p>
            </div>
            <div className="flex flex-col items-start text-left">
              <p className="mb-1 text-xs text-muted-foreground">업데이트</p>
              <p className="text-sm font-semibold text-foreground">{renderDateValue(result.updatedAt ?? result.lastUpdate)}</p>
            </div>
            <div className="flex flex-col items-center text-center">
              <p className="mb-1 text-xs text-muted-foreground">비용</p>
              <p className="text-sm font-semibold text-foreground">{result.isFree ? '무료' : '유료/미상'}</p>
            </div>
            <div className="flex flex-col items-center text-center">
              <p className="mb-1 text-xs text-muted-foreground">점수</p>
              <div className="inline-flex items-center whitespace-nowrap rounded-full border border-blue-200 bg-blue-50 px-2.5 py-1 text-sm font-semibold text-blue-700 shadow-sm">
                {renderScoreBadge(result.score)}
              </div>
            </div>
            {result.rank ? (
              <div className="flex flex-col items-center text-center">
                <p className="mb-1 text-xs text-muted-foreground">추천 순위</p>
                <div className="inline-flex items-center whitespace-nowrap rounded-full border border-amber-200 bg-amber-50 px-2.5 py-1 text-sm font-semibold text-amber-700 shadow-sm">
                  {result.rank}위
                </div>
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  );
}

function ApiAttachmentCard(props: {
  result: Extract<ResultCard, { type: 'api' }>;
  onOpenDetail?: (result: ResultCard) => void;
  onAddComparison?: (result: ResultCard) => void;
  onToggleBookmark?: (result: ResultCard) => void;
  isBookmarked?: (result: ResultCard) => boolean;
  canBookmark?: boolean;
  canCompare?: boolean;
}) {
  const { result, ...actions } = props;
  const bookmarked = actions.isBookmarked?.(result) ?? false;

  return (
    <div
      className={`rounded-xl border border-border bg-white p-6 shadow-md transition-shadow hover:shadow-lg ${
        actions.onOpenDetail ? 'cursor-pointer' : ''
      }`}
      role={actions.onOpenDetail ? 'button' : undefined}
      tabIndex={actions.onOpenDetail ? 0 : undefined}
      onClick={actions.onOpenDetail ? () => actions.onOpenDetail?.(result) : undefined}
      onKeyDown={
        actions.onOpenDetail
          ? (event) => {
              if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                actions.onOpenDetail?.(result);
              }
            }
          : undefined
      }
    >
      <div className="flex items-start gap-4">
        <div className="w-12 h-12 rounded-lg flex items-center justify-center flex-shrink-0 ds-resource-api-icon">
          <Code className="w-6 h-6 text-black" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="mb-2 grid grid-cols-[minmax(0,1fr)_auto] items-start gap-3">
            <div className="min-w-0">
              <h3 className="text-lg font-semibold text-foreground mb-1 break-words leading-snug">{result.name}</h3>
              <div className="flex items-center gap-3 text-sm text-muted-foreground flex-wrap">
                <span>출처: {renderMetaValue(result.provider, '정보 없음')}</span>
              </div>
            </div>
            <div className="flex items-center gap-2 self-start whitespace-nowrap pl-2">
              <button
                type="button"
                onClick={(event) => {
                  event.stopPropagation();
                  actions.onToggleBookmark?.(result);
                }}
                onKeyDown={(event) => {
                  event.stopPropagation();
                  if (event.key === ' ') {
                    event.preventDefault();
                  }
                }}
                disabled={!actions.canBookmark}
                className="rounded-md p-2.5 cursor-pointer disabled:cursor-pointer disabled:opacity-40"
                aria-label={bookmarked ? '북마크 해제' : '북마크 추가'}
                title={bookmarked ? '북마크 해제' : '북마크 추가'}
              >
                <Bookmark className={`h-5 w-5 ${bookmarked ? 'fill-[#4f76df] text-[#4f76df]' : 'text-muted-foreground'}`} />
              </button>
            </div>
          </div>

          <div className={`mt-4 grid grid-cols-2 gap-4 ${result.rank ? 'md:grid-cols-5' : 'md:grid-cols-4'}`}>
            <div className="flex flex-col items-start text-left">
              <p className="mb-1 text-xs text-muted-foreground">타입</p>
              <p className="text-sm font-semibold text-foreground">Open API</p>
            </div>
            <div className="flex flex-col items-start text-left">
              <p className="mb-1 text-xs text-muted-foreground">업데이트</p>
              <p className="text-sm font-semibold text-foreground">{renderDateValue(result.updatedAt)}</p>
            </div>
            <div className="flex flex-col items-center text-center">
              <p className="mb-1 text-xs text-muted-foreground">비용</p>
              <p className="text-sm font-semibold text-foreground">{result.isFree ? '무료' : '유료/미상'}</p>
            </div>
            <div className="flex flex-col items-center text-center">
              <p className="mb-1 text-xs text-muted-foreground">점수</p>
              <div className="inline-flex items-center whitespace-nowrap rounded-full border border-blue-200 bg-blue-50 px-2.5 py-1 text-sm font-semibold text-blue-700 shadow-sm">
                {renderScoreBadge(result.score)}
              </div>
            </div>
            {result.rank ? (
              <div className="flex flex-col items-center text-center">
                <p className="mb-1 text-xs text-muted-foreground">추천 순위</p>
                <div className="inline-flex items-center whitespace-nowrap rounded-full border border-amber-200 bg-amber-50 px-2.5 py-1 text-sm font-semibold text-amber-700 shadow-sm">
                  {result.rank}위
                </div>
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  );
}
