# Codex Dev LLM Router Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a dev-only Codex adapter in front of the current GMS LLM paths, with automatic fallback to GMS and no nginx or Jenkinsfile changes in the first rollout.

**Architecture:** A new `codex-adapter-dev` service runs `codex exec` with a shared mounted Codex home directory. FastAPI adds a small `LlmRouter` abstraction so existing services can call “primary Codex, fallback GMS” without changing the external API contract. Dev rollout uses optional `env-dev` keys and manual S1 secret placement so existing CI/CD stays intact.

**Tech Stack:** FastAPI, httpx, Python subprocess / asyncio, Docker Compose, Jenkins dev pipeline, Codex CLI, unittest

---

## Chunk 1: Dev Adapter Scaffold

### Task 1: Add dev-only adapter container and config surface

**Files:**
- Create: `data-platform/codex_adapter/Dockerfile.dev`
- Modify: `data-platform/docker-compose.dev.yml`
- Modify: `data-platform/api/app/core/config.py`
- Test: `scripts/tests/dev-deploy-guardrails.test.sh`

- [x] **Step 1: Write the failing config plan checks**

Document the target env keys in comments or docstrings inside `config.py` additions before wiring usage:

- `CODEX_ADAPTER_ENABLED`
- `CODEX_ADAPTER_BASE_URL`
- `CODEX_FALLBACK_TO_GMS`
- `CODEX_MODEL`
- `CODEX_TIMEOUT_SECONDS`
- `CODEX_MAX_CONCURRENCY`
- `CODEX_MAX_QUEUE`

- [x] **Step 2: Add config fields to FastAPI settings**

Add minimal optional settings in [config.py](/Users/ryuwon/Desktop/soda/data-platform/api/app/core/config.py). Do not remove or rename existing GMS settings.

- [x] **Step 3: Add `codex-adapter-dev` to dev compose**

Modify [docker-compose.dev.yml](/Users/ryuwon/Desktop/soda/data-platform/docker-compose.dev.yml) to define a dev-only service with:

- image build from `data-platform/codex_adapter/Dockerfile.dev`
- internal port `8091`
- volume mount `${CODEX_HOME_HOST_PATH:-./.codex-empty}:/root/.codex`
- shared dev network membership matching `fastapi-dev`

- [x] **Step 4: Add adapter Dockerfile**

Create a Dockerfile that:

- starts from Python slim
- installs Node/npm
- installs `@openai/codex@0.116.0`
- installs root `requirements.txt`
- runs adapter uvicorn app

- [x] **Step 5: Run compose config validation**

Run:

```bash
docker compose --env-file .env.dev --profile dev -f data-platform/docker-compose.yml -f data-platform/docker-compose.dev.yml config >/dev/null
```

Expected: exit code `0`

- [x] **Step 6: Run existing deploy guardrail test**

Run:

```bash
bash scripts/tests/dev-deploy-guardrails.test.sh
```

Expected: `dev-deploy-guardrails tests passed`

## Chunk 2: Codex Adapter Service

### Task 2: Implement the adapter request/response contract

**Files:**
- Create: `data-platform/codex_adapter/app/__init__.py`
- Create: `data-platform/codex_adapter/app/config.py`
- Create: `data-platform/codex_adapter/app/schemas.py`
- Create: `data-platform/codex_adapter/app/status.py`
- Create: `data-platform/codex_adapter/app/main.py`
- Test: `data-platform/codex_adapter/tests/test_runner.py`

- [x] **Step 1: Write a failing status test skeleton**

Create `data-platform/codex_adapter/tests/test_runner.py` with a minimal case that expects:

```python
self.assertFalse(status["authPresent"])
self.assertEqual(status["maxConcurrency"], 1)
```

- [x] **Step 2: Run the test to confirm the file is discovered**

Run:

```bash
python -m unittest discover -s data-platform/codex_adapter/tests -p 'test_runner.py' -v
```

Expected: import or attribute failure before implementation

- [x] **Step 3: Add adapter schemas and status model**

Create request/response schema models for:

- generic chat completion style request
- status response
- error response

- [x] **Step 4: Add adapter FastAPI app**

Create routes:

- `GET /health`
- `GET /status`
- `POST /v1/chat/completions`

- [x] **Step 5: Re-run the adapter test**

Run:

```bash
python -m unittest discover -s data-platform/codex_adapter/tests -p 'test_runner.py' -v
```

Expected: status-related test now passes or moves to runner failure

### Task 3: Add serialized Codex execution and bounded queue

**Files:**
- Create: `data-platform/codex_adapter/app/runner.py`
- Modify: `data-platform/codex_adapter/app/main.py`
- Modify: `data-platform/codex_adapter/app/status.py`
- Test: `data-platform/codex_adapter/tests/test_runner.py`

- [x] **Step 1: Write failing tests for overload and missing auth**

Add cases covering:

- missing `/root/.codex/auth.json`
- queue overflow returns adapter error
- non-zero subprocess exit becomes structured upstream error

- [x] **Step 2: Run the focused adapter tests**

Run:

```bash
python -m unittest discover -s data-platform/codex_adapter/tests -p 'test_runner.py' -v
```

Expected: failures showing missing runner behavior

- [x] **Step 3: Implement `runner.py`**

Implement:

- `asyncio.Semaphore(max_concurrency)`
- bounded in-memory queue accounting
- `codex exec` subprocess call
- timeout handling
- `auth.json` presence check
- result normalization to a chat-completion-like payload

- [x] **Step 4: Wire runner into `POST /v1/chat/completions`**

Return structured success on valid output and structured failure on adapter-side errors.

- [x] **Step 5: Re-run adapter tests**

Run:

```bash
python -m unittest discover -s data-platform/codex_adapter/tests -p 'test_runner.py' -v
```

Expected: PASS

## Chunk 3: FastAPI Router and GMS Fallback

### Task 4: Extract existing GMS chat client

**Files:**
- Create: `data-platform/api/app/services/gms_chat_client.py`
- Modify: `data-platform/api/app/services/chat_intent_service.py`
- Modify: `data-platform/api/app/services/rag_service.py`
- Modify: `data-platform/api/app/services/merge_recommendation_service.py`
- Modify: `data-platform/api/app/services/dataset_recommendation_service.py`
- Test: `data-platform/api/tests/test_llm_router.py`

- [x] **Step 1: Write a failing GMS passthrough test**

Create a test that patches `httpx` and asserts the outgoing GMS request still includes:

```python
self.assertEqual(payload["model"], "gpt-5.2")
self.assertIn("Authorization", headers)
```

- [x] **Step 2: Run the focused API test**

Run:

```bash
python -m unittest discover -s data-platform/api/tests -p 'test_llm_router.py' -v
```

Expected: import failure for missing router/client modules

- [x] **Step 3: Create `gms_chat_client.py`**

Move direct GMS POST logic into a reusable client without changing payload semantics.

- [x] **Step 4: Update one caller first**

Switch `chat_intent_service.py` to use `GmsChatClient` and verify behavior is unchanged.

- [x] **Step 5: Re-run focused API test**

Run:

```bash
python -m unittest discover -s data-platform/api/tests -p 'test_llm_router.py' -v
```

Expected: still failing on missing fallback router, but direct GMS path import works

### Task 5: Add FastAPI `LlmRouter` with Codex primary and GMS fallback

**Files:**
- Create: `data-platform/api/app/services/llm_router.py`
- Modify: `data-platform/api/app/services/chat_intent_service.py`
- Modify: `data-platform/api/app/services/rag_service.py`
- Modify: `data-platform/api/app/services/merge_recommendation_service.py`
- Modify: `data-platform/api/app/services/dataset_recommendation_service.py`
- Modify: `data-platform/api/app/services/openapi_recommendation_service.py`
- Test: `data-platform/api/tests/test_llm_router.py`

- [x] **Step 1: Add failing router tests**

Add cases for:

- adapter success returns Codex result and model
- adapter timeout falls back to GMS
- adapter malformed response falls back to GMS
- adapter disabled goes straight to GMS

- [x] **Step 2: Run router tests**

Run:

```bash
python -m unittest discover -s data-platform/api/tests -p 'test_llm_router.py' -v
```

Expected: FAIL with missing `LlmRouter`

- [x] **Step 3: Implement `LlmRouter`**

Implement:

- adapter-first decision
- single retry path to GMS
- fallback reason tracking
- model name propagation

- [x] **Step 4: Switch all four LLM call sites**

Update:

- [chat_intent_service.py](/Users/ryuwon/Desktop/soda/data-platform/api/app/services/chat_intent_service.py)
- [rag_service.py](/Users/ryuwon/Desktop/soda/data-platform/api/app/services/rag_service.py)
- [merge_recommendation_service.py](/Users/ryuwon/Desktop/soda/data-platform/api/app/services/merge_recommendation_service.py)
- [dataset_recommendation_service.py](/Users/ryuwon/Desktop/soda/data-platform/api/app/services/dataset_recommendation_service.py)

and make `openapi_recommendation_service.py` persist the returned model value instead of hardcoding `settings.gpt_model`.

- [x] **Step 5: Re-run router tests**

Run:

```bash
python -m unittest data-platform.api.tests.test_llm_router -v
```

Expected: PASS

## Chunk 4: Local-only Status Endpoint

### Task 6: Expose FastAPI status for local dev verification

**Files:**
- Modify: `data-platform/api/app/api/v1/router.py`
- Modify: `data-platform/api/app/api/v1/endpoints/rag.py`
- Create: `data-platform/api/tests/test_llm_status_endpoint.py`
- Test: `data-platform/api/tests/test_llm_status_endpoint.py`

- [x] **Step 1: Write a failing endpoint test**

Add a test expecting:

```python
self.assertEqual(response.status_code, 200)
self.assertEqual(body["primaryProvider"], "codex")
```

- [x] **Step 2: Run the endpoint test**

Run:

```bash
python -m unittest discover -s data-platform/api/tests -p 'test_llm_status_endpoint.py' -v
```

Expected: FAIL because the endpoint does not exist

- [x] **Step 3: Add `GET /v1/internal/llm/status`**

Wire the endpoint in the existing router tree. Do not add nginx config.

- [x] **Step 4: Re-run the endpoint test**

Run:

```bash
python -m unittest discover -s data-platform/api/tests -p 'test_llm_status_endpoint.py' -v
```

Expected: PASS

## Chunk 5: Verification and Dev Rollout

### Task 7: Verify local Python tests and compose rendering

**Files:**
- Test only

- [x] **Step 1: Run adapter unit tests**

Run:

```bash
python -m unittest discover -s data-platform/codex_adapter/tests -p 'test_runner.py' -v
```

Expected: PASS

- [x] **Step 2: Run FastAPI router/status tests**

Run:

```bash
python -m unittest discover -s data-platform/api/tests -p 'test_llm*.py' -v
```

Expected: PASS

- [x] **Step 3: Run existing API smoke-adjacent tests**

Run:

```bash
python -m unittest discover -s data-platform/api/tests -p 'test_metrics.py' -v
python -m unittest discover -s data-platform/api/tests -p 'test_collector.py' -v
```

Expected: PASS

- [x] **Step 4: Run compose config validation**

Run:

```bash
docker compose --env-file .env.dev --profile dev \
  -f data-platform/docker-compose.yml \
  -f data-platform/docker-compose.dev.yml config >/dev/null
```

Expected: exit code `0`

- [x] **Step 5: Run dev deploy guardrail test**

Run:

```bash
bash scripts/tests/dev-deploy-guardrails.test.sh
```

Expected: `dev-deploy-guardrails tests passed`

### Task 8: Dev rollout checklist

**Files:**
- No repo changes required

- [ ] **Step 1: Update Jenkins `env-dev` credential**

Add only optional keys. Do not add them to `require-env-keys.sh`.

- [ ] **Step 2: Place Codex home on S1 dev**

Ensure:

```bash
mkdir -p /home/ubuntu/soda-dev/secrets/codex-home
install -m 600 auth.json /home/ubuntu/soda-dev/secrets/codex-home/auth.json
```

- [ ] **Step 3: Deploy `develop` through existing dev pipeline**

Expected: existing dev Jenkins stages pass without Jenkinsfile changes

- [ ] **Step 4: Verify FastAPI health**

From S1:

```bash
curl -f http://127.0.0.1:18086/v1/health
curl -f http://127.0.0.1:18086/v1/internal/llm/status
```

Expected: both return `200`

- [ ] **Step 5: Verify primary and fallback behavior**

1. Send one normal chat request and confirm model/provider shows Codex path
2. Stop `codex-adapter-dev` or temporarily move `auth.json`
3. Repeat the request and confirm fallback to GMS still returns success

Plan complete and saved to `docs/plans/2026-03-27-codex-dev-llm-router-implementation-plan.md`. Ready to execute?
