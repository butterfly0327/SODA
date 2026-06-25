# SODA 모니터링 / 관측 설계

## 1. 목표

SODA 운영 환경의 관측 지점을 `S2` 중심으로 통합한다.

- 단일 진입점: `https://j14e105.p.ssafy.io/grafana/`
- 단일 관측 평면: `S2`
- 1차 범위:
  - `S1 서버 상태`
  - `S2 서버 상태`
  - `dev 환경 로그 / 메트릭`
  - `prod 환경 로그 / 메트릭`
- 1차 알림:
  - 서버, 컨테이너, 핵심 health, queue backlog, `RDS` / `ElastiCache` / `S3` health check

## 2. 범위와 비범위

### 범위

- `S2`에 `Grafana`, `Prometheus`, `Loki`, `Alertmanager`를 관측 중심으로 둔다.
- `S1 nginx`가 `/grafana/`를 `S2 grafana-prod`로 reverse proxy 한다.
- `S1`, `S2`, `dev`, `prod`, `RDS`, `ElastiCache`, `S3`를 단일 Grafana에서 조회한다.
- `frontend`는 브라우저 코드 계측 없이 서버 관점만 본다.
- `Spring Boot`, `FastAPI`는 Prometheus metrics endpoint를 추가한다.
- 로그는 `Docker json-file + Promtail + Loki`를 1차 기준으로 사용한다.

### 비범위

- `frontend web-vitals`, `browser RUM`, `Sentry`, tracing은 2차 범위다.
- `S3`는 1차에서 health check만 다룬다.
- `master` failover 자동화는 이번 설계 범위가 아니다.

## 3. 현재 상태 요약

### 3.1 실제 런타임

- `S1`
  - `nginx`, `prod-frontend`, `spring-blue`, `spring-green`, `fastapi-prod`
  - `dev-frontend`, `dev-spring`, `fastapi-dev`, `dev-postgres`, `dev-redis`, `minio`
- `S2`
  - `grafana-prod`, `prometheus-prod`, `loki-prod`, `promtail-prod`, `cadvisor-prod`
  - `rabbitmq-prod`, `celery-worker-prod`, `celery-beat-prod`, `jenkins-prod`

### 3.2 확인된 갭

- `/grafana/` 외부 프록시가 아직 없다.
- `S1`에는 `promtail`, `cadvisor`, `node exporter`, `nginx exporter`가 없다.
- `Prometheus` scrape 범위가 `self + cadvisor` 수준으로 얕다.
- `Alertmanager`는 문서에는 있으나 실제 compose에는 없다.
- `Loki`는 persistent volume이 없다.
- `Spring Boot`는 `Actuator + Micrometer + Prometheus registry`가 없다.
- `FastAPI`는 Prometheus 계측 미들웨어가 없다.
- `frontend`는 별도 브라우저 계측이 없다.

## 4. 결정 사항

### 4.1 단일 Observability Plane

- `S2`를 단일 관측 평면으로 둔다.
- `Grafana`, `Prometheus`, `Loki`, `Alertmanager`, `Blackbox Exporter`, `node-exporter`는 `S2`에 둔다.

### 4.2 접근 방식

- 외부 사용자는 `S1 nginx`를 통해서만 Grafana에 접근한다.
- URL은 `https://j14e105.p.ssafy.io/grafana/`를 사용한다.
- 인증은 `Grafana 자체 로그인`을 사용한다.
- `Prometheus`, `Loki`, `Alertmanager`는 외부 직접 노출하지 않는다.

### 4.3 대시보드 구성

- `S1 서버 상태 모니터`
- `S2 서버 상태 모니터`
- `dev 환경 로그 / 메트릭`
- `prod 환경 로그 / 메트릭`

### 4.4 AWS 포함 범위

- `RDS PostgreSQL`, `ElastiCache Redis`는 1차 대상이다.
- `S3`는 1차에서 보조 지표만 고려한다.

### 4.5 알림

- `Alertmanager -> Mattermost`를 기본 채널로 사용한다.
- 1차 알림은 운영 핵심 상태 위주로 제한한다.

## 5. 목표 토폴로지

```text
[User]
  -> https://j14e105.p.ssafy.io/grafana/
  -> S1 nginx
  -> S2 grafana-prod

[S2 observability plane]
  - grafana-prod
  - prometheus-prod
  - loki-prod
  - alertmanager-prod
  - blackbox-exporter
  - node-exporter-s2
  - promtail-prod
  - cadvisor-prod

[S1 collection agents]
  - promtail-s1
  - cadvisor-s1
  - node-exporter-s1
  - nginx-prometheus-exporter

[Application metrics]
  - spring-blue / spring-green / dev-spring -> /actuator/prometheus
  - fastapi-prod / fastapi-dev -> /metrics
  - rabbitmq-prod -> rabbitmq_prometheus

[Managed services]
  - RDS PostgreSQL -> blackbox tcp health check
  - ElastiCache Redis -> blackbox tcp health check
  - S3 -> blackbox http health check
```

## 6. 수집 설계

### 6.1 S1 서버 상태

수집 대상:

- host CPU, memory, load, disk, filesystem, network
- Docker container CPU, memory, restart, I/O
- nginx 요청량, active connections, 4xx, 5xx

구성:

- `node-exporter-s1`
- `cadvisor-s1`
- `nginx-prometheus-exporter`
- `blackbox-exporter`에서 `S1` 경유 주요 URL probe

비고:

- `S1`은 private IP `172.26.6.207` 기준으로 `S2 Prometheus`가 scrape 한다.
- 관련 포트는 `S2` 보안 그룹에서만 접근 가능하도록 제한한다.

### 6.2 S2 서버 상태

수집 대상:

- host CPU, memory, disk, network
- monitoring stack health
- `rabbitmq-prod`, `celery-worker-prod`, `celery-beat-prod`, `jenkins-prod`

구성:

- `node-exporter-s2`
- 기존 `cadvisor-prod`
- `rabbitmq_prometheus`
- `blackbox-exporter`

### 6.3 dev 환경 로그 / 메트릭

대상:

- `dev-frontend`
- `dev-spring`
- `fastapi-dev`
- `dev-postgres`, `dev-redis`, `minio`

메트릭:

- `dev-spring`: request count, error count, latency, JVM
- `fastapi-dev`: request count, status code, latency
- `dev` URL blackbox

로그:

- `promtail-s1`가 `env=dev` 라벨로 수집한다.
- Docker container label 기반으로 `service`, `container`, `env`, `server`를 붙인다.

### 6.4 prod 환경 로그 / 메트릭

대상:

- `nginx`
- `prod-frontend`
- `spring-blue`
- `spring-green`
- `fastapi-prod`
- `rabbitmq-prod`
- `celery-worker-prod`
- `celery-beat-prod`
- `RDS`
- `ElastiCache`

메트릭:

- `spring-blue`, `spring-green`: request, error, latency, JVM
- `fastapi-prod`: request, error, latency
- `RabbitMQ`: queue depth, consumers, messages rate
- `RDS`, `ElastiCache`, `S3`: health check 위주 probe

로그:

- `promtail-s1`가 prod app 로그를 수집한다.
- `promtail-prod`가 `S2` 로컬 로그를 수집한다.

## 7. 앱 계측 원칙

### 7.1 Spring Boot

추가:

- `org.springframework.boot:spring-boot-starter-actuator`
- `io.micrometer:micrometer-registry-prometheus`

노출 경로:

- `/actuator/health`
- `/actuator/prometheus`

1차 원칙:

- application metrics만 우선 추가한다.
- custom business metric은 2차로 미룬다.

### 7.2 FastAPI

추가:

- `prometheus-fastapi-instrumentator`

노출 경로:

- `/metrics`

1차 원칙:

- middleware 기반 request metric만 우선 추가한다.
- 세부 RAG 단계 metric은 2차로 미룬다.

### 7.3 Logging

1차 원칙:

- `stdout/stderr + Docker json-file + Promtail` 조합을 기준으로 간다.
- `logback-spring.xml`과 JSON structured logging은 2차 옵션이다.

판단:

- 현재 단계에서는 `logback` 필수 아님
- 다만 검색 품질과 필드 기반 탐색이 중요해지면 2차로 `structured logging` 도입

## 8. Grafana 대시보드 정의

### 8.1 S1 서버 상태 모니터

패널:

- host CPU / load / memory / disk
- network throughput
- Docker container CPU / memory / restart
- nginx active connections
- nginx requests by status
- prod / dev blackbox health

### 8.2 S2 서버 상태 모니터

패널:

- host CPU / memory / disk
- monitoring stack health
- Jenkins up
- RabbitMQ queue depth / connections / consumers
- Celery worker / beat up

### 8.3 dev 환경 로그 / 메트릭

패널:

- `dev-spring` request rate / error rate / p95 latency
- `fastapi-dev` request rate / error rate / p95 latency
- dev health endpoint blackbox
- dev logs by service
- top error logs

### 8.4 prod 환경 로그 / 메트릭

패널:

- `spring-blue` / `spring-green` request rate / error rate / latency
- `fastapi-prod` request rate / error rate / latency
- prod health endpoint blackbox
- RabbitMQ queue depth
- `RDS`, `ElastiCache`, `S3` health check
- prod logs by service

## 9. 알림 설계

### 9.1 Critical

- prod root or health blackbox down
- `nginx`, `spring-blue`, `fastapi-prod` down
- `rabbitmq-prod`, `celery-worker-prod`, `celery-beat-prod` down
- `grafana-prod`, `prometheus-prod`, `loki-prod` down

### 9.2 Warning

- S1 or S2 CPU > 85%
- memory availability low
- disk usage > 80%
- Spring/FastAPI 5xx ratio 증가
- Spring/FastAPI p95 latency 증가
- RabbitMQ queue backlog 증가
- RDS / ElastiCache / S3 health check 실패

### 9.3 알림 채널

- 1차 채널: Mattermost webhook
- 알림 노이즈를 줄이기 위해 `for` 조건과 재알림 간격을 사용한다.

## 10. 보안 / 네트워크 원칙

- `Grafana`만 `S1 nginx` 프록시로 공개한다.
- `Prometheus`, `Loki`, `Alertmanager`는 외부 비공개 유지
- `S1` exporter 포트는 `S2` private IP에서만 접근 허용
- `Grafana`는 subpath 모드로 설정한다.
  - `GF_SERVER_ROOT_URL=https://j14e105.p.ssafy.io/grafana/`
  - `GF_SERVER_SERVE_FROM_SUB_PATH=true`
- AWS 메트릭 수집은 가능하면 static key보다 `S2 EC2 IAM Role`을 우선한다.

## 11. 구현 순서

1. `S1 nginx`에 `/grafana/` proxy 추가
2. `S2`에 `Alertmanager`, `Blackbox Exporter`, `node-exporter-s2`, Loki persistence 추가
3. `S1`에 `promtail-s1`, `cadvisor-s1`, `node-exporter-s1`, `nginx exporter` 추가
4. `Spring Boot` metrics 추가
5. `FastAPI` metrics 추가
6. `Grafana` dashboard provisioning과 alert rule 반영
7. `Mattermost` alert channel 연결

## 12. 주요 리스크와 대응

### 리스크 1. S1 수집기 미배포

- 현재 `S1`에는 관련 수집기가 없다.
- 대응: `infra/docker-compose.common.yml`, `scripts/infra/s1/up-prod.sh`를 같이 수정한다.

### 리스크 2. Loki 비영속

- 현재 `Loki`는 재기동 시 로그 보존이 흔들릴 수 있다.
- 대응: volume을 명시적으로 추가하고 retention 정책을 문서화한다.

### 리스크 3. AWS managed 접근성

- `RDS`, `ElastiCache`, `S3`는 blackbox probe 기준으로만 본다.
- 대응: 세부 성능 분석은 별도 클라우드 콘솔 또는 전용 exporter를 분리 검토한다.

### 리스크 4. blue / green 혼동

- 현재 트래픽은 사실상 `spring-blue` 고정이다.
- 대응: prod 대시보드에서 active label을 명시하고, green은 standby로 표시한다.

## 13. 완료 기준

- `/grafana/`로 Grafana 로그인 페이지 접근 가능
- 4개 대시보드가 provisioning 되어 있음
- `S1`, `S2`, `dev`, `prod` 주요 지표와 `RDS`, `ElastiCache`, `S3` health check 조회 가능
- `dev`, `prod` 로그를 Loki에서 필터링 가능
- Mattermost로 기본 critical / warning 알림 수신 가능
