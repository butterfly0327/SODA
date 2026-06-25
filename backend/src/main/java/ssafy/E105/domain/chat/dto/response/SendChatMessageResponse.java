package ssafy.E105.domain.chat.dto.response;

import com.fasterxml.jackson.databind.JsonNode;

public record SendChatMessageResponse(
        Long conversationId,
        Long userTurnId,
        Long assistantTurnId,
        String assistantMessage,
        String mergedReason,
        JsonNode datasetRecommendations,
        JsonNode openApiRecommendations
) {
}
