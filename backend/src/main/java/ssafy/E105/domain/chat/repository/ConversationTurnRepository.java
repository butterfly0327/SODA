package ssafy.E105.domain.chat.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import ssafy.E105.domain.chat.entity.ConversationTurnEntity;

import java.util.List;
import java.util.Optional;

public interface ConversationTurnRepository extends JpaRepository<ConversationTurnEntity, Long> {

    List<ConversationTurnEntity> findByConversationIdOrderByTurnOrderAsc(Long conversationId);

    Optional<ConversationTurnEntity> findTopByConversationIdOrderByTurnOrderDesc(Long conversationId);
}
