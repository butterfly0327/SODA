package ssafy.E105.domain.dataset.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Entity
@Table(name = "dataset_sources")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class DatasetSourceEntity {

    @Id
    private Short id;

    @Column(name = "source_name", nullable = false)
    private String sourceName;
}
