# =============================================================================
# Makefile - 운영 명령어 집합 (S1/S2 기준)
# =============================================================================
#
# 📋 아키텍처 개요:
#   - Local: 단일 호스트 통합 검증용 스택 (S1 + S2 일부 포함)
#   - Dev: Server 1 개발 환경 스택
#   - Prod: Server 1 운영 환경 스택
#   - S2: Async / CI / Monitoring 보조 스택
#
# 🚀 권장 시작 순서:
#   1. make infra-preflight       # compose 계약 검증
#   2. make local-up              # 로컬 통합 검증
#      또는 make dev-up / make prod-up
#   3. make infra-s2-up-monitoring / infra-s2-up-ci   # 필요 시
#
# ⚠️ 주의사항:
#   - local-up은 단일 호스트 통합 검증용입니다.
#   - dev-up / prod-up은 환경 축 기준의 대표 진입점입니다.
#   - infra-config-phase0, infra-up-dev 등 기존 명령은 호환 alias로 유지합니다.
#
# =============================================================================

.DEFAULT_GOAL := help

.PHONY: \
	help init \
	infra-bootstrap-networks infra-preflight infra-config-phase0 \
	local-up local-down local-ps \
	dev-up dev-down dev-ps \
	prod-up prod-down prod-ps \
	infra-local-up-dev infra-local-down-dev infra-local-ps \
	infra-up-dev infra-down-dev infra-ps \
	infra-s1-up-common infra-s1-down-common infra-s1-ps-common \
	infra-s1-up-dev infra-s1-down-dev infra-s1-ps-dev \
	infra-s1-up-prod infra-s1-down-prod infra-s1-ps-prod \
	infra-s2-up-async infra-s2-down-async infra-s2-ps-async \
	infra-s2-up-monitoring infra-s2-stop-monitoring infra-s2-down-monitoring \
	infra-s2-up-ci infra-s2-stop-ci infra-s2-down-ci infra-s2-ps \
	fe-up fe-down fe-logs \
	be-build be-up be-down be-logs be-dev-run \
	dev-app-up dev-app-down dev-app-ps \
	prod-app-up prod-app-down prod-app-ps \
	status \
	up-local down-local ps-local up-dev down-dev ps-dev up-prod down-prod ps-prod

INFRA_SCRIPT_DIR := scripts/infra
COMMON_SCRIPT_DIR := $(INFRA_SCRIPT_DIR)/common
LOCAL_SCRIPT_DIR := $(INFRA_SCRIPT_DIR)/local
S1_SCRIPT_DIR := $(INFRA_SCRIPT_DIR)/s1
S2_SCRIPT_DIR := $(INFRA_SCRIPT_DIR)/s2
DEV_SCRIPT_DIR := $(INFRA_SCRIPT_DIR)/dev

ifeq ($(OS),Windows_NT)
    COPY_CMD = powershell -NoProfile -Command "Copy-Item -Path 'scripts/init/prepare-commit-msg' -Destination '.git/hooks/prepare-commit-msg' -Force"
    ECHO_OK = powershell -NoProfile -Command "Write-Host '[OK] Git Hook installed successfully' -ForegroundColor Green"
else
    COPY_CMD = cp scripts/init/prepare-commit-msg .git/hooks/prepare-commit-msg && chmod +x .git/hooks/prepare-commit-msg
    ECHO_OK = echo "\033[0;32m[OK]\033[0m Git Hook installed successfully"
endif

# =============================================================================
# 기본 명령어 - 도움말
# =============================================================================
help:
	@echo "=============================================="
	@echo "  SODA - 운영 명령어 집합"
	@echo "=============================================="
	@echo ""
	@echo "  🔧 Init & Validation:"
	@echo "    make init                 - Git hook 설치"
	@echo "    make infra-bootstrap-networks - 외부 Docker 네트워크 준비"
	@echo "    make infra-preflight      - Dev/Prod compose 계약 검증"
	@echo "    make infra-config-phase0  - bootstrap + preflight 레거시 alias"
	@echo ""
	@echo "  🏠 Local Environment (All-in-One):"
	@echo "    make local-up             - 로컬 통합 스택 기동"
	@echo "    make local-down           - 로컬 통합 스택 중단"
	@echo "    make local-ps             - 로컬 통합 스택 상태 확인"
	@echo "    make infra-local-up-dev   - local-up 상세 alias"
	@echo "    make infra-local-down-dev - local-down 상세 alias"
	@echo "    make infra-local-ps       - local-ps 상세 alias"
	@echo ""
	@echo "  🚀 Environment Stacks (S1):"
	@echo "    make dev-up               - S1 Dev 환경 기동"
	@echo "    make dev-down             - S1 Dev 환경 중단"
	@echo "    make dev-ps               - S1 Dev 환경 상태 확인"
	@echo "    make prod-up              - S1 Prod 환경 기동"
	@echo "    make prod-down            - S1 Prod 환경 중단"
	@echo "    make prod-ps              - S1 Prod 환경 상태 확인"
	@echo "    make infra-s1-up-common   - S1 common 서비스 기동"
	@echo "    make infra-s1-down-common - S1 common 서비스 중단"
	@echo "    make infra-s1-ps-common   - S1 common 서비스 상태 확인"
	@echo "    make infra-s1-up-dev      - dev-up 상세 alias"
	@echo "    make infra-s1-down-dev    - dev-down 상세 alias"
	@echo "    make infra-s1-ps-dev      - dev-ps 상세 alias"
	@echo "    make infra-s1-up-prod     - prod-up 상세 alias"
	@echo "    make infra-s1-down-prod   - prod-down 상세 alias"
	@echo "    make infra-s1-ps-prod     - prod-ps 상세 alias"
	@echo ""
	@echo "  🧰 Developer Shortcuts:"
	@echo "    make fe-up                - 프론트 Dev 컨테이너 기동"
	@echo "    make fe-down              - 프론트 Dev 컨테이너 중단"
	@echo "    make fe-logs              - 프론트 Dev 로그"
	@echo "    make be-build             - 백엔드 Dev bootJar 빌드"
	@echo "    make be-up                - 백엔드 Dev + 의존성 기동"
	@echo "    make be-down              - 백엔드 Dev + 의존성 중단"
	@echo "    make be-logs              - 백엔드 Dev 로그"
	@echo "    make be-dev-run           - SSH 터널 기반 로컬 백엔드 실행"
	@echo ""
	@echo "  🖥️  Server 2 (Async / CI / Monitoring):"
	@echo "    make infra-s2-up-async       - RabbitMQ + Celery + crawler 기동"
	@echo "    make infra-s2-down-async     - RabbitMQ + Celery + crawler 중단"
	@echo "    make infra-s2-ps-async       - RabbitMQ + Celery + crawler 상태 확인"
	@echo "    make infra-s2-up-monitoring  - Monitoring 스택 기동"
	@echo "    make infra-s2-stop-monitoring - Monitoring 스택 중단"
	@echo "    make infra-s2-down-monitoring - stop-monitoring legacy alias"
	@echo "    make infra-s2-up-ci          - Jenkins 기동"
	@echo "    make infra-s2-stop-ci        - Jenkins 중단"
	@echo "    make infra-s2-down-ci        - stop-ci legacy alias"
	@echo "    make infra-s2-ps             - S2 상태 확인"
	@echo ""
	@echo "  🔁 Compatibility Aliases:"
	@echo "    make infra-config-phase0  -> make infra-bootstrap-networks && infra-preflight"
	@echo "    make infra-up-dev         -> make local-up"
	@echo "    make infra-down-dev       -> make local-down"
	@echo "    make infra-ps             -> make local-ps"
	@echo "    make dev-app-up          -> make dev-up"
	@echo "    make dev-app-down        -> make dev-down"
	@echo "    make dev-app-ps          -> make dev-ps"
	@echo "    make prod-app-up         -> make prod-up"
	@echo "    make prod-app-down       -> make prod-down"
	@echo "    make prod-app-ps         -> make prod-ps"
	@echo "    make up-local            -> make local-up"
	@echo "    make down-local          -> make local-down"
	@echo "    make ps-local            -> make local-ps"
	@echo "    make up-dev              -> make dev-up"
	@echo "    make down-dev            -> make dev-down"
	@echo "    make ps-dev              -> make dev-ps"
	@echo "    make up-prod             -> make prod-up"
	@echo "    make down-prod           -> make prod-down"
	@echo "    make ps-prod             -> make prod-ps"
	@echo "    make status               - local/S1/S2 전체 상태 요약"
	@echo ""
	@echo "=============================================="

# =============================================================================
# Init & Validation
# =============================================================================
init:
	@$(COPY_CMD)
	@$(ECHO_OK)

infra-bootstrap-networks:
	@bash $(COMMON_SCRIPT_DIR)/bootstrap-networks.sh

infra-preflight:
	@bash $(COMMON_SCRIPT_DIR)/preflight.sh

infra-config-phase0: infra-bootstrap-networks infra-preflight

# =============================================================================
# Local Environment (All-in-One)
# =============================================================================
local-up:
	@bash $(LOCAL_SCRIPT_DIR)/up-dev.sh

local-down:
	@bash $(LOCAL_SCRIPT_DIR)/down-dev.sh

local-ps:
	@bash $(LOCAL_SCRIPT_DIR)/ps.sh

# =============================================================================
# Environment Stacks - Server 1
# =============================================================================
dev-up:
	@bash $(S1_SCRIPT_DIR)/up-dev.sh

dev-down:
	@bash $(S1_SCRIPT_DIR)/down-dev.sh

dev-ps:
	@bash $(S1_SCRIPT_DIR)/ps-dev.sh

prod-up:
	@bash $(S1_SCRIPT_DIR)/up-prod.sh

prod-down:
	@bash $(S1_SCRIPT_DIR)/down-prod.sh

prod-ps:
	@bash $(S1_SCRIPT_DIR)/ps-prod.sh

# 상세 명령 노출 (운영/문서용)
infra-local-up-dev: local-up
infra-local-down-dev: local-down
infra-local-ps: local-ps

infra-s1-up-common:
	@bash $(S1_SCRIPT_DIR)/up-common.sh

infra-s1-down-common:
	@bash $(S1_SCRIPT_DIR)/down-common.sh

infra-s1-ps-common:
	@bash $(S1_SCRIPT_DIR)/ps-common.sh

infra-s1-up-dev: dev-up
infra-s1-down-dev: dev-down
infra-s1-ps-dev: dev-ps
infra-s1-up-prod: prod-up
infra-s1-down-prod: prod-down
infra-s1-ps-prod: prod-ps

# 기존 명령 호환
infra-up-dev: local-up
infra-down-dev: local-down
infra-ps: local-ps

# =============================================================================
# Developer Shortcuts
# =============================================================================
fe-up:
	@bash $(DEV_SCRIPT_DIR)/fe-up.sh

fe-down:
	@bash $(DEV_SCRIPT_DIR)/fe-down.sh

fe-logs:
	@bash $(DEV_SCRIPT_DIR)/fe-logs.sh

be-build:
	@bash $(COMMON_SCRIPT_DIR)/build-backend-dev.sh

be-up:
	@bash $(DEV_SCRIPT_DIR)/be-up.sh

be-down:
	@bash $(DEV_SCRIPT_DIR)/be-down.sh

be-logs:
	@bash $(DEV_SCRIPT_DIR)/be-logs.sh

be-dev-run:
	@bash $(DEV_SCRIPT_DIR)/be-dev-run.sh

# =============================================================================
# Server 2 - Async / CI / Monitoring
# =============================================================================
infra-s2-up-async:
	@bash $(S2_SCRIPT_DIR)/up-async.sh

infra-s2-down-async:
	@bash $(S2_SCRIPT_DIR)/down-async.sh

infra-s2-ps-async:
	@bash $(S2_SCRIPT_DIR)/ps-async.sh

infra-s2-up-monitoring:
	@bash $(S2_SCRIPT_DIR)/up-monitoring.sh

infra-s2-stop-monitoring:
	@bash $(S2_SCRIPT_DIR)/down-monitoring.sh

infra-s2-up-ci:
	@bash $(S2_SCRIPT_DIR)/up-ci.sh

infra-s2-stop-ci:
	@bash $(S2_SCRIPT_DIR)/down-ci.sh

infra-s2-ps:
	@bash $(S2_SCRIPT_DIR)/ps.sh

# 기존 명령 호환
infra-s2-down-monitoring: infra-s2-stop-monitoring
infra-s2-down-ci: infra-s2-stop-ci

# =============================================================================
# Legacy / Alias Commands
# =============================================================================
dev-app-up: dev-up
dev-app-down: dev-down
dev-app-ps: dev-ps

prod-app-up: prod-up
prod-app-down: prod-down
prod-app-ps: prod-ps

status:
	@bash scripts/infra/status.sh

up-local: local-up
down-local: local-down
ps-local: local-ps

up-dev: dev-up
down-dev: dev-down
ps-dev: dev-ps

up-prod: prod-up
down-prod: prod-down
ps-prod: prod-ps
