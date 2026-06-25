# Codex Prod Rollout Checklist

**Goal:** Promote the dev-only Codex-backed LLM routing to prod with the same `Codex primary -> GMS fallback` behavior while keeping secret handling manual and outside the repository worktree.

**Current Status:**
- FastAPI already reads `LLM_PRIMARY_PROVIDER` and `CODEX_*` env keys.
- Prod compose now defines a `codex-adapter-prod` service, but runtime enablement still requires a valid auth mount and prod env rollout.
- S1 currently has only `/home/ubuntu/codex-home-dev/auth.json`; `/home/ubuntu/codex-home-prod/auth.json` is not present.

## 1. Code and Compose Changes

- Verify `codex-adapter-prod` in [data-platform/docker-compose.prod.yml](/Users/ryuwon/Desktop/soda/data-platform/docker-compose.prod.yml) is deployed on S1.
- Match the dev adapter shape:
  - build from `data-platform/codex_adapter/Dockerfile.dev` or a prod-specific equivalent
  - internal port `8091`
  - mount `/home/ubuntu/codex-home-prod:/root/.codex`
  - expose the service on the same prod network as `fastapi-prod`
- Point prod FastAPI to `CODEX_ADAPTER_BASE_URL=http://codex-adapter-prod:8091`.

## 2. Prod Environment Values

Add these keys to the Jenkins `env-prod` file credential:

```env
LLM_PRIMARY_PROVIDER=codex
CODEX_ADAPTER_ENABLED=true
CODEX_ADAPTER_BASE_URL=http://codex-adapter-prod:8091
CODEX_FALLBACK_TO_GMS=true
CODEX_MODEL=gpt-5.4
CODEX_TIMEOUT_SECONDS=45
CODEX_MAX_CONCURRENCY=1
CODEX_MAX_QUEUE=100
CODEX_HOME_HOST_PATH=/home/ubuntu/codex-home-prod
```

Notes:
- Keep these keys optional from the app perspective.
- Do not add them to `require-env-keys.sh` unless prod rollout policy changes.

## 3. Secret Placement

- Create `/home/ubuntu/codex-home-prod` on S1 with mode `700`.
- Place `auth.json` at `/home/ubuntu/codex-home-prod/auth.json` with mode `600`.
- Keep the file outside `/home/ubuntu/soda-prod` so Jenkins `git clean -fd` cannot delete it.
- Continue using manual secret placement unless Jenkins secret-file delivery is added later.

## 4. Pre-Deploy Validation

- Run:

```bash
docker compose --env-file .env.prod --profile prod -f data-platform/docker-compose.yml -f data-platform/docker-compose.prod.yml config
```

- Verify `.env.prod` contains the `CODEX_*` keys with the prod adapter hostname.
- After the prod adapter is live, switch models by changing only `CODEX_MODEL` in `.env.prod` or the Jenkins `env-prod` credential and redeploying FastAPI/adapter.
- Confirm `/home/ubuntu/codex-home-prod/auth.json` exists on S1 before the first prod deployment.

## 5. Deployment

- Promote the branch through the normal `feat -> develop -> master` flow.
- Trigger the existing prod deployment after the prod compose change and `env-prod` credential update are both in place.
- Because the secret remains manual, no Jenkinsfile change is required for the first prod rollout.

## 6. Post-Deploy Smoke Checks

From S1 after deploy:

- Check `fastapi-prod` and `codex-adapter-prod` container health.
- Verify `GET /v1/health` succeeds.
- Verify `GET /v1/internal/llm/status` shows:
  - `primaryProvider=codex`
  - `authPresent=true`
  - `maxQueue=100`
- Send one real chat request and confirm `llmModel` is `gpt-5.4`.
- Check adapter logs for repeated timeout or queue overflow errors.

## 7. Rollback

- Fast rollback: change `LLM_PRIMARY_PROVIDER=gms` or `CODEX_ADAPTER_ENABLED=false` in `env-prod`.
- Secret rollback is optional; `/home/ubuntu/codex-home-prod/auth.json` can remain on disk unused.
- If the adapter service itself causes issues, remove or disable the prod adapter service in compose and redeploy.

## 8. Capacity Watchpoints

- Initial settings should stay conservative:
  - `CODEX_MAX_CONCURRENCY=1`
  - `CODEX_MAX_QUEUE=100`
- Watch for:
  - rising latency
  - adapter timeout frequency
  - queue overflow frequency
  - fallback ratio to GMS
- If prod traffic exceeds the single-session Codex limit, treat GMS fallback as the safety path rather than forcing more Codex parallelism immediately.
