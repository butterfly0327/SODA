package ssafy.E105.domain.chat.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.TransactionDefinition;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.support.TransactionTemplate;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.web.reactive.function.client.WebClientResponseException;
import ssafy.E105.domain.chat.dto.request.SendChatMessageRequest;
import ssafy.E105.domain.chat.dto.response.*;
import ssafy.E105.domain.chat.entity.*;
import ssafy.E105.domain.chat.repository.*;
import ssafy.E105.global.exception.CustomException;
import ssafy.E105.global.exception.ErrorCode;

import java.util.*;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.Executor;
import java.util.concurrent.RejectedExecutionException;
import java.util.stream.Collectors;

@Service
public class ChatService {

    private static final Logger log = LoggerFactory.getLogger(ChatService.class);
    private static final int MAX_INPUT_MESSAGE_LENGTH = 2000;
    private static final int MAX_HISTORY_TURNS = 10;
    private static final int MAX_HISTORY_ITEM_CONTENT_LENGTH = 1000;
    private static final int MAX_HISTORY_TOTAL_CONTENT_LENGTH = 12000;
    private static final int FINALIZE_FAILURE_RETRY_COUNT = 2;
    private static final String USER_VISIBLE_FAILURE_MESSAGE = "문제가 발생하여 답변 생성에 실패하였습니다. 다시 시도해주세요";

    private final ConversationRepository conversationRepository;
    private final ConversationTurnRepository conversationTurnRepository;
    private final DatasetRecommendationRepository datasetRecommendationRepository;
    private final OpenApiRecommendationRepository openApiRecommendationRepository;
    private final RecommendationRepository recommendationRepository;
    private final WebClient webClient;
    private final ObjectMapper objectMapper;
    private final TransactionTemplate requiresNewTransactionTemplate;
    private final Executor chatRecommendationExecutor;

    @Value("${fastapi.base-url}")
    private String fastApiBaseUrl;

    public ChatService(
            ConversationRepository conversationRepository,
            ConversationTurnRepository conversationTurnRepository,
            DatasetRecommendationRepository datasetRecommendationRepository,
            OpenApiRecommendationRepository openApiRecommendationRepository,
            RecommendationRepository recommendationRepository,
            WebClient webClient,
            ObjectMapper objectMapper,
            PlatformTransactionManager transactionManager,
            @Qualifier("chatRecommendationExecutor") Executor chatRecommendationExecutor
    ) {
        this.conversationRepository = conversationRepository;
        this.conversationTurnRepository = conversationTurnRepository;
        this.datasetRecommendationRepository = datasetRecommendationRepository;
        this.openApiRecommendationRepository = openApiRecommendationRepository;
        this.recommendationRepository = recommendationRepository;
        this.webClient = webClient;
        this.objectMapper = objectMapper;
        this.requiresNewTransactionTemplate = new TransactionTemplate(transactionManager);
        this.requiresNewTransactionTemplate.setPropagationBehavior(TransactionDefinition.PROPAGATION_REQUIRES_NEW);
        this.chatRecommendationExecutor = chatRecommendationExecutor;
    }

    public SendChatMessageAcceptedResponse sendChatMessage(Long userId, SendChatMessageRequest request) {
        String message = validateMessage(request.message());

        ChatPreparation preparation = requiresNewTransactionTemplate.execute(
                status -> prepareChatMessage(userId, request.conversationId(), message)
        );

        if (preparation == null) {
            throw new CustomException(ErrorCode.FASTAPI_SERVER_ERROR);
        }

        try {
            chatRecommendationExecutor.execute(() -> processRecommendationAsync(preparation));
        } catch (RejectedExecutionException e) {
            finalizeFailureWithRetry(
                    preparation,
                    "추천 작업이 큐에 등록되지 않았습니다. 잠시 후 다시 시도해주세요.",
                    "executor_rejected"
            );
            throw new CustomException(ErrorCode.FASTAPI_SERVER_ERROR);
        }

        return new SendChatMessageAcceptedResponse(
                preparation.conversationId(),
                preparation.userTurnId(),
                preparation.recommendationId(),
                RecommendationStatus.PENDING
        );
    }

    @Transactional(readOnly = true)
    public RecommendationStatusResponse getRecommendationStatus(Long userId, Long recommendationId) {
        if (recommendationId == null || recommendationId <= 0) {
            throw new CustomException(ErrorCode.INVALID_INPUT);
        }

        RecommendationEntity recommendation = recommendationRepository.findById(recommendationId)
                .orElseThrow(() -> new CustomException(ErrorCode.RECOMMENDATION_NOT_FOUND));

        ConversationEntity conversation = recommendation.getUserTurn().getConversation();
        if (!Objects.equals(conversation.getUserId(), userId)) {
            throw new CustomException(ErrorCode.RECOMMENDATION_FORBIDDEN);
        }

        DatasetRecommendationEntity datasetRecommendation = recommendation.getDatasetRecommendation();
        OpenApiRecommendationEntity openApiRecommendation = recommendation.getOpenApiRecommendation();

        return new RecommendationStatusResponse(
                recommendation.getId(),
                conversation.getId(),
                recommendation.getUserTurn().getId(),
                recommendation.getAssistantTurn() == null ? null : recommendation.getAssistantTurn().getId(),
                recommendation.getStatus(),
                recommendation.getMergedReasonText(),
                datasetRecommendation.getRecommendedItemsJson(),
                openApiRecommendation.getRecommendedItemsJson(),
                toUserVisibleErrorSummary(recommendation.getStatus(), recommendation.getErrorSummary()),
                recommendation.getUpdatedAt()
        );
    }

    @Transactional(readOnly = true)
    public List<ConversationListItemResponse> getConversationList(Long userId) {
        return conversationRepository.findByUserIdAndDeletedAtIsNullOrderByUpdatedAtDesc(userId)
                .stream()
                .map(c -> new ConversationListItemResponse(c.getId(), c.getTitle(), c.getCreatedAt(), c.getUpdatedAt()))
                .toList();
    }

    @Transactional(readOnly = true)
    public ConversationDetailResponse getConversationDetail(Long userId, Long conversationId) {
        ConversationEntity conversation = getOwnedConversation(userId, conversationId);

        List<ConversationTurnEntity> turns = conversationTurnRepository.findByConversationIdOrderByTurnOrderAsc(conversation.getId());
        List<ConversationTurnResponse> turnResponses = turns.stream()
                .map(t -> new ConversationTurnResponse(
                        t.getId(),
                        t.getTurnOrder(),
                        t.getRole(),
                        t.getContent(),
                        t.getResponseTimeMs(),
                        t.getCreatedAt()
                ))
                .toList();

        List<Long> userTurnIds = turns.stream()
                .filter(t -> t.getRole() == TurnRole.USER)
                .map(ConversationTurnEntity::getId)
                .toList();

        List<RecommendationDetailResponse> recommendationDetails = new ArrayList<>();
        if (!userTurnIds.isEmpty()) {
            List<RecommendationEntity> recommendations = recommendationRepository.findByUserTurnIdIn(userTurnIds);

            Set<Long> datasetIds = recommendations.stream()
                    .map(r -> r.getDatasetRecommendation().getId())
                    .collect(Collectors.toSet());
            Set<Long> openApiIds = recommendations.stream()
                    .map(r -> r.getOpenApiRecommendation().getId())
                    .collect(Collectors.toSet());

            Map<Long, DatasetRecommendationEntity> datasetMap = datasetRecommendationRepository.findByIdIn(datasetIds)
                    .stream()
                    .collect(Collectors.toMap(DatasetRecommendationEntity::getId, d -> d));
            Map<Long, OpenApiRecommendationEntity> openApiMap = openApiRecommendationRepository.findByIdIn(openApiIds)
                    .stream()
                    .collect(Collectors.toMap(OpenApiRecommendationEntity::getId, d -> d));

            recommendationDetails = recommendations.stream()
                    .sorted(Comparator.comparing(r -> r.getUserTurn().getTurnOrder()))
                    .map(r -> {
                        DatasetRecommendationEntity d = datasetMap.get(r.getDatasetRecommendation().getId());
                        OpenApiRecommendationEntity o = openApiMap.get(r.getOpenApiRecommendation().getId());
                        return new RecommendationDetailResponse(
                                r.getId(),
                                r.getUserTurn().getId(),
                                r.getAssistantTurn() == null ? null : r.getAssistantTurn().getId(),
                                r.getStatus(),
                                r.getMergedReasonText(),
                                d == null ? null : d.getReasonText(),
                                o == null ? null : o.getReasonText(),
                                d == null ? JsonNodeFactory.instance.arrayNode() : d.getRecommendedItemsJson(),
                                o == null ? JsonNodeFactory.instance.arrayNode() : o.getRecommendedItemsJson(),
                                toUserVisibleErrorSummary(r.getStatus(), r.getErrorSummary())
                        );
                    })
                    .toList();
        }

        return new ConversationDetailResponse(
                conversation.getId(),
                conversation.getTitle(),
                turnResponses,
                recommendationDetails
        );
    }

    @Transactional
    public void deleteConversation(Long userId, Long conversationId) {
        ConversationEntity conversation = getOwnedConversation(userId, conversationId);
        conversation.markDeleted();
        conversationRepository.save(conversation);
    }

    private ChatPreparation prepareChatMessage(Long userId, Long conversationId, String message) {
        ConversationEntity conversation = resolveConversation(userId, conversationId, message);
        List<ConversationTurnEntity> previousTurns = conversationTurnRepository.findByConversationIdOrderByTurnOrderAsc(conversation.getId());
        int lastTurnOrder = previousTurns.isEmpty() ? 0 : previousTurns.get(previousTurns.size() - 1).getTurnOrder();
        int nextUserTurnOrder = lastTurnOrder % 2 == 0 ? lastTurnOrder + 1 : lastTurnOrder + 2;

        ConversationTurnEntity userTurn = conversationTurnRepository.save(
                ConversationTurnEntity.of(conversation, nextUserTurnOrder, message, TurnRole.USER, null)
        );

        DatasetRecommendationEntity datasetRecommendation = datasetRecommendationRepository.save(
                DatasetRecommendationEntity.createPending(userTurn, null)
        );
        OpenApiRecommendationEntity openApiRecommendation = openApiRecommendationRepository.save(
                OpenApiRecommendationEntity.createPending(userTurn, null)
        );
        RecommendationEntity recommendation = recommendationRepository.save(
                RecommendationEntity.createPending(userTurn, datasetRecommendation, openApiRecommendation, null)
        );

        if (conversation.getTitle() == null || conversation.getTitle().isBlank()) {
            conversation.updateTitle(makeConversationTitle(message));
        } else {
            conversation.touch();
        }
        conversationRepository.save(conversation);

        List<Map<String, String>> history = buildHistory(previousTurns, userTurn);

        return new ChatPreparation(
                conversation.getId(),
                userTurn.getId(),
                datasetRecommendation.getId(),
                openApiRecommendation.getId(),
                recommendation.getId(),
                userId,
                message,
                history,
                System.currentTimeMillis()
        );
    }

    private void processRecommendationAsync(ChatPreparation preparation) {
        try {
            requiresNewTransactionTemplate.execute(status -> {
                markRecommendationRunning(preparation);
                return null;
            });

            RecommendationMode mode = inferRecommendationModeWithLlm(
                    preparation.message(),
                    preparation.history()
            );

            ExternalRecommendation datasetRecommendation;
            ExternalRecommendation openApiRecommendation;
            ExternalMergeResult mergeResult = null;

            if (mode == RecommendationMode.CHAT_ONLY) {
                datasetRecommendation = buildSkippedRecommendation(
                        preparation.datasetRecommendationId(),
                        ""
                );
                openApiRecommendation = buildSkippedRecommendation(
                        preparation.openApiRecommendationId(),
                        ""
                );
                ExternalChatAnswer chatAnswer = callChatAnswerApi(
                        preparation.conversationId(),
                        preparation.userId(),
                        preparation.userTurnId(),
                        preparation.message(),
                        preparation.history()
                );
                mergeResult = new ExternalMergeResult(
                        preparation.recommendationId(),
                        chatAnswer.answerText(),
                        chatAnswer.llmModel()
                );
            } else {
                if (mode == RecommendationMode.BOTH) {
                    ParallelRecommendationResult parallelResult = callRecommendationsInParallel(preparation);
                    datasetRecommendation = parallelResult.datasetRecommendation();
                    openApiRecommendation = parallelResult.openApiRecommendation();
                } else {
                    if (mode == RecommendationMode.OPENAPI_ONLY) {
                        datasetRecommendation = buildSkippedRecommendation(
                                preparation.datasetRecommendationId(),
                                ""
                        );
                    } else {
                        datasetRecommendation = callDatasetRecommendationApi(
                                preparation.conversationId(),
                                preparation.userId(),
                                preparation.userTurnId(),
                                preparation.datasetRecommendationId(),
                                preparation.message(),
                                preparation.history()
                        );
                    }

                    if (mode == RecommendationMode.DATASET_ONLY) {
                        openApiRecommendation = buildSkippedRecommendation(
                                preparation.openApiRecommendationId(),
                                ""
                        );
                    } else {
                        openApiRecommendation = callOpenApiRecommendationApi(
                                preparation.conversationId(),
                                preparation.userId(),
                                preparation.userTurnId(),
                                preparation.openApiRecommendationId(),
                                preparation.message(),
                                preparation.history()
                        );
                    }
                }

                if (mode == RecommendationMode.BOTH) {
                    boolean datasetFailed = datasetRecommendation.status() == RecommendationStatus.FAILED;
                    boolean openApiFailed = openApiRecommendation.status() == RecommendationStatus.FAILED;

                    if (datasetFailed && openApiFailed) {
                        String combinedErrorSummary = buildCombinedFailureSummary(datasetRecommendation, openApiRecommendation);
                        ExternalRecommendation finalDatasetRecommendation = datasetRecommendation;
                        ExternalRecommendation finalOpenApiRecommendation = openApiRecommendation;
                        requiresNewTransactionTemplate.execute(status -> {
                            finalizeChatDualFailure(
                                    preparation,
                                    finalDatasetRecommendation,
                                    finalOpenApiRecommendation,
                                    combinedErrorSummary
                            );
                            return null;
                        });
                        return;
                    }

                    try {
                        mergeResult = callMergeReasonApi(
                                preparation.conversationId(),
                                preparation.userId(),
                                preparation.userTurnId(),
                                preparation.recommendationId(),
                                preparation.message(),
                                datasetRecommendation,
                                openApiRecommendation,
                                preparation.history()
                        );
                    } catch (Exception mergeException) {
                        String mergeSummary = resolveErrorSummary(mergeException);
                        log.warn(
                                "추천 병합 단계 실패. recommendationId={}, userTurnId={}, reason={}",
                                preparation.recommendationId(),
                                preparation.userTurnId(),
                                mergeSummary
                        );
                        mergeResult = null;
                    }
                }
            }

            ensureRecommendationIdMatch(preparation.datasetRecommendationId(), datasetRecommendation.recommendationId());
            ensureRecommendationIdMatch(preparation.openApiRecommendationId(), openApiRecommendation.recommendationId());
            if (mergeResult != null) {
                ensureRecommendationIdMatch(preparation.recommendationId(), mergeResult.recommendationId());
            }

            ExternalRecommendation finalDatasetRecommendation = datasetRecommendation;
            ExternalRecommendation finalOpenApiRecommendation = openApiRecommendation;
            ExternalMergeResult finalMergeResult = mergeResult;

            requiresNewTransactionTemplate.execute(status -> {
                finalizeChatSuccess(preparation, finalDatasetRecommendation, finalOpenApiRecommendation, finalMergeResult);
                return null;
            });
        } catch (Exception e) {
            String errorSummary = resolveErrorSummary(e);
            finalizeFailureWithRetry(preparation, errorSummary, "async_exception");
        }
    }

    private void finalizeChatSuccess(
            ChatPreparation preparation,
            ExternalRecommendation datasetResult,
            ExternalRecommendation openApiResult,
            ExternalMergeResult mergeResult
    ) {
        ConversationEntity conversation = getOwnedConversation(preparation.userId(), preparation.conversationId());
        ConversationTurnEntity userTurn = conversationTurnRepository.findById(preparation.userTurnId())
                .orElseThrow(() -> new CustomException(ErrorCode.CONVERSATION_NOT_FOUND));

        DatasetRecommendationEntity datasetRecommendation = datasetRecommendationRepository.findById(preparation.datasetRecommendationId())
                .orElseThrow(() -> new CustomException(ErrorCode.FASTAPI_SERVER_ERROR));
        OpenApiRecommendationEntity openApiRecommendation = openApiRecommendationRepository.findById(preparation.openApiRecommendationId())
                .orElseThrow(() -> new CustomException(ErrorCode.FASTAPI_SERVER_ERROR));
        RecommendationEntity recommendation = recommendationRepository.findById(preparation.recommendationId())
                .orElseThrow(() -> new CustomException(ErrorCode.FASTAPI_SERVER_ERROR));

        applyDatasetResult(datasetRecommendation, datasetResult);
        applyOpenApiResult(openApiRecommendation, openApiResult);
        String finalReasonRaw = mergeResult != null
                ? mergeResult.mergedReasonText()
                : resolveAssistantMessage(null, datasetResult.reasonText(), openApiResult.reasonText());
        String finalReason = sanitizeIdentifierTokens(finalReasonRaw);
        String finalLlmModel = mergeResult != null
                ? mergeResult.llmModel()
                : resolveSingleModeModel(datasetResult.llmModel(), openApiResult.llmModel());
        recommendation.markSuccess(finalReason, finalLlmModel);

        String assistantMessage = resolveAssistantMessage(
                finalReason,
                datasetResult.reasonText(),
                openApiResult.reasonText()
        );
        int responseTimeMs = Math.toIntExact(Math.max(System.currentTimeMillis() - preparation.startMs(), 0L));

        int assistantTurnOrder = userTurn.getTurnOrder() + 1;

        ConversationTurnEntity assistantTurn = conversationTurnRepository.save(
                ConversationTurnEntity.of(conversation, assistantTurnOrder, assistantMessage, TurnRole.ASSISTANT, responseTimeMs)
        );

        recommendation.linkAssistantTurn(assistantTurn);

        datasetRecommendationRepository.save(datasetRecommendation);
        openApiRecommendationRepository.save(openApiRecommendation);
        recommendationRepository.save(recommendation);

        conversation.touch();
        if (conversation.getTitle() == null || conversation.getTitle().isBlank()) {
            conversation.updateTitle(makeConversationTitle(preparation.message()));
        }
        conversationRepository.save(conversation);
    }

    private void finalizeChatFailure(ChatPreparation preparation, String errorSummary) {
        datasetRecommendationRepository.findById(preparation.datasetRecommendationId()).ifPresent(entity -> {
            if (entity.getStatus() != RecommendationStatus.SUCCESS) {
                entity.markFailed(errorSummary);
                datasetRecommendationRepository.save(entity);
            }
        });

        openApiRecommendationRepository.findById(preparation.openApiRecommendationId()).ifPresent(entity -> {
            if (entity.getStatus() != RecommendationStatus.SUCCESS) {
                entity.markFailed(errorSummary);
                openApiRecommendationRepository.save(entity);
            }
        });

        recommendationRepository.findById(preparation.recommendationId()).ifPresent(entity -> {
            entity.markFailed(errorSummary);
            recommendationRepository.save(entity);
        });

        conversationRepository.findByIdAndDeletedAtIsNull(preparation.conversationId()).ifPresent(conversation -> {
            if (Objects.equals(conversation.getUserId(), preparation.userId())) {
                conversation.touch();
                conversationRepository.save(conversation);
            }
        });
    }

    private void markRecommendationRunning(ChatPreparation preparation) {
        datasetRecommendationRepository.findById(preparation.datasetRecommendationId()).ifPresent(entity -> {
            entity.markRunning(null);
            datasetRecommendationRepository.save(entity);
        });

        openApiRecommendationRepository.findById(preparation.openApiRecommendationId()).ifPresent(entity -> {
            entity.markRunning(null);
            openApiRecommendationRepository.save(entity);
        });

        recommendationRepository.findById(preparation.recommendationId()).ifPresent(entity -> {
            entity.markRunning(null);
            recommendationRepository.save(entity);
        });
    }

    private ConversationEntity resolveConversation(Long userId, Long conversationId, String firstMessage) {
        if (conversationId == null) {
            ConversationEntity conversation = ConversationEntity.create(userId, makeConversationTitle(firstMessage));
            return conversationRepository.save(conversation);
        }

        if (conversationId <= 0) {
            throw new CustomException(ErrorCode.INVALID_CONVERSATION_ID);
        }

        return getOwnedConversationForUpdate(userId, conversationId);
    }

    private ConversationEntity getOwnedConversation(Long userId, Long conversationId) {
        ConversationEntity conversation = conversationRepository.findByIdAndDeletedAtIsNull(conversationId)
                .orElseThrow(() -> new CustomException(ErrorCode.CONVERSATION_NOT_FOUND));

        if (!Objects.equals(conversation.getUserId(), userId)) {
            throw new CustomException(ErrorCode.CONVERSATION_FORBIDDEN);
        }

        return conversation;
    }

    private ConversationEntity getOwnedConversationForUpdate(Long userId, Long conversationId) {
        ConversationEntity conversation = conversationRepository.findByIdAndDeletedAtIsNullForUpdate(conversationId)
                .orElseThrow(() -> new CustomException(ErrorCode.CONVERSATION_NOT_FOUND));

        if (!Objects.equals(conversation.getUserId(), userId)) {
            throw new CustomException(ErrorCode.CONVERSATION_FORBIDDEN);
        }

        return conversation;
    }

    private String validateMessage(String message) {
        if (message == null || message.isBlank()) {
            throw new CustomException(ErrorCode.INVALID_CHAT_MESSAGE);
        }

        String trimmed = message.trim();
        if (trimmed.length() > MAX_INPUT_MESSAGE_LENGTH) {
            throw new CustomException(ErrorCode.INVALID_CHAT_MESSAGE);
        }

        return trimmed;
    }

    private String makeConversationTitle(String message) {
        int maxLength = 30;
        if (message.length() <= maxLength) {
            return message;
        }
        return message.substring(0, maxLength) + "...";
    }

    private List<Map<String, String>> buildHistory(List<ConversationTurnEntity> previousTurns, ConversationTurnEntity currentUserTurn) {
        List<Map<String, String>> reverseOrderedHistory = new ArrayList<>();
        int remainingChars = MAX_HISTORY_TOTAL_CONTENT_LENGTH;
        int previousLimit = Math.max(MAX_HISTORY_TURNS - 1, 0);
        int startIndex = Math.max(previousTurns.size() - previousLimit, 0);

        remainingChars = appendHistoryEntry(
                reverseOrderedHistory,
                currentUserTurn.getRole(),
                currentUserTurn.getContent(),
                remainingChars,
                true
        );

        for (int i = previousTurns.size() - 1; i >= startIndex; i--) {
            if (remainingChars <= 0) {
                break;
            }

            ConversationTurnEntity turn = previousTurns.get(i);
            remainingChars = appendHistoryEntry(reverseOrderedHistory, turn.getRole(), turn.getContent(), remainingChars, false);
        }

        Collections.reverse(reverseOrderedHistory);
        return reverseOrderedHistory;
    }

    private int appendHistoryEntry(
            List<Map<String, String>> history,
            TurnRole role,
            String rawContent,
            int remainingChars,
            boolean forceInclude
    ) {
        if (remainingChars <= 0 && !forceInclude) {
            return 0;
        }

        String content = rawContent == null ? "" : rawContent;
        if (content.length() > MAX_HISTORY_ITEM_CONTENT_LENGTH) {
            content = content.substring(0, MAX_HISTORY_ITEM_CONTENT_LENGTH);
        }

        if (remainingChars <= 0) {
            content = "";
        } else if (content.length() > remainingChars) {
            content = content.substring(0, remainingChars);
        }

        if (!forceInclude && content.isBlank()) {
            return remainingChars;
        }

        history.add(Map.of(
                "role", role.name(),
                "content", content
        ));

        return Math.max(remainingChars - content.length(), 0);
    }

    private RecommendationMode inferRecommendationModeWithLlm(String message, List<Map<String, String>> history) {
        try {
            JsonNode root = postFastApi("/infer-recommendation-mode", Map.of(
                    "message", message,
                    "history", history
            ));
            JsonNode data = root.path("data").isMissingNode() ? root : root.path("data");
            RecommendationMode parsed = parseRecommendationMode(readText(data, "mode"));
            if (parsed != null) {
                return parsed;
            }
            log.warn("추천 모드 LLM 응답이 비정상입니다. CHAT_ONLY로 대체합니다.");
        } catch (Exception e) {
            log.warn("추천 모드 LLM 판별 실패. CHAT_ONLY로 대체합니다. reason={}", e.getMessage());
        }

        return RecommendationMode.CHAT_ONLY;
    }

    private RecommendationMode parseRecommendationMode(String rawMode) {
        if (rawMode == null || rawMode.isBlank()) {
            return null;
        }

        String normalized = rawMode.trim().toUpperCase(Locale.ROOT);
        return switch (normalized) {
            case "CHAT_ONLY" -> RecommendationMode.CHAT_ONLY;
            case "DATASET_ONLY" -> RecommendationMode.DATASET_ONLY;
            case "OPENAPI_ONLY" -> RecommendationMode.OPENAPI_ONLY;
            case "BOTH" -> RecommendationMode.BOTH;
            default -> null;
        };
    }

    private ExternalRecommendation buildSkippedRecommendation(Long recommendationId, String reasonText) {
        return new ExternalRecommendation(
                recommendationId,
                reasonText,
                JsonNodeFactory.instance.arrayNode(),
                "skipped",
                RecommendationStatus.SUCCESS,
                null
        );
    }

    private void finalizeChatDualFailure(
            ChatPreparation preparation,
            ExternalRecommendation datasetResult,
            ExternalRecommendation openApiResult,
            String combinedErrorSummary
    ) {
        datasetRecommendationRepository.findById(preparation.datasetRecommendationId()).ifPresent(entity -> {
            if (entity.getStatus() != RecommendationStatus.SUCCESS) {
                entity.markFailed(
                        datasetResult.errorSummary() == null || datasetResult.errorSummary().isBlank()
                                ? combinedErrorSummary
                                : datasetResult.errorSummary()
                );
                datasetRecommendationRepository.save(entity);
            }
        });

        openApiRecommendationRepository.findById(preparation.openApiRecommendationId()).ifPresent(entity -> {
            if (entity.getStatus() != RecommendationStatus.SUCCESS) {
                entity.markFailed(
                        openApiResult.errorSummary() == null || openApiResult.errorSummary().isBlank()
                                ? combinedErrorSummary
                                : openApiResult.errorSummary()
                );
                openApiRecommendationRepository.save(entity);
            }
        });

        recommendationRepository.findById(preparation.recommendationId()).ifPresent(entity -> {
            entity.markFailed(combinedErrorSummary);
            recommendationRepository.save(entity);
        });

        conversationRepository.findByIdAndDeletedAtIsNull(preparation.conversationId()).ifPresent(conversation -> {
            if (Objects.equals(conversation.getUserId(), preparation.userId())) {
                conversation.touch();
                conversationRepository.save(conversation);
            }
        });
    }

    private ExternalRecommendation buildFailedRecommendation(Long recommendationId, String reasonText, String errorSummary) {
        return new ExternalRecommendation(
                recommendationId,
                reasonText,
                JsonNodeFactory.instance.arrayNode(),
                "failed",
                RecommendationStatus.FAILED,
                errorSummary
        );
    }

    private ExternalChatAnswer callChatAnswerApi(
            Long conversationId,
            Long userId,
            Long userTurnId,
            String message,
            List<Map<String, String>> history
    ) {
        JsonNode root = postFastApi("/chat-answer", Map.of(
                "conversationId", conversationId,
                "userId", userId,
                "userTurnId", userTurnId,
                "message", message,
                "history", history
        ));
        JsonNode data = root.path("data").isMissingNode() ? root : root.path("data");
        String answerText = sanitizeIdentifierTokens(readText(data, "answer", "assistantMessage", "reasonText"));
        if (answerText == null || answerText.isBlank()) {
            answerText = "요청하신 내용을 기반으로 답변을 생성했습니다.";
        }
        String llmModel = readText(data, "llmModel", "model");
        return new ExternalChatAnswer(answerText, llmModel);
    }

    private String resolveSingleModeModel(String datasetModel, String openApiModel) {
        if (datasetModel != null && !datasetModel.isBlank() && !Objects.equals(datasetModel, "skipped")) {
            return datasetModel;
        }
        if (openApiModel != null && !openApiModel.isBlank() && !Objects.equals(openApiModel, "skipped")) {
            return openApiModel;
        }
        return null;
    }

    private void finalizeFailureWithRetry(ChatPreparation preparation, String errorSummary, String trigger) {
        for (int attempt = 1; attempt <= FINALIZE_FAILURE_RETRY_COUNT; attempt++) {
            try {
                requiresNewTransactionTemplate.execute(status -> {
                    finalizeChatFailure(preparation, errorSummary);
                    return null;
                });

                if (attempt > 1) {
                    log.info(
                            "추천 실패 상태 저장 재시도 성공. trigger={}, recommendationId={}, attempt={}",
                            trigger,
                            preparation.recommendationId(),
                            attempt
                    );
                }
                return;
            } catch (Exception finalizeError) {
                log.warn(
                        "추천 실패 상태 저장 재시도 실패. trigger={}, recommendationId={}, attempt={}/{}, reason={}",
                        trigger,
                        preparation.recommendationId(),
                        attempt,
                        FINALIZE_FAILURE_RETRY_COUNT,
                        finalizeError.getMessage(),
                        finalizeError
                );
            }
        }

        log.error(
                "추천 실패 상태 저장 최종 실패. trigger={}, recommendationId={}",
                trigger,
                preparation.recommendationId()
        );
    }

    private ParallelRecommendationResult callRecommendationsInParallel(ChatPreparation preparation) {
        try {
            CompletableFuture<ExternalRecommendation> datasetFuture = CompletableFuture.supplyAsync(
                    () -> callDatasetRecommendationApiSafely(preparation),
                    chatRecommendationExecutor
            );
            CompletableFuture<ExternalRecommendation> openApiFuture = CompletableFuture.supplyAsync(
                    () -> callOpenApiRecommendationApiSafely(preparation),
                    chatRecommendationExecutor
            );
            return new ParallelRecommendationResult(datasetFuture.join(), openApiFuture.join());
        } catch (RejectedExecutionException queueError) {
            log.warn(
                    "병렬 추천 작업 큐 등록 실패. 순차 처리로 대체합니다. recommendationId={}, userTurnId={}, reason={}",
                    preparation.recommendationId(),
                    preparation.userTurnId(),
                    queueError.getMessage()
            );
            return new ParallelRecommendationResult(
                    callDatasetRecommendationApiSafely(preparation),
                    callOpenApiRecommendationApiSafely(preparation)
            );
        }
    }

    private ExternalRecommendation callDatasetRecommendationApiSafely(ChatPreparation preparation) {
        try {
            return callDatasetRecommendationApi(
                    preparation.conversationId(),
                    preparation.userId(),
                    preparation.userTurnId(),
                    preparation.datasetRecommendationId(),
                    preparation.message(),
                    preparation.history()
            );
        } catch (Exception e) {
            String errorSummary = resolveErrorSummary(e);
            log.warn(
                    "데이터셋 추천 단계 실패. recommendationId={}, userTurnId={}, reason={}",
                    preparation.recommendationId(),
                    preparation.userTurnId(),
                    errorSummary
            );
            return buildFailedRecommendation(
                    preparation.datasetRecommendationId(),
                    "",
                    errorSummary
            );
        }
    }

    private ExternalRecommendation callOpenApiRecommendationApiSafely(ChatPreparation preparation) {
        try {
            return callOpenApiRecommendationApi(
                    preparation.conversationId(),
                    preparation.userId(),
                    preparation.userTurnId(),
                    preparation.openApiRecommendationId(),
                    preparation.message(),
                    preparation.history()
            );
        } catch (Exception e) {
            String errorSummary = resolveErrorSummary(e);
            log.warn(
                    "OpenAPI 추천 단계 실패. recommendationId={}, userTurnId={}, reason={}",
                    preparation.recommendationId(),
                    preparation.userTurnId(),
                    errorSummary
            );
            return buildFailedRecommendation(
                    preparation.openApiRecommendationId(),
                    "",
                    errorSummary
            );
        }
    }

    private ExternalRecommendation callDatasetRecommendationApi(
            Long conversationId,
            Long userId,
            Long userTurnId,
            Long datasetRecommendationId,
            String message,
            List<Map<String, String>> history
    ) {
        JsonNode root = postFastApi("/recommend-datasets", Map.of(
                "conversationId", conversationId,
                "userId", userId,
                "userTurnId", userTurnId,
                "datasetRecommendationId", datasetRecommendationId,
                "message", message,
                "history", history
        ));
        return parseExternalRecommendation(root, true);
    }

    private ExternalRecommendation callOpenApiRecommendationApi(
            Long conversationId,
            Long userId,
            Long userTurnId,
            Long openApiRecommendationId,
            String message,
            List<Map<String, String>> history
    ) {
        JsonNode root = postFastApi("/recommend-open-apis", Map.of(
                "conversationId", conversationId,
                "userId", userId,
                "userTurnId", userTurnId,
                "openapiRecommendationId", openApiRecommendationId,
                "message", message,
                "history", history
        ));
        return parseExternalRecommendation(root, false);
    }

    private ExternalMergeResult callMergeReasonApi(
            Long conversationId,
            Long userId,
            Long userTurnId,
            Long recommendationId,
            String message,
            ExternalRecommendation dataset,
            ExternalRecommendation openApi,
            List<Map<String, String>> history
    ) {
        JsonNode root = postFastApi("/merge-recommendation-reason", Map.of(
                "conversationId", conversationId,
                "userId", userId,
                "userTurnId", userTurnId,
                "recommendationId", recommendationId,
                "message", message,
                "history", history,
                "datasetRecommendationId", dataset.recommendationId(),
                "openapiRecommendationId", openApi.recommendationId(),
                "datasetReason", dataset.reasonText(),
                "openapiReason", openApi.reasonText()
        ));

        JsonNode data = root.path("data").isMissingNode() ? root : root.path("data");
        Long returnedRecommendationId = readLong(data, "recommendationId", "id");
        String mergedReasonText = readText(data, "mergedReasonText", "reasonText", "assistantMessage");
        String llmModel = readText(data, "llmModel", "model");

        return new ExternalMergeResult(returnedRecommendationId, mergedReasonText, llmModel);
    }

    private JsonNode postFastApi(String path, Map<String, Object> body) {
        try {
            JsonNode node = webClient.post()
                    .uri(fastApiBaseUrl + path)
                    .contentType(MediaType.APPLICATION_JSON)
                    .bodyValue(body)
                    .retrieve()
                    .bodyToMono(JsonNode.class)
                    .block();
            return node == null ? objectMapper.createObjectNode() : node;
        } catch (WebClientResponseException e) {
            String errorSummary = buildFastApiErrorSummary(
                    path,
                    e.getRawStatusCode(),
                    e.getResponseBodyAsString(),
                    e.getMessage()
            );
            throw new RuntimeException(errorSummary, e);
        } catch (Exception e) {
            throw new RuntimeException(
                    "추천 서버 호출 실패(path=" + path + "): " + sanitizeErrorText(e.getMessage()),
                    e
            );
        }
    }

    private ExternalRecommendation parseExternalRecommendation(JsonNode root, boolean dataset) {
        JsonNode data = root.path("data").isMissingNode() ? root : root.path("data");

        Long recommendationId = dataset
                ? readLong(data, "datasetRecommendationId", "recommendationId", "id")
                : readLong(data, "openapiRecommendationId", "recommendationId", "id");
        String reasonText = sanitizeIdentifierTokens(readText(data, "reasonText", "reason"));
        String llmModel = readText(data, "llmModel", "model");
        JsonNode items = readJson(data, "recommendedItems", "recommendedItemsJson", "items");

        return new ExternalRecommendation(
                recommendationId,
                reasonText,
                items,
                llmModel,
                RecommendationStatus.SUCCESS,
                null
        );
    }

    private String resolveAssistantMessage(String mergedReason, String datasetReason, String openApiReason) {
        String sanitizedMerged = sanitizeIdentifierTokens(mergedReason);
        String sanitizedDataset = sanitizeIdentifierTokens(datasetReason);
        String sanitizedOpenApi = sanitizeIdentifierTokens(openApiReason);

        if (sanitizedMerged != null && !sanitizedMerged.isBlank()) {
            return sanitizedMerged;
        }
        if (sanitizedDataset != null && !sanitizedDataset.isBlank() && sanitizedOpenApi != null && !sanitizedOpenApi.isBlank()) {
            return sanitizedDataset + "\n\n" + sanitizedOpenApi;
        }
        if (sanitizedDataset != null && !sanitizedDataset.isBlank()) {
            return sanitizedDataset;
        }
        if (sanitizedOpenApi != null && !sanitizedOpenApi.isBlank()) {
            return sanitizedOpenApi;
        }
        return "추천 결과를 생성했습니다.";
    }

    private String sanitizeIdentifierTokens(String text) {
        if (text == null || text.isBlank()) {
            return text;
        }
        String sanitized = text
                .replace("\r\n", "\n")
                .replaceAll("(?i)\\b(?:dataset|openapi)[_\\s-]*id\\s*[=:]\\s*\\d+\\b", "")
                .replaceAll("(?i)\\b(?:dataset|openapi)[_\\s-]*id\\s+\\d+\\b", "")
                .replaceAll("[ \\t]{2,}", " ")
                .replaceAll("\\n[ \\t]+", "\n")
                .replaceAll("[ \\t]+\\n", "\n")
                .replaceAll("\\n{3,}", "\\n\\n")
                .trim();
        return formatChatParagraphs(sanitized);
    }

    private String formatChatParagraphs(String text) {
        if (text == null || text.isBlank()) {
            return text;
        }

        String normalized = text.replaceAll("\\n{3,}", "\\n\\n").trim();
        if (normalized.matches("(?s).*(?m)^(?:#{1,6}\\s+|[-*+]\\s+|\\d+[.)]\\s+).*$")) {
            return normalized;
        }
        String[] paragraphs = normalized.split("\\n\\n");
        List<String> compactParagraphs = Arrays.stream(paragraphs)
                .map(String::trim)
                .filter(p -> !p.isBlank())
                .toList();
        if (compactParagraphs.size() >= 2) {
            return String.join("\n\n", compactParagraphs);
        }

        List<String> sentences = splitSentences(normalized);
        if (sentences.size() <= 2) {
            if (normalized.length() > 220) {
                int firstSentenceBoundary = findFirstSentenceBoundary(normalized);
                if (firstSentenceBoundary > 20 && firstSentenceBoundary < normalized.length() - 1) {
                    String first = normalized.substring(0, firstSentenceBoundary).trim();
                    String rest = normalized.substring(firstSentenceBoundary).trim();
                    if (!first.isBlank() && !rest.isBlank()) {
                        return first + "\n\n" + rest;
                    }
                }
            }
            return normalized;
        }

        List<String> chunks = new ArrayList<>();
        for (int i = 0; i < sentences.size(); i += 2) {
            int end = Math.min(i + 2, sentences.size());
            chunks.add(String.join(" ", sentences.subList(i, end)).trim());
        }
        return String.join("\n\n", chunks);
    }

    private List<String> splitSentences(String text) {
        if (text == null || text.isBlank()) {
            return List.of();
        }

        return Arrays.stream(text.split("(?<=[.!?])\\s+|\\n+"))
                .map(String::trim)
                .filter(s -> !s.isBlank())
                .toList();
    }

    private int findFirstSentenceBoundary(String text) {
        int period = text.indexOf('.');
        if (period >= 0) {
            return period + 1;
        }

        String[] markers = {"다 ", "요 ", "죠 "};
        for (String marker : markers) {
            int index = text.indexOf(marker);
            if (index > 20) {
                return index + marker.length();
            }
        }

        int middle = text.length() / 2;
        int leftBound = Math.max(middle - 60, 0);
        int rightBound = Math.min(middle + 60, text.length());
        int spaceIndex = text.lastIndexOf(' ', rightBound);
        if (spaceIndex >= leftBound) {
            return spaceIndex + 1;
        }
        return -1;
    }

    private void ensureRecommendationIdMatch(Long expectedId, Long actualId) {
        if (actualId != null && !Objects.equals(expectedId, actualId)) {
            throw new CustomException(ErrorCode.FASTAPI_SERVER_ERROR);
        }
    }

    private String resolveErrorSummary(Exception e) {
        String direct = sanitizeErrorText(e.getMessage());
        if (direct != null) {
            return direct;
        }

        Throwable cause = e.getCause();
        while (cause != null) {
            String causeMessage = sanitizeErrorText(cause.getMessage());
            if (causeMessage != null) {
                return causeMessage;
            }
            cause = cause.getCause();
        }

        return "추천 생성 중 오류가 발생했습니다.";
    }

    private String buildFastApiErrorSummary(
            String path,
            int statusCode,
            String responseBody,
            String fallbackMessage
    ) {
        String upstreamMessage = extractUpstreamMessage(responseBody);
        if (upstreamMessage == null) {
            upstreamMessage = sanitizeErrorText(fallbackMessage);
        }
        if (upstreamMessage == null) {
            upstreamMessage = "upstream_error";
        }

        return sanitizeErrorText(
                "추천 서버 호출 실패(path=" + path + ", status=" + statusCode + "): " + upstreamMessage
        );
    }

    private String extractUpstreamMessage(String responseBody) {
        if (responseBody == null || responseBody.isBlank()) {
            return null;
        }

        try {
            JsonNode root = objectMapper.readTree(responseBody);
            String extracted = readText(root, "message", "detail", "error", "errorSummary");
            if (extracted != null) {
                return extracted;
            }
        } catch (Exception ignored) {
            // no-op: 아래에서 원문 일부를 사용
        }

        return sanitizeErrorText(responseBody);
    }

    private String sanitizeErrorText(String text) {
        if (text == null) {
            return null;
        }
        String normalized = text.replaceAll("\\s+", " ").trim();
        if (normalized.isBlank()) {
            return null;
        }
        int maxLength = 360;
        if (normalized.length() <= maxLength) {
            return normalized;
        }
        return normalized.substring(0, maxLength - 3) + "...";
    }

    private String toUserVisibleErrorSummary(RecommendationStatus status, String errorSummary) {
        if (status == RecommendationStatus.FAILED) {
            return USER_VISIBLE_FAILURE_MESSAGE;
        }
        return errorSummary;
    }

    private void applyDatasetResult(DatasetRecommendationEntity entity, ExternalRecommendation result) {
        if (result.status() == RecommendationStatus.FAILED) {
            entity.markFailed(result.errorSummary());
            return;
        }
        entity.markSuccess(result.reasonText(), result.items(), result.llmModel());
    }

    private void applyOpenApiResult(OpenApiRecommendationEntity entity, ExternalRecommendation result) {
        if (result.status() == RecommendationStatus.FAILED) {
            entity.markFailed(result.errorSummary());
            return;
        }
        entity.markSuccess(result.reasonText(), result.items(), result.llmModel());
    }

    private String buildCombinedFailureSummary(ExternalRecommendation dataset, ExternalRecommendation openApi) {
        List<String> reasons = new ArrayList<>();
        if (dataset.errorSummary() != null && !dataset.errorSummary().isBlank()) {
            reasons.add("dataset=" + dataset.errorSummary());
        }
        if (openApi.errorSummary() != null && !openApi.errorSummary().isBlank()) {
            reasons.add("openapi=" + openApi.errorSummary());
        }
        if (reasons.isEmpty()) {
            return "추천 생성 중 오류가 발생했습니다.";
        }
        return sanitizeErrorText(String.join(" | ", reasons));
    }

    private Long readLong(JsonNode data, String... keys) {
        for (String key : keys) {
            JsonNode node = data.get(key);
            if (node == null || node.isNull()) {
                continue;
            }
            if (node.isIntegralNumber()) {
                return node.asLong();
            }
            if (node.isTextual()) {
                try {
                    return Long.parseLong(node.asText());
                } catch (NumberFormatException ignored) {
                    return null;
                }
            }
        }
        return null;
    }

    private String readText(JsonNode data, String... keys) {
        for (String key : keys) {
            JsonNode node = data.get(key);
            if (node != null && !node.isNull()) {
                String value = node.asText();
                if (!value.isBlank()) {
                    return value;
                }
            }
        }
        return null;
    }

    private JsonNode readJson(JsonNode data, String... keys) {
        for (String key : keys) {
            JsonNode node = data.get(key);
            if (node != null && !node.isNull()) {
                return node;
            }
        }
        return JsonNodeFactory.instance.arrayNode();
    }

    private record ParallelRecommendationResult(
            ExternalRecommendation datasetRecommendation,
            ExternalRecommendation openApiRecommendation
    ) {
    }

    private record ExternalRecommendation(
            Long recommendationId,
            String reasonText,
            JsonNode items,
            String llmModel,
            RecommendationStatus status,
            String errorSummary
    ) {
    }

    private record ExternalMergeResult(
            Long recommendationId,
            String mergedReasonText,
            String llmModel
    ) {
    }

    private record ExternalChatAnswer(
            String answerText,
            String llmModel
    ) {
    }

    private record ChatPreparation(
            Long conversationId,
            Long userTurnId,
            Long datasetRecommendationId,
            Long openApiRecommendationId,
            Long recommendationId,
            Long userId,
            String message,
            List<Map<String, String>> history,
            long startMs
    ) {
    }

    private enum RecommendationMode {
        CHAT_ONLY,
        BOTH,
        DATASET_ONLY,
        OPENAPI_ONLY
    }
}
