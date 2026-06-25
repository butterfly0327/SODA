package ssafy.E105.domain.chat.controller;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.bind.annotation.*;
import ssafy.E105.domain.chat.dto.request.SendChatMessageRequest;
import ssafy.E105.domain.chat.dto.response.ConversationDetailResponse;
import ssafy.E105.domain.chat.dto.response.ConversationListItemResponse;
import ssafy.E105.domain.chat.dto.response.RecommendationStatusResponse;
import ssafy.E105.domain.chat.dto.response.SendChatMessageAcceptedResponse;
import ssafy.E105.domain.chat.service.ChatService;
import ssafy.E105.global.common.response.ApiResponse;
import ssafy.E105.global.exception.CustomException;
import ssafy.E105.global.exception.ErrorCode;

import java.util.List;

@RestController
@RequestMapping("/v1")
public class ChatController {

    private final ChatService chatService;

    public ChatController(ChatService chatService) {
        this.chatService = chatService;
    }

    @PostMapping("/chat/messages")
    public ResponseEntity<ApiResponse<SendChatMessageAcceptedResponse>> sendChatMessage(
            @RequestBody SendChatMessageRequest request
    ) {
        Long userId = getAuthenticatedUserId();
        SendChatMessageAcceptedResponse response = chatService.sendChatMessage(userId, request);
        return ResponseEntity.status(HttpStatus.ACCEPTED)
                .header("Location", "/v1/recommendations/" + response.recommendationId())
                .body(ApiResponse.accepted("채팅 메시지가 접수되었습니다. 추천 생성이 진행 중입니다.", response));
    }

    @GetMapping("/recommendations/{recommendationId}")
    public ResponseEntity<ApiResponse<RecommendationStatusResponse>> getRecommendationStatus(
            @PathVariable Long recommendationId
    ) {
        Long userId = getAuthenticatedUserId();
        RecommendationStatusResponse response = chatService.getRecommendationStatus(userId, recommendationId);
        return ResponseEntity.ok(ApiResponse.success("추천 상태 조회가 완료되었습니다.", response));
    }

    @GetMapping("/conversations")
    public ResponseEntity<ApiResponse<List<ConversationListItemResponse>>> getConversationList() {
        Long userId = getAuthenticatedUserId();
        List<ConversationListItemResponse> response = chatService.getConversationList(userId);
        return ResponseEntity.ok(ApiResponse.success("대화 목록 조회가 완료되었습니다.", response));
    }

    @GetMapping("/conversations/{conversationId}")
    public ResponseEntity<ApiResponse<ConversationDetailResponse>> getConversationDetail(
            @PathVariable Long conversationId
    ) {
        Long userId = getAuthenticatedUserId();
        ConversationDetailResponse response = chatService.getConversationDetail(userId, conversationId);
        return ResponseEntity.ok(ApiResponse.success("대화 상세 조회가 완료되었습니다.", response));
    }

    @DeleteMapping("/conversations/{conversationId}")
    public ResponseEntity<ApiResponse<Void>> deleteConversation(@PathVariable Long conversationId) {
        Long userId = getAuthenticatedUserId();
        chatService.deleteConversation(userId, conversationId);
        return ResponseEntity.ok(ApiResponse.success("대화 삭제가 완료되었습니다."));
    }

    private Long getAuthenticatedUserId() {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        if (authentication == null || authentication.getPrincipal() == null) {
            throw new CustomException(ErrorCode.INVALID_USER);
        }

        Object principal = authentication.getPrincipal();
        if (principal instanceof Long userId) {
            return userId;
        }
        throw new CustomException(ErrorCode.INVALID_USER);
    }
}
