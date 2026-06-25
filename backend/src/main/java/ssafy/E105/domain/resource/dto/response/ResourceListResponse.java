package ssafy.E105.domain.resource.dto.response;

import java.util.List;

public record ResourceListResponse(
        int totalCount,
        int totalPages,
        int currentPage,
        boolean hasNext,
        List<ResourceItemResponse> items
) {}
