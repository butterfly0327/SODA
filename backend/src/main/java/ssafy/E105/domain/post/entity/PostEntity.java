package ssafy.E105.domain.post.entity;

import jakarta.persistence.*;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

import java.time.LocalDateTime;
import java.util.Arrays;

@Entity
@Table(name = "posts")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class PostEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "user_id", nullable = false)
    private Long userId;

    @Column(nullable = false, length = 255)
    private String title;

    @Column(columnDefinition = "TEXT")
    private String content;

    @JdbcTypeCode(SqlTypes.ARRAY)
    @Column(name = "openapi_id", columnDefinition = "BIGINT[]")
    private Long[] openapiId;

    @JdbcTypeCode(SqlTypes.ARRAY)
    @Column(name = "dataset_id", columnDefinition = "BIGINT[]")
    private Long[] datasetId;

    @Column(name = "view_count", nullable = false)
    private Integer viewCount = 0;

    @Column(name = "favorite", nullable = false)
    private Integer favorite = 0;

    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;

    @Column(name = "is_deleted", nullable = false)
    private boolean isDeleted = false;

    public static PostEntity create(Long userId, String title, String content, Long[] datasetIds, Long[] openApiIds) {
        PostEntity entity = new PostEntity();
        entity.userId = userId;
        entity.title = title;
        entity.content = content;
        entity.datasetId = datasetIds == null ? new Long[0] : Arrays.copyOf(datasetIds, datasetIds.length);
        entity.openapiId = openApiIds == null ? new Long[0] : Arrays.copyOf(openApiIds, openApiIds.length);
        entity.viewCount = 0;
        entity.favorite = 0;
        entity.isDeleted = false;
        entity.createdAt = LocalDateTime.now();
        entity.updatedAt = LocalDateTime.now();
        return entity;
    }

    public void update(String title, String content, Long[] datasetIds, Long[] openApiIds) {
        this.title = title;
        this.content = content;
        this.datasetId = datasetIds == null ? new Long[0] : Arrays.copyOf(datasetIds, datasetIds.length);
        this.openapiId = openApiIds == null ? new Long[0] : Arrays.copyOf(openApiIds, openApiIds.length);
        this.updatedAt = LocalDateTime.now();
    }

    public void increaseViewCount() {
        this.viewCount = this.viewCount + 1;
        this.updatedAt = LocalDateTime.now();
    }

    public void increaseFavorite() {
        this.favorite = this.favorite + 1;
        this.updatedAt = LocalDateTime.now();
    }

    public void decreaseFavorite() {
        this.favorite = Math.max(0, this.favorite - 1);
        this.updatedAt = LocalDateTime.now();
    }

    public void softDelete() {
        this.isDeleted = true;
        this.updatedAt = LocalDateTime.now();
    }
}
