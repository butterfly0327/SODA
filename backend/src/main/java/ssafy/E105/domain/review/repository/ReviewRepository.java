package ssafy.E105.domain.review.repository;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import ssafy.E105.domain.review.entity.ReviewEntity;

import java.util.List;
import java.util.Optional;

public interface ReviewRepository extends JpaRepository<ReviewEntity, Long> {

    boolean existsByUserIdAndResourceTypeAndResourceIdAndIsDeletedFalse(
            Long userId, String resourceType, Long resourceId);

    long countByUserIdAndIsDeletedFalse(Long userId);

    Optional<ReviewEntity> findByIdAndIsDeletedFalse(Long id);

    Page<ReviewEntity> findByUserIdAndIsDeletedFalseOrderByCreatedAtDesc(Long userId, Pageable pageable);

    @Query("select r from ReviewEntity r where r.userId = :userId and r.isDeleted = false")
    java.util.List<ReviewEntity> findByUserIdAndIsDeletedFalse(@Param("userId") Long userId);

    List<ReviewEntity> findByResourceTypeAndResourceIdAndIsDeletedFalseOrderByCreatedAtDesc(
            String resourceType, Long resourceId);

    // resourceId → AVG(rating) * 20 → 0~100 점수
    @Query("SELECT r.resourceId, AVG(r.rating) FROM ReviewEntity r " +
            "WHERE r.resourceType = :type AND r.resourceId IN :ids AND r.isDeleted = false " +
            "GROUP BY r.resourceId")
    List<Object[]> findAvgRatingByTypeAndIds(@Param("type") String type, @Param("ids") List<Long> ids);

    @Query(value = "SELECT COALESCE(AVG(rating), 0) FROM reviews WHERE resource_type = :type AND resource_id = :id AND deleted_at IS NULL",
            nativeQuery = true)
    double findAvgRatingByTypeAndId(@Param("type") String type, @Param("id") Long id);

    @Modifying
    @Query(value = "UPDATE reviews SET is_deleted = true, updated_at = CURRENT_TIMESTAMP WHERE user_id = :userId", nativeQuery = true)
    void deleteByUserId(@Param("userId") Long userId);
}
