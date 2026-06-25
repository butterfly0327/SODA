package ssafy.E105.domain.superapp.dto;

import com.fasterxml.jackson.annotation.JsonInclude;

import java.util.List;

@JsonInclude(JsonInclude.Include.NON_NULL)
public record SuperAppResourceDetailResponse(
        Long id,
        String type,
        String title,
        Double score,
        Boolean isFree,
        String createdAt,
        DatasetDetail datasetDetail,
        OpenApiDetail openApiDetail
) {

    public record DatasetDetail(
            String subtitle,
            String descriptionShort,
            String descriptionLong,
            String publisherName,
            List<String> domains,
            List<String> tasks,
            List<String> modalities,
            List<String> tags,
            List<String> languages,
            String licenseName,
            String licenseUrl,
            Boolean commercialUseAllowed,
            String accessType,
            Long rowCount,
            Long datasetSizeBytes,
            String sourceUpdatedAt,
            String canonicalUrl,
            String landingUrl,
            String schemaJson
    ) {}

    public record OpenApiDetail(
            String description,
            String provider,
            String baseUrl,
            String docsUrl,
            String authType,
            String category,
            List<String> tags,
            Integer rateLimit,
            Integer dailyLimit,
            String pricingNote,
            Boolean commercialUse,
            Boolean requiresApproval,
            String responseFormat,
            Double avgResponseTime
    ) {}
}
