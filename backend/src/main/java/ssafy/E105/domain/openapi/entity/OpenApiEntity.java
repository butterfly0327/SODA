package ssafy.E105.domain.openapi.entity;

import jakarta.persistence.*;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;
import ssafy.E105.global.common.entity.BaseTimeEntity;

import java.time.LocalDateTime;
import java.util.List;

@Entity
@Table(name = "open_apis")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class OpenApiEntity extends BaseTimeEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "openapi_source_id", nullable = false)
    private Short openapiSourceId;

    @Column(name = "source_openapi_key", nullable = false, length = 255)
    private String sourceOpenapiKey;

    @Column(name = "name", nullable = false, length = 255)
    private String name;

    @Column(name = "description")
    private String description;

    @Column(name = "provider", length = 100)
    private String provider;

    @Column(name = "base_url", nullable = false, length = 500)
    private String baseUrl;

    @Column(name = "docs_url", length = 500)
    private String docsUrl;

    @Column(name = "auth_type", nullable = false, length = 20)
    private String authType;

    @Column(name = "category", length = 100)
    private String category;

    @JdbcTypeCode(SqlTypes.ARRAY)
    @Column(name = "tags", columnDefinition = "text[]")
    private List<String> tags;

    @Column(name = "rate_limit")
    private Integer rateLimit;

    @Column(name = "daily_limit")
    private Integer dailyLimit;

    @Column(name = "is_free")
    private Boolean isFree;

    @Column(name = "pricing_note", length = 255)
    private String pricingNote;

    @Column(name = "commercial_use")
    private Boolean commercialUse;

    @Column(name = "requires_approval", nullable = false)
    private boolean requiresApproval = false;

    @Column(name = "response_format", length = 20)
    private String responseFormat;

    @Column(name = "avg_response_time")
    private Double avgResponseTime;

    @Column(name = "response_schema", columnDefinition = "jsonb")
    private String responseSchema;

    @Column(name = "collected_at")
    private LocalDateTime collectedAt;

    @Column(name = "is_deleted", nullable = false)
    private boolean isDeleted = false;

    @Column(name = "avg_rating", nullable = false)
    private double avgRating = 0.0;
}
