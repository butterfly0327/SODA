package ssafy.E105.domain.chatresource.controller;

import org.springframework.http.ResponseEntity;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import ssafy.E105.domain.chatresource.dto.request.ChatResourceCardsBatchRequest;
import ssafy.E105.domain.chatresource.dto.response.ChatResourceCardsBatchResponse;
import ssafy.E105.domain.chatresource.dto.response.ChatResourceDetailResponse;
import ssafy.E105.domain.chatresource.service.ChatResourceService;
import ssafy.E105.domain.resource.enums.ResourceType;
import ssafy.E105.global.common.response.ApiResponse;
import ssafy.E105.global.exception.CustomException;
import ssafy.E105.global.exception.ErrorCode;

@RestController
@RequestMapping("/v1/chat-resources")
public class ChatResourceController {

    private final ChatResourceService chatResourceService;

    public ChatResourceController(ChatResourceService chatResourceService) {
        this.chatResourceService = chatResourceService;
    }

    @PostMapping("/cards/batch")
    public ResponseEntity<ApiResponse<ChatResourceCardsBatchResponse>> getCardsBatch(
            @RequestBody ChatResourceCardsBatchRequest request
    ) {
        getAuthenticatedUserId();
        return chatResourceService.getCardsBatch(request);
    }

    @GetMapping("/{resourceType}/{resourceId}")
    public ResponseEntity<ApiResponse<ChatResourceDetailResponse>> getResourceDetail(
            @PathVariable ResourceType resourceType,
            @PathVariable Long resourceId,
            @RequestParam Double recommendationScore
    ) {
        getAuthenticatedUserId();
        return chatResourceService.getResourceDetail(resourceType, resourceId, recommendationScore);
    }

    private Long getAuthenticatedUserId() {
        var authentication = SecurityContextHolder.getContext().getAuthentication();
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
