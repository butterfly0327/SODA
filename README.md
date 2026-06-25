<div align="center">

# SODA

### SSAFY Open-api Dataset Assistant

**프로젝트에 필요한 데이터, 한 번에 찾고 바로 검토할 수 있게 돕는 플랫폼**

<br>

[![React](https://img.shields.io/badge/React-61DAFB?style=flat-square&logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=flat-square&logo=typescript&logoColor=white)](https://www.typescriptlang.org)
[![Spring Boot](https://img.shields.io/badge/Spring_Boot_3-6DB33F?style=flat-square&logo=springboot&logoColor=white)](https://spring.io/projects/spring-boot)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=flat-square&logo=postgresql&logoColor=white)](https://www.postgresql.org)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white)](https://www.docker.com)
[![Jenkins](https://img.shields.io/badge/Jenkins-D24939?style=flat-square&logo=jenkins&logoColor=white)](https://www.jenkins.io)

</div>

---

## 프로젝트 소개

**SODA**는 SSAFY 교육생을 위한 **RAG 기반 데이터 자원 추천 및 적합도 분석 플랫폼**입니다.

프로젝트 목적을 자연어로 입력하면 여러 Open API와 데이터셋 후보를 함께 검색하고, 적합도 분석과 활용 가이드를 제공합니다.

### 왜 필요한가

- 데이터 자원이 여러 사이트에 흩어져 있어 직접 탐색 비용이 큽니다.
- 키워드 검색만으로는 프로젝트 목적에 맞는 조합을 찾기 어렵습니다.
- 데이터셋과 API의 구조, 품질, 활용 난이도를 빠르게 파악하기 어렵습니다.

**SODA는 탐색 시간을 줄이고, 실제 프로젝트에 바로 쓸 수 있는 데이터 자원을 추천하는 것을 목표로 합니다.**

### 핵심 기능

- **자연어 기반 검색**: 프로젝트 설명을 입력하면 의미 기반으로 데이터 자원을 찾습니다.
- **RAG 기반 추천**: `pgvector` 검색 결과를 바탕으로 LLM이 추천 이유와 활용 가이드를 만듭니다.
- **데이터셋 + Open API 통합 추천**: 데이터와 API를 한 번에 제안합니다.
- **비동기 수집 파이프라인**: 신규 데이터 자원 수집과 임베딩 생성을 백그라운드에서 처리합니다.
- **프로젝트 적합도 분석**: 목적에 맞는 점수와 판단 근거를 제공합니다.

### 핵심 흐름

```text
사용자 입력
  -> Query Embedding
  -> pgvector 검색
  -> LLM 분석/추천 생성
  -> 결과 반환
```

---

## 현재 아키텍처 결정

- 기준 문서: `docs/adr/ADR-003-rabbitmq-redis-for-async-processing.md`
- 선택안: **Option D**
- 핵심 원칙:
  - `Celery`는 비동기 실행기로 유지
  - `RabbitMQ`는 작업 브로커로 사용
  - `Redis`는 캐시, rate limit, 짧은 TTL 상태 저장에 사용

### 서버 역할

- `S1`: `prod active + dev active`
  - 단일 `Nginx`
  - `prod Frontend / Spring Boot / FastAPI`
  - `dev Frontend / Spring Boot / FastAPI`
  - `dev PostgreSQL / Redis / MinIO`
- `S2`: `async / ops`
  - `RabbitMQ`
  - `Celery Worker / Beat`
  - 수집기(crawler)
  - `Jenkins`
  - `Prometheus / Grafana / Loki / Alertmanager`

### 관리형 상태 저장소

- `prod`
  - `RDS PostgreSQL + pgvector`: 메타데이터, 임베딩, 검색 인덱스
  - `ElastiCache Redis`: 캐시, rate limit, lock, 짧은 상태값
  - `S3`: 원본 파일 및 대용량 산출물 저장
- `dev`
  - `S1` 내부 `PostgreSQL / Redis / MinIO`

### 네트워크 / Ingress 기준

- `S1 nginx`는 하나만 두고 다음 경로를 분기한다.
  - `/`, `/api`, `/rag` -> `prod`
  - `/dev`, `/dev/api`, `/dev/rag` -> `dev`
- `S2`는 외부 ingress를 받지 않는다.
- 현재 구조에서는 `prod` 자동 failover를 제공하지 않는다.
- `dev`는 외부 공개 환경이지만 single-host로 운영한다.

### 현재 저장소 상태

- 현재 저장소는 `D안` 기준의 compose/문서 계약을 맞춰가는 단계입니다.
- 현재 기준의 목표 구조는 `S1 service ingress + S2 async/ops`입니다.
- 일부 서비스 compose는 아직 placeholder 실행(`sleep infinity`) 상태일 수 있습니다.
- 따라서 이 README는 "완성된 배포 가이드"보다 "현재 기준 아키텍처와 운영 계약"을 설명하는 문서로 읽는 것이 맞습니다. 

---

## 기술 스택

| 분류 | 기술 |
|---|---|
| Frontend | React, TypeScript, Tailwind CSS |
| Backend | Spring Boot 3, Spring Data JPA, Spring Security |
| AI/RAG | Python FastAPI, LangChain, LLM API, pgvector |
| DB | PostgreSQL + pgvector |
| Async Processing | Celery, RabbitMQ |
| Cache / State | Redis, ElastiCache |
| Storage | S3, MinIO |
| Data Collection | CKAN API, REST API SDK, OAI-PMH, SPARQL, Python crawler |
| Infra | Docker, Docker Compose, Nginx, AWS |
| CI/CD | Jenkins, GitLab |
| Monitoring | Prometheus, Grafana, Loki |

---

## 프로젝트 구조

```text
S14P21E105/
├── backend/                # Spring Boot API
│   ├── docker-compose.yml
│   ├── docker-compose.dev.yml
│   └── docker-compose.prod.yml
├── data-platform/          # FastAPI RAG + crawler + worker runtime
│   ├── api/
│   ├── crawler/
│   │   ├── openapi/
│   │   └── dataset/
│   ├── docker-compose.yml
│   ├── docker-compose.dev.yml
│   ├── docker-compose.prod.yml
│   └── docker-compose.worker.yml
├── docs/                   # 기획/아키텍처/ADR/계획 문서
├── frontend/               # React frontend
├── infra/                  # Nginx, Jenkins, Monitoring, 공통 인프라
├── scripts/                # 초기화 및 공통 스크립트
├── Makefile
└── README.md
```

### Compose 운영 원칙

- `docker-compose.yml`은 공통 계약 파일이면서 개발자가 바로 실행해볼 수 있는 기본 런타임을 가진다.
- `docker-compose.dev.yml`은 HMR, reload, bind mount 같은 개발 편의 기능을 추가한다.
- `docker-compose.prod.yml`은 운영 배포 차이만 override한다.
- 서비스 도메인(`frontend/backend/data-platform`)의 `docker-compose.local.yml`은 제거했다.
- `infra/docker-compose.local.yml`만 로컬 운영 도구 포트 공개용으로 유지한다.
- `data-platform`은 여기에 `docker-compose.worker.yml`을 추가로 사용해 워커성 서비스를 분리합니다.
- `FastAPI` 코드는 `backend/`가 아니라 `data-platform/api/`에서 관리합니다.
- `infra/`는 공통 인프라와 운영성 컴포넌트만 다룹니다.

### 현재 Compose 방향

- 개발 기본값: `docker-compose.yml` 또는 `docker-compose.yml + docker-compose.dev.yml`
- 운영 배포: `docker-compose.yml + docker-compose.prod.yml`
- 목표는 `base`가 contract-only placeholder가 아니라 개발자가 바로 확인 가능한 runnable default가 되는 것이다.

---

## 주요 문서

- 아키텍처: `docs/Infrastructure.md`
- 인프라 실행 계획: `infra/S1_S2_INFRA_PLAN.md`
- 비동기 처리 ADR: `docs/adr/ADR-003-rabbitmq-redis-for-async-processing.md`

---

## 시작하기

### 1. 클론

```bash
git clone https://lab.ssafy.com/s14-bigdata-dist-sub1/S14P21E105.git
cd S14P21E105
```

### 2. 초기 세팅

```bash
make init
```

Git hook이 설치되어 커밋 메시지의 Jira 이슈 키가 자동 변환됩니다.

### 3. 환경 변수 준비

- 개발용: `.env.dev`
- 운영용: `.env.prod`

현재 compose는 루트의 `.env.dev`, `.env.prod`를 직접 참조합니다.

### 4. Compose 실행 기준

- 개발 기본값: `docker-compose.yml` 또는 `docker-compose.yml + docker-compose.dev.yml`
- 운영: `docker-compose.yml + docker-compose.prod.yml`
- 개발자 로컬 실행은 `docker-compose.yml` 또는 `docker-compose.yml + docker-compose.dev.yml`을 기본 경로로 본다.

### 5. 문서 확인

- 아키텍처 결정을 먼저 확인하려면 `docs/adr`와 `docs/Infrastructure.md`를 읽는 것을 권장합니다.

---

## 커밋 컨벤션

### 커밋 메시지

```text
{type}[#{이슈번호}]: {내용}
```

```bash
feat[#31]: docker-compose.dev.yml 생성
fix[#32]: RDS 커넥션 타임아웃 수정
refactor[#33]: Celery 태스크 구조 개선
chore[#41]: .gitignore 업데이트
docs[#42]: API 명세서 작성
```

`make init` 실행 후 `[#31]`은 자동으로 `[S14P21E105-31]`로 변환되어 Jira에 연결됩니다.

### 타입

| type | 용도 |
|---|---|
| `feat` | 새 기능 |
| `fix` | 버그 수정 |
| `hotfix` | 긴급 수정 |
| `refactor` | 리팩토링 |
| `chore` | 설정, 기타 |
| `test` | 테스트 |
| `docs` | 문서 |

### 브랜치

```text
feat/{설명}-{이슈번호}     예: feat/server-init-31
fix/{설명}-{이슈번호}      예: fix/rds-timeout-32
feat/{기능명}              예: feat/infra-init
```

### MR

- 제목에 Jira 이슈 키 포함: `S14P21E105-32 Prod AWS 서비스 연결`
- 본문에 `Closes S14P21E105-32` 포함 시 머지 후 Jira 이슈 자동 완료
