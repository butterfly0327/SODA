package ssafy.E105.domain.dataset.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import ssafy.E105.domain.dataset.entity.DatasetSourceEntity;

public interface DatasetSourceRepository extends JpaRepository<DatasetSourceEntity, Short> {
}
