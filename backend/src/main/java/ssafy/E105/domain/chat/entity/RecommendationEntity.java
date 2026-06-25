package ssafy.E105.domain.chat.entity;

import jakarta.persistence.*;
import ssafy.E105.global.common.entity.BaseTimeEntity;

@Entity
@Table(name = "recommendations")
public class RecommendationEntity extends BaseTimeEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "user_turn_id", nullable = false)
    private ConversationTurnEntity userTurn;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "assistant_turn_id")
    private ConversationTurnEntity assistantTurn;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "dataset_recommendation_id", nullable = false)
    private DatasetRecommendationEntity datasetRecommendation;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "openapi_recommendation_id", nullable = false)
    private OpenApiRecommendationEntity openApiRecommendation;

    @Column(name = "merged_reason_text", columnDefinition = "TEXT")
    private String mergedReasonText;

    @Column(name = "llm_model", length = 100)
    private String llmModel;

    @Enumerated(EnumType.STRING)
    @Column(name = "status", nullable = false, length = 20)
    private RecommendationStatus status = RecommendationStatus.SUCCESS;

    @Column(name = "error_summary", columnDefinition = "TEXT")
    private String errorSummary;

    protected RecommendationEntity() {
    }

    public RecommendationEntity(
            ConversationTurnEntity userTurn,
            ConversationTurnEntity assistantTurn,
            DatasetRecommendationEntity datasetRecommendation,
            OpenApiRecommendationEntity openApiRecommendation,
            String mergedReasonText,
            String llmModel,
            RecommendationStatus status,
            String errorSummary
    ) {
        this.userTurn = userTurn;
        this.assistantTurn = assistantTurn;
        this.datasetRecommendation = datasetRecommendation;
        this.openApiRecommendation = openApiRecommendation;
        this.mergedReasonText = mergedReasonText;
        this.llmModel = llmModel;
        this.status = status == null ? RecommendationStatus.SUCCESS : status;
        this.errorSummary = errorSummary;
    }

    public static RecommendationEntity create(
            ConversationTurnEntity userTurn,
            DatasetRecommendationEntity datasetRecommendation,
            OpenApiRecommendationEntity openApiRecommendation,
            String mergedReasonText,
            String llmModel
    ) {
        return new RecommendationEntity(
                userTurn,
                null,
                datasetRecommendation,
                openApiRecommendation,
                mergedReasonText,
                llmModel,
                RecommendationStatus.SUCCESS,
                null
        );
    }

    public static RecommendationEntity createRunning(
            ConversationTurnEntity userTurn,
            DatasetRecommendationEntity datasetRecommendation,
            OpenApiRecommendationEntity openApiRecommendation,
            String llmModel
    ) {
        return new RecommendationEntity(
                userTurn,
                null,
                datasetRecommendation,
                openApiRecommendation,
                null,
                llmModel,
                RecommendationStatus.RUNNING,
                null
        );
    }

    public static RecommendationEntity createPending(
            ConversationTurnEntity userTurn,
            DatasetRecommendationEntity datasetRecommendation,
            OpenApiRecommendationEntity openApiRecommendation,
            String llmModel
    ) {
        return new RecommendationEntity(
                userTurn,
                null,
                datasetRecommendation,
                openApiRecommendation,
                null,
                llmModel,
                RecommendationStatus.PENDING,
                null
        );
    }

    public void linkAssistantTurn(ConversationTurnEntity assistantTurn) {
        this.assistantTurn = assistantTurn;
    }

    public void markRunning(String llmModel) {
        this.status = RecommendationStatus.RUNNING;
        if (llmModel != null && !llmModel.isBlank()) {
            this.llmModel = llmModel;
        }
        this.errorSummary = null;
    }

    public void markSuccess(String mergedReasonText, String llmModel) {
        this.mergedReasonText = mergedReasonText;
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

    public ConversationTurnEntity getAssistantTurn() {
        return assistantTurn;
    }

    public DatasetRecommendationEntity getDatasetRecommendation() {
        return datasetRecommendation;
    }

    public OpenApiRecommendationEntity getOpenApiRecommendation() {
        return openApiRecommendation;
    }

    public String getMergedReasonText() {
        return mergedReasonText;
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
