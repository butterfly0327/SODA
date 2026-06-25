package ssafy.E105.domain.chat.dto.response;

import com.fasterxml.jackson.databind.JsonNode;
import ssafy.E105.domain.chat.entity.RecommendationStatus;

import java.time.LocalDateTime;

public record RecommendationStatusResponse(
        Long recommendationId,
        Long conversationId,
        Long userTurnId,
        Long assistantTurnId,
        RecommendationStatus status,
        String mergedReason,
        JsonNode datasetRecommendations,
        JsonNode openApiRecommendations,
        String errorSummary,
        LocalDateTime updatedAt
) {
}
