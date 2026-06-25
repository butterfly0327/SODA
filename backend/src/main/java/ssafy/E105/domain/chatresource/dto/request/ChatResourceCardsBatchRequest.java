package ssafy.E105.domain.chatresource.dto.request;

import ssafy.E105.domain.resource.enums.ResourceType;

import java.util.List;

public record ChatResourceCardsBatchRequest(
        List<Item> items
) {
    public record Item(
            ResourceType resourceType,
            Long resourceId,
            Double recommendationScore,
            Integer rank
    ) {
    }
}
