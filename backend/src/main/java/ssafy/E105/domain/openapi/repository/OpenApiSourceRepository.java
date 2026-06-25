package ssafy.E105.domain.openapi.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import ssafy.E105.domain.openapi.entity.OpenApiSourceEntity;

public interface OpenApiSourceRepository extends JpaRepository<OpenApiSourceEntity, Short> {
}
