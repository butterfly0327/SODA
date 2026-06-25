package ssafy.E105.domain.post.dto.response;

public record PostListItemResponse(
        Long postId,
        Long authorId,
        String name,
        String title,
        int viewCount,
        int favorite,
        String createdAt,
        String updatedAt
) {
}
