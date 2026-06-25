package ssafy.E105.domain.chat.entity;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import jakarta.persistence.*;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;
import ssafy.E105.global.common.entity.BaseTimeEntity;

@Entity
@Table(name = "dataset_recommendations")
public class DatasetRecommendationEntity extends BaseTimeEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "user_turn_id", nullable = false)
    private ConversationTurnEntity userTurn;

    @Column(name = "reason_text", columnDefinition = "TEXT")
    private String reasonText;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "recommended_items_json", nullable = false, columnDefinition = "jsonb")
    private JsonNode recommendedItemsJson = JsonNodeFactory.instance.arrayNode();

    @Column(name = "llm_model", length = 100)
    private String llmModel;

    @Enumerated(EnumType.STRING)
    @Column(name = "status", nullable = false, length = 20)
    private RecommendationStatus status = RecommendationStatus.SUCCESS;

    @Column(name = "error_summary", columnDefinition = "TEXT")
    private String errorSummary;

    protected DatasetRecommendationEntity() {
    }

    public DatasetRecommendationEntity(ConversationTurnEntity userTurn, String reasonText, JsonNode recommendedItemsJson, String llmModel, RecommendationStatus status, String errorSummary) {
        this.userTurn = userTurn;
        this.reasonText = reasonText;
        this.recommendedItemsJson = recommendedItemsJson == null ? JsonNodeFactory.instance.arrayNode() : recommendedItemsJson;
        this.llmModel = llmModel;
        this.status = status == null ? RecommendationStatus.SUCCESS : status;
        this.errorSummary = errorSummary;
    }

    public static DatasetRecommendationEntity create(ConversationTurnEntity userTurn, String reasonText, JsonNode recommendedItemsJson, String llmModel) {
        return new DatasetRecommendationEntity(userTurn, reasonText, recommendedItemsJson, llmModel, RecommendationStatus.SUCCESS, null);
    }

    public static DatasetRecommendationEntity createRunning(ConversationTurnEntity userTurn, String llmModel) {
        return new DatasetRecommendationEntity(
                userTurn,
                null,
                JsonNodeFactory.instance.arrayNode(),
                llmModel,
                RecommendationStatus.RUNNING,
                null
        );
    }

    public static DatasetRecommendationEntity createPending(ConversationTurnEntity userTurn, String llmModel) {
        return new DatasetRecommendationEntity(
                userTurn,
                null,
                JsonNodeFactory.instance.arrayNode(),
                llmModel,
                RecommendationStatus.PENDING,
                null
        );
    }

    public void markRunning(String llmModel) {
        this.status = RecommendationStatus.RUNNING;
        if (llmModel != null && !llmModel.isBlank()) {
            this.llmModel = llmModel;
        }
        this.errorSummary = null;
    }

    public void markSuccess(String reasonText, JsonNode recommendedItemsJson, String llmModel) {
        this.reasonText = reasonText;
        this.recommendedItemsJson = recommendedItemsJson == null ? JsonNodeFactory.instance.arrayNode() : recommendedItemsJson;
        if (llmModel != null && !llmModel.isBlank()) {
            this.llmModel = llmModel;
        }
        this.status = RecommendationStatus.SUCCESS;
        this.errorSummary = null;
    }

    public void markFailed(String errorSummary) {
        this.status = RecommendationStatus.FAILED;
        this.errorSummary = errorSummary;
    }

    public Long getId() {
        return id;
    }

    public ConversationTurnEntity getUserTurn() {
        return userTurn;
    }

    public String getReasonText() {
        return reasonText;
    }

    public JsonNode getRecommendedItemsJson() {
        return recommendedItemsJson;
    }

    public String getLlmModel() {
        return llmModel;
    }

    public RecommendationStatus getStatus() {
        return status;
    }

    public String getErrorSummary() {
        return errorSummary;
    }
}
