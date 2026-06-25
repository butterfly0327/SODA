package ssafy.E105.domain.user.dto.response;

public record MyPostResponse(
        Long id,
        String title,
        String createdAt,
        int likeCount,
        int referenceCount
) {
}
