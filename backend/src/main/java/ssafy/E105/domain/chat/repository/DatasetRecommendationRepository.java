package ssafy.E105.domain.chat.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import ssafy.E105.domain.chat.entity.DatasetRecommendationEntity;

import java.util.Collection;
import java.util.List;

public interface DatasetRecommendationRepository extends JpaRepository<DatasetRecommendationEntity, Long> {

    List<DatasetRecommendationEntity> findByIdIn(Collection<Long> ids);
}
