package ssafy.E105.domain.chat.dto.response;

import ssafy.E105.domain.chat.entity.RecommendationStatus;

public record SendChatMessageAcceptedResponse(
        Long conversationId,
        Long userTurnId,
        Long recommendationId,
        RecommendationStatus status
) {
}
