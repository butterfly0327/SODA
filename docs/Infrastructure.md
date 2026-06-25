# SODA Infrastructure Architecture

## 1. Overview

SODA의 현재 목표 아키텍처는 **2대 서버 + prod 관리형 상태 저장소 + dev 로컬 상태 저장소**를 기반으로 한다.

모니터링 상세 설계는 [`docs/plans/2026-03-21-monitoring-observability-design.md`](./plans/2026-03-21-monitoring-observability-design.md)를 기준으로 본다.

- `S1`: `prod active + dev active`
- `S2`: `async / ops`
- `prod state`: `RDS PostgreSQL + pgvector`, `ElastiCache Redis`, `S3`
- `dev state`: `S1` 내부 `PostgreSQL`, `Redis`, `MinIO`

이 문서의 전제는 다음과 같다.

- `HDFS`, `Spark`는 MVP 범위에서 제외한다.
- 비동기 작업은 `Celery + RabbitMQ` 조합으로 처리한다.
- `Redis`는 브로커가 아니라 캐시/임시 상태 계층으로 사용한다.
- 현재 구조는 `S1` ingress를 단일 진입점으로 사용하며, 자동 failover는 범위에 포함하지 않는다.
- 현재 저장소는 이 목표 구조에 맞춰가는 중이며, 일부 compose 서비스는 placeholder 상태일 수 있다.
- Compose 계층은 `base = dev-default runnable`, `prod = override` 방향으로 단순화하는 것을 목표로 한다.

## 2. Design Principles

### 2.1 Build Small First

- 처음부터 과한 분산 분석 플랫폼을 만들지 않는다.
- 서비스 완성도와 운영 가능성을 먼저 확보한 뒤 확장한다.

### 2.2 Split Active and Async Roles

- `S1`은 사용자 요청을 받는 기본 active 서비스 서버다.
- `S2`는 비동기 처리와 운영 도구를 맡는다.
- `dev`는 외부 공개하지만 `S1` 단일 서버에서만 운영한다.

### 2.3 Separate Broker From Cache

- `RabbitMQ`는 작업 전달과 재시도 경로를 담당한다.
- `Redis`는 검색 캐시, rate limit, 분산 lock, 짧은 상태값만 담당한다.
- `Redis Pub/Sub`는 작업 큐로 사용하지 않는다.

### 2.4 Externalize Prod State, Keep Dev State Local

- `prod`는 `RDS`, `ElastiCache`, `S3`를 기준으로 한다.
- `dev`는 `S1` 내부 `PostgreSQL`, `Redis`, `MinIO`로 독립 운영한다.
- `prod`와 `dev`는 저장소와 네트워크 경계를 섞지 않는다.

### 2.5 Keep Application Ingress Local, Proxy Ops Explicitly

- `S1 nginx`의 기본 app upstream은 `S1` 내부 app 컨테이너만 가진다.
- `S2`는 app ingress를 받지 않는다.
- 운영 도구 노출은 예외적으로 `S1 nginx`의 명시적 reverse proxy 경로로만 허용한다.
- 현재 예외 경로는 `/jenkins/`, 목표 경로는 `/grafana/`다.

### 2.6 Prefer Runnable Base Compose

- `docker-compose.yml`은 contract-only skeleton보다 개발자가 바로 실행해볼 수 있는 기본 런타임을 갖는 편이 낫다.
- `docker-compose.dev.yml`은 개발 편의 옵션을 추가하는 계층이다.
- `docker-compose.prod.yml`은 운영 배포 차이만 override한다.
- 서비스 도메인(`frontend/backend/data-platform`)의 `docker-compose.local.yml`은 유지하지 않는다.
- `infra/docker-compose.local.yml`만 로컬 운영 도구 포트 노출용으로 유지한다.

## 3. Target Topology

```text
=========================================================================================
External Entry
=========================================================================================

[direct DNS]
  -> S1 ingress only


=========================================================================================
S1
prod active + dev active
=========================================================================================

[S1 nginx]
  joins:
  - s1-prod-edge
  - s1-dev-edge

  routes:
  - /             -> prod-frontend
  - /api          -> prod-spring
  - /rag          -> prod-fastapi
  - /jenkins      -> s2-jenkins (ops proxy)
  - /grafana      -> s2-grafana (ops proxy)
  - /dev          -> dev-frontend
  - /dev/api      -> dev-spring
  - /dev/rag      -> dev-fastapi
  - /dev/objects  -> dev-minio (optional)

[s1-prod-edge]
  members:
  - s1-nginx
  - prod-frontend
  - prod-spring
  - prod-fastapi

[s1-dev-edge]
  members:
  - s1-nginx
  - dev-frontend
  - dev-spring
  - dev-fastapi
  - dev-minio (optional)

[s1-dev-data]
  members:
  - dev-spring
  - dev-fastapi
  - dev-postgres
  - dev-redis
  - dev-minio


=========================================================================================
S2
async / ops
=========================================================================================

[s2-async-net]
  members:
  - rabbitmq
  - celery-beat
  - celery-worker
  - crawler-openapi
  - crawler-dataset

[s2-ops-net]
  members:
  - jenkins
  - prometheus
  - grafana
  - loki
  - alertmanager
  - promtail
  - cadvisor
  - blackbox-exporter
  - node-exporter


=========================================================================================
External Managed Services
prod only
=========================================================================================

[RDS PostgreSQL + pgvector]
[ElastiCache Redis]
[S3]

reachable from:
- prod active app on S1
- async workers on S2
```

## 4. Server Roles

### 4.1 S1: Active Service Plane + Dev Plane

S1은 `prod`의 기본 active 서버이면서 `dev` 외부 공개 환경도 함께 담당한다.

주요 서비스:

- `Nginx` 단일 ingress
- `prod Frontend`
- `prod Spring Boot API`
- `prod FastAPI RAG API`
- `dev Frontend`
- `dev Spring Boot API`
- `dev FastAPI RAG API`
- `dev PostgreSQL`
- `dev Redis`
- `dev MinIO`

책임:

- `prod` 사용자 요청의 기본 처리
- `dev` 외부 공개 환경 제공
- `dev` 전용 로컬 데이터 계층 보유

원칙:

- `prod`와 `dev`는 path와 네트워크로 경계를 나눈다.
- `Nginx`는 `s1-prod-edge`, `s1-dev-edge` 두 네트워크에만 붙는다.
- `prod` 앱은 `s1-prod-edge`만 사용한다.
- `dev` 앱은 `s1-dev-edge`, `s1-dev-data`를 사용한다.

### 4.2 S2: Async / Ops Plane

S2는 비동기 처리와 운영성 컴포넌트를 담당한다.

주요 서비스:

- `RabbitMQ`
- `Celery Beat`
- `Celery Worker`
- 수집기(crawler)
- `Jenkins`
- `Prometheus`
- `Grafana`
- `Loki`
- `Alertmanager`

책임:

- 주기적 수집 작업 스케줄링
- 수집, 정규화, 임베딩 생성
- 재색인 및 배치성 후처리
- 운영 가시성, CI/CD, 알림

원칙:

- `RabbitMQ`와 worker는 `s2-async-net` 안에서만 통신한다.
- 운영 도구는 `s2-ops-net`으로 분리한다.

### 4.3 External Entry

외부 진입점은 `S1` 단일 `Nginx`다.

- `prod`: `S1` 직접 진입
- `dev`: `S1` 직접 진입

원칙:

- 현재 구조는 `prod` 자동 failover를 제공하지 않는다.
- `dev`는 공개 환경이지만 failover 대상이 아니다.

### 4.4 Managed Services

운영 환경 기준 관리형 서비스는 다음과 같다.

| 서비스 | 역할 |
| --- | --- |
| `RDS PostgreSQL + pgvector` | `prod` 메타데이터, 임베딩, 검색 인덱스, 서비스 데이터 |
| `ElastiCache Redis` | `prod` 캐시, rate limit, lock, 짧은 TTL 상태 |
| `S3` | `prod` 원본 파일, API 응답 샘플, 배치 산출물 |

## 5. Async Processing Flow

### 5.1 Why an Async Pipeline Exists

Open API 및 데이터셋 수집은 다음 특성을 가진다.

- 소스별 호출 속도와 rate limit이 다르다.
- 개별 소스 실패를 전체 실패로 만들면 안 된다.
- 수집과 임베딩은 처리 시간이 길고 즉시 응답 경로에서 분리해야 한다.

이 때문에 `Celery + RabbitMQ` 기반 파이프라인을 사용한다.

### 5.2 Queue Model

기본 큐는 다음처럼 나눈다.

- `collect_queue`: 사이트별 수집 작업
- `embed_queue`: 임베딩 생성 작업
- `reindex_queue`: 재색인 및 일괄 후처리
- `dead_letter_queue`: 반복 실패 작업 보관

### 5.3 End-to-End Flow

```text
Celery Beat
  -> collect task enqueue
  -> RabbitMQ collect_queue
  -> Celery Worker consumes
  -> source fetch / normalize
  -> metadata save to PostgreSQL
  -> file save to S3
  -> embed task enqueue
  -> RabbitMQ embed_queue
  -> Celery Worker consumes
  -> embedding generation
  -> pgvector update
```

### 5.4 Failure Handling

- 일시적 실패는 재시도한다.
- 반복 실패는 dead letter queue로 보낸다.
- 소스별 rate limit은 `Redis` 카운터로 제어한다.
- 작업 상태는 애플리케이션 로그와 메트릭으로 관측한다.

## 6. Data and Storage Strategy

### 6.1 PostgreSQL + pgvector

`prod` 저장 대상:

- 데이터셋 메타데이터
- Open API 메타데이터
- 임베딩 벡터
- 추천 결과, 사용자 관련 도메인 데이터

선택 이유:

- 메타데이터와 벡터 검색을 한 저장소에서 다룰 수 있다.
- 조인과 필터링이 필요할 때 구조가 단순하다.
- 별도 벡터 DB를 추가하지 않아도 MVP 요구를 충족한다.

### 6.2 Redis / ElastiCache

`prod` 저장 대상:

- 검색 결과 캐시
- rate limiting 카운터
- 중복 방지 lock
- 짧은 TTL 상태값

비목표:

- 메시지 브로커 역할
- 장기 영속 데이터 저장

### 6.3 S3 / MinIO

- `S3`: `prod` 원본 파일, Open API 응답 샘플, 대용량 JSON/CSV, 재처리 아카이브
- `MinIO`: `dev` 원본 파일 및 테스트 산출물

### 6.4 Dev Local State on S1

`dev`는 `S1` 내부 로컬 저장소를 기준으로 운영한다.

- `dev-postgres`
- `dev-redis`
- `dev-minio`

원칙:

- `prod` 앱은 이 경로를 사용하지 않는다.
- `dev` 앱만 `s1-dev-data`를 통해 접근한다.

## 7. Network and Security Rules

### 7.1 Public Entry Points

기본 외부 노출은 다음만 허용한다.

- `22`: 운영자 SSH 또는 대체 접근 채널
- `80`, `443`: `S1 nginx`

진입 규칙:

- `prod`는 external routing layer를 통해 `S1` 또는 `S2`로 들어간다.
- `dev`는 `S1 nginx`로만 들어간다.
- DB, Redis, RabbitMQ, monitoring, worker 포트는 외부 직접 노출하지 않는다.
- Jenkins와 Grafana는 외부 직접 포트 노출 대신 `S1 nginx` 프록시 또는 터널 기반 접근을 우선한다.

### 7.2 Target Logical Networks

| 네트워크 | 역할 | 주요 멤버 |
| --- | --- | --- |
| `s1-prod-edge` | `prod` ingress와 active app 연결 | `s1-nginx`, `prod-frontend`, `prod-spring`, `prod-fastapi` |
| `s1-dev-edge` | `dev` ingress와 dev app 연결 | `s1-nginx`, `dev-frontend`, `dev-spring`, `dev-fastapi`, `dev-minio(optional)` |
| `s1-dev-data` | `dev` app와 로컬 데이터 저장소 연결 | `dev-spring`, `dev-fastapi`, `dev-postgres`, `dev-redis`, `dev-minio` |
| `s2-async-net` | 브로커, 스케줄러, worker, crawler 연결 | `rabbitmq`, `celery-beat`, `celery-worker`, `crawler-openapi`, `crawler-dataset` |
| `s2-ops-net` | 모니터링과 CI/CD 연결 | `jenkins`, `prometheus`, `grafana`, `loki`, `alertmanager`, `promtail`, `cadvisor` |

현재 저장소의 compose 네트워크 이름은 이 logical contract로 점진적으로 수렴하는 중이다.

### 7.3 Connectivity Rules

- 같은 Docker 호스트 내 통신은 서비스명과 내부 포트를 사용한다.
- `S1 nginx`는 `S1` 내부 app만 upstream으로 가진다.
- `prod` app과 `async` worker는 외부 `RDS`, `ElastiCache`, `S3`에 접근한다.
- `dev` app은 `S1` 내부 `PostgreSQL`, `Redis`, `MinIO`에 접근한다.

### 7.4 Failure Isolation

- `S1` 장애가 곧 작업 큐 장애를 의미하면 안 된다.
- `S2` 장애가 곧 `dev` 경로 장애를 의미하면 안 된다.
- `prod` 읽기 경로와 백그라운드 쓰기 경로를 분리한다.
- 현재 구조의 SPOF는 `S1` ingress이며, 이는 운영 리스크로 명시하고 관리한다.
- `dev`는 single-host 공개 환경으로 유지하며 자동 failover 대상에 포함하지 않는다.

## 8. Environment Strategy

### 8.1 Production

- `S1`: `prod active`
- `S2`: `async / ops`
- `RDS PostgreSQL + pgvector`
- `ElastiCache Redis`
- `S3`
- `RabbitMQ`는 self-hosted 또는 추후 `Amazon MQ for RabbitMQ` 전환 검토

### 8.2 Development

- `S1`: `dev active`
- `S1` 내부 `PostgreSQL`
- `S1` 내부 `Redis`
- `S1` 내부 `MinIO`
- 필요 시 `dev` 비동기 작업은 별도 queue namespace 또는 vhost로 분리한다.

환경 차이 원칙:

- 애플리케이션 코드는 엔드포인트만 바뀌고 동작 방식은 같아야 한다.
- 브로커 URL과 캐시 URL은 반드시 분리한다.
- `prod`와 `dev` queue / cache key / bucket namespace는 분리한다.
- 루트의 `.env.dev`, `.env.prod`를 기준으로 환경 변수를 관리한다.

## 9. Compose and Repository Contracts

### 9.1 Compose Layout

- `frontend/`: FE 서비스 compose
- `backend/`: Spring Boot 서비스 compose
- `data-platform/`: FastAPI, crawler, worker compose
- `infra/`: Nginx, Jenkins, monitoring 등 공통 인프라 compose

### 9.2 Data Platform Contract

- `data-platform/api/`: FastAPI RAG 서비스
- `data-platform/crawler/openapi/`: Open API 수집기
- `data-platform/crawler/dataset/`: 데이터셋 수집기
- `data-platform/docker-compose.worker.yml`: Celery worker, beat, crawler 배치

`data-platform/spark/`, `data-platform/hdfs/`는 현재 저장소에 남아 있어도 MVP 운영 경로에는 포함하지 않는다.

## 10. Delivery Phases

### Phase 1. Foundation

- 문서, 환경 변수, Compose 계약을 정리한다.
- `RabbitMQ`, `Redis`, `PostgreSQL`, `S3` 역할을 분리한다.
- `prod`와 `dev` 데이터 경계를 고정한다.
- HDFS/Spark를 MVP 기본 경로에서 제외한다.

### Phase 2. Service Plane

- `S1` 단일 `Nginx`에 `prod/dev` path 라우팅을 정리한다.
- `S1`의 `prod active`와 `dev active` 경로(`/`, `/api`, `/dev`, `/dev/api`)를 먼저 안정화한다.

### Phase 3. Async Plane

- `S2`에 `RabbitMQ`, `Celery Beat`, `Celery Worker`, crawler를 올린다.
- `collect`, `embed`, `reindex` 큐를 분리한다.

### Phase 4. Data Wiring

- `prod`는 `PostgreSQL + pgvector`, `Redis`, `S3`를 연결한다.
- `dev`는 `S1` 내부 `PostgreSQL`, `Redis`, `MinIO`를 연결한다.
- 수집 -> 저장 -> 임베딩 흐름을 end-to-end로 연결한다.

### Phase 5. Ops

- `Jenkins`, `Prometheus`, `Grafana`, `Loki`, `Alertmanager`를 정비한다.
- 큐 적체, worker 실패, 서비스 헬스 체크를 관측 가능하게 만든다.
- `S1` ingress SPOF와 `S2` async/ops 상태를 운영자가 확인할 수 있게 한다.

### Phase 6. Hardening

- retry / DLQ 정책을 정리한다.
- 운영 알림과 배포 가드레일을 강화한다.
- 필요할 때만 ingress failover, broker 고가용성, multi-AZ 확장을 검토한다.

## 11. Explicit Non-Goals

다음 항목은 현재 MVP 인프라 범위에 포함하지 않는다.

- `HDFS` 기반 데이터 레이크
- `Spark` 기반 분산 분석 파이프라인
- Redis를 브로커와 캐시로 동시에 혼용하는 구조
- `prod` 자동 failover
- `dev` 자동 failover
- `RabbitMQ` 클러스터 기반 고가용성

## 12. Summary

현재 SODA 인프라의 핵심은 다음 한 줄로 정리된다.

> `S1`은 단일 `Nginx`로 `prod active + dev active`를 운영하고, `S2`는 `async/ops`를 담당하며, `prod` 상태 저장은 `RDS + ElastiCache + S3`, `dev` 상태 저장은 `S1` 내부 `PostgreSQL + Redis + MinIO`로 분리한다.
