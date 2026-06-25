# Dataset Bootstrap Time Budget Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 갯수 제한 대신 시간 예산 기반으로 dataset bootstrap 수집을 수행해 발표 전 초기 적재 속도를 높인다.

**Architecture:** 기존 4시간 자동수집 스케줄은 유지하되, `max_runtime_seconds`가 설정된 경우 safe throttle은 유지하면서 safe limit cap과 default limit 주입만 우회한다. 수집기는 데이터가 바닥나면 즉시 종료하고, 데이터가 많으면 시간 예산이 끝나는 시점에 checkpoint를 남기고 종료한다.

**Tech Stack:** Python, Celery, argparse CLI, unittest

---

### Task 1: 시간 예산 인터페이스 정의

**Files:**
- Modify: `C:\Users\SSAFY\Desktop\soda\data-platform\crawler\dataset\src\metadata_ingest\cli.py`
- Modify: `C:\Users\SSAFY\Desktop\soda\data-platform\api\app\tasks\platform_tasks.py`
- Modify: `C:\Users\SSAFY\Desktop\soda\data-platform\api\app\core\celery_app.py`
- Test: `C:\Users\SSAFY\Desktop\soda\data-platform\api\tests\test_platform_tasks.py`
- Test: `C:\Users\SSAFY\Desktop\soda\data-platform\api\tests\test_celery_schedule.py`

**Step 1: Write the failing tests**

- task가 `max_runtime_seconds`를 subprocess args로 넘기는 테스트 추가
- schedule이 `DATASET_AUTO_COLLECTION_MAX_RUNTIME_SECONDS`를 kwargs로 실어주는 테스트 추가

**Step 2: Run tests to verify they fail**

Run:

```powershell
python -m unittest C:\Users\SSAFY\Desktop\soda\data-platform\api\tests\test_platform_tasks.py
python -m unittest C:\Users\SSAFY\Desktop\soda\data-platform\api\tests\test_celery_schedule.py
```

Expected:
- 새 테스트가 `--max-runtime-seconds` 또는 schedule kwargs 부재로 FAIL

**Step 3: Write minimal implementation**

- CLI에 `--max-runtime-seconds` 추가
- task에 `max_runtime_seconds` 인자 추가
- beat schedule builder가 env 값이 있을 때 kwargs에 `max_runtime_seconds` 포함

**Step 4: Run tests to verify they pass**

같은 unittest 명령 재실행

**Step 5: Commit**

```bash
git add data-platform/api/app/core/celery_app.py data-platform/api/app/tasks/platform_tasks.py data-platform/crawler/dataset/src/metadata_ingest/cli.py data-platform/api/tests/test_platform_tasks.py data-platform/api/tests/test_celery_schedule.py
git commit -m "feat: add dataset bootstrap time budget inputs"
```

### Task 2: safe cap 우회와 시간 예산 종료 구현

**Files:**
- Modify: `C:\Users\SSAFY\Desktop\soda\data-platform\crawler\dataset\src\metadata_ingest\base.py`
- Modify: `C:\Users\SSAFY\Desktop\soda\data-platform\crawler\dataset\src\metadata_ingest\cli.py`
- Test: `C:\Users\SSAFY\Desktop\soda\data-platform\crawler\dataset\tests\test_time_budget.py`

**Step 1: Write the failing tests**

- `max_runtime_seconds`가 있으면 safe mode여도 default safe limit를 강제로 넣지 않는 테스트
- 수집 루프가 시간 예산 초과 시 checkpoint를 남기고 종료하는 테스트

**Step 2: Run tests to verify they fail**

Run:

```powershell
python -m unittest C:\Users\SSAFY\Desktop\soda\data-platform\crawler\dataset\tests\test_time_budget.py
```

Expected:
- 현재 로직에서 limit cap 또는 종료 조건 부재로 FAIL

**Step 3: Write minimal implementation**

- `max_runtime_seconds`가 있으면 `safe`라도 count cap을 우회
- `BaseDatasetCollector.run()`에 monotonic time budget 종료 조건 추가

**Step 4: Run tests to verify they pass**

같은 unittest 명령 재실행

**Step 5: Commit**

```bash
git add data-platform/crawler/dataset/src/metadata_ingest/base.py data-platform/crawler/dataset/src/metadata_ingest/cli.py data-platform/crawler/dataset/tests/test_time_budget.py
git commit -m "feat: add time-budgeted dataset bootstrap execution"
```

### Task 3: 배포 기본값과 회귀 검증

**Files:**
- Modify: `C:\Users\SSAFY\Desktop\soda\.env.dev`
- Modify: `C:\Users\SSAFY\Desktop\soda\.env.prod`
- Modify: `C:\Users\SSAFY\Desktop\soda\docs\plans\2026-03-24-data-platform-celery-batch-design.md`

**Step 1: Write the failing verification**

- schedule reload로 `.env` 기반 `max_runtime_seconds`가 반영되는지 확인

**Step 2: Run verification**

Run:

```powershell
python -m unittest C:\Users\SSAFY\Desktop\soda\data-platform\api\tests\test_celery_schedule.py
python -m unittest discover -s C:\Users\SSAFY\Desktop\soda\data-platform\crawler\dataset\tests -p "test_*.py"
```

**Step 3: Write minimal implementation**

- dev/prod env에 `DATASET_AUTO_COLLECTION_MAX_RUNTIME_SECONDS=1200` 추가
- 설계 문서에 bootstrap time-budget 운영 원칙 반영

**Step 4: Run verification**

- 같은 unittest 명령 재실행
- 추가로 `python -m py_compile` 수행

**Step 5: Commit**

```bash
git add .env.dev .env.prod docs/plans/2026-03-24-data-platform-celery-batch-design.md
git commit -m "docs: configure dataset bootstrap time budget defaults"
```
