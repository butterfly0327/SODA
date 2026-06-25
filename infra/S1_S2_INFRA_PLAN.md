# S1 / S2 Infrastructure Execution Plan

## 1. Purpose

이 문서는 [`docs/Infrastructure.md`](../docs/Infrastructure.md)를 기준으로, 현재 저장소를 `D안` 네트워크 구조에 맞춰가기 위한 `S1 / S2` 인프라 구현 방향을 정리한다.

모니터링 세부 설계와 rollout 순서는 [`docs/plans/2026-03-21-monitoring-observability-design.md`](../docs/plans/2026-03-21-monitoring-observability-design.md), [`docs/plans/2026-03-21-monitoring-observability-implementation-plan.md`](../docs/plans/2026-03-21-monitoring-observability-implementation-plan.md)를 기준으로 본다.

- `S1`: `prod active + dev active`
- `S2`: `async / ops`
- 범위: compose 구조, 환경 변수, 서비스 역할, 네트워크 경계, 실행 순서, 운영 가드레일

주의:

- 현재 저장소의 compose는 스캐폴딩 단계이며 일부 서비스는 placeholder 실행 상태다.
- 따라서 이 문서는 "지금 즉시 동일하게 떠 있는 실제 런타임"보다 "저장소가 수렴해야 할 목표 실행 계약"을 설명한다.
- 목표 방향은 `base compose가 개발자 기본 실행 경로가 되는 것`이다.

## 2. Decision Summary

이번 계획은 다음 결정을 전제로 한다.

1. `Celery`를 유지한다.
2. `RabbitMQ`를 작업 브로커로 사용한다.
3. `Redis`는 캐시, rate limit, lock, 짧은 TTL 상태값 용도로 사용한다.
4. `HDFS`, `Spark`는 MVP 운영 범위에서 제외한다.
5. `S1`은 단일 `Nginx`로 `prod/dev` path 기반 라우팅을 담당한다.
6. `S2`는 `async / ops`를 담당한다.
7. `prod` 데이터는 관리형 저장소를 사용하고, `dev` 데이터는 `S1` 내부 로컬 컨테이너를 사용한다.
8. 현재 구조는 `S1` 단일 ingress를 사용하며 자동 failover는 범위에 포함하지 않는다.

## 3. Current Target Topology

### S1

- `Nginx`
- `prod Frontend`
- `prod Spring Boot API`
- `prod FastAPI RAG API`
- `dev Frontend`
- `dev Spring Boot API`
- `dev FastAPI RAG API`
- `dev PostgreSQL`
- `dev Redis`
- `dev MinIO`

### S2

- `RabbitMQ`
- `Celery Beat`
- `Celery Worker`
- `crawler-openapi`
- `crawler-dataset`
- `Jenkins`
- `Prometheus`
- `Grafana`
- `Loki`
- `Alertmanager`
- `Blackbox Exporter`
- `node-exporter`

### Managed Services

- `RDS PostgreSQL + pgvector` (`prod` only)
- `ElastiCache Redis` (`prod` only)
- `S3` (`prod` only)

## 4. Execution Principles

### 4.1 Single Nginx on S1 Routes Prod and Dev

- `S1 nginx`는 하나만 둔다.
- `/`, `/api`, `/rag`는 `prod`로 보낸다.
- `/jenkins`, `/grafana`는 `S2 ops` reverse proxy 경로로 보낸다.
- `/dev`, `/dev/api`, `/dev/rag`는 `dev`로 보낸다.
- `dev` object proxy가 필요하면 `/dev/objects`를 사용한다.

### 4.2 Async and Ops Must Be Kept on S2

- `S2`는 `async / ops`를 담당한다.
- 긴 작업은 API 요청 스레드 안에서 직접 수행하지 않는다.

### 4.3 Broker and Cache Must Be Split

- `RabbitMQ` URL과 `Redis` URL은 별도 환경 변수로 둔다.
- Redis를 브로커 대체 용도로 섞지 않는다.
- 큐 장애와 캐시 장애를 독립적으로 관찰할 수 있어야 한다.

### 4.4 Prod and Dev Boundaries Must Be Explicit

- `prod`와 `dev`는 path, 네트워크, 저장소를 분리한다.
- `prod`는 외부 관리형 저장소를 사용한다.
- `dev`는 `S1` 내부 `PostgreSQL`, `Redis`, `MinIO`를 사용한다.
- `dev`는 공개 환경이지만 failover 대상은 아니다.

### 4.5 Ingress Must Be Local-Upstream Only

- `S1 nginx`의 기본 app upstream은 `S1` 내부 app만 가진다.
- `S2`는 ingress를 받지 않는다.
- 운영 도구 접근은 `S1 nginx`의 명시적 reverse proxy 경로로만 허용한다.

## 5. Compose Contract

### 5.1 Domain Layout

- `frontend/`
  - `docker-compose.yml`
  - `docker-compose.dev.yml`
  - `docker-compose.prod.yml`
- `backend/`
  - `docker-compose.yml`
  - `docker-compose.dev.yml`
  - `docker-compose.prod.yml`
- `data-platform/`
  - `docker-compose.yml`
  - `docker-compose.dev.yml`
  - `docker-compose.prod.yml`
  - `docker-compose.worker.yml`
- `infra/`
  - `docker-compose.common.yml`
  - `docker-compose.local.yml`
  - `docker-compose.worker.yml`

원칙:

- 서비스 도메인의 `docker-compose.yml`은 개발자가 바로 실행 가능한 기본 런타임을 가진다.
- `docker-compose.prod.yml`은 운영 환경 override만 담당한다.
- 서비스 도메인(`frontend/backend/data-platform`)의 `docker-compose.local.yml`은 유지하지 않는다.
- `infra/docker-compose.local.yml`만 로컬 운영 도구 포트 공개용으로 유지한다.

### 5.2 Runtime Ownership

| 영역 | 책임 |
| --- | --- |
| `frontend/` | React 서비스 |
| `backend/` | Spring Boot 서비스 |
| `data-platform/api/` | FastAPI RAG |
| `data-platform/crawler/*` | 데이터 수집기 |
| `data-platform/docker-compose.worker.yml` | Celery worker/beat, crawler |
| `infra/` | Nginx, Jenkins, monitoring, 공통 인프라 |

추가 원칙:

- `frontend/backend/data-platform`의 base compose만으로도 개발자가 최소 기동 확인을 할 수 있어야 한다.
- `dev` override는 HMR, reload, bind mount 같은 개발 편의 기능을 얹는 계층이다.
- `local`은 별도 가치가 없으면 제거 후보로 본다.

### 5.3 Deferred Paths

다음 경로는 현재 저장소에 남아 있어도 MVP 실행 경로에는 포함하지 않는다.

- `data-platform/hdfs/`
- `data-platform/spark/`

## 6. Service Placement

### 6.1 S1

반드시 올라가야 하는 서비스:

- `nginx`
- `prod-frontend`
- `prod-spring`
- `prod-fastapi`
- `dev-frontend`
- `dev-spring`
- `dev-fastapi`

`dev` 로컬 데이터 계층:

- `dev-postgres`
- `dev-redis`
- `dev-minio`

### 6.2 S2

반드시 올라가야 하는 서비스:

- `rabbitmq`
- `celery-worker`
- `celery-beat`
- `crawler-openapi`
- `crawler-dataset`
- `prometheus`
- `grafana`
- `loki`
- `alertmanager`
- `jenkins`

### 6.3 External Prod State

`prod`에서 공통으로 바라보는 외부 저장소:

- `RDS PostgreSQL + pgvector`
- `ElastiCache Redis`
- `S3`

## 7. Recommended Execution Phases

### Phase 1. Foundation

대상:

- 문서 계약
- 환경 변수
- Compose 이름과 책임 분리

목표:

- 브로커와 캐시 경계를 먼저 고정한다.
- `prod`와 `dev` 저장소 경계를 고정한다.
- HDFS/Spark를 MVP 기본 명령에서 제외한다.

완료 기준:

- `.env`에서 `BROKER_URL`, `CACHE_URL`이 분리되어 있다.
- `.env.dev`, `.env.prod`가 루트에 준비되어 있다.
- 문서와 compose 책임이 일치한다.

### Phase 2. Service Plane

대상:

- `S1 nginx`
- `prod frontend/backend/fastapi`
- `dev frontend/backend/fastapi`
- `S1` local db/cache/object storage

목표:

- `S1` 기준 사용자 요청 경로를 먼저 검증할 수 있게 한다.

완료 기준:

- `/`
- `/api`
- `/dev`
- `/dev/api`

경로가 정상 응답한다.
또한 `frontend/backend/data-platform`의 base compose가 개발자 로컬 기준 최소 실행 가능 상태여야 한다.

### Phase 3. Async Plane

대상:

- `RabbitMQ`
- `Celery Worker`
- `Celery Beat`
- `crawler`

목표:

- 수집 작업과 임베딩 작업이 분리된 큐를 통해 실행된다.

완료 기준:

- `collect_queue`, `embed_queue`가 생성된다.
- 샘플 수집 작업이 enqueue -> consume -> 저장까지 이어진다.

### Phase 4. Data Wiring

대상:

- `RDS PostgreSQL + pgvector`
- `ElastiCache Redis`
- `S3`
- `S1 dev-postgres`
- `S1 dev-redis`
- `S1 dev-minio`

목표:

- `prod`와 `dev`가 서로 다른 저장소 계약을 안정적으로 사용한다.
- 수집 -> 저장 -> 임베딩 전체 흐름을 연결한다.

완료 기준:

- `prod` API와 worker가 동일한 운영 저장소 계약을 사용한다.
- `dev` API가 `S1` 로컬 저장소로 정상 동작한다.
- 파일 업로드와 메타데이터 저장이 정상 동작한다.
- 임베딩 결과가 pgvector에 반영된다.

### Phase 5. Ops

대상:

- `Jenkins`
- `Prometheus`
- `Grafana`
- `Loki`
- `Alertmanager`

목표:

- 작업 큐 적체, worker 실패, 수집 실패, `S1` ingress SPOF와 운영 상태를 관찰할 수 있게 한다.

완료 기준:

- RabbitMQ 상태
- Celery worker 상태
- 주요 서비스 헬스 체크
를 한 화면 또는 한 경로에서 확인할 수 있다.

### Phase 6. Hardening

대상:

- retry / DLQ 정책
- 배포 스크립트
- 운영 알림

목표:

- 실패 작업이 조용히 사라지지 않도록 한다.
- `S1` ingress 장애를 운영자가 즉시 감지할 수 있어야 한다.

완료 기준:

- 재시도 정책이 정의되어 있다.
- DLQ 또는 실패 작업 조회 경로가 있다.
- 운영자용 확인 절차가 문서화되어 있다.

## 8. Network Contract

### 8.1 Public Paths

기본 공개 포트:

- `22`
- `80`
- `443`

경로 규칙:

- `prod`, `dev` 모두 `S1`으로 들어간다.
- DB, Redis, RabbitMQ, monitoring, worker 포트는 외부에 직접 열지 않는다.
- Jenkins/Grafana 공개 노출은 최소화한다.

### 8.2 Target Logical Networks

| 네트워크 | 역할 | 멤버 |
| --- | --- | --- |
| `s1-prod-edge` | `prod` ingress와 active app 연결 | `s1-nginx`, `prod-frontend`, `prod-spring`, `prod-fastapi` |
| `s1-dev-edge` | `dev` ingress와 dev app 연결 | `s1-nginx`, `dev-frontend`, `dev-spring`, `dev-fastapi`, `dev-minio(optional)` |
| `s1-dev-data` | `dev` app와 로컬 저장소 연결 | `dev-spring`, `dev-fastapi`, `dev-postgres`, `dev-redis`, `dev-minio` |
| `s2-async-net` | 브로커/worker/crawler 연결 | `rabbitmq`, `celery-beat`, `celery-worker`, `crawler-openapi`, `crawler-dataset` |
| `s2-ops-net` | 모니터링/CI-CD 연결 | `jenkins`, `prometheus`, `grafana`, `loki`, `alertmanager`, `promtail`, `cadvisor` |

### 8.3 Inter-Service Communication

- 같은 호스트에서는 Docker 네트워크와 서비스명으로 통신한다.
- 다른 호스트 간 통신은 private endpoint 접근으로 처리한다.
- `S1 nginx`는 `S1` app만 upstream으로 가진다.
- `prod` app과 worker는 외부 `RDS`, `ElastiCache`, `S3`에 접근한다.
- `dev` app은 `S1` 내부 `PostgreSQL`, `Redis`, `MinIO`에 접근한다.

## 9. Risk Controls

### Risk 1. RabbitMQ 운영 부담

통제:

- 모니터링과 큐 상태 확인 경로를 먼저 만든다.
- collect/embed 큐를 분리하고 failure 경로를 명시한다.

### Risk 2. Redis 오용

통제:

- Redis를 브로커로 혼용하지 않는다.
- cache key prefix와 TTL 정책을 문서화한다.

### Risk 3. Prod / Dev 오염

통제:

- `prod`와 `dev` 환경 변수를 분리한다.
- `dev`는 `S1` 로컬 저장소만 사용한다.
- queue namespace, cache prefix, bucket 이름을 분리한다.

### Risk 4. Single Ingress SPOF

통제:

- `S1` ingress 헬스 체크와 외부 uptime check를 붙인다.
- 장애 시 수동 복구 절차를 명확히 유지한다.

### Risk 5. 과도한 범위 확장

통제:

- HDFS/Spark는 이번 범위에 넣지 않는다.
- broker HA와 multi-AZ는 Phase 6 이후 추가 검토로 둔다.

## 10. Done Definition

다음 조건을 충족하면 현재 S1/S2 인프라 정렬이 완료된 것으로 본다.

- README, docs, infra 문서가 동일한 구조를 설명한다.
- `S1 = prod active + dev active`, `S2 = async/ops` 경계가 명확하다.
- `RabbitMQ = 브로커`, `Redis = 캐시/상태` 역할이 문서와 설정에서 분리된다.
- `prod = managed state`, `dev = S1 local state` 경계가 문서상 일관된다.
- `S1 nginx` path 라우팅과 `S2 async/ops` 역할이 문서상 일관된다.
- 수집 -> 저장 -> 임베딩 흐름이 문서상 일관된다.

## 11. Optional Future Work

현재 문서 범위를 벗어나지만 향후 검토 가능한 항목:

- `Amazon MQ for RabbitMQ`
- broker 고가용성
- LB 또는 DNS failover
- `dev` 별도 서버 분리
- 추가 worker 노드
