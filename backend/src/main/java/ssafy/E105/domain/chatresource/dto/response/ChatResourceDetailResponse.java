package ssafy.E105.domain.chatresource.dto.response;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.databind.JsonNode;

import java.util.List;

@JsonInclude(JsonInclude.Include.ALWAYS)
public record ChatResourceDetailResponse(
        Long id,
        String name,
        String type,
        String updatedAt,
        Boolean isFree,
        String sourceName,
        Double recommendationScore,
        String originUrl,
        DatasetDetail datasetDetail,
        OpenApiDetail openApiDetail
) {
    public record DatasetDetail(
            String descriptionLong,
            JsonNode schemaJson,
            Long datasetSizeBytes,
            Long rowCount,
            JsonNode metrics,
            String licenseName,
            List<String> classification,
            List<String> tags,
            List<String> languages
    ) {
    }

    public record OpenApiDetail(
            String description,
            String authType,
            String category,
            List<String> tags,
            Integer rateLimit,
            Integer dailyLimit,
            String pricingNote,
            String responseFormat,
            Double avgResponseTime,
            JsonNode responseSchema
    ) {
    }
}
