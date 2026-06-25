package ssafy.E105.domain.resource.service;

import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import ssafy.E105.domain.bookmark.entity.BookmarkEntity;
import ssafy.E105.domain.bookmark.repository.BookmarkRepository;
import ssafy.E105.domain.dataset.entity.DatasetEntity;
import ssafy.E105.domain.dataset.repository.DatasetRepository;
import ssafy.E105.domain.dataset.repository.DatasetSourceRepository;
import ssafy.E105.domain.openapi.entity.OpenApiEntity;
import ssafy.E105.domain.openapi.repository.OpenApiRepository;
import ssafy.E105.domain.openapi.repository.OpenApiSourceRepository;
import ssafy.E105.domain.resource.dto.response.ResourceDetailResponse;
import ssafy.E105.domain.resource.dto.response.ResourceItemResponse;
import ssafy.E105.domain.resource.dto.response.ResourceListResponse;
import ssafy.E105.domain.resource.enums.ResourceType;
import ssafy.E105.domain.resource.enums.SortType;
import ssafy.E105.domain.review.entity.ReviewEntity;
import ssafy.E105.domain.review.repository.ReviewRepository;
import ssafy.E105.domain.user.entity.UserEntity;
import ssafy.E105.domain.user.repository.UserRepository;
import ssafy.E105.global.common.util.KstDateTimeFormatter;
import ssafy.E105.global.exception.CustomException;
import ssafy.E105.global.exception.ErrorCode;

import java.util.*;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;
import java.util.stream.Stream;

@Service
@RequiredArgsConstructor
public class ResourceService {
    private static final long COUNT_CACHE_TTL_MILLIS = 30_000L;
    private static final int MAX_COUNT_CACHE_ENTRIES = 256;

    private final DatasetRepository datasetRepository;
    private final OpenApiRepository openApiRepository;
    private final DatasetSourceRepository datasetSourceRepository;
    private final OpenApiSourceRepository openApiSourceRepository;
    private final ReviewRepository reviewRepository;
    private final BookmarkRepository bookmarkRepository;
    private final UserRepository userRepository;
    private final Map<ResourceCountCacheKey, ResourceCountCacheEntry> resourceCountCache =
            new ConcurrentHashMap<>();

    public ResourceListResponse getResources(
            String keyword, ResourceType type, SortType sort, int page, int size, Long userId) {

        String kw = keyword != null && !keyword.isBlank() ? keyword : null;
        int offset = page * size;

        // 북마크 정보 한 번에 가져오기 (userId가 있을 때만)
        Map<Long, Boolean> bookmarkMap = userId != null ? calcBookmarkMap(userId) : Map.of();

        List<ResourceItemResponse> items;
        int totalCount;

        if (type == ResourceType.DATASET) {
            // COUNT + SELECT 병렬 실행
            CompletableFuture<Long> countFuture =
                    CompletableFuture.supplyAsync(() -> getCachedCount(
                            ResourceType.DATASET,
                            kw,
                            () -> datasetRepository.countActive(kw)
                    ));
            CompletableFuture<List<DatasetEntity>> dataFuture =
                    CompletableFuture.supplyAsync(() -> sort == SortType.SCORE
                            ? datasetRepository.searchActivePagedByScore(kw, offset, size)
                            : datasetRepository.searchActivePagedByLatest(kw, offset, size));
            totalCount = countFuture.join().intValue();
            List<DatasetEntity> datasets = dataFuture.join();
            if (sort == SortType.SCORE) {
                items = datasets.stream().map(d -> toDatasetItem(d, d.getAvgRating(), bookmarkMap)).toList();
            } else {
                Map<Long, Double> scoreMap = calcScoreMap(ResourceType.DATASET,
                        datasets.stream().map(DatasetEntity::getId).toList());
                items = datasets.stream().map(d -> toDatasetItem(d, scoreMap.get(d.getId()), bookmarkMap)).toList();
            }

        } else if (type == ResourceType.OPEN_API) {
            // COUNT + SELECT 병렬 실행
            CompletableFuture<Long> countFuture =
                    CompletableFuture.supplyAsync(() -> getCachedCount(
                            ResourceType.OPEN_API,
                            kw,
                            () -> openApiRepository.countActive(kw)
                    ));
            CompletableFuture<List<OpenApiEntity>> dataFuture =
                    CompletableFuture.supplyAsync(() -> sort == SortType.SCORE
                            ? openApiRepository.searchActivePagedByScore(kw, offset, size)
                            : openApiRepository.searchActivePagedByLatest(kw, offset, size));
            totalCount = countFuture.join().intValue();
            List<OpenApiEntity> openApis = dataFuture.join();
            if (sort == SortType.SCORE) {
                items = openApis.stream().map(o -> toOpenApiItem(o, o.getAvgRating(), bookmarkMap)).toList();
            } else {
                Map<Long, Double> scoreMap = calcScoreMap(ResourceType.OPEN_API,
                        openApis.stream().map(OpenApiEntity::getId).toList());
                items = openApis.stream().map(o -> toOpenApiItem(o, scoreMap.get(o.getId()), bookmarkMap)).toList();
            }

        } else { // ALL: DATASET 먼저, OPEN_API 뒤에 (글로벌 offset 기반)
            // Phase 1: COUNT 병렬 실행
            CompletableFuture<Long> datasetCountFuture =
                    CompletableFuture.supplyAsync(() -> getCachedCount(
                            ResourceType.DATASET,
                            kw,
                            () -> datasetRepository.countActive(kw)
                    ));
            CompletableFuture<Long> openApiCountFuture =
                    CompletableFuture.supplyAsync(() -> getCachedCount(
                            ResourceType.OPEN_API,
                            kw,
                            () -> openApiRepository.countActive(kw)
                    ));
            long datasetCount = datasetCountFuture.join();
            long openApiCount = openApiCountFuture.join();
            totalCount = (int) (datasetCount + openApiCount);

            List<DatasetEntity> datasets;
            List<OpenApiEntity> openApis;

            if (offset < datasetCount) {
                int datasetSize = (int) Math.min(size, datasetCount - offset);
                int remaining = size - datasetSize;

                if (remaining > 0) {
                    // 경계: dataset + openapi Phase 2 병렬 fetch
                    CompletableFuture<List<DatasetEntity>> datasetFuture =
                            CompletableFuture.supplyAsync(() -> sort == SortType.SCORE
                                    ? datasetRepository.searchActivePagedByScore(kw, offset, datasetSize)
                                    : datasetRepository.searchActivePagedByLatest(kw, offset, datasetSize));
                    CompletableFuture<List<OpenApiEntity>> openApiFuture =
                            CompletableFuture.supplyAsync(() -> sort == SortType.SCORE
                                    ? openApiRepository.searchActivePagedByScore(kw, 0, remaining)
                                    : openApiRepository.searchActivePagedByLatest(kw, 0, remaining));
                    datasets = datasetFuture.join();
                    openApis = openApiFuture.join();
                } else {
                    // dataset 구간만
                    datasets = sort == SortType.SCORE
                            ? datasetRepository.searchActivePagedByScore(kw, offset, datasetSize)
                            : datasetRepository.searchActivePagedByLatest(kw, offset, datasetSize);
                    openApis = List.of();
                }
            } else {
                // dataset 구간을 완전히 지나침 → openapi 구간
                int openApiOffset = (int) (offset - datasetCount);
                datasets = List.of();
                openApis = sort == SortType.SCORE
                        ? openApiRepository.searchActivePagedByScore(kw, openApiOffset, size)
                        : openApiRepository.searchActivePagedByLatest(kw, openApiOffset, size);
            }

            if (sort == SortType.SCORE) {
                items = Stream.concat(
                        datasets.stream().map(d -> toDatasetItem(d, d.getAvgRating(), bookmarkMap)),
                        openApis.stream().map(o -> toOpenApiItem(o, o.getAvgRating(), bookmarkMap))
                ).toList();
            } else {
                Map<Long, Double> datasetScoreMap = calcScoreMap(ResourceType.DATASET,
                        datasets.stream().map(DatasetEntity::getId).toList());
                Map<Long, Double> openApiScoreMap = calcScoreMap(ResourceType.OPEN_API,
                        openApis.stream().map(OpenApiEntity::getId).toList());
                items = Stream.concat(
                        datasets.stream().map(d -> toDatasetItem(d, datasetScoreMap.get(d.getId()), bookmarkMap)),
                        openApis.stream().map(o -> toOpenApiItem(o, openApiScoreMap.get(o.getId()), bookmarkMap))
                ).toList();
            }
        }

        int totalPages = size == 0 ? 1 : (int) Math.ceil((double) totalCount / size);
        return new ResourceListResponse(totalCount, totalPages, page, page < totalPages - 1, items);
    }

    private ResourceItemResponse toDatasetItem(DatasetEntity d, Double score, Map<Long, Boolean> bookmarkMap) {
        boolean isBookmarked = bookmarkMap.getOrDefault(d.getId(), false);
        return new ResourceItemResponse(
                d.getId(),
                ResourceType.DATASET.name(),
                d.getTitle(),
                score,
                d.getPaymentRequired() == null || !d.getPaymentRequired(),
                KstDateTimeFormatter.format(d.getCreatedAt()),
                isBookmarked,
                new ResourceItemResponse.DatasetMeta(
                        resolveDatasetSiteName(d),
                        KstDateTimeFormatter.formatDate(d.getSourceUpdatedAt()),
                        d.getRowCount(),
                        d.getDomains(),
                        d.getAccessType(),
                        d.getCommercialUseAllowed(),
                        d.getTags()
                ),
                null
        );
    }

    private ResourceItemResponse toOpenApiItem(OpenApiEntity o, Double score, Map<Long, Boolean> bookmarkMap) {
        boolean isBookmarked = bookmarkMap.getOrDefault(o.getId(), false);
        return new ResourceItemResponse(
                o.getId(),
                ResourceType.OPEN_API.name(),
                o.getName(),
                score,
                o.getIsFree(),
                KstDateTimeFormatter.format(o.getCreatedAt()),
                isBookmarked,
                null,
                new ResourceItemResponse.OpenApiMeta(
                        resolveOpenApiSiteName(o),
                        o.getCategory(),
                        o.getAvgResponseTime(),
                        o.getAuthType(),
                        o.getDailyLimit(),
                        o.getResponseFormat(),
                        o.getCommercialUse(),
                        o.getTags()
                )
        );
    }

    public ResourceDetailResponse getResourceDetail(ResourceType type, Long id, Long userId) {
        if (type == ResourceType.ALL) {
            throw new CustomException(ErrorCode.INVALID_INPUT);
        }

        Map<Long, Double> scoreMap = calcScoreMap(type, List.of(id));
        Double score = scoreMap.get(id);

        // 북마크 정보 한 번에 가져오기
        Map<Long, Boolean> bookmarkMap = userId != null ? calcBookmarkMap(userId) : Map.of();
        boolean isBookmarked = bookmarkMap.getOrDefault(id, false);

        List<ReviewEntity> reviewEntities =
                reviewRepository.findByResourceTypeAndResourceIdAndIsDeletedFalseOrderByCreatedAtDesc(type.name(), id);

        List<Long> userIds = reviewEntities.stream()
                .map(ReviewEntity::getUserId) // Review 엔티티의 userId 필드
                .distinct()
                .toList();

        Map<Long, String> userNameMap = userRepository.findAllById(userIds).stream()
                .collect(Collectors.toMap(UserEntity::getId, UserEntity::getName));

        List<ResourceDetailResponse.ReviewItem> reviews = reviewEntities.stream()
                .map(r -> new ResourceDetailResponse.ReviewItem(
                        r.getId(),
                        r.getUserId(),
                        userNameMap.getOrDefault(r.getUserId(), "알 수 없는 사용자"), // ID로 이름 찾기
                        r.getRating().intValue(),
                        r.getContent(),
                        KstDateTimeFormatter.format(r.getCreatedAt())
                )).toList();

        if (type == ResourceType.DATASET) {
            DatasetEntity d = datasetRepository.findByIdAndStatus(id, "ACTIVE")
                    .orElseThrow(() -> new CustomException(ErrorCode.RESOURCE_NOT_FOUND));

            return new ResourceDetailResponse(
                    d.getId(),
                    ResourceType.DATASET.name(),
                    d.getTitle(),
                    score,
                    d.getPaymentRequired() == null || !d.getPaymentRequired(),
                    KstDateTimeFormatter.format(d.getCreatedAt()),
                    isBookmarked,
                    new ResourceDetailResponse.DatasetDetail(
                            d.getSubtitle(),
                            d.getDescriptionShort(),
                            d.getDescriptionLong(),
                            resolveDatasetSiteName(d),
                            d.getDomains(),
                            d.getTasks(),
                            d.getModalities(),
                            d.getTags(),
                            d.getLanguages(),
                            d.getLicenseName(),
                            d.getLicenseUrl(),
                            d.getCommercialUseAllowed(),
                            d.getAccessType(),
                            d.getRowCount(),
                            d.getDatasetSizeBytes(),
                            KstDateTimeFormatter.formatDate(d.getSourceUpdatedAt()),
                            d.getCanonicalUrl(),
                            d.getLandingUrl(),
                            d.getSchemaJson()
                    ),
                    null,
                    reviews
            );
        } else {
            OpenApiEntity o = openApiRepository.findByIdAndIsDeletedFalse(id)
                    .orElseThrow(() -> new CustomException(ErrorCode.RESOURCE_NOT_FOUND));

            return new ResourceDetailResponse(
                    o.getId(),
                    ResourceType.OPEN_API.name(),
                    o.getName(),
                    score,
                    o.getIsFree(),
                    KstDateTimeFormatter.format(o.getCreatedAt()),
                    isBookmarked,
                    null,
                    new ResourceDetailResponse.OpenApiDetail(
                            o.getDescription(),
                            resolveOpenApiSiteName(o),
                            o.getBaseUrl(),
                            o.getDocsUrl(),
                            o.getAuthType(),
                            o.getCategory(),
                            o.getTags(),
                            o.getRateLimit(),
                            o.getDailyLimit(),
                            o.getPricingNote(),
                            o.getCommercialUse(),
                            o.isRequiresApproval(),
                            o.getResponseFormat(),
                            o.getAvgResponseTime()
                    ),
                    reviews
            );
        }
    }

    // 점수순 or 최신순 정렬
    private void sort(List<ResourceItemResponse> items, SortType sort) {
        Comparator<ResourceItemResponse> comparator = switch (sort) {
            case SCORE -> Comparator.comparing(ResourceItemResponse::score,
                    Comparator.nullsLast(Comparator.reverseOrder()));
            case LATEST -> Comparator.comparing(ResourceItemResponse::createdAt,
                    Comparator.nullsLast(Comparator.reverseOrder()));
        };
        items.sort(comparator);
    }

    // AVG(rating)
    private Map<Long, Double> calcScoreMap(ResourceType type, List<Long> ids) {
        if (ids.isEmpty()) return Map.of();
        return reviewRepository.findAvgRatingByTypeAndIds(type.name(), ids).stream()
                .collect(Collectors.toMap(
                        row -> (Long) row[0],
                        row -> ((Number) row[1]).doubleValue()
                ));
    }

    // 북마크 여부 확인 (한 번의 쿼리로 모든 북마크 IDs 가져오기)
    private Map<Long, Boolean> calcBookmarkMap(Long userId) {
        if (userId == null) return Map.of();
        
        // 사용자의 모든 북마크 가져오기
        List<BookmarkEntity> bookmarks = bookmarkRepository.findByUserIdAndDeletedAtIsNull(userId);
        
        // resourceId -> true 매핑
        return bookmarks.stream()
                .collect(Collectors.toMap(
                        BookmarkEntity::getResourceId,
                        b -> true,
                        (existing, replacement) -> existing
                ));
    }

    private String resolveDatasetSiteName(DatasetEntity dataset) {
        if (dataset.getDatasetSourceId() != null) {
            String sourceName = datasetSourceRepository.findById(dataset.getDatasetSourceId())
                    .map(source -> source.getSourceName())
                    .orElse(null);
            if (sourceName != null && !sourceName.isBlank()) {
                return sourceName;
            }
        }
        return dataset.getPublisherName();
    }

    private String resolveOpenApiSiteName(OpenApiEntity openApi) {
        if (openApi.getOpenapiSourceId() != null) {
            String sourceName = openApiSourceRepository.findById(openApi.getOpenapiSourceId())
                    .map(source -> source.getSourceName())
                    .orElse(null);
            if (sourceName != null && !sourceName.isBlank()) {
                return sourceName;
            }
        }
        return openApi.getProvider();
    }

    private long getCachedCount(ResourceType type, String keyword, CountSupplier loader) {
        long now = System.currentTimeMillis();
        ResourceCountCacheKey key = new ResourceCountCacheKey(type, normalizeKeyword(keyword));

        if (resourceCountCache.size() > MAX_COUNT_CACHE_ENTRIES) {
            evictExpiredCounts(now);
        }

        ResourceCountCacheEntry entry = resourceCountCache.compute(key, (_key, existing) -> {
            if (existing != null && existing.expiresAtMillis() > now) {
                return existing;
            }
            return new ResourceCountCacheEntry(loader.get(), now + COUNT_CACHE_TTL_MILLIS);
        });
        return entry.count();
    }

    private void evictExpiredCounts(long now) {
        resourceCountCache.entrySet().removeIf(entry -> entry.getValue().expiresAtMillis() <= now);
    }

    private String normalizeKeyword(String keyword) {
        if (keyword == null) {
            return null;
        }
        String normalized = keyword.trim();
        if (normalized.isEmpty()) {
            return null;
        }
        return normalized.toLowerCase(Locale.ROOT);
    }

    @FunctionalInterface
    private interface CountSupplier {
        long get();
    }

    private record ResourceCountCacheKey(ResourceType type, String keyword) {}

    private record ResourceCountCacheEntry(long count, long expiresAtMillis) {}
}
