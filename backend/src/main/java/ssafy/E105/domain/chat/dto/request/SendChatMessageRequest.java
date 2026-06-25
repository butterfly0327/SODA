package ssafy.E105.domain.chat.dto.request;

public record SendChatMessageRequest(
        Long conversationId,
        String message
) {
}
