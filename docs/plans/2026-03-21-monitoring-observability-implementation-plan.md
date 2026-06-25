# SODA 모니터링 / 관측 구현 계획

## 1. 목적

`S2`를 단일 observability plane으로 사용하고, `S1 / S2 / dev / prod / AWS`를 Grafana 4개 대시보드와 기본 알림으로 관찰 가능하게 만든다.

핵심 구조는 다음과 같다.

- `S1`: 애플리케이션과 수집 agent
- `S2`: `Grafana + Prometheus + Loki + Alertmanager`와 exporter
- `S1 nginx`: `/grafana/`만 예외적으로 `S2 grafana-prod`로 reverse proxy

## 2. 대상 파일

- 수정
  - `infra/nginx/nginx.conf`
  - `infra/docker-compose.common.yml`
  - `infra/docker-compose.worker.prod.yml`
  - `infra/monitoring/prometheus.prod.yml`
  - `infra/monitoring/loki.yml`
  - `scripts/infra/s1/up-prod.sh`
  - `scripts/infra/s2/up-monitoring.sh`
  - `backend/build.gradle`
  - `backend/src/main/resources/application.yml`
  - `data-platform/api/app/main.py`
  - `requirements.txt`
- 추가
  - `infra/monitoring/alertmanager.yml`
  - `infra/monitoring/blackbox.yml`
  - `infra/monitoring/promtail.s1.yml`
  - `infra/monitoring/grafana/dashboards/*.json`
  - `infra/monitoring/grafana/provisioning/dashboards/*.yml`
  - `infra/monitoring/prometheus-alerts/*.yml`

## 3. 구현 단계

### 3.1 Grafana 접근 경로 확정

대상 파일:

- `infra/nginx/nginx.conf`
- `infra/docker-compose.worker.prod.yml`

작업:

- `/grafana/` reverse proxy location 추가
- `grafana-prod` 환경 변수에 `GF_SERVER_ROOT_URL`, `GF_SERVER_SERVE_FROM_SUB_PATH=true` 추가

검증:

- `curl -I https://j14e105.p.ssafy.io/grafana/` 기준으로 로그인 페이지 응답 확인

### 3.2 S2 observability plane 보강

대상 파일:

- `infra/docker-compose.worker.prod.yml`
- `scripts/infra/s2/up-monitoring.sh`
- `infra/monitoring/alertmanager.yml`
- `infra/monitoring/blackbox.yml`
- `infra/monitoring/loki.yml`

작업:

- `alertmanager-prod`, `blackbox-exporter`, `node-exporter-s2` 서비스 추가
- `loki` persistent volume 추가
- `up-monitoring.sh`가 새 서비스를 함께 올리도록 수정

검증:

- `docker compose ... config`
- 개별 health check

### 3.3 S1 수집 agent 추가

대상 파일:

- `infra/docker-compose.common.yml`
- `scripts/infra/s1/up-prod.sh`
- `infra/monitoring/promtail.s1.yml`

작업:

- `node-exporter-s1`, `cadvisor-s1`, `promtail-s1`, `nginx-prometheus-exporter` 추가
- `up-prod.sh`가 `nginx`뿐 아니라 S1 수집 agent도 함께 올리도록 수정

검증:

- `S2`에서 `S1` exporter port scrape 가능 여부 확인

### 3.4 Prometheus scrape / alert rule 확장

대상 파일:

- `infra/monitoring/prometheus.prod.yml`
- `infra/monitoring/prometheus-alerts/s1.yml`
- `infra/monitoring/prometheus-alerts/s2.yml`
- `infra/monitoring/prometheus-alerts/apps.yml`

작업:

- `S1 / S2 / app / aws-health / blackbox` scrape job 정의
- alert rule file include

검증:

- `promtool check config`
- `promtool check rules`

### 3.5 Spring Boot 메트릭 추가

대상 파일:

- `backend/build.gradle`
- `backend/src/main/resources/application.yml`

작업:

- Actuator, Micrometer, Prometheus registry 의존성 추가
- `/actuator/prometheus` 노출 설정 추가

검증:

- `spring-blue`, `spring-green`, `dev-spring` scrape 가능 여부 확인

### 3.6 FastAPI 메트릭 추가

대상 파일:

- `requirements.txt`
- `data-platform/api/app/main.py`

작업:

- Prometheus metrics middleware 추가
- `/metrics` endpoint 노출

검증:

- `fastapi-prod`, `fastapi-dev` scrape 가능 여부 확인

### 3.7 AWS 관리형 health check

대상 파일:

- `infra/docker-compose.worker.prod.yml`

작업:

- `RDS PostgreSQL`, `ElastiCache Redis` TCP health check 정의
- `S3` HTTP health check 정의

검증:

- Prometheus에서 probe target / label 확인

### 3.8 Grafana provisioning

대상 파일:

- `infra/monitoring/grafana/provisioning/dashboards/default.yml`
- `infra/monitoring/grafana/dashboards/s1-server.json`
- `infra/monitoring/grafana/dashboards/s2-server.json`
- `infra/monitoring/grafana/dashboards/data-dev.json`
- `infra/monitoring/grafana/dashboards/data-prod.json`

작업:

- datasource 외에 dashboards provisioning 추가
- 4개 대시보드 기본 패널 구성

검증:

- Grafana 재기동 후 자동 로드 확인

### 3.9 Alertmanager / Mattermost 연결

대상 파일:

- `infra/monitoring/alertmanager.yml`
- `infra/docker-compose.worker.prod.yml`

작업:

- Mattermost webhook receiver 설정
- `critical`, `warning` route 구분

검증:

- 테스트 alert 전송 확인

### 3.10 운영 검증과 문서 정리

대상 파일:

- `docs/Infrastructure.md`
- `infra/S1_S2_INFRA_PLAN.md`
- `docs/plans/2026-03-21-monitoring-observability-design.md`

작업:

- `docker compose config`, `promtool`, endpoint curl, Grafana login, Prometheus target 상태 검증
- `dev`, `prod` 각각 로그 / 메트릭이 4개 대시보드에 표시되는지 확인
- `S1 / S2` exporter port 정책과 Mattermost alert 수신 절차 문서화

## 4. 선행 조건

- `S1 nginx`가 `S2 grafana-prod`에 private network로 접근 가능해야 한다.
- `S1` exporter 포트는 `S2`에서만 접근 가능하도록 보안 그룹이 정리되어야 한다.
- `RabbitMQ`의 `rabbitmq_prometheus` plugin은 계속 활성 상태여야 한다.

## 5. 검증 순서

1. `docker compose config`
2. `promtool check config`
3. `promtool check rules`
4. 개별 metrics endpoint curl
5. Grafana `/grafana/` 로그인 페이지 확인
6. Prometheus target up 확인
7. Loki 로그 유입 확인
8. Mattermost 테스트 alert 확인

## 6. 완료 기준

- `/grafana/` 경로로 Grafana 로그인 페이지 접근 가능
- 4개 대시보드가 provisioning 되어 있음
- `S1`, `S2`, `dev`, `prod` 주요 지표와 `RDS`, `ElastiCache`, `S3` health check 조회 가능
- `dev`, `prod` 로그를 Loki에서 필터링 가능
- Mattermost로 기본 `critical`, `warning` 알림 수신 가능
