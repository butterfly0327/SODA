package ssafy.E105.domain.post.dto.request;

import java.util.List;

public record UpdatePostRequest(
        String title,
        String content,
        List<Long> datasetIds,
        List<Long> openApiIds
) {
}
