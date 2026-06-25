package ssafy.E105.domain.chat.entity;

import jakarta.persistence.*;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;

@Entity
@Table(name = "conversation_turns")
public class ConversationTurnEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "conversation_id", nullable = false)
    private ConversationEntity conversation;

    @Column(name = "turn_order", nullable = false)
    private Integer turnOrder;

    @Column(name = "content", nullable = false, columnDefinition = "TEXT")
    private String content;

    @Enumerated(EnumType.STRING)
    @Column(name = "role", nullable = false, length = 20)
    private TurnRole role;

    @Column(name = "response_time_ms")
    private Integer responseTimeMs;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    protected ConversationTurnEntity() {
    }

    public ConversationTurnEntity(ConversationEntity conversation, Integer turnOrder, String content, TurnRole role, Integer responseTimeMs) {
        this.conversation = conversation;
        this.turnOrder = turnOrder;
        this.content = content;
        this.role = role;
        this.responseTimeMs = responseTimeMs;
    }

    public static ConversationTurnEntity of(ConversationEntity conversation, Integer turnOrder, String content, TurnRole role, Integer responseTimeMs) {
        return new ConversationTurnEntity(conversation, turnOrder, content, role, responseTimeMs);
    }

    public Long getId() {
        return id;
    }

    public ConversationEntity getConversation() {
        return conversation;
    }

    public Integer getTurnOrder() {
        return turnOrder;
    }

    public String getContent() {
        return content;
    }

    public TurnRole getRole() {
        return role;
    }

    public Integer getResponseTimeMs() {
        return responseTimeMs;
    }

    public LocalDateTime getCreatedAt() {
        return createdAt;
    }
}
