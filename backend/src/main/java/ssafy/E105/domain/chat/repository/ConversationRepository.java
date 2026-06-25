package ssafy.E105.domain.chat.repository;

import jakarta.persistence.LockModeType;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import ssafy.E105.domain.chat.entity.ConversationEntity;

import java.util.List;
import java.util.Optional;

public interface ConversationRepository extends JpaRepository<ConversationEntity, Long> {

    Optional<ConversationEntity> findByIdAndDeletedAtIsNull(Long id);

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("select c from ConversationEntity c where c.id = :id and c.deletedAt is null")
    Optional<ConversationEntity> findByIdAndDeletedAtIsNullForUpdate(@Param("id") Long id);

    List<ConversationEntity> findByUserIdAndDeletedAtIsNullOrderByUpdatedAtDesc(Long userId);

    @Modifying
    @Query(value = "UPDATE conversations SET deleted_at = CURRENT_TIMESTAMP WHERE user_id = :userId AND deleted_at IS NULL", nativeQuery = true)
    void deleteByUserId(@Param("userId") Long userId);
}
