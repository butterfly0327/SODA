package ssafy.E105.domain.bookmark.repository;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import ssafy.E105.domain.bookmark.entity.BookmarkEntity;

import java.util.Optional;
import java.util.List;

public interface BookmarkRepository extends JpaRepository<BookmarkEntity, Long> {

    long countByUserIdAndDeletedAtIsNull(Long userId);

    List<BookmarkEntity> findByUserIdAndDeletedAtIsNullOrderByCreatedAtDesc(Long userId);

    Page<BookmarkEntity> findByUserIdAndDeletedAtIsNullOrderByCreatedAtDesc(Long userId, Pageable pageable);

    boolean existsByUserIdAndResourceTypeAndResourceIdAndDeletedAtIsNull(
            Long userId, String resourceType, Long resourceId);

    Optional<BookmarkEntity> findByIdAndDeletedAtIsNull(Long bookmarkId);

    // 사용자의 모든 북마크 가져오기
    List<BookmarkEntity> findByUserIdAndDeletedAtIsNull(Long userId);

    @Modifying
    @Query(value = "UPDATE bookmarks SET deleted_at = CURRENT_TIMESTAMP WHERE user_id = :userId AND deleted_at IS NULL", nativeQuery = true)
    void deleteByUserId(@Param("userId") Long userId);
}
