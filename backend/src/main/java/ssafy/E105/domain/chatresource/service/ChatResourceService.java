package ssafy.E105.domain.chatresource.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import ssafy.E105.domain.chatresource.dto.request.ChatResourceCardsBatchRequest;
import ssafy.E105.domain.chatresource.dto.response.ChatResourceCardsBatchResponse;
import ssafy.E105.domain.chatresource.dto.response.ChatResourceDetailResponse;
import ssafy.E105.domain.dataset.entity.DatasetEntity;
import ssafy.E105.domain.dataset.repository.DatasetRepository;
import ssafy.E105.domain.dataset.repository.DatasetSourceRepository;
import ssafy.E105.domain.openapi.entity.OpenApiEntity;
import ssafy.E105.domain.openapi.repository.OpenApiRepository;
import ssafy.E105.domain.openapi.repository.OpenApiSourceRepository;
import ssafy.E105.domain.resource.enums.ResourceType;
import ssafy.E105.global.common.util.KstDateTimeFormatter;
import ssafy.E105.global.common.response.ApiResponse;
import ssafy.E105.global.exception.CustomException;
import ssafy.E105.global.exception.ErrorCode;

import java.util.ArrayList;
import java.util.List;

@Service
public class ChatResourceService {

    private static final String ACTIVE_DATASET_STATUS = "ACTIVE";

    private final DatasetRepository datasetRepository;
    private final OpenApiRepository openApiRepository;
    private final DatasetSourceRepository datasetSourceRepository;
    private final OpenApiSourceRepository openApiSourceRepository;
    private final ObjectMapper objectMapper;

    public ChatResourceService(
            DatasetRepository datasetRepository,
            OpenApiRepository openApiRepository,
            DatasetSourceRepository datasetSourceRepository,
            OpenApiSourceRepository openApiSourceRepository,
            ObjectMapper objectMapper
    ) {
        this.datasetRepository = datasetRepository;
        this.openApiRepository = openApiRepository;
        this.datasetSourceRepository = datasetSourceRepository;
        this.openApiSourceRepository = openApiSourceRepository;
        this.objectMapper = objectMapper;
    }

    public ResponseEntity<ApiResponse<ChatResourceCardsBatchResponse>> getCardsBatch(ChatResourceCardsBatchRequest request) {
        validateCardsBatchRequest(request);

        List<ChatResourceCardsBatchResponse.Card> cards = new ArrayList<>();
        List<ChatResourceCardsBatchResponse.ItemError> errors = new ArrayList<>();

        for (ChatResourceCardsBatchRequest.Item item : request.items()) {
            if (item.resourceType() == ResourceType.DATASET) {
                DatasetEntity dataset = datasetRepository.findByIdAndStatus(item.resourceId(), ACTIVE_DATASET_STATUS).orElse(null);
                if (dataset == null) {
                    errors.add(new ChatResourceCardsBatchResponse.ItemError(
                            ResourceType.DATASET.name(),
                            item.resourceId(),
                            ErrorCode.RESOURCE_NOT_FOUND.name(),
                            ErrorCode.RESOURCE_NOT_FOUND.getMessage()
                    ));
                    continue;
                }

                cards.add(new ChatResourceCardsBatchResponse.Card(
                        dataset.getId(),
                        dataset.getTitle(),
                        ResourceType.DATASET.name(),
                        toDateTimeString(dataset.getUpdatedAt()),
                        dataset.getPaymentRequired() == null || !dataset.getPaymentRequired(),
                        resolveDatasetSiteName(dataset),
                        item.recommendationScore(),
                        item.rank()
                ));
                continue;
            }

            OpenApiEntity openApi = openApiRepository.findByIdAndIsDeletedFalse(item.resourceId()).orElse(null);
            if (openApi == null) {
                errors.add(new ChatResourceCardsBatchResponse.ItemError(
                        ResourceType.OPEN_API.name(),
                        item.resourceId(),
                        ErrorCode.RESOURCE_NOT_FOUND.name(),
                        ErrorCode.RESOURCE_NOT_FOUND.getMessage()
                ));
                continue;
            }

            cards.add(new ChatResourceCardsBatchResponse.Card(
                    openApi.getId(),
                    openApi.getName(),
                    ResourceType.OPEN_API.name(),
                    toDateTimeString(openApi.getUpdatedAt()),
                    openApi.getIsFree(),
                    resolveOpenApiSiteName(openApi),
                    item.recommendationScore(),
                    item.rank()
            ));
        }

        return ResponseEntity.ok(ApiResponse.success(
                "채팅 카드 배치 조회가 완료되었습니다.",
                new ChatResourceCardsBatchResponse(cards, errors)
        ));
    }

    public ResponseEntity<ApiResponse<ChatResourceDetailResponse>> getResourceDetail(
            ResourceType resourceType,
            Long resourceId,
            Double recommendationScore
    ) {
        validateDetailRequest(resourceType, resourceId, recommendationScore);

        if (resourceType == ResourceType.DATASET) {
            DatasetEntity dataset = datasetRepository.findByIdAndStatus(resourceId, ACTIVE_DATASET_STATUS)
                    .orElseThrow(() -> new CustomException(ErrorCode.RESOURCE_NOT_FOUND));

            ChatResourceDetailResponse response = new ChatResourceDetailResponse(
                    dataset.getId(),
                    dataset.getTitle(),
                    ResourceType.DATASET.name(),
                    toDateTimeString(dataset.getUpdatedAt()),
                    dataset.getPaymentRequired() == null || !dataset.getPaymentRequired(),
                    resolveDatasetSiteName(dataset),
                    recommendationScore,
                    dataset.getLandingUrl(),
                    new ChatResourceDetailResponse.DatasetDetail(
                            dataset.getDescriptionLong(),
                            readJson(dataset.getSchemaJson()),
                            dataset.getDatasetSizeBytes(),
                            dataset.getRowCount(),
                            readJson(dataset.getMetricsJson()),
                            dataset.getLicenseName(),
                            dataset.getDomains(),
                            dataset.getTags(),
                            dataset.getLanguages()
                    ),
                    null
            );

            return ResponseEntity.ok(ApiResponse.success("채팅 상세 조회가 완료되었습니다.", response));
        }

        OpenApiEntity openApi = openApiRepository.findByIdAndIsDeletedFalse(resourceId)
                .orElseThrow(() -> new CustomException(ErrorCode.RESOURCE_NOT_FOUND));

        ChatResourceDetailResponse response = new ChatResourceDetailResponse(
                openApi.getId(),
                openApi.getName(),
                ResourceType.OPEN_API.name(),
                toDateTimeString(openApi.getUpdatedAt()),
                openApi.getIsFree(),
                resolveOpenApiSiteName(openApi),
                recommendationScore,
                openApi.getDocsUrl(),
                null,
                new ChatResourceDetailResponse.OpenApiDetail(
                        openApi.getDescription(),
                        openApi.getAuthType(),
                        openApi.getCategory(),
                        openApi.getTags(),
                        openApi.getRateLimit(),
                        openApi.getDailyLimit(),
                        openApi.getPricingNote(),
                        openApi.getResponseFormat(),
                        openApi.getAvgResponseTime(),
                        readJson(openApi.getResponseSchema())
                )
        );

        return ResponseEntity.ok(ApiResponse.success("채팅 상세 조회가 완료되었습니다.", response));
    }

    private void validateCardsBatchRequest(ChatResourceCardsBatchRequest request) {
        if (request == null || request.items() == null || request.items().isEmpty()) {
            throw new CustomException(ErrorCode.INVALID_INPUT);
        }

        for (ChatResourceCardsBatchRequest.Item item : request.items()) {
            if (item == null
                    || item.resourceType() == null
                    || (item.resourceType() != ResourceType.DATASET && item.resourceType() != ResourceType.OPEN_API)
                    || item.resourceId() == null
                    || item.resourceId() <= 0
                    || item.recommendationScore() == null) {
                throw new CustomException(ErrorCode.INVALID_INPUT);
            }
        }
    }

    private void validateDetailRequest(ResourceType resourceType, Long resourceId, Double recommendationScore) {
        if (resourceType == null
                || (resourceType != ResourceType.DATASET && resourceType != ResourceType.OPEN_API)
                || resourceId == null
                || resourceId <= 0
                || recommendationScore == null) {
            throw new CustomException(ErrorCode.INVALID_INPUT);
        }
    }

    private String resolveDatasetSiteName(DatasetEntity dataset) {
        Short sourceId = dataset.getDatasetSourceId();
        if (sourceId != null) {
            String sourceName = datasetSourceRepository.findById(sourceId)
                    .map(source -> source.getSourceName())
                    .orElse(null);
            if (sourceName != null && !sourceName.isBlank()) {
                return sourceName;
            }
        }
        return dataset.getPublisherName();
    }

    private String resolveOpenApiSiteName(OpenApiEntity openApi) {
        Short sourceId = openApi.getOpenapiSourceId();
        if (sourceId != null) {
            String sourceName = openApiSourceRepository.findById(sourceId)
                    .map(source -> source.getSourceName())
                    .orElse(null);
            if (sourceName != null && !sourceName.isBlank()) {
                return sourceName;
            }
        }
        return openApi.getProvider();
    }

    private JsonNode readJson(String rawJson) {
        if (rawJson == null || rawJson.isBlank()) {
            return null;
        }

        try {
            return objectMapper.readTree(rawJson);
        } catch (Exception ignored) {
            return null;
        }
    }

    private String toDateTimeString(java.time.LocalDateTime localDateTime) {
        return KstDateTimeFormatter.format(localDateTime);
    }
}
