package ssafy.E105.domain.bookmark.dto.request;

import ssafy.E105.domain.resource.enums.ResourceType;

public record BookmarkRequest(
        ResourceType resourceType,
        Long resourceId
) {
}
