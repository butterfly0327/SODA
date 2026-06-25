package ssafy.E105.domain.post.repository;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import ssafy.E105.domain.post.entity.PostEntity;

import java.util.Optional;

public interface PostRepository extends JpaRepository<PostEntity, Long> {

    long countByUserIdAndIsDeleted(Long userId, boolean isDeleted);

    Page<PostEntity> findByUserIdAndIsDeletedOrderByCreatedAtDesc(Long userId, boolean isDeleted, Pageable pageable);

    Page<PostEntity> findByIsDeletedFalse(Pageable pageable);

    @Query("""
            select p
            from PostEntity p
            where p.isDeleted = false
              and (
                lower(p.title) like lower(concat('%', :keyword, '%'))
                or lower(coalesce(p.content, '')) like lower(concat('%', :keyword, '%'))
              )
            """)
    Page<PostEntity> searchByKeyword(@Param("keyword") String keyword, Pageable pageable);

    Optional<PostEntity> findByIdAndIsDeletedFalse(Long id);

    @Query("select p from PostEntity p where p.userId = :userId and p.isDeleted = false")
    java.util.List<PostEntity> findByUserIdAndIsDeletedFalse(@Param("userId") Long userId);

    @Modifying
    @Query("update PostEntity p set p.viewCount = p.viewCount + 1, p.updatedAt = CURRENT_TIMESTAMP where p.id = :postId and p.isDeleted = false")
    int incrementViewCount(@Param("postId") Long postId);

    @Modifying
    @Query(value = "UPDATE posts SET is_deleted = true, updated_at = CURRENT_TIMESTAMP WHERE user_id = :userId", nativeQuery = true)
    void softDeleteByUserId(@Param("userId") Long userId);
}
