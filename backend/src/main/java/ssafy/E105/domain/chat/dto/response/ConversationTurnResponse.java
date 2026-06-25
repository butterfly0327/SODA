package ssafy.E105.domain.chat.dto.response;

import ssafy.E105.domain.chat.entity.TurnRole;

import java.time.LocalDateTime;

public record ConversationTurnResponse(
        Long turnId,
        Integer turnOrder,
        TurnRole role,
        String content,
        Integer responseTimeMs,
        LocalDateTime createdAt
) {
}
