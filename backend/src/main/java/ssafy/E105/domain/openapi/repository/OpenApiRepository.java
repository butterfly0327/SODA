package ssafy.E105.domain.openapi.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.transaction.annotation.Transactional;
import ssafy.E105.domain.openapi.entity.OpenApiEntity;

import java.util.List;
import java.util.Optional;

public interface OpenApiRepository extends JpaRepository<OpenApiEntity, Long> {

    Optional<OpenApiEntity> findByIdAndIsDeletedFalse(Long id);

    @Query(value = "SELECT * FROM open_apis WHERE is_deleted = false AND (:keyword IS NULL OR name ILIKE '%' || :keyword || '%')",
            nativeQuery = true)
    List<OpenApiEntity> searchActive(@Param("keyword") String keyword);

    @Query(value = "SELECT COUNT(*) FROM open_apis WHERE is_deleted = false AND (:keyword IS NULL OR name ILIKE '%' || :keyword || '%')",
            nativeQuery = true)
    long countActive(@Param("keyword") String keyword);

    @Query(value = "SELECT * FROM open_apis WHERE is_deleted = false AND (:keyword IS NULL OR name ILIKE '%' || :keyword || '%') ORDER BY created_at DESC LIMIT :size OFFSET :offset",
            nativeQuery = true)
    List<OpenApiEntity> searchActivePagedByLatest(@Param("keyword") String keyword, @Param("offset") int offset, @Param("size") int size);

    @Query(value = "SELECT * FROM open_apis WHERE is_deleted = false AND (:keyword IS NULL OR name ILIKE '%' || :keyword || '%') ORDER BY avg_rating DESC, id LIMIT :size OFFSET :offset",
            nativeQuery = true)
    List<OpenApiEntity> searchActivePagedByScore(@Param("keyword") String keyword, @Param("offset") int offset, @Param("size") int size);

    List<OpenApiEntity> findByIdInAndIsDeletedFalse(List<Long> ids);

    @Transactional
    @Modifying
    @Query(value = "UPDATE open_apis SET avg_rating = :avgRating WHERE id = :id", nativeQuery = true)
    void updateAvgRating(@Param("id") Long id, @Param("avgRating") double avgRating);
}
