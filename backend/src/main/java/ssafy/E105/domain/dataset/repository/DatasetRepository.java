package ssafy.E105.domain.dataset.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.transaction.annotation.Transactional;
import ssafy.E105.domain.dataset.entity.DatasetEntity;

import java.util.List;
import java.util.Optional;

public interface DatasetRepository extends JpaRepository<DatasetEntity, Long> {

    Optional<DatasetEntity> findByIdAndStatus(Long id, String status);

    @Query(value = "SELECT * FROM datasets WHERE status = 'ACTIVE' AND (:keyword IS NULL OR title ILIKE '%' || :keyword || '%')",
            nativeQuery = true)
    List<DatasetEntity> searchActive(@Param("keyword") String keyword);

    @Query(value = "SELECT COUNT(*) FROM datasets WHERE status = 'ACTIVE' AND (:keyword IS NULL OR title ILIKE '%' || :keyword || '%')",
            nativeQuery = true)
    long countActive(@Param("keyword") String keyword);

    @Query(value = "SELECT * FROM datasets WHERE status = 'ACTIVE' AND (:keyword IS NULL OR title ILIKE '%' || :keyword || '%') ORDER BY created_at DESC LIMIT :size OFFSET :offset",
            nativeQuery = true)
    List<DatasetEntity> searchActivePagedByLatest(@Param("keyword") String keyword, @Param("offset") int offset, @Param("size") int size);

    @Query(value = "SELECT * FROM datasets WHERE status = 'ACTIVE' AND (:keyword IS NULL OR title ILIKE '%' || :keyword || '%') ORDER BY avg_rating DESC, id LIMIT :size OFFSET :offset",
            nativeQuery = true)
    List<DatasetEntity> searchActivePagedByScore(@Param("keyword") String keyword, @Param("offset") int offset, @Param("size") int size);

    List<DatasetEntity> findByIdInAndStatus(List<Long> ids, String status);

    @Transactional
    @Modifying
    @Query(value = "UPDATE datasets SET avg_rating = :avgRating WHERE id = :id", nativeQuery = true)
    void updateAvgRating(@Param("id") Long id, @Param("avgRating") double avgRating);
}
