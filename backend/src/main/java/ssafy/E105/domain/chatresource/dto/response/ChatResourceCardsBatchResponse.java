package ssafy.E105.domain.chatresource.dto.response;

import java.util.List;

public record ChatResourceCardsBatchResponse(
        List<Card> cards,
        List<ItemError> errors
) {
    public record Card(
            Long id,
            String name,
            String type,
            String updatedAt,
            Boolean isFree,
            String sourceName,
            Double recommendationScore,
            Integer rank
    ) {
    }

    public record ItemError(
            String resourceType,
            Long resourceId,
            String code,
            String message
    ) {
    }
}
