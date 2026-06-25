package ssafy.E105.domain.superapp.controller;

import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.bind.annotation.*;
import ssafy.E105.domain.resource.enums.ResourceType;
import ssafy.E105.domain.resource.enums.SortType;
import ssafy.E105.domain.superapp.dto.SuperAppPromptRecommendationRequest;
import ssafy.E105.domain.superapp.dto.SuperAppPromptRecommendationResponse;
import ssafy.E105.domain.superapp.dto.SuperAppResourceDetailResponse;
import ssafy.E105.domain.superapp.dto.SuperAppResourceListResponse;
import ssafy.E105.domain.superapp.service.SuperAppService;
import ssafy.E105.global.common.response.ApiResponse;
import ssafy.E105.global.exception.CustomException;
import ssafy.E105.global.exception.ErrorCode;

@RestController
@RequiredArgsConstructor
@RequestMapping("/v1/soda")
public class SuperAppController {

    private final SuperAppService superAppService;

    @GetMapping("/resources")
    public ResponseEntity<ApiResponse<SuperAppResourceListResponse>> getResources(
            @RequestParam String appId,
            @RequestParam(required = false) String keyword,
            @RequestParam(defaultValue = "ALL") ResourceType type,
            @RequestParam(defaultValue = "SCORE") SortType sort,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        SuperAppResourceListResponse result = superAppService.getResources(keyword, type, sort, page, size);
        return ResponseEntity.ok(ApiResponse.success("리소스 목록 조회가 완료되었습니다.", result));
    }

    @GetMapping("/resources/{type}/{id}")
    public ResponseEntity<ApiResponse<SuperAppResourceDetailResponse>> getResourceDetail(
            @RequestParam String appId,
            @PathVariable ResourceType type,
            @PathVariable Long id) {
        SuperAppResourceDetailResponse result = superAppService.getResourceDetail(type, id);
        return ResponseEntity.ok(ApiResponse.success("리소스 상세 조회가 완료되었습니다.", result));
    }

    @PostMapping("/recommendations")
    public ResponseEntity<ApiResponse<SuperAppPromptRecommendationResponse>> recommendResourcesByPrompt(
            @RequestParam String appId,
            @RequestHeader(value = "X-Access-Token", required = false) String accessToken,
            @RequestBody SuperAppPromptRecommendationRequest request
    ) {
        if (accessToken == null || accessToken.isBlank()) {
            throw new CustomException(ErrorCode.SUPERAPP_AUTH_FAILED);
        }

        Long userId = getAuthenticatedUserId();
        SuperAppPromptRecommendationResponse result =
                superAppService.recommendResourcesByPrompt(userId, appId, request);
        return ResponseEntity.ok(ApiResponse.success("추천이 완료되었습니다.", result));
    }

    private Long getAuthenticatedUserId() {
        var authentication = SecurityContextHolder.getContext().getAuthentication();
        if (authentication == null || authentication.getPrincipal() == null) {
            throw new CustomException(ErrorCode.SUPERAPP_AUTH_FAILED);
        }

        Object principal = authentication.getPrincipal();
        if (principal instanceof Long userId) {
            return userId;
        }
        throw new CustomException(ErrorCode.SUPERAPP_AUTH_FAILED);
    }
}
