package ssafy.E105.domain.chat.entity;

import jakarta.persistence.*;
import ssafy.E105.global.common.entity.BaseTimeEntity;

import java.time.LocalDateTime;

@Entity
@Table(name = "conversations")
public class ConversationEntity extends BaseTimeEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "user_id", nullable = false)
    private Long userId;

    @Column(name = "title", length = 255)
    private String title;

    @Column(name = "deleted_at")
    private LocalDateTime deletedAt;

    protected ConversationEntity() {
    }

    public ConversationEntity(Long userId, String title) {
        this.userId = userId;
        this.title = title;
    }

    public static ConversationEntity create(Long userId, String title) {
        return new ConversationEntity(userId, title);
    }

    public void touch() {
        setUpdatedAt(LocalDateTime.now());
    }

    public void markDeleted() {
        this.deletedAt = LocalDateTime.now();
        touch();
    }

    public void updateTitle(String title) {
        this.title = title;
        touch();
    }

    public Long getId() {
        return id;
    }

    public Long getUserId() {
        return userId;
    }

    public String getTitle() {
        return title;
    }

    public LocalDateTime getDeletedAt() {
        return deletedAt;
    }
}
