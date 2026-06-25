package ssafy.E105.domain.superapp.dto;

import com.fasterxml.jackson.databind.JsonNode;

import java.util.List;

public record SuperAppPromptRecommendationResponse(
        String mergedReason,
        String datasetReason,
        String openApiReason,
        List<DatasetRecommendation> datasetRecommendations,
        List<OpenApiRecommendation> openApiRecommendations
) {
    public record DatasetRecommendation(
            Long datasetId,
            Integer rank,
            Double suitabilityScore,
            DatasetCard card,
            DatasetDetail detail,
            List<Review> reviews
    ) {
    }

    public record OpenApiRecommendation(
            Long openApiId,
            Integer rank,
            Double score,
            OpenApiCard card,
            OpenApiDetail detail,
            List<Review> reviews
    ) {
    }

    public record DatasetCard(
            String title,
            String sourceName,
            String updatedAt,
            Boolean isFree
    ) {
    }

    public record OpenApiCard(
            String name,
            String provider,
            String updatedAt,
            Boolean isFree
    ) {
    }

    public record DatasetDetail(
            String canonicalUrl,
            String descriptionLong,
            Long rowCount,
            String lastUpdate,
            List<String> domains,
            List<String> tasks,
            List<String> modalities,
            List<String> tags,
            String accessType,
            Boolean loginRequired,
            Boolean approvalRequired,
            Boolean isRestricted,
            String licenseName,
            Boolean commercialUseAllowed,
            List<String> languages,
            Metrics metrics,
            String sourceVersion,
            String sourceCreatedAt,
            String sourceUpdatedAt,
            String createdAt,
            List<Creator> creators,
            JsonNode schemaJson
    ) {
    }

    public record OpenApiDetail(
            String docsUrl,
            String description,
            String authType,
            String category,
            String responseFormat,
            List<String> tags,
            String pricingNote,
            Boolean commercialUse,
            Boolean requiresApproval
    ) {
    }

    public record Metrics(
            Long viewCount,
            Long requestCount
    ) {
    }

    public record Creator(
            String name,
            String role,
            String phone,
            String url
    ) {
    }

    public record Review(
            Long id,
            String name,
            Integer rating,
            String content,
            String createdAt
    ) {
    }
}
