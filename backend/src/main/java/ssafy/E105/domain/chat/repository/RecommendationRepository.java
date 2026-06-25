package ssafy.E105.domain.chat.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import ssafy.E105.domain.chat.entity.RecommendationEntity;

import java.util.Collection;
import java.util.List;
import java.util.Optional;

public interface RecommendationRepository extends JpaRepository<RecommendationEntity, Long> {

    Optional<RecommendationEntity> findByUserTurnId(Long userTurnId);

    List<RecommendationEntity> findByUserTurnIdIn(Collection<Long> userTurnIds);
}
