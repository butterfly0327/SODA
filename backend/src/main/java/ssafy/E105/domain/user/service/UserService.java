package ssafy.E105.domain.user.service;

import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import ssafy.E105.domain.bookmark.entity.BookmarkEntity;
import ssafy.E105.domain.bookmark.repository.BookmarkRepository;
import ssafy.E105.domain.chat.entity.ConversationEntity;
import ssafy.E105.domain.chat.repository.ConversationRepository;
import ssafy.E105.domain.dataset.entity.DatasetEntity;
import ssafy.E105.domain.dataset.repository.DatasetRepository;
import ssafy.E105.domain.openapi.entity.OpenApiEntity;
import ssafy.E105.domain.openapi.repository.OpenApiRepository;
import ssafy.E105.domain.post.entity.PostEntity;
import ssafy.E105.domain.post.repository.PostRepository;
import ssafy.E105.domain.review.entity.ReviewEntity;
import ssafy.E105.domain.review.repository.ReviewRepository;
import ssafy.E105.domain.user.dto.response.MyBookmarkResponse;
import ssafy.E105.domain.user.dto.response.MyPostResponse;
import ssafy.E105.domain.user.dto.response.MyReviewResponse;
import ssafy.E105.domain.user.dto.response.PageResponse;
import ssafy.E105.domain.user.dto.response.UserProfileResponse;
import ssafy.E105.domain.user.entity.UserEntity;
import ssafy.E105.domain.user.repository.UserRepository;
import ssafy.E105.global.common.util.KstDateTimeFormatter;
import ssafy.E105.global.common.response.ApiResponse;
import ssafy.E105.global.exception.CustomException;
import ssafy.E105.global.exception.ErrorCode;

import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;
import java.time.LocalDateTime;

@Service
@RequiredArgsConstructor
public class UserService {

    private static final Logger logger = LoggerFactory.getLogger(UserService.class);

    private final UserRepository userRepository;
    private final ReviewRepository reviewRepository;
    private final PostRepository postRepository;
    private final BookmarkRepository bookmarkRepository;
    private final ConversationRepository conversationRepository;
    private final DatasetRepository datasetRepository;
    private final OpenApiRepository openApiRepository;
    private final RedisTemplate<String, String> redisTemplate;

    public ResponseEntity<ApiResponse<UserProfileResponse>> getMyProfile(Long userId) {
        UserEntity user = userRepository.findById(userId)
                .orElseThrow(() -> new CustomException(ErrorCode.INVALID_USER));
        
        if (user.isDeleted()) {
            throw new CustomException(ErrorCode.INVALID_USER);
        }

        long postCount = postRepository.countByUserIdAndIsDeleted(userId, false);
        long reviewCount = reviewRepository.countByUserIdAndIsDeletedFalse(userId);
        long bookmarkCount = bookmarkRepository.countByUserIdAndDeletedAtIsNull(userId);

        return ResponseEntity.ok(ApiResponse.success(
                "프로필 조회 성공",
                new UserProfileResponse(
                        user.getId(),
                        user.getName(),
                        user.getEmail(),
                        KstDateTimeFormatter.format(user.getCreatedAt()),
                        postCount,
                        reviewCount,
                        bookmarkCount
                )
        ));
    }

    public ResponseEntity<ApiResponse<PageResponse<MyPostResponse>>> getMyPosts(
            Long userId, int page, int size) {
        
        UserEntity user = userRepository.findById(userId)
                .orElseThrow(() -> new CustomException(ErrorCode.INVALID_USER));
        
        if (user.isDeleted()) {
            throw new CustomException(ErrorCode.INVALID_USER);
        }

        Page<PostEntity> postPage = postRepository.findByUserIdAndIsDeletedOrderByCreatedAtDesc(
                userId, false, PageRequest.of(page, size));

        List<MyPostResponse> content = postPage.getContent().stream()
                .map(p -> new MyPostResponse(
                        p.getId(),
                        p.getTitle(),
                        KstDateTimeFormatter.format(p.getCreatedAt()),
                        p.getFavorite(),
                        countReferences(p)
                ))
                .toList();

        return ResponseEntity.ok(ApiResponse.success(
                "내 게시글 목록 조회 성공",
                new PageResponse<>(content, page, size,
                        postPage.getTotalElements(), postPage.getTotalPages())
        ));
    }

    public ResponseEntity<ApiResponse<PageResponse<MyReviewResponse>>> getMyReviews(
            Long userId, int page, int size) {
        
        UserEntity user = userRepository.findById(userId)
                .orElseThrow(() -> new CustomException(ErrorCode.INVALID_USER));
        
        if (user.isDeleted()) {
            throw new CustomException(ErrorCode.INVALID_USER);
        }

        Page<ReviewEntity> reviewPage = reviewRepository.findByUserIdAndIsDeletedFalseOrderByCreatedAtDesc(
                userId, PageRequest.of(page, size));

        List<ReviewEntity> reviews = reviewPage.getContent();

        Set<Long> datasetIds = reviews.stream()
                .filter(r -> "DATASET".equals(r.getResourceType()))
                .map(ReviewEntity::getResourceId)
                .collect(Collectors.toSet());

        Set<Long> openApiIds = reviews.stream()
                .filter(r -> "OPEN_API".equals(r.getResourceType()))
                .map(ReviewEntity::getResourceId)
                .collect(Collectors.toSet());

        Map<Long, String> datasetTitles = datasetRepository.findAllById(datasetIds).stream()
                .collect(Collectors.toMap(d -> d.getId(), d -> d.getTitle() != null ? d.getTitle() : ""));

        Map<Long, String> openApiTitles = openApiRepository.findAllById(openApiIds).stream()
                .collect(Collectors.toMap(o -> o.getId(), o -> o.getName()));

        List<MyReviewResponse> content = reviews.stream()
                .map(r -> {
                    String title = "DATASET".equals(r.getResourceType())
                            ? datasetTitles.getOrDefault(r.getResourceId(), "")
                            : openApiTitles.getOrDefault(r.getResourceId(), "");
                    return new MyReviewResponse(
                            r.getId(),
                            r.getResourceType(),
                            r.getResourceId(),
                            title,
                            r.getRating().intValue(),
                            r.getContent(),
                            KstDateTimeFormatter.format(r.getCreatedAt())
                    );
                })
                .toList();

        return ResponseEntity.ok(ApiResponse.success(
                "내 리뷰 목록 조회 성공",
                new PageResponse<>(content, page, size,
                        reviewPage.getTotalElements(), reviewPage.getTotalPages())
        ));
    }

    public ResponseEntity<ApiResponse<PageResponse<MyBookmarkResponse>>> getMyBookmarks(
            Long userId, int page, int size, String keyword, String type, Boolean freeOnly) {
        
        UserEntity user = userRepository.findById(userId)
                .orElseThrow(() -> new CustomException(ErrorCode.INVALID_USER));
        
        if (user.isDeleted()) {
            throw new CustomException(ErrorCode.INVALID_USER);
        }

        List<BookmarkEntity> bookmarks = bookmarkRepository.findByUserIdAndDeletedAtIsNullOrderByCreatedAtDesc(userId);

        String normalizedKeywordCandidate = keyword == null ? null : keyword.trim();
        final String normalizedKeyword =
                (normalizedKeywordCandidate == null || normalizedKeywordCandidate.isEmpty())
                        ? null
                        : normalizedKeywordCandidate;

        String normalizedTypeCandidate = type == null ? null : type.trim().toUpperCase(Locale.ROOT);
        final String normalizedType =
                (normalizedTypeCandidate == null || normalizedTypeCandidate.isEmpty())
                        ? null
                        : normalizedTypeCandidate;

        // 타입별로 resourceId 모아서 배치 조회
        Set<Long> datasetIds = bookmarks.stream()
                .filter(b -> "DATASET".equals(b.getResourceType()))
                .map(BookmarkEntity::getResourceId)
                .collect(Collectors.toSet());

        Set<Long> openApiIds = bookmarks.stream()
                .filter(b -> "OPEN_API".equals(b.getResourceType()))
                .map(BookmarkEntity::getResourceId)
                .collect(Collectors.toSet());

        Map<Long, DatasetEntity> datasetMap = datasetRepository.findAllById(datasetIds).stream()
                .collect(Collectors.toMap(DatasetEntity::getId, d -> d));

        Map<Long, OpenApiEntity> openApiMap = openApiRepository.findAllById(openApiIds).stream()
                .collect(Collectors.toMap(OpenApiEntity::getId, o -> o));

        // 평균 평점 배치 조회
        Map<Long, Double> datasetScores = reviewRepository
                .findAvgRatingByTypeAndIds("DATASET", List.copyOf(datasetIds)).stream()
                .collect(Collectors.toMap(row -> (Long) row[0], row -> ((Number) row[1]).doubleValue()));

        Map<Long, Double> openApiScores = reviewRepository
                .findAvgRatingByTypeAndIds("OPEN_API", List.copyOf(openApiIds)).stream()
                .collect(Collectors.toMap(row -> (Long) row[0], row -> ((Number) row[1]).doubleValue()));

        List<MyBookmarkResponse> filtered = bookmarks.stream()
                .map(b -> {
                    boolean isDataset = "DATASET".equals(b.getResourceType());
                    DatasetEntity dataset = isDataset ? datasetMap.get(b.getResourceId()) : null;
                    OpenApiEntity openApi = isDataset ? null : openApiMap.get(b.getResourceId());
                    String title;
                    Boolean isFree;
                    Double score;

                    if (isDataset) {
                        title = dataset != null && dataset.getTitle() != null ? dataset.getTitle() : "";
                        isFree = dataset != null ? (dataset.getPaymentRequired() == null ? null : !dataset.getPaymentRequired()) : null;
                        score = datasetScores.get(b.getResourceId());
                    } else {
                        title = openApi != null ? openApi.getName() : "";
                        isFree = openApi != null ? openApi.getIsFree() : null;
                        score = openApiScores.get(b.getResourceId());
                    }

                    return new MyBookmarkResponse(
                            b.getId(),
                            b.getResourceId(),
                            b.getResourceType(),
                            title,
                            score,
                            isFree,
                            true,
                            getResourceCreatedAt(dataset, openApi),
                            KstDateTimeFormatter.format(b.getCreatedAt()),
                            toDatasetBookmarkMeta(dataset),
                            toOpenApiBookmarkMeta(openApi)
                    );
                })
                .filter(bookmark -> {
                    if (normalizedType != null && !normalizedType.equals(bookmark.type())) {
                        return false;
                    }

                    if (normalizedKeyword != null) {
                        String resourceTitle = bookmark.title() == null ? "" : bookmark.title();
                        if (!resourceTitle.toLowerCase(Locale.ROOT).contains(normalizedKeyword.toLowerCase(Locale.ROOT))) {
                            return false;
                        }
                    }

                    if (freeOnly != null) {
                        boolean isFreeTarget = Boolean.TRUE.equals(freeOnly);
                        if (!Boolean.valueOf(isFreeTarget).equals(bookmark.isFree())) {
                            return false;
                        }
                    }

                    return true;
                })
                .toList();

        int safeSize = size <= 0 ? 10 : size;
        int safePage = Math.max(page, 0);
        int fromIndex = Math.min(safePage * safeSize, filtered.size());
        int toIndex = Math.min(fromIndex + safeSize, filtered.size());
        List<MyBookmarkResponse> pageContent = filtered.subList(fromIndex, toIndex);
        long totalElements = filtered.size();
        int totalPages = (int) Math.ceil((double) totalElements / safeSize);

        return ResponseEntity.ok(ApiResponse.success(
                "내 북마크 목록 조회 성공",
                new PageResponse<>(pageContent, safePage, safeSize, totalElements, totalPages)
        ));
    }

    private String getResourceCreatedAt(DatasetEntity dataset, OpenApiEntity openApi) {
        if (dataset != null) {
            return KstDateTimeFormatter.format(dataset.getCreatedAt());
        }

        if (openApi != null) {
            return KstDateTimeFormatter.format(openApi.getCreatedAt());
        }

        return null;
    }

    private int countReferences(PostEntity post) {
        int datasetCount = post.getDatasetId() == null ? 0 : post.getDatasetId().length;
        int openApiCount = post.getOpenapiId() == null ? 0 : post.getOpenapiId().length;
        return datasetCount + openApiCount;
    }

    private MyBookmarkResponse.DatasetMeta toDatasetBookmarkMeta(DatasetEntity dataset) {
        if (dataset == null) {
            return null;
        }

        return new MyBookmarkResponse.DatasetMeta(
                dataset.getPublisherName(),
                KstDateTimeFormatter.formatDate(dataset.getSourceUpdatedAt()),
                dataset.getRowCount(),
                dataset.getDomains(),
                dataset.getAccessType(),
                dataset.getCommercialUseAllowed(),
                dataset.getTags()
        );
    }

    private MyBookmarkResponse.OpenApiMeta toOpenApiBookmarkMeta(OpenApiEntity openApi) {
        if (openApi == null) {
            return null;
        }

        return new MyBookmarkResponse.OpenApiMeta(
                openApi.getProvider(),
                openApi.getCategory(),
                openApi.getAvgResponseTime(),
                openApi.getAuthType(),
                openApi.getDailyLimit(),
                openApi.getResponseFormat(),
                openApi.getCommercialUse(),
                openApi.getTags()
        );
    }

    @Transactional
    public void withdraw(Long userId) {
        UserEntity user = userRepository.findById(userId)
                .orElseThrow(() -> new CustomException(ErrorCode.INVALID_USER));

        logger.info("===== 회원탈퇴 시작 - userId: {} =====", userId);

        // 사용자가 작성한 게시글 soft-delete
        List<PostEntity> posts = postRepository.findByUserIdAndIsDeletedFalse(userId);
        logger.info("조회된 게시글 수: {}", posts.size());
        posts.forEach(p -> p.softDelete());
        postRepository.saveAll(posts);
        logger.info("게시글 soft-delete 완료");

        // 사용자가 작성한 리뷰 soft-delete
        List<ReviewEntity> reviews = reviewRepository.findByUserIdAndIsDeletedFalse(userId);
        logger.info("조회된 리뷰 수: {}", reviews.size());
        reviews.forEach(r -> r.delete());
        reviewRepository.saveAll(reviews);
        logger.info("리뷰 soft-delete 완료");

        // 사용자가 등록한 북마크 soft-delete
        List<BookmarkEntity> bookmarks = bookmarkRepository.findByUserIdAndDeletedAtIsNull(userId);
        logger.info("조회된 북마크 수: {}", bookmarks.size());
        bookmarks.forEach(b -> b.delete());
        bookmarkRepository.saveAll(bookmarks);
        logger.info("북마크 soft-delete 완료");

        // 사용자가 나눈 대화 soft-delete
        List<ConversationEntity> conversations = conversationRepository.findByUserIdAndDeletedAtIsNullOrderByUpdatedAtDesc(userId);
        logger.info("조회된 대화 수: {}", conversations.size());
        conversations.forEach(c -> c.markDeleted());
        conversationRepository.saveAll(conversations);
        logger.info("대화 soft-delete 완료");

        // 사용자 soft-delete
        user.delete();
        userRepository.save(user);
        logger.info("사용자 soft-delete 완료");
        
        redisTemplate.delete(String.valueOf(userId));
        logger.info("===== 회원탈퇴 완료 =====");
    }
}
