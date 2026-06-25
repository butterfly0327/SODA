import { chatApi } from '@/api/chatApi';
import { chatResourceApi } from '@/api/chatResourceApi';
import { recommendationApi } from '@/api/recommendationApi';
import type {
  ConversationDetail,
  RecommendationDetail,
  SendChatMessageAcceptedResponse,
  SendChatMessageResponse,
} from '@/api/types';
import {
  mapChatBatchCardToResultCard,
  mapChatBatchItem,
  normalizeRecommendationScore,
} from '@/app/lib/chatResourceAdapter';
import type { Conversation, Message } from '@/stores/chatStore';
import type { ResultCard, SearchResultData } from '@/types/recommendation';

type RecommendationType = 'dataset' | 'api';

const USER_VISIBLE_CHAT_FAILURE_MESSAGE = '문제가 발생하여 답변 생성에 실패하였습니다. 다시 시도해주세요';

interface RecommendationSummary {
  id?: number;
  datasetId?: number;
  openApiId?: number;
  openapiId?: number;
  score?: number | string;
  recommendationScore?: number | string;
  suitabilityScore?: number | string;
  title?: string;
  datasetTitle?: string;
  openApiTitle?: string;
  openapiTitle?: string;
  name?: string;
  datasetName?: string;
  openApiName?: string;
  openapiName?: string;
}

interface ChatSendResult {
  conversationId: string;
  status: 'success' | 'failed';
  hydratedConversation?: Conversation;
  content?: string;
  searchResult?: SearchResultData;
}

function isLegacySendMessageResponse(
  response: SendChatMessageAcceptedResponse | SendChatMessageResponse,
): response is SendChatMessageResponse {
  return 'assistantMessage' in response;
}

function isTerminalRecommendationStatus(status: string) {
  return status === 'SUCCESS' || status === 'FAILED';
}

function wait(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function normalizeRecommendationItems(raw: RecommendationSummary[] | null | undefined): RecommendationSummary[] {
  if (!Array.isArray(raw)) {
    return [];
  }
  return raw.filter((item) => typeof item === 'object' && item !== null);
}

function toNumber(value: unknown): number | undefined {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === 'string' && value.trim() !== '') {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : undefined;
  }
  return undefined;
}

function resolveRecommendationId(item: RecommendationSummary, type: RecommendationType): number | undefined {
  const legacyId = toNumber(item.id);
  if (legacyId !== undefined) {
    return legacyId;
  }

  if (type === 'dataset') {
    return toNumber(item.datasetId);
  }

  return toNumber(item.openApiId) ?? toNumber(item.openapiId);
}

function resolveRecommendationName(item: RecommendationSummary): string | undefined {
  const candidates = [
    item.title,
    item.name,
    item.datasetTitle,
    item.openApiTitle,
    item.openapiTitle,
    item.datasetName,
    item.openApiName,
    item.openapiName,
  ];

  return candidates.find((candidate) => typeof candidate === 'string' && candidate.trim() !== '');
}

function resolveRecommendationScore(item: RecommendationSummary) {
  const candidates = [
    toNumber(item.recommendationScore),
    toNumber(item.suitabilityScore),
    toNumber(item.score),
  ];

  const resolved = candidates.find((candidate) => candidate !== undefined);
  return normalizeRecommendationScore(resolved);
}

function sanitizeCardReason(reason: string | undefined) {
  if (!reason) {
    return undefined;
  }

  const normalized = reason
    .replace(/\r\n/g, '\n')
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .find((line) => !/^(요약 추천|마무리 제안|실무 적용 아키텍처|실행을 위한 구체적 체크리스트)/.test(line));

  if (!normalized) {
    return undefined;
  }

  const collapsed = normalized.replace(/\s+/g, ' ').trim();
  if (collapsed.length <= 160) {
    return collapsed;
  }

  return `${collapsed.slice(0, 157).trimEnd()}...`;
}

function buildFallbackCard(item: RecommendationSummary, type: RecommendationType, reason: string): ResultCard {
  const resolvedId = resolveRecommendationId(item, type);
  const name = resolveRecommendationName(item) ?? '이름 없는 리소스';
  const score = resolveRecommendationScore(item);
  if (type === 'dataset') {
    return {
      id: resolvedId,
      type,
      name,
      score,
      source: '상세 정보 로드 실패',
      reasons: reason ? [reason] : [],
    };
  }
  return {
    id: resolvedId,
    type,
    name,
    score,
    category: '상세 정보 로드 실패',
    reasons: reason ? [reason] : [],
  };
}

async function buildSearchResultData(args: {
  query?: string;
  analysis: string;
  datasetReason?: string;
  openApiReason?: string;
  datasetRecommendations: RecommendationSummary[] | null | undefined;
  openApiRecommendations: RecommendationSummary[] | null | undefined;
}): Promise<SearchResultData> {
  const datasetItems = normalizeRecommendationItems(args.datasetRecommendations);
  const openApiItems = normalizeRecommendationItems(args.openApiRecommendations);
  const datasetCardReason = sanitizeCardReason(args.datasetReason);
  const openApiCardReason = sanitizeCardReason(args.openApiReason);

  const entries = [
    ...datasetItems.map((item) => ({
      item,
      type: 'dataset' as const,
      reason: datasetCardReason ?? '',
    })),
    ...openApiItems.map((item) => ({
      item,
      type: 'api' as const,
      reason: openApiCardReason ?? '',
    })),
  ];

  const rankedEntries = [...entries]
    .map((entry) => ({
      ...entry,
      recommendationScore: resolveRecommendationScore(entry.item),
    }))
    .sort((a, b) => (b.recommendationScore ?? -Infinity) - (a.recommendationScore ?? -Infinity))
    .map((entry, index) => ({
      ...entry,
      rank: index + 1,
    }));

  const rankByKey = new Map<string, number>();
  rankedEntries.forEach((entry) => {
    const resourceId = resolveRecommendationId(entry.item, entry.type);
    if (resourceId !== undefined) {
      rankByKey.set(`${entry.type}:${resourceId}`, entry.rank);
    }
  });

  const requestItems = rankedEntries.flatMap((entry) => {
    const resourceId = resolveRecommendationId(entry.item, entry.type);
    const recommendationScore = entry.recommendationScore;

    if (resourceId === undefined || recommendationScore === undefined) {
      return [];
    }

    return [mapChatBatchItem(entry.type, resourceId, recommendationScore, entry.rank)];
  });

  const cardsByKey = new Map<string, ResultCard>();

  if (requestItems.length > 0) {
    try {
      const response = await chatResourceApi.getCardsBatch(requestItems);
      response.cards.forEach((card) => {
        const mapped = mapChatBatchCardToResultCard(card);
        cardsByKey.set(`${mapped.type}:${mapped.id}`, mapped);
      });
    } catch {
      // fall through to per-item fallback cards
    }
  }

  const results = entries.map(({ item, type, reason }) => {
    const resourceId = resolveRecommendationId(item, type);
    if (resourceId === undefined) {
      return buildFallbackCard(item, type, reason);
    }

    const key = `${type}:${resourceId}`;
    const card = cardsByKey.get(key);
    if (!card) {
      return buildFallbackCard(item, type, reason);
    }

    return {
      ...card,
      rank: rankByKey.get(key),
      reasons: reason ? [reason] : [],
    };
  });

  return {
    searchQuery: args.query,
    totalCandidates: results.length,
    recommendations: results.length,
    analysis: args.analysis,
    results,
  };
}

function toTimestamp(value: string | undefined): number {
  if (!value) {
    return Date.now();
  }
  const timestamp = new Date(value).getTime();
  return Number.isNaN(timestamp) ? Date.now() : timestamp;
}

function mapTurnRole(role: string): Message['role'] | null {
  if (role === 'USER') return 'user';
  if (role === 'ASSISTANT') return 'assistant';
  return null;
}

function buildPendingRecommendationContent(recommendation: RecommendationDetail) {
  switch (recommendation.status) {
    case 'FAILED':
      return USER_VISIBLE_CHAT_FAILURE_MESSAGE;
    case 'SUCCESS':
      return '추천 결과를 동기화하는 중입니다...';
    case 'RUNNING':
      return '추천을 생성하고 있습니다...';
    case 'PENDING':
    default:
      return '추천 요청이 접수되었습니다. 결과를 준비하고 있습니다...';
  }
}

function buildConversationMessages(
  detail: ConversationDetail,
  assistantSearchResults: Map<number, SearchResultData>,
): Message[] {
  const placeholderMessagesByUserTurnId = detail.recommendations
    .filter((recommendation) => recommendation.assistantTurnId === null)
    .reduce<Map<number, Message[]>>((map, recommendation) => {
      const existing = map.get(recommendation.userTurnId) ?? [];
      existing.push({
        id: `recommendation-${recommendation.recommendationId}`,
        role: 'assistant',
        content: buildPendingRecommendationContent(recommendation),
        timestamp: toTimestamp(recommendation.updatedAt),
      });
      map.set(recommendation.userTurnId, existing);
      return map;
    }, new Map());

  const messages: Message[] = [];

  detail.turns.forEach((turn) => {
    const role = mapTurnRole(turn.role);
    if (!role) {
      return;
    }

    messages.push({
      id: String(turn.turnId),
      role,
      content: turn.content,
      timestamp: toTimestamp(turn.createdAt),
      searchResult: role === 'assistant' ? assistantSearchResults.get(turn.turnId) : undefined,
    });

    const placeholders = placeholderMessagesByUserTurnId.get(turn.turnId);
    if (placeholders) {
      messages.push(...placeholders);
    }
  });

  return messages;
}

async function buildAssistantSearchResults(detail: ConversationDetail): Promise<Map<number, SearchResultData>> {
  const entries = await Promise.all(
    detail.recommendations
      .filter((recommendation) => recommendation.assistantTurnId !== null)
      .map(async (recommendation) => {
        const searchResult = await buildSearchResultData({
          analysis: recommendation.mergedReason || '추천 결과를 불러왔습니다.',
          datasetReason: recommendation.datasetReason,
          openApiReason: recommendation.openApiReason,
          datasetRecommendations: recommendation.datasetRecommendations,
          openApiRecommendations: recommendation.openApiRecommendations,
        });
        return [recommendation.assistantTurnId as number, searchResult] as const;
      }),
  );

  return new Map(entries);
}

async function pollRecommendation(
  recommendationId: number,
  options: { intervalMs?: number; maxAttempts?: number } = {},
): Promise<RecommendationDetail> {
  const intervalMs = options.intervalMs ?? 1500;
  const maxAttempts = options.maxAttempts ?? 60;

  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    const recommendation = await recommendationApi.getRecommendation(recommendationId);

    if (isTerminalRecommendationStatus(recommendation.status)) {
      return recommendation;
    }

    await wait(intervalMs);
  }

  throw new Error('추천 결과 조회 시간이 초과되었습니다. 잠시 후 다시 시도해주세요.');
}

async function hydrateConversation(conversationId: string): Promise<Conversation> {
  const detail = await chatApi.getConversationDetail(Number(conversationId));
  const assistantSearchResults = await buildAssistantSearchResults(detail);
  const messages = buildConversationMessages(detail, assistantSearchResults);

  return {
    id: String(detail.conversationId),
    title: detail.title,
    messages,
    createdAt: messages[0]?.timestamp ?? Date.now(),
    updatedAt: messages[messages.length - 1]?.timestamp ?? Date.now(),
    projectId: null,
  };
}

export const chatService = {
  requestMessage: async (request: { conversationId?: string | null; message: string }) => {
    const parsedConversationId = request.conversationId ? Number(request.conversationId) : undefined;
    return chatApi.sendMessage({
      conversationId: parsedConversationId !== undefined && Number.isFinite(parsedConversationId) ? parsedConversationId : undefined,
      message: request.message,
    });
  },

  pollRecommendation,

  refreshConversation: hydrateConversation,

  sendMessage: async (request: { conversationId?: string | null; message: string }): Promise<ChatSendResult> => {
    const response = await chatService.requestMessage(request);

    if (isLegacySendMessageResponse(response)) {
      const searchResult = await buildSearchResultData({
        query: request.message,
        analysis: response.mergedReason || response.assistantMessage || '추천 결과를 찾았습니다.',
        datasetRecommendations: response.datasetRecommendations,
        openApiRecommendations: response.openApiRecommendations,
      });

      return {
        conversationId: String(response.conversationId),
        status: 'success',
        content: response.assistantMessage || '추천 결과를 찾았습니다.',
        searchResult,
      };
    }

    const recommendation = await chatService.pollRecommendation(response.recommendationId);

  if (recommendation.status === 'FAILED') {
    return {
      conversationId: String(response.conversationId),
      status: 'failed',
      content: USER_VISIBLE_CHAT_FAILURE_MESSAGE,
    };
  }

    const hydratedConversation = await chatService.refreshConversation(String(response.conversationId));

    
    return {
      conversationId: String(response.conversationId),
      status: 'success',
      hydratedConversation,
    };
  },

  hydrateConversation,
};
