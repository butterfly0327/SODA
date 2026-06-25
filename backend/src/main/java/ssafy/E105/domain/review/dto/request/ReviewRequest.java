package ssafy.E105.domain.review.dto.request;

public record ReviewRequest(
        Integer rating,
        String content
) {}
