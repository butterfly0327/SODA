package ssafy.E105.domain.chat.dto.response;

import com.fasterxml.jackson.databind.JsonNode;
import ssafy.E105.domain.chat.entity.RecommendationStatus;

public record RecommendationDetailResponse(
        Long recommendationId,
        Long userTurnId,
        Long assistantTurnId,
        RecommendationStatus status,
        String mergedReason,
        String datasetReason,
        String openApiReason,
        JsonNode datasetRecommendations,
        JsonNode openApiRecommendations,
        String errorSummary
) {
}
