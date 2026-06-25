package ssafy.E105.domain.post.dto.response;

import java.util.List;

public record PostListResponse(
        List<PostListItemResponse> content,
        int page,
        int size,
        long totalElements,
        int totalPages,
        String sort
) {
}
