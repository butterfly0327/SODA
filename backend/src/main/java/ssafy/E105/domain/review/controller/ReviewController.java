package ssafy.E105.domain.review.controller;

import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;
import ssafy.E105.domain.resource.enums.ResourceType;
import ssafy.E105.domain.review.dto.request.ReviewRequest;
import ssafy.E105.domain.review.dto.response.ReviewResponse;
import ssafy.E105.domain.review.service.ReviewService;
import ssafy.E105.global.common.response.ApiResponse;

@RestController
@RequiredArgsConstructor
@RequestMapping("/v1/resources")
public class ReviewController {

    private final ReviewService reviewService;

    @PostMapping("/{type}/{id}/reviews")
    public ResponseEntity<ApiResponse<ReviewResponse>> createReview(
            @PathVariable ResourceType type,
            @PathVariable Long id,
            @RequestBody ReviewRequest request,
            @AuthenticationPrincipal Long userId) {
        return reviewService.createReview(type, id, request, userId);
    }

    @PutMapping("/{type}/{id}/reviews/{reviewId}")
    public ResponseEntity<ApiResponse<ReviewResponse>> updateReview(
            @PathVariable ResourceType type,
            @PathVariable Long id,
            @PathVariable Long reviewId,
            @RequestBody ReviewRequest request,
            @AuthenticationPrincipal Long userId) {
        return reviewService.updateReview(reviewId, request, userId);
    }

    @DeleteMapping("/{type}/{id}/reviews/{reviewId}")
    public ResponseEntity<ApiResponse<Void>> deleteReview(
            @PathVariable ResourceType type,
            @PathVariable Long id,
            @PathVariable Long reviewId,
            @AuthenticationPrincipal Long userId) {
        return reviewService.deleteReview(reviewId, userId);
    }
}
