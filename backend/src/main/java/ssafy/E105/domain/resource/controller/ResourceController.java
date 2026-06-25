package ssafy.E105.domain.resource.controller;

import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.bind.annotation.*;
import ssafy.E105.domain.resource.dto.response.ResourceDetailResponse;
import ssafy.E105.domain.resource.dto.response.ResourceListResponse;
import ssafy.E105.domain.resource.enums.ResourceType;
import ssafy.E105.domain.resource.enums.SortType;
import ssafy.E105.domain.resource.service.ResourceService;
import ssafy.E105.global.common.response.ApiResponse;

@RestController
@RequiredArgsConstructor
@RequestMapping("/v1/resources")
public class ResourceController {

    private final ResourceService resourceService;

    @GetMapping
    public ResponseEntity<ApiResponse<ResourceListResponse>> getResources(
            @RequestParam(required = false) String keyword,
            @RequestParam(defaultValue = "ALL") ResourceType type,
            @RequestParam(defaultValue = "SCORE") SortType sort,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        Long userId = getCurrentUserId();
        ResourceListResponse result = resourceService.getResources(keyword, type, sort, page, size, userId);
        return ResponseEntity.ok(ApiResponse.success("리소스 목록 조회가 완료되었습니다.", result));
    }

    @GetMapping("/{type}/{id}")
    public ResponseEntity<ApiResponse<ResourceDetailResponse>> getResourceDetail(
            @PathVariable ResourceType type,
            @PathVariable Long id) {
        Long userId = getCurrentUserId();
        ResourceDetailResponse result = resourceService.getResourceDetail(type, id, userId);
        return ResponseEntity.ok(ApiResponse.success("리소스 상세 조회가 완료되었습니다.", result));
    }

    private Long getCurrentUserId() {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        if (authentication != null && authentication.getPrincipal() instanceof Long) {
            return (Long) authentication.getPrincipal();
        }
        return null;
    }

}
