package ssafy.E105.domain.superapp.dto;

import java.util.List;

public record SuperAppResourceListResponse(
        int totalCount,
        int totalPages,
        int currentPage,
        boolean hasNext,
        List<SuperAppResourceItemResponse> items
) {}
