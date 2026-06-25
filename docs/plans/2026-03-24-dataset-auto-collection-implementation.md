# Dataset Auto Collection Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Celery 기반 dataset 자동수집 1차를 구현해 FastAPI 수동 실행과 beat 정기 실행을 같은 실행 경로로 통일한다.

**Architecture:** FastAPI는 thread/subprocess 대신 Celery task enqueue만 수행하고, 실제 수집은 `platform.collect_dataset_metadata`가 source 단위로 실행한다. Beat는 dataset 전 source를 4시간 간격 + source별 offset으로 스케줄링하며, 동일 source 동시 실행은 DB lock으로 차단한다.

**Tech Stack:** FastAPI, Celery, RabbitMQ, Python unittest, psycopg, PostgreSQL advisory lock

---

### Task 1: FastAPI 수동 실행을 Celery dispatch로 전환

**Files:**
- Modify: `C:\Users\SSAFY\Desktop\soda\data-platform\api\app\api\v1\endpoints\collector.py`
- Modify: `C:\Users\SSAFY\Desktop\soda\data-platform\api\app\schemas\collector.py`
- Modify: `C:\Users\SSAFY\Desktop\soda\data-platform\api\app\services\collector_service.py`
- Test: `C:\Users\SSAFY\Desktop\soda\data-platform\api\tests\test_collector.py`

**Step 1: Write the failing API tests**

Create `test_collector.py` covering:
- `POST /v1/collector/datasets/runs` returns `202`
- response includes `taskId`, `datasetSourceId`, `parserVersion`
- endpoint dispatches `platform.collect_dataset_metadata`
- broker/dispatch failure returns `500`

**Step 2: Run test to verify it fails**

Run:
```bash
python -m unittest C:\Users\SSAFY\Desktop\soda\data-platform\api\tests\test_collector.py -v
```

Expected:
- FAIL because current response schema has no `taskId`
- or FAIL because endpoint still uses `collector_service`

**Step 3: Write minimal implementation**

Implementation notes:
- replace thread-based service dispatch with Celery task enqueue
- use `collect_dataset_metadata.apply_async(...)`
- return `taskId` from Celery AsyncResult
- keep validation/error shape compatible with current API style

**Step 4: Run test to verify it passes**

Run:
```bash
python -m unittest C:\Users\SSAFY\Desktop\soda\data-platform\api\tests\test_collector.py -v
```

Expected:
- PASS

**Step 5: Commit**

Do not commit yet without user approval.

### Task 2: Dataset source overlap 방지 추가

**Files:**
- Modify: `C:\Users\SSAFY\Desktop\soda\data-platform\crawler\dataset\src\metadata_ingest\db.py`
- Modify: `C:\Users\SSAFY\Desktop\soda\data-platform\crawler\dataset\src\metadata_ingest\base.py`
- Modify: `C:\Users\SSAFY\Desktop\soda\data-platform\crawler\dataset\src\metadata_ingest\cli.py`
- Test: `C:\Users\SSAFY\Desktop\soda\data-platform\crawler\dataset\tests\test_run_lock.py`

**Step 1: Write the failing lock tests**

Cover:
- `Database.start_run()` refuses to start if same source lock is already held
- CLI summary reports `skipped` or equivalent non-fatal status for overlap

Use mocked database cursor/connection objects rather than real DB.

**Step 2: Run test to verify it fails**

Run:
```bash
python -m unittest C:\Users\SSAFY\Desktop\soda\data-platform\crawler\dataset\tests\test_run_lock.py -v
```

Expected:
- FAIL because no source lock behavior exists yet

**Step 3: Write minimal implementation**

Implementation notes:
- add source-scoped advisory lock or equivalent per-source DB lock in `start_run`
- raise a distinct exception for overlap
- convert overlap into non-fatal `skipped` summary at CLI level

**Step 4: Run test to verify it passes**

Run:
```bash
python -m unittest C:\Users\SSAFY\Desktop\soda\data-platform\crawler\dataset\tests\test_run_lock.py -v
```

Expected:
- PASS

**Step 5: Commit**

Do not commit yet without user approval.

### Task 3: Beat 스케줄을 dataset 전 source 4시간 간격 + offset으로 생성

**Files:**
- Modify: `C:\Users\SSAFY\Desktop\soda\data-platform\api\app\core\celery_app.py`
- Modify: `C:\Users\SSAFY\Desktop\soda\data-platform\api\app\tasks\platform_tasks.py`
- Test: `C:\Users\SSAFY\Desktop\soda\data-platform\api\tests\test_celery_schedule.py`

**Step 1: Write the failing schedule tests**

Cover:
- heartbeat 외에 dataset source별 beat entry 생성
- 각 source는 4시간 간격을 유지
- source별 minute offset이 다름
- `all` source는 beat schedule에 없음

**Step 2: Run test to verify it fails**

Run:
```bash
python -m unittest C:\Users\SSAFY\Desktop\soda\data-platform\api\tests\test_celery_schedule.py -v
```

Expected:
- FAIL because current beat schedule has only `platform-heartbeat`

**Step 3: Write minimal implementation**

Implementation notes:
- build beat schedule from a static source metadata table
- encode 4-hour schedule with fixed offsets
- include `safe=true`
- use bounded incremental batch defaults
- keep RabbitMQ dev/prod separation unchanged

**Step 4: Run test to verify it passes**

Run:
```bash
python -m unittest C:\Users\SSAFY\Desktop\soda\data-platform\api\tests\test_celery_schedule.py -v
```

Expected:
- PASS

**Step 5: Commit**

Do not commit yet without user approval.

### Task 4: Task argument/실행 계약을 bounded incremental batch에 맞게 정리

**Files:**
- Modify: `C:\Users\SSAFY\Desktop\soda\data-platform\api\app\tasks\platform_tasks.py`
- Modify: `C:\Users\SSAFY\Desktop\soda\data-platform\crawler\dataset\src\metadata_ingest\config.py`
- Modify: `C:\Users\SSAFY\Desktop\soda\data-platform\crawler\dataset\src\metadata_ingest\cli.py`
- Test: `C:\Users\SSAFY\Desktop\soda\data-platform\api\tests\test_platform_tasks.py`

**Step 1: Write the failing task tests**

Cover:
- beat path always passes `safe=true`
- source task uses bounded limit defaults when explicit limit is absent
- manual trigger can still override `limit` / `from_scratch`

**Step 2: Run test to verify it fails**

Run:
```bash
python -m unittest C:\Users\SSAFY\Desktop\soda\data-platform\api\tests\test_platform_tasks.py -v
```

Expected:
- FAIL because current task contract does not distinguish beat-safe defaults clearly

**Step 3: Write minimal implementation**

Implementation notes:
- add explicit task args or helper for schedule-time defaults
- avoid changing manual trigger semantics
- keep CLI `--safe` / `--limit` behavior compatible

**Step 4: Run test to verify it passes**

Run:
```bash
python -m unittest C:\Users\SSAFY\Desktop\soda\data-platform\api\tests\test_platform_tasks.py -v
```

Expected:
- PASS

**Step 5: Commit**

Do not commit yet without user approval.

### Task 5: 문서와 smoke verification 정리

**Files:**
- Modify: `C:\Users\SSAFY\Desktop\soda\docs\plans\2026-03-24-data-platform-celery-batch-design.md`
- Modify: `C:\Users\SSAFY\Desktop\soda\docs\plans\2026-03-24-data-platform-celery-batch-proposal.md`

**Step 1: Update implementation notes**

Reflect final implementation details:
- task response shape
- lock strategy
- beat generation
- bounded incremental batch defaults

**Step 2: Run focused verification**

Run:
```bash
python -m unittest C:\Users\SSAFY\Desktop\soda\data-platform\api\tests\test_collector.py -v
python -m unittest C:\Users\SSAFY\Desktop\soda\data-platform\api\tests\test_celery_schedule.py -v
python -m unittest C:\Users\SSAFY\Desktop\soda\data-platform\api\tests\test_platform_tasks.py -v
python -m unittest C:\Users\SSAFY\Desktop\soda\data-platform\crawler\dataset\tests\test_run_lock.py -v
```

Expected:
- PASS

**Step 3: Record residual risks**

Document:
- real Celery/DB integration still needs runtime verification in container
- external API quota behavior is partially documentation-based
- high-risk sources need production observation after deploy

**Step 4: Commit**

Do not commit yet without user approval.
