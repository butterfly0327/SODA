package ssafy.E105.domain.chat.dto.response;

import java.util.List;

public record ConversationDetailResponse(
        Long conversationId,
        String title,
        List<ConversationTurnResponse> turns,
        List<RecommendationDetailResponse> recommendations
) {
}
