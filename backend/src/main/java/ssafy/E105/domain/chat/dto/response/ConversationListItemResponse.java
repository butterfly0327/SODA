package ssafy.E105.domain.chat.dto.response;

import java.time.LocalDateTime;

public record ConversationListItemResponse(
        Long conversationId,
        String title,
        LocalDateTime createdAt,
        LocalDateTime updatedAt
) {
}
