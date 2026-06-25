package ssafy.E105.domain.user.dto.response;

public record MyReviewResponse(
        Long id,
        String resourceType,
        Long resourceId,
        String resourceTitle,
        int rating,
        String content,
        String createdAt
) {
}
