package ssafy.E105.domain.chat.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import ssafy.E105.domain.chat.entity.OpenApiRecommendationEntity;

import java.util.Collection;
import java.util.List;

public interface OpenApiRecommendationRepository extends JpaRepository<OpenApiRecommendationEntity, Long> {

    List<OpenApiRecommendationEntity> findByIdIn(Collection<Long> ids);
}
