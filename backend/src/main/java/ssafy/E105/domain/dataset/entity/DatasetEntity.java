package ssafy.E105.domain.dataset.entity;

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
@Table(name = "datasets")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class DatasetEntity extends BaseTimeEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "dataset_source_id", nullable = false)
    private Short datasetSourceId;

    @Column(name = "last_ingest_run_id")
    private Long lastIngestRunId;

    @Column(name = "source_dataset_key", nullable = false)
    private String sourceDatasetKey;

    @JdbcTypeCode(SqlTypes.CHAR)
    @Column(name = "record_hash", columnDefinition = "char(64)")
    private String recordHash;

    @Column(name = "canonical_url")
    private String canonicalUrl;

    @Column(name = "landing_url")
    private String landingUrl;

    @Column(name = "title")
    private String title;

    @Column(name = "subtitle")
    private String subtitle;

    @Column(name = "description_short")
    private String descriptionShort;

    @Column(name = "description_long")
    private String descriptionLong;

    @Column(name = "search_text")
    private String searchText;

    @Column(name = "publisher_name")
    private String publisherName;

    @JdbcTypeCode(SqlTypes.ARRAY)
    @Column(name = "domains", columnDefinition = "text[]")
    private List<String> domains;

    @JdbcTypeCode(SqlTypes.ARRAY)
    @Column(name = "tasks", columnDefinition = "text[]")
    private List<String> tasks;

    @JdbcTypeCode(SqlTypes.ARRAY)
    @Column(name = "modalities", columnDefinition = "text[]")
    private List<String> modalities;

    @JdbcTypeCode(SqlTypes.ARRAY)
    @Column(name = "tags", columnDefinition = "text[]")
    private List<String> tags;

    @JdbcTypeCode(SqlTypes.ARRAY)
    @Column(name = "languages", columnDefinition = "text[]")
    private List<String> languages;

    @Column(name = "license_name")
    private String licenseName;

    @Column(name = "license_url")
    private String licenseUrl;

    @Column(name = "commercial_use_allowed")
    private Boolean commercialUseAllowed;

    @Column(name = "access_type", length = 20)
    private String accessType;

    @Column(name = "login_required")
    private Boolean loginRequired;

    @Column(name = "approval_required")
    private Boolean approvalRequired;

    @Column(name = "payment_required")
    private Boolean paymentRequired;

    @Column(name = "is_restricted")
    private Boolean isRestricted;

    @Column(name = "source_created_at")
    private LocalDateTime sourceCreatedAt;

    @Column(name = "source_updated_at")
    private LocalDateTime sourceUpdatedAt;

    @Column(name = "source_version")
    private String sourceVersion;

    @Column(name = "row_count")
    private Long rowCount;

    @Column(name = "dataset_size_bytes")
    private Long datasetSizeBytes;

    @Column(name = "field_presence_json", columnDefinition = "jsonb")
    private String fieldPresenceJson;

    @Column(name = "creators_json", columnDefinition = "jsonb")
    private String creatorsJson;

    @Column(name = "resources_json", columnDefinition = "jsonb")
    private String resourcesJson;

    @Column(name = "schema_json", columnDefinition = "jsonb")
    private String schemaJson;

    @Column(name = "metrics_json", columnDefinition = "jsonb")
    private String metricsJson;

    @Column(name = "extra_json", columnDefinition = "jsonb")
    private String extraJson;

    @Column(name = "raw_json", columnDefinition = "jsonb")
    private String rawJson;

    @Column(name = "status", nullable = false, length = 20)
    private String status;

    @Column(name = "last_ingested_at", nullable = false)
    private LocalDateTime lastIngestedAt;

    @Column(name = "avg_rating", nullable = false)
    private double avgRating = 0.0;
}
