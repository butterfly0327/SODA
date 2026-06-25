package ssafy.E105.domain.post.service;

import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import ssafy.E105.domain.dataset.repository.DatasetRepository;
import ssafy.E105.domain.openapi.repository.OpenApiRepository;
import ssafy.E105.domain.post.dto.request.CreatePostRequest;
import ssafy.E105.domain.post.dto.request.UpdatePostRequest;
import ssafy.E105.domain.post.dto.response.*;
import ssafy.E105.domain.post.entity.PostEntity;
import ssafy.E105.domain.post.enums.PostSortType;
import ssafy.E105.domain.post.repository.PostRepository;
import ssafy.E105.domain.user.repository.UserRepository;
import ssafy.E105.global.common.util.KstDateTimeFormatter;
import ssafy.E105.global.common.response.ApiResponse;
import ssafy.E105.global.exception.CustomException;
import ssafy.E105.global.exception.ErrorCode;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class PostService {

    private static final String ACTIVE_DATASET_STATUS = "ACTIVE";
    private static final DateTimeFormatter COMMUNITY_DATE_TIME_FORMATTER =
            DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm");

    private final PostRepository postRepository;
    private final UserRepository userRepository;
    private final DatasetRepository datasetRepository;
    private final OpenApiRepository openApiRepository;

    @Transactional
    public ResponseEntity<ApiResponse<PostCreateResponse>> createPost(CreatePostRequest request, Long userId) {
        validateUser(userId);

        String title = validateAndNormalizeTitle(request.title());
        String content = normalizeContent(request.content());
        Long[] datasetIds = toNormalizedIdArray(request.datasetIds());
        Long[] openApiIds = toNormalizedIdArray(request.openApiIds());

        PostEntity saved = postRepository.save(PostEntity.create(userId, title, content, datasetIds, openApiIds));

        return ResponseEntity.status(201).body(ApiResponse.created(
                "게시글이 등록되었습니다.",
                new PostCreateResponse(saved.getId(), KstDateTimeFormatter.format(saved.getCreatedAt()))
        ));
    }

    @Transactional(readOnly = true)
    public ResponseEntity<ApiResponse<PostListResponse>> getPostList(int page, int size, PostSortType sort, String keyword) {
        if (page < 0 || size <= 0) {
            throw new CustomException(ErrorCode.INVALID_INPUT);
        }

        String normalizedKeyword = normalizeKeyword(keyword);
        Page<PostEntity> postPage = normalizedKeyword == null
                ? postRepository.findByIsDeletedFalse(PageRequest.of(page, size, sort.toSort()))
                : postRepository.searchByKeyword(normalizedKeyword, PageRequest.of(page, size, sort.toSort()));
        Set<Long> authorIds = postPage.getContent().stream()
                .map(PostEntity::getUserId)
                .filter(Objects::nonNull)
                .collect(Collectors.toSet());
        Map<Long, String> authorNamesById = userRepository.findAllById(authorIds).stream()
                .collect(Collectors.toMap(user -> user.getId(), user -> user.getName() != null ? user.getName() : ""));

        List<PostListItemResponse> content = postPage.getContent().stream()
                .map(post -> new PostListItemResponse(
                        post.getId(),
                        post.getUserId(),
                        authorNamesById.getOrDefault(post.getUserId(), ""),
                        post.getTitle(),
                        post.getViewCount(),
                        post.getFavorite(),
                        KstDateTimeFormatter.format(post.getCreatedAt()),
                        KstDateTimeFormatter.format(post.getUpdatedAt())
                ))
                .toList();

        return ResponseEntity.ok(ApiResponse.success(
                "게시글 목록 조회가 완료되었습니다.",
                new PostListResponse(
                        content,
                        page,
                        size,
                        postPage.getTotalElements(),
                        postPage.getTotalPages(),
                        sort.name()
                )
        ));
    }

    @Transactional
    public ResponseEntity<ApiResponse<PostDetailResponse>> getPostDetail(Long postId, boolean increaseViewCount) {
        if (increaseViewCount) {
            int updatedRows = postRepository.incrementViewCount(postId);
            if (updatedRows == 0) {
                throw new CustomException(ErrorCode.POST_NOT_FOUND);
            }
        }

        PostEntity post = postRepository.findByIdAndIsDeletedFalse(postId)
                .orElseThrow(() -> new CustomException(ErrorCode.POST_NOT_FOUND));

        List<PostResourceReferenceResponse> datasetReferences = resolveDatasetReferences(post.getDatasetId());
        List<PostResourceReferenceResponse> openApiReferences = resolveOpenApiReferences(post.getOpenapiId());
        String authorName = resolveAuthorName(post.getUserId());

        return ResponseEntity.ok(ApiResponse.success(
                "게시글 상세 조회가 완료되었습니다.",
                new PostDetailResponse(
                        post.getId(),
                        post.getUserId(),
                        authorName,
                        post.getTitle(),
                        post.getContent(),
                        post.getViewCount(),
                        post.getFavorite(),
                        datasetReferences,
                        openApiReferences,
                        KstDateTimeFormatter.format(post.getCreatedAt()),
                        KstDateTimeFormatter.format(post.getUpdatedAt())
                )
        ));
    }

    @Transactional
    public ResponseEntity<ApiResponse<PostUpdateResponse>> updatePost(Long postId, UpdatePostRequest request, Long userId) {
        validateUser(userId);
        PostEntity post = postRepository.findByIdAndIsDeletedFalse(postId)
                .orElseThrow(() -> new CustomException(ErrorCode.POST_NOT_FOUND));

        if (!Objects.equals(post.getUserId(), userId)) {
            throw new CustomException(ErrorCode.POST_FORBIDDEN);
        }

        String title = request.title() == null ? post.getTitle() : validateAndNormalizeTitle(request.title());
        String content = request.content() == null ? post.getContent() : normalizeContent(request.content());

        Long[] datasetIds = request.datasetIds() == null
                ? safeArray(post.getDatasetId())
                : toNormalizedIdArray(request.datasetIds());
        Long[] openApiIds = request.openApiIds() == null
                ? safeArray(post.getOpenapiId())
                : toNormalizedIdArray(request.openApiIds());

        post.update(title, content, datasetIds, openApiIds);
        postRepository.save(post);

        return ResponseEntity.ok(ApiResponse.success(
                "게시글 수정이 완료되었습니다.",
                new PostUpdateResponse(post.getId(), KstDateTimeFormatter.format(post.getUpdatedAt()))
        ));
    }

    private String formatCommunityDateTime(LocalDateTime dateTime) {
        if (dateTime == null) {
            return null;
        }
        return COMMUNITY_DATE_TIME_FORMATTER.format(dateTime);
    }

    @Transactional
    public ResponseEntity<ApiResponse<Void>> deletePost(Long postId, Long userId) {
        validateUser(userId);
        PostEntity post = postRepository.findByIdAndIsDeletedFalse(postId)
                .orElseThrow(() -> new CustomException(ErrorCode.POST_NOT_FOUND));

        if (!Objects.equals(post.getUserId(), userId)) {
            throw new CustomException(ErrorCode.POST_FORBIDDEN);
        }

        post.softDelete();
        postRepository.save(post);
        return ResponseEntity.ok(ApiResponse.success("게시글 삭제가 완료되었습니다."));
    }

    private void validateUser(Long userId) {
        if (userId == null) {
            throw new CustomException(ErrorCode.INVALID_USER);
        }
        userRepository.findById(userId).orElseThrow(() -> new CustomException(ErrorCode.INVALID_USER));
    }

    private String resolveAuthorName(Long userId) {
        if (userId == null) {
            return "";
        }
        return userRepository.findById(userId)
                .map(user -> user.getName() != null ? user.getName() : "")
                .orElse("");
    }

    private String validateAndNormalizeTitle(String title) {
        if (title == null || title.isBlank()) {
            throw new CustomException(ErrorCode.INVALID_POST_TITLE);
        }
        return title.trim();
    }

    private String normalizeContent(String content) {
        if (content == null) {
            return null;
        }
        String normalized = content.trim();
        return normalized.isEmpty() ? null : normalized;
    }

    private String normalizeKeyword(String keyword) {
        if (keyword == null) {
            return null;
        }
        String normalized = keyword.trim();
        return normalized.isEmpty() ? null : normalized;
    }

    private Long[] toNormalizedIdArray(List<Long> ids) {
        if (ids == null || ids.isEmpty()) {
            return new Long[0];
        }
        if (ids.stream().anyMatch(id -> id == null || id <= 0)) {
            throw new CustomException(ErrorCode.INVALID_INPUT);
        }
        List<Long> normalized = ids.stream()
                .distinct()
                .toList();
        return normalized.toArray(new Long[0]);
    }

    private Long[] safeArray(Long[] source) {
        if (source == null || source.length == 0) {
            return new Long[0];
        }
        return Arrays.copyOf(source, source.length);
    }

    private List<PostResourceReferenceResponse> resolveDatasetReferences(Long[] datasetIds) {
        List<Long> ids = toIdList(datasetIds);
        if (ids.isEmpty()) {
            return Collections.emptyList();
        }

        return datasetRepository.findByIdInAndStatus(ids, ACTIVE_DATASET_STATUS).stream()
                .map(dataset -> new PostResourceReferenceResponse(dataset.getId(), dataset.getTitle()))
                .toList();
    }

    private List<PostResourceReferenceResponse> resolveOpenApiReferences(Long[] openApiIds) {
        List<Long> ids = toIdList(openApiIds);
        if (ids.isEmpty()) {
            return Collections.emptyList();
        }

        return openApiRepository.findByIdInAndIsDeletedFalse(ids).stream()
                .map(openApi -> new PostResourceReferenceResponse(openApi.getId(), openApi.getName()))
                .toList();
    }

    private List<Long> toIdList(Long[] ids) {
        if (ids == null || ids.length == 0) {
            return Collections.emptyList();
        }
        return Arrays.stream(ids)
                .filter(Objects::nonNull)
                .distinct()
                .toList();
    }
}
