package ssafy.E105.domain.superapp.dto;

import com.fasterxml.jackson.annotation.JsonInclude;

@JsonInclude(JsonInclude.Include.NON_NULL)
public record SuperAppResourceItemResponse(
        Long id,
        String type,
        String title,
        Double score,
        Boolean isFree,
        String createdAt,
        DatasetMeta datasetMeta,
        OpenApiMeta openApiMeta
) {
    public record DatasetMeta(
            String publisherName,
            String sourceUpdatedAt,
            Long sampleCount
    ) {}

    public record OpenApiMeta(
            String category,
            Double avgResponseTime,
            String authType,
            Integer dailyLimit
    ) {}
}
