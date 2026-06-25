package ssafy.E105.domain.review.dto.response;

public record ReviewResponse(
        Long id,
        Integer rating,
        String content,
        String createdAt
) {}
