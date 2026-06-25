package ssafy.E105.domain.post.dto.response;

import java.util.List;

public record PostDetailResponse(
        Long postId,
        Long authorId,
        String name,
        String title,
        String content,
        int viewCount,
        int favorite,
        List<PostResourceReferenceResponse> datasetReferences,
        List<PostResourceReferenceResponse> openApiReferences,
        String createdAt,
        String updatedAt
) {
}
