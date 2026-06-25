package ssafy.E105.domain.superapp.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ArrayNode;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import ssafy.E105.domain.chat.dto.request.SendChatMessageRequest;
import ssafy.E105.domain.chat.dto.response.ConversationDetailResponse;
import ssafy.E105.domain.chat.dto.response.RecommendationDetailResponse;
import ssafy.E105.domain.chat.dto.response.RecommendationStatusResponse;
import ssafy.E105.domain.chat.dto.response.SendChatMessageAcceptedResponse;
import ssafy.E105.domain.chat.entity.RecommendationStatus;
import ssafy.E105.domain.chat.service.ChatService;
import ssafy.E105.domain.chatresource.dto.request.ChatResourceCardsBatchRequest;
import ssafy.E105.domain.chatresource.dto.response.ChatResourceCardsBatchResponse;
import ssafy.E105.domain.chatresource.dto.response.ChatResourceDetailResponse;
import ssafy.E105.domain.chatresource.service.ChatResourceService;
import ssafy.E105.domain.resource.dto.response.ResourceDetailResponse;
import ssafy.E105.domain.resource.dto.response.ResourceItemResponse;
import ssafy.E105.domain.resource.dto.response.ResourceListResponse;
import ssafy.E105.domain.resource.enums.ResourceType;
import ssafy.E105.domain.resource.enums.SortType;
import ssafy.E105.domain.resource.service.ResourceService;
import ssafy.E105.domain.superapp.dto.SuperAppPromptRecommendationRequest;
import ssafy.E105.domain.superapp.dto.SuperAppPromptRecommendationResponse;
import ssafy.E105.domain.superapp.dto.SuperAppResourceDetailResponse;
import ssafy.E105.domain.superapp.dto.SuperAppResourceItemResponse;
import ssafy.E105.domain.superapp.dto.SuperAppResourceListResponse;
import ssafy.E105.global.common.response.ApiResponse;
import ssafy.E105.global.exception.CustomException;
import ssafy.E105.global.exception.ErrorCode;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;

@Service
@RequiredArgsConstructor
public class SuperAppService {

    private static final long DEFAULT_RECOMMENDATION_TIMEOUT_MS = 300_000L;
    private static final long RECOMMENDATION_POLL_INTERVAL_MS = 1_000L;

    private final ResourceService resourceService;
    private final ChatService chatService;
    private final ChatResourceService chatResourceService;

    @org.springframework.beans.factory.annotation.Value("${superapp.recommendation-timeout-ms:300000}")
    private long recommendationTimeoutMs;

    public SuperAppResourceListResponse getResources(
            String keyword, ResourceType type, SortType sort, int page, int size) {
        // userId 없이 호출 (null)
        ResourceListResponse response = resourceService.getResources(keyword, type, sort, page, size, null);
        
        // SuperApp 전용 DTO로 변환
        List<SuperAppResourceItemResponse> items = response.items().stream()
                .map(this::toSuperAppItem)
                .toList();
        
        return new SuperAppResourceListResponse(
                response.totalCount(),
                response.totalPages(),
                response.currentPage(),
                response.hasNext(),
                items
        );
    }

    public SuperAppResourceDetailResponse getResourceDetail(ResourceType type, Long id) {
        // userId 없이 호출 (null)
        ResourceDetailResponse response = resourceService.getResourceDetail(type, id, null);
        return toSuperAppDetail(response);
    }

    public SuperAppPromptRecommendationResponse recommendResourcesByPrompt(
            Long userId,
            String appId,
            SuperAppPromptRecommendationRequest request
    ) {
        validatePromptRecommendationInput(appId, request);

        try {
            SendChatMessageAcceptedResponse acceptedResponse =
                    chatService.sendChatMessage(userId, new SendChatMessageRequest(null, request.message()));

            RecommendationStatusResponse statusResponse = waitUntilRecommendationFinished(
                    userId,
                    acceptedResponse.recommendationId()
            );

            if (statusResponse.status() == RecommendationStatus.FAILED) {
                throw new CustomException(ErrorCode.SUPERAPP_RECOMMENDATION_FAILED);
            }

            RecommendationReasonPair reasonPair = resolveRecommendationReasonPair(
                    userId,
                    statusResponse.conversationId(),
                    statusResponse.recommendationId(),
                    statusResponse.mergedReason()
            );

            List<RecommendationCandidate> datasetCandidates = extractCandidates(
                    statusResponse.datasetRecommendations(),
                    ResourceType.DATASET
            );
            List<RecommendationCandidate> openApiCandidates = extractCandidates(
                    statusResponse.openApiRecommendations(),
                    ResourceType.OPEN_API
            );

            Map<ResourceKey, ChatResourceCardsBatchResponse.Card> cardMap = fetchCardMap(datasetCandidates, openApiCandidates);
            Map<ResourceKey, ChatResourceDetailResponse> detailMap = fetchDetailMap(datasetCandidates, openApiCandidates);

            Map<ResourceKey, ResourceDetailResponse> resourceDetailMap = fetchResourceDetailMap(datasetCandidates, openApiCandidates);

            List<SuperAppPromptRecommendationResponse.DatasetRecommendation> datasetRecommendations =
                    buildDatasetRecommendations(datasetCandidates, cardMap, detailMap, resourceDetailMap);
            List<SuperAppPromptRecommendationResponse.OpenApiRecommendation> openApiRecommendations =
                    buildOpenApiRecommendations(openApiCandidates, cardMap, detailMap, resourceDetailMap);

            return new SuperAppPromptRecommendationResponse(
                    statusResponse.mergedReason(),
                    reasonPair.datasetReason(),
                    reasonPair.openApiReason(),
                    datasetRecommendations,
                    openApiRecommendations
            );
        } catch (CustomException e) {
            if (e.getErrorCode() == ErrorCode.SUPERAPP_RECOMMENDATION_TIMEOUT
                    || e.getErrorCode() == ErrorCode.SUPERAPP_RECOMMENDATION_FAILED
                    || e.getErrorCode() == ErrorCode.INVALID_INPUT
                    || e.getErrorCode() == ErrorCode.INVALID_USER
                    || e.getErrorCode() == ErrorCode.INVALID_TOKEN
                    || e.getErrorCode() == ErrorCode.ACCESS_DENIED
                    || e.getErrorCode() == ErrorCode.SUPERAPP_AUTH_FAILED) {
                throw e;
            }

            throw new CustomException(ErrorCode.SUPERAPP_RECOMMENDATION_FAILED);
        }
    }

    private SuperAppResourceItemResponse toSuperAppItem(ResourceItemResponse item) {
        // isBookmarked (7번째 필드) 건너뛰고 매핑
        if (item.datasetMeta() != null) {
            return new SuperAppResourceItemResponse(
                    item.id(),
                    item.type(),
                    item.title(),
                    item.score(),
                    item.isFree(),
                    item.createdAt(),
                    new SuperAppResourceItemResponse.DatasetMeta(
                            item.datasetMeta().publisherName(),
                            item.datasetMeta().sourceUpdatedAt(),
                            item.datasetMeta().sampleCount()
                    ),
                    null
            );
        } else {
            return new SuperAppResourceItemResponse(
                    item.id(),
                    item.type(),
                    item.title(),
                    item.score(),
                    item.isFree(),
                    item.createdAt(),
                    null,
                    new SuperAppResourceItemResponse.OpenApiMeta(
                            item.openApiMeta().category(),
                            item.openApiMeta().avgResponseTime(),
                            item.openApiMeta().authType(),
                            item.openApiMeta().dailyLimit()
                    )
            );
        }
    }

    private SuperAppResourceDetailResponse toSuperAppDetail(ResourceDetailResponse detail) {
        // isBookmarked (7번째 필드) 건너뛰고 매핑
        return new SuperAppResourceDetailResponse(
                detail.id(),
                detail.type(),
                detail.title(),
                detail.score(),
                detail.isFree(),
                detail.createdAt(),
                detail.datasetDetail() != null ? toSuperAppDatasetDetail(detail.datasetDetail()) : null,
                detail.openApiDetail() != null ? toSuperAppOpenApiDetail(detail.openApiDetail()) : null
        );
    }

    private SuperAppResourceDetailResponse.DatasetDetail toSuperAppDatasetDetail(
            ResourceDetailResponse.DatasetDetail d) {
        return new SuperAppResourceDetailResponse.DatasetDetail(
                d.subtitle(),
                d.descriptionShort(),
                d.descriptionLong(),
                d.publisherName(),
                d.domains(),
                d.tasks(),
                d.modalities(),
                d.tags(),
                d.languages(),
                d.licenseName(),
                d.licenseUrl(),
                d.commercialUseAllowed(),
                d.accessType(),
                d.rowCount(),
                d.datasetSizeBytes(),
                d.sourceUpdatedAt(),
                d.canonicalUrl(),
                d.landingUrl(),
                d.schemaJson()
        );
    }

    private SuperAppResourceDetailResponse.OpenApiDetail toSuperAppOpenApiDetail(
            ResourceDetailResponse.OpenApiDetail o) {
        return new SuperAppResourceDetailResponse.OpenApiDetail(
                o.description(),
                o.provider(),
                o.baseUrl(),
                o.docsUrl(),
                o.authType(),
                o.category(),
                o.tags(),
                o.rateLimit(),
                o.dailyLimit(),
                o.pricingNote(),
                o.commercialUse(),
                o.requiresApproval(),
                o.responseFormat(),
                o.avgResponseTime()
        );
    }

    private void validatePromptRecommendationInput(String appId, SuperAppPromptRecommendationRequest request) {
        if (appId == null || appId.isBlank() || request == null || request.message() == null || request.message().isBlank()) {
            throw new CustomException(ErrorCode.INVALID_INPUT);
        }
    }

    private RecommendationStatusResponse waitUntilRecommendationFinished(Long userId, Long recommendationId) {
        long effectiveTimeoutMs = recommendationTimeoutMs > 0 ? recommendationTimeoutMs : DEFAULT_RECOMMENDATION_TIMEOUT_MS;
        long deadline = System.currentTimeMillis() + effectiveTimeoutMs;

        while (System.currentTimeMillis() <= deadline) {
            RecommendationStatusResponse statusResponse = chatService.getRecommendationStatus(userId, recommendationId);
            if (statusResponse.status() == RecommendationStatus.SUCCESS
                    || statusResponse.status() == RecommendationStatus.FAILED) {
                return statusResponse;
            }

            try {
                Thread.sleep(RECOMMENDATION_POLL_INTERVAL_MS);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                throw new CustomException(ErrorCode.SUPERAPP_RECOMMENDATION_FAILED);
            }
        }

        throw new CustomException(ErrorCode.SUPERAPP_RECOMMENDATION_TIMEOUT);
    }

    private RecommendationReasonPair resolveRecommendationReasonPair(
            Long userId,
            Long conversationId,
            Long recommendationId,
            String fallbackReason
    ) {
        ConversationDetailResponse conversationDetail;
        try {
            conversationDetail = chatService.getConversationDetail(userId, conversationId);
        } catch (CustomException e) {
            return new RecommendationReasonPair(fallbackReason, fallbackReason);
        }

        RecommendationDetailResponse recommendationDetail = conversationDetail.recommendations().stream()
                .filter(item -> Objects.equals(item.recommendationId(), recommendationId))
                .findFirst()
                .orElse(null);

        if (recommendationDetail == null) {
            return new RecommendationReasonPair(fallbackReason, fallbackReason);
        }

        return new RecommendationReasonPair(
                firstNonBlank(recommendationDetail.datasetReason(), fallbackReason),
                firstNonBlank(recommendationDetail.openApiReason(), fallbackReason)
        );
    }

    private List<RecommendationCandidate> extractCandidates(JsonNode rawRecommendations, ResourceType type) {
        if (!(rawRecommendations instanceof ArrayNode recommendationArray) || recommendationArray.isEmpty()) {
            return List.of();
        }

        List<RecommendationCandidate> candidates = new ArrayList<>();
        for (int i = 0; i < recommendationArray.size(); i++) {
            JsonNode item = recommendationArray.get(i);
            Long resourceId = resolveResourceId(item, type);
            if (resourceId == null || resourceId <= 0) {
                continue;
            }

            candidates.add(new RecommendationCandidate(
                    type,
                    resourceId,
                    readText(item,
                            "title",
                            "name",
                            type == ResourceType.DATASET ? "datasetTitle" : "openApiTitle",
                            type == ResourceType.DATASET ? "datasetName" : "openApiName",
                            type == ResourceType.OPEN_API ? "openapiTitle" : "",
                            type == ResourceType.OPEN_API ? "openapiName" : ""
                    ),
                    readText(item, "reason"),
                    readDouble(item, "score", "recommendationScore", "suitabilityScore"),
                    i + 1
            ));
        }

        return candidates;
    }

    private Map<ResourceKey, ChatResourceCardsBatchResponse.Card> fetchCardMap(
            List<RecommendationCandidate> datasetCandidates,
            List<RecommendationCandidate> openApiCandidates
    ) {
        List<ChatResourceCardsBatchRequest.Item> batchItems = new ArrayList<>();

        for (RecommendationCandidate candidate : mergeCandidates(datasetCandidates, openApiCandidates)) {
            batchItems.add(new ChatResourceCardsBatchRequest.Item(
                    candidate.resourceType(),
                    candidate.resourceId(),
                    candidate.score() == null ? 0.0 : candidate.score(),
                    candidate.rank()
            ));
        }

        if (batchItems.isEmpty()) {
            return Map.of();
        }

        ApiResponse<ChatResourceCardsBatchResponse> apiResponse = chatResourceService
                .getCardsBatch(new ChatResourceCardsBatchRequest(batchItems))
                .getBody();
        if (apiResponse == null || apiResponse.getData() == null || apiResponse.getData().cards() == null) {
            return Map.of();
        }

        Map<ResourceKey, ChatResourceCardsBatchResponse.Card> result = new HashMap<>();
        for (ChatResourceCardsBatchResponse.Card card : apiResponse.getData().cards()) {
            ResourceType resourceType = parseResourceType(card.type());
            if (resourceType == null || card.id() == null) {
                continue;
            }
            result.put(new ResourceKey(resourceType, card.id()), card);
        }
        return result;
    }

    private Map<ResourceKey, ChatResourceDetailResponse> fetchDetailMap(
            List<RecommendationCandidate> datasetCandidates,
            List<RecommendationCandidate> openApiCandidates
    ) {
        List<RecommendationCandidate> mergedCandidates = mergeCandidates(datasetCandidates, openApiCandidates);
        if (mergedCandidates.isEmpty()) {
            return Map.of();
        }

        Map<ResourceKey, ChatResourceDetailResponse> detailMap = new HashMap<>();
        for (RecommendationCandidate candidate : mergedCandidates) {
            try {
                ApiResponse<ChatResourceDetailResponse> apiResponse = chatResourceService
                        .getResourceDetail(
                                candidate.resourceType(),
                                candidate.resourceId(),
                                candidate.score() == null ? 0.0 : candidate.score()
                        )
                        .getBody();

                if (apiResponse == null || apiResponse.getData() == null) {
                    continue;
                }

                detailMap.put(new ResourceKey(candidate.resourceType(), candidate.resourceId()), apiResponse.getData());
            } catch (CustomException e) {
                if (e.getErrorCode() != ErrorCode.RESOURCE_NOT_FOUND) {
                    throw e;
                }
            }
        }

        return detailMap;
    }

    private Map<ResourceKey, ResourceDetailResponse> fetchResourceDetailMap(
            List<RecommendationCandidate> datasetCandidates,
            List<RecommendationCandidate> openApiCandidates
    ) {
        List<RecommendationCandidate> mergedCandidates = mergeCandidates(datasetCandidates, openApiCandidates);
        if (mergedCandidates.isEmpty()) {
            return Map.of();
        }

        Map<ResourceKey, ResourceDetailResponse> detailMap = new HashMap<>();
        for (RecommendationCandidate candidate : mergedCandidates) {
            try {
                ResourceDetailResponse response = resourceService.getResourceDetail(candidate.resourceType(), candidate.resourceId(), null);
                detailMap.put(new ResourceKey(candidate.resourceType(), candidate.resourceId()), response);
            } catch (CustomException e) {
                if (e.getErrorCode() != ErrorCode.RESOURCE_NOT_FOUND) {
                    throw e;
                }
            }
        }
        return detailMap;
    }

    private List<SuperAppPromptRecommendationResponse.DatasetRecommendation> buildDatasetRecommendations(
            List<RecommendationCandidate> candidates,
            Map<ResourceKey, ChatResourceCardsBatchResponse.Card> cardMap,
            Map<ResourceKey, ChatResourceDetailResponse> detailMap,
            Map<ResourceKey, ResourceDetailResponse> resourceDetailMap
    ) {
        if (candidates.isEmpty()) {
            return List.of();
        }

        List<RecommendationCandidate> sorted = candidates.stream()
                .sorted(Comparator.comparing(RecommendationCandidate::rank))
                .toList();

        List<SuperAppPromptRecommendationResponse.DatasetRecommendation> response = new ArrayList<>();
        for (RecommendationCandidate candidate : sorted) {
            ResourceKey key = new ResourceKey(candidate.resourceType(), candidate.resourceId());
            ChatResourceCardsBatchResponse.Card card = cardMap.get(key);
            ChatResourceDetailResponse detail = detailMap.get(key);
            ResourceDetailResponse resourceDetail = resourceDetailMap.get(key);

            SuperAppPromptRecommendationResponse.DatasetCard datasetCard = new SuperAppPromptRecommendationResponse.DatasetCard(
                    firstNonBlank(card == null ? null : card.name(), candidate.title(), detail == null ? null : detail.name()),
                    card == null ? null : card.sourceName(),
                    card == null ? null : card.updatedAt(),
                    card == null ? null : card.isFree()
            );

            SuperAppPromptRecommendationResponse.DatasetDetail datasetDetail = buildDatasetDetail(detail, resourceDetail);

            response.add(new SuperAppPromptRecommendationResponse.DatasetRecommendation(
                    candidate.resourceId(),
                    candidate.rank(),
                    firstNonNull(candidate.score(), card == null ? null : card.recommendationScore(), detail == null ? null : detail.recommendationScore()),
                    datasetCard,
                    datasetDetail,
                    mapReviews(resourceDetail)
            ));
        }

        return response;
    }

    private List<SuperAppPromptRecommendationResponse.OpenApiRecommendation> buildOpenApiRecommendations(
            List<RecommendationCandidate> candidates,
            Map<ResourceKey, ChatResourceCardsBatchResponse.Card> cardMap,
            Map<ResourceKey, ChatResourceDetailResponse> detailMap,
            Map<ResourceKey, ResourceDetailResponse> resourceDetailMap
    ) {
        if (candidates.isEmpty()) {
            return List.of();
        }

        List<RecommendationCandidate> sorted = candidates.stream()
                .sorted(Comparator.comparing(RecommendationCandidate::rank))
                .toList();

        List<SuperAppPromptRecommendationResponse.OpenApiRecommendation> response = new ArrayList<>();
        for (RecommendationCandidate candidate : sorted) {
            ResourceKey key = new ResourceKey(candidate.resourceType(), candidate.resourceId());
            ChatResourceCardsBatchResponse.Card card = cardMap.get(key);
            ChatResourceDetailResponse detail = detailMap.get(key);
            ResourceDetailResponse resourceDetail = resourceDetailMap.get(key);

            ResourceDetailResponse.OpenApiDetail openApiDetailSource = resourceDetail == null ? null : resourceDetail.openApiDetail();

            SuperAppPromptRecommendationResponse.OpenApiCard openApiCard = new SuperAppPromptRecommendationResponse.OpenApiCard(
                    firstNonBlank(card == null ? null : card.name(), candidate.title(), detail == null ? null : detail.name()),
                    firstNonBlank(
                            openApiDetailSource == null ? null : openApiDetailSource.provider(),
                            card == null ? null : card.sourceName()
                    ),
                    card == null ? null : card.updatedAt(),
                    card == null ? null : card.isFree()
            );

            SuperAppPromptRecommendationResponse.OpenApiDetail openApiDetail = buildOpenApiDetail(detail, resourceDetail);

            response.add(new SuperAppPromptRecommendationResponse.OpenApiRecommendation(
                    candidate.resourceId(),
                    candidate.rank(),
                    firstNonNull(candidate.score(), card == null ? null : card.recommendationScore(), detail == null ? null : detail.recommendationScore()),
                    openApiCard,
                    openApiDetail,
                    mapReviews(resourceDetail)
            ));
        }

        return response;
    }

    private SuperAppPromptRecommendationResponse.DatasetDetail buildDatasetDetail(
            ChatResourceDetailResponse chatDetail,
            ResourceDetailResponse resourceDetail
    ) {
        ChatResourceDetailResponse.DatasetDetail chatDataset = chatDetail == null ? null : chatDetail.datasetDetail();
        ResourceDetailResponse.DatasetDetail resourceDataset = resourceDetail == null ? null : resourceDetail.datasetDetail();

        JsonNode metricsNode = chatDataset == null ? null : chatDataset.metrics();

        return new SuperAppPromptRecommendationResponse.DatasetDetail(
                firstNonBlank(
                        resourceDataset == null ? null : resourceDataset.canonicalUrl(),
                        chatDetail == null ? null : chatDetail.originUrl()
                ),
                firstNonBlank(
                        chatDataset == null ? null : chatDataset.descriptionLong(),
                        resourceDataset == null ? null : resourceDataset.descriptionLong()
                ),
                firstNonNull(
                        chatDataset == null ? null : chatDataset.rowCount(),
                        resourceDataset == null ? null : resourceDataset.rowCount()
                ),
                resourceDataset == null ? null : resourceDataset.sourceUpdatedAt(),
                resourceDataset == null ? null : resourceDataset.domains(),
                resourceDataset == null ? null : resourceDataset.tasks(),
                resourceDataset == null ? null : resourceDataset.modalities(),
                firstNonNull(
                        chatDataset == null ? null : chatDataset.tags(),
                        resourceDataset == null ? null : resourceDataset.tags()
                ),
                resourceDataset == null ? null : resourceDataset.accessType(),
                null,
                null,
                null,
                firstNonBlank(
                        chatDataset == null ? null : chatDataset.licenseName(),
                        resourceDataset == null ? null : resourceDataset.licenseName()
                ),
                resourceDataset == null ? null : resourceDataset.commercialUseAllowed(),
                firstNonNull(
                        chatDataset == null ? null : chatDataset.languages(),
                        resourceDataset == null ? null : resourceDataset.languages()
                ),
                new SuperAppPromptRecommendationResponse.Metrics(
                        readLong(metricsNode, "viewCount"),
                        readLong(metricsNode, "requestCount")
                ),
                null,
                null,
                resourceDataset == null ? null : resourceDataset.sourceUpdatedAt(),
                null,
                null,
                chatDataset == null ? null : chatDataset.schemaJson()
        );
    }

    private SuperAppPromptRecommendationResponse.OpenApiDetail buildOpenApiDetail(
            ChatResourceDetailResponse chatDetail,
            ResourceDetailResponse resourceDetail
    ) {
        ChatResourceDetailResponse.OpenApiDetail chatOpenApi = chatDetail == null ? null : chatDetail.openApiDetail();
        ResourceDetailResponse.OpenApiDetail resourceOpenApi = resourceDetail == null ? null : resourceDetail.openApiDetail();

        return new SuperAppPromptRecommendationResponse.OpenApiDetail(
                firstNonBlank(
                        resourceOpenApi == null ? null : resourceOpenApi.docsUrl(),
                        chatDetail == null ? null : chatDetail.originUrl()
                ),
                firstNonBlank(
                        resourceOpenApi == null ? null : resourceOpenApi.description(),
                        chatOpenApi == null ? null : chatOpenApi.description()
                ),
                firstNonBlank(
                        resourceOpenApi == null ? null : resourceOpenApi.authType(),
                        chatOpenApi == null ? null : chatOpenApi.authType()
                ),
                firstNonBlank(
                        resourceOpenApi == null ? null : resourceOpenApi.category(),
                        chatOpenApi == null ? null : chatOpenApi.category()
                ),
                firstNonBlank(
                        resourceOpenApi == null ? null : resourceOpenApi.responseFormat(),
                        chatOpenApi == null ? null : chatOpenApi.responseFormat()
                ),
                firstNonNull(
                        resourceOpenApi == null ? null : resourceOpenApi.tags(),
                        chatOpenApi == null ? null : chatOpenApi.tags()
                ),
                firstNonBlank(
                        resourceOpenApi == null ? null : resourceOpenApi.pricingNote(),
                        chatOpenApi == null ? null : chatOpenApi.pricingNote()
                ),
                resourceOpenApi == null ? null : resourceOpenApi.commercialUse(),
                resourceOpenApi == null ? null : resourceOpenApi.requiresApproval()
        );
    }

    private List<SuperAppPromptRecommendationResponse.Review> mapReviews(ResourceDetailResponse resourceDetail) {
        if (resourceDetail == null || resourceDetail.reviews() == null || resourceDetail.reviews().isEmpty()) {
            return List.of();
        }

        return resourceDetail.reviews().stream()
                .map(review -> new SuperAppPromptRecommendationResponse.Review(
                        review.id(),
                        review.name(),
                        review.rating(),
                        review.content(),
                        review.createdAt()
                ))
                .toList();
    }

    private List<RecommendationCandidate> mergeCandidates(
            List<RecommendationCandidate> datasetCandidates,
            List<RecommendationCandidate> openApiCandidates
    ) {
        List<RecommendationCandidate> merged = new ArrayList<>(datasetCandidates.size() + openApiCandidates.size());
        merged.addAll(datasetCandidates);
        merged.addAll(openApiCandidates);
        return merged;
    }

    private Long resolveResourceId(JsonNode item, ResourceType resourceType) {
        if (resourceType == ResourceType.DATASET) {
            return readLong(item, "id", "datasetId");
        }
        return readLong(item, "id", "openApiId", "openapiId");
    }

    private Long readLong(JsonNode node, String... keys) {
        if (node == null || node.isNull()) {
            return null;
        }
        for (String key : keys) {
            if (key == null || key.isBlank()) {
                continue;
            }
            JsonNode value = node.get(key);
            if (value == null || value.isNull()) {
                continue;
            }
            if (value.isIntegralNumber()) {
                return value.asLong();
            }
            if (value.isTextual()) {
                try {
                    return Long.parseLong(value.asText().trim());
                } catch (NumberFormatException ignored) {
                    continue;
                }
            }
        }
        return null;
    }

    private Double readDouble(JsonNode node, String... keys) {
        if (node == null || node.isNull()) {
            return null;
        }
        for (String key : keys) {
            JsonNode value = node.get(key);
            if (value == null || value.isNull()) {
                continue;
            }
            if (value.isNumber()) {
                return value.asDouble();
            }
            if (value.isTextual()) {
                try {
                    return Double.parseDouble(value.asText().trim());
                } catch (NumberFormatException ignored) {
                    continue;
                }
            }
        }
        return null;
    }

    private String readText(JsonNode node, String... keys) {
        if (node == null || node.isNull()) {
            return null;
        }
        for (String key : keys) {
            if (key == null || key.isBlank()) {
                continue;
            }
            JsonNode value = node.get(key);
            if (value == null || value.isNull()) {
                continue;
            }
            String text = value.asText(null);
            if (text != null && !text.isBlank()) {
                return text;
            }
        }
        return null;
    }

    private ResourceType parseResourceType(String rawType) {
        if (rawType == null || rawType.isBlank()) {
            return null;
        }

        try {
            return ResourceType.valueOf(rawType.trim().toUpperCase(Locale.ROOT));
        } catch (IllegalArgumentException ignored) {
            return null;
        }
    }

    private String firstNonBlank(String... candidates) {
        for (String candidate : candidates) {
            if (candidate != null && !candidate.isBlank()) {
                return candidate;
            }
        }
        return null;
    }

    @SafeVarargs
    private final <T> T firstNonNull(T... candidates) {
        for (T candidate : candidates) {
            if (candidate != null) {
                return candidate;
            }
        }
        return null;
    }

    private record RecommendationCandidate(
            ResourceType resourceType,
            Long resourceId,
            String title,
            String reason,
            Double score,
            int rank
    ) {
    }

    private record ResourceKey(ResourceType resourceType, Long resourceId) {
    }

    private record RecommendationReasonPair(String datasetReason, String openApiReason) {
    }
}
