package ssafy.E105.domain.review.service;

import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import ssafy.E105.domain.dataset.repository.DatasetRepository;
import ssafy.E105.domain.openapi.repository.OpenApiRepository;
import ssafy.E105.domain.resource.enums.ResourceType;
import ssafy.E105.domain.review.dto.request.ReviewRequest;
import ssafy.E105.domain.review.dto.response.ReviewResponse;
import ssafy.E105.domain.review.entity.ReviewEntity;
import ssafy.E105.domain.review.repository.ReviewRepository;
import ssafy.E105.global.common.util.KstDateTimeFormatter;
import ssafy.E105.global.common.response.ApiResponse;
import ssafy.E105.global.exception.CustomException;
import ssafy.E105.global.exception.ErrorCode;

@Service
@RequiredArgsConstructor
public class ReviewService {

    private final DatasetRepository datasetRepository;
    private final OpenApiRepository openApiRepository;
    private final ReviewRepository reviewRepository;

    @Transactional
    public ResponseEntity<ApiResponse<ReviewResponse>> createReview(
            ResourceType type, Long resourceId, ReviewRequest request, Long userId) {

        if (type == ResourceType.ALL) {
            throw new CustomException(ErrorCode.INVALID_INPUT);
        }
        if (request.rating() == null || request.rating() < 1 || request.rating() > 5) {
            throw new CustomException(ErrorCode.INVALID_RATING);
        }

        // 리소스 존재 확인
        if (type == ResourceType.DATASET) {
            datasetRepository.findByIdAndStatus(resourceId, "ACTIVE")
                    .orElseThrow(() -> new CustomException(ErrorCode.RESOURCE_NOT_FOUND));
        } else {
            openApiRepository.findByIdAndIsDeletedFalse(resourceId)
                    .orElseThrow(() -> new CustomException(ErrorCode.RESOURCE_NOT_FOUND));
        }

        // 중복 리뷰 확인
        if (reviewRepository.existsByUserIdAndResourceTypeAndResourceIdAndIsDeletedFalse(
                userId, type.name(), resourceId)) {
            throw new CustomException(ErrorCode.DUPLICATE_REVIEW);
        }

        ReviewEntity saved = reviewRepository.save(
                ReviewEntity.create(userId, type.name(), resourceId,
                        request.rating().shortValue(), request.content()));

        updateAvgRating(type, resourceId);

        return ResponseEntity.status(201).body(ApiResponse.created(
                "리뷰가 등록되었습니다.",
                new ReviewResponse(
                        saved.getId(),
                        saved.getRating().intValue(),
                        saved.getContent(),
                        KstDateTimeFormatter.format(saved.getCreatedAt())
                )));
    }

    @Transactional
    public ResponseEntity<ApiResponse<ReviewResponse>> updateReview(
            Long reviewId, ReviewRequest request, Long userId) {

        if (request.rating() == null || request.rating() < 1 || request.rating() > 5) {
            throw new CustomException(ErrorCode.INVALID_RATING);
        }

        ReviewEntity review = reviewRepository.findByIdAndIsDeletedFalse(reviewId)
                .orElseThrow(() -> new CustomException(ErrorCode.REVIEW_NOT_FOUND));

        if (!review.getUserId().equals(userId)) {
            throw new CustomException(ErrorCode.REVIEW_FORBIDDEN);
        }

        review.update(request.rating().shortValue(), request.content());
        reviewRepository.save(review);

        updateAvgRating(ResourceType.valueOf(review.getResourceType()), review.getResourceId());

        return ResponseEntity.ok(ApiResponse.success(
                "리뷰가 수정되었습니다.",
                new ReviewResponse(
                        review.getId(),
                        review.getRating().intValue(),
                        review.getContent(),
                        KstDateTimeFormatter.format(review.getCreatedAt())
                )));
    }

    @Transactional
    public ResponseEntity<ApiResponse<Void>> deleteReview(Long reviewId, Long userId) {
        ReviewEntity review = reviewRepository.findByIdAndIsDeletedFalse(reviewId)
                .orElseThrow(() -> new CustomException(ErrorCode.REVIEW_NOT_FOUND));

        if (!review.getUserId().equals(userId)) {
            throw new CustomException(ErrorCode.REVIEW_FORBIDDEN);
        }

        review.delete();
        reviewRepository.save(review);

        updateAvgRating(ResourceType.valueOf(review.getResourceType()), review.getResourceId());

        return ResponseEntity.ok(ApiResponse.success("리뷰가 삭제되었습니다.", null));
    }

    private void updateAvgRating(ResourceType type, Long resourceId) {
        double avg = reviewRepository.findAvgRatingByTypeAndId(type.name(), resourceId);
        if (type == ResourceType.DATASET) {
            datasetRepository.updateAvgRating(resourceId, avg);
        } else {
            openApiRepository.updateAvgRating(resourceId, avg);
        }
    }
}
