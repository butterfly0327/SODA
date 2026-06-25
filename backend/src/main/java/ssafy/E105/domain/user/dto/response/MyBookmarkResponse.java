package ssafy.E105.domain.user.dto.response;

import com.fasterxml.jackson.annotation.JsonInclude;

import java.util.List;

@JsonInclude(JsonInclude.Include.NON_NULL)
public record MyBookmarkResponse(
        Long bookmarkId,
        Long id,
        String type,
        String title,
        Double score,
        Boolean isFree,
        Boolean isBookmarked,
        String createdAt,
        String bookmarkedAt,
        DatasetMeta datasetMeta,
        OpenApiMeta openApiMeta
) {
    public record DatasetMeta(
            String publisherName,
            String sourceUpdatedAt,
            Long sampleCount,
            List<String> domains,
            String accessType,
            Boolean commercialUseAllowed,
            List<String> tags
    ) {}

    public record OpenApiMeta(
            String provider,
            String category,
            Double avgResponseTime,
            String authType,
            Integer dailyLimit,
            String responseFormat,
            Boolean commercialUse,
            List<String> tags
    ) {}
}
