package ssafy.E105.domain.bookmark.service;

import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import ssafy.E105.domain.bookmark.dto.request.BookmarkRequest;
import ssafy.E105.domain.bookmark.dto.response.BookmarkCreateResponse;
import ssafy.E105.domain.bookmark.entity.BookmarkEntity;
import ssafy.E105.domain.bookmark.repository.BookmarkRepository;
import ssafy.E105.domain.dataset.repository.DatasetRepository;
import ssafy.E105.domain.openapi.repository.OpenApiRepository;
import ssafy.E105.domain.resource.enums.ResourceType;
import ssafy.E105.domain.user.entity.UserEntity;
import ssafy.E105.domain.user.repository.UserRepository;
import ssafy.E105.global.common.util.KstDateTimeFormatter;
import ssafy.E105.global.common.response.ApiResponse;
import ssafy.E105.global.exception.CustomException;
import ssafy.E105.global.exception.ErrorCode;

@Service
public class BookmarkService {

    private static final String ACTIVE_DATASET_STATUS = "ACTIVE";

    private final BookmarkRepository bookmarkRepository;
    private final DatasetRepository datasetRepository;
    private final OpenApiRepository openApiRepository;
    private final UserRepository userRepository;

    public BookmarkService(
            BookmarkRepository bookmarkRepository,
            DatasetRepository datasetRepository,
            OpenApiRepository openApiRepository,
            UserRepository userRepository
    ) {
        this.bookmarkRepository = bookmarkRepository;
        this.datasetRepository = datasetRepository;
        this.openApiRepository = openApiRepository;
        this.userRepository = userRepository;
    }

    @Transactional
    public ResponseEntity<ApiResponse<BookmarkCreateResponse>> createBookmark(BookmarkRequest request, Long userId) {
        validateUser(userId);
        validateRequest(request);

        ResourceType resourceType = request.resourceType();
        Long resourceId = request.resourceId();

        validateResourceExists(resourceType, resourceId);

        if (bookmarkRepository.existsByUserIdAndResourceTypeAndResourceIdAndDeletedAtIsNull(
                userId, resourceType.name(), resourceId)) {
            throw new CustomException(ErrorCode.DUPLICATE_BOOKMARK);
        }

        BookmarkEntity saved = bookmarkRepository.save(BookmarkEntity.create(userId, resourceType.name(), resourceId));

        return ResponseEntity.status(201).body(ApiResponse.created(
                "북마크가 등록되었습니다.",
                new BookmarkCreateResponse(
                        saved.getId(),
                        saved.getResourceType(),
                        saved.getResourceId(),
                        KstDateTimeFormatter.format(saved.getCreatedAt())
                )
        ));
    }

    @Transactional
    public ResponseEntity<ApiResponse<Void>> deleteBookmark(Long bookmarkId, Long userId) {
        validateUser(userId);

        BookmarkEntity bookmark = bookmarkRepository.findByIdAndDeletedAtIsNull(bookmarkId)
                .orElseThrow(() -> new CustomException(ErrorCode.BOOKMARK_NOT_FOUND));

        if (!bookmark.getUserId().equals(userId)) {
            throw new CustomException(ErrorCode.BOOKMARK_FORBIDDEN);
        }

        bookmark.delete();
        bookmarkRepository.save(bookmark);

        return ResponseEntity.ok(ApiResponse.success("북마크 삭제가 완료되었습니다.", null));
    }

    private void validateUser(Long userId) {
        if (userId == null) {
            throw new CustomException(ErrorCode.INVALID_USER);
        }
        UserEntity user = userRepository.findById(userId)
                .orElseThrow(() -> new CustomException(ErrorCode.INVALID_USER));
        if (user.isDeleted()) {
            throw new CustomException(ErrorCode.INVALID_USER);
        }
    }

    private void validateRequest(BookmarkRequest request) {
        if (request == null || request.resourceType() == null || request.resourceId() == null || request.resourceId() <= 0) {
            throw new CustomException(ErrorCode.INVALID_INPUT);
        }
        if (request.resourceType() == ResourceType.ALL) {
            throw new CustomException(ErrorCode.INVALID_INPUT);
        }
    }

    private void validateResourceExists(ResourceType resourceType, Long resourceId) {
        if (resourceType == ResourceType.DATASET) {
            datasetRepository.findByIdAndStatus(resourceId, ACTIVE_DATASET_STATUS)
                    .orElseThrow(() -> new CustomException(ErrorCode.RESOURCE_NOT_FOUND));
            return;
        }

        openApiRepository.findByIdAndIsDeletedFalse(resourceId)
                .orElseThrow(() -> new CustomException(ErrorCode.RESOURCE_NOT_FOUND));
    }
}
