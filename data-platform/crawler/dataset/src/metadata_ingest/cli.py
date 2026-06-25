from __future__ import annotations

import argparse
import json
import time
from typing import Any, Dict, List

from .config import Settings
from .db import Database, SourceRunAlreadyActiveError
from .sources import COLLECTORS


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="10개 데이터셋 메타데이터 소스 수집기")
    parser.add_argument(
        "--source",
        default="all",
        help="수집 소스. all 또는 " + ", ".join(sorted(COLLECTORS.keys())),
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="소스별 최대 upsert 건수(미지정 시 safe 모드에서는 DEFAULT_SAFE_LIMIT 사용)",
    )
    parser.add_argument("--from-scratch", action="store_true", help="이전 checkpoint를 무시하고 처음부터 수집")
    parser.add_argument(
        "--reconcile-missing",
        action="store_true",
        help="full from-scratch 성공 run 기준으로 이번에 보지 못한 기존 ACTIVE row를 INACTIVE 처리",
    )
    parser.add_argument("--list-sources", action="store_true", help="지원 소스 목록 출력 후 종료")
    parser.add_argument(
        "--safe",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="IP 차단 방지를 위한 안전 모드(요청 간격/저용량 기본 제한/배치 쿨다운 활성화)",
    )
    parser.add_argument(
        "--max-runtime-seconds",
        type=int,
        default=None,
        help="이 시간(초)을 넘기기 전에 checkpoint를 저장하고 종료",
    )
    parser.add_argument(
        "--exclude-source",
        action="append",
        default=[],
        help="all 수집 시 제외할 소스(반복 지정 가능)",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.list_sources:
        print("\n".join(["all"] + sorted(COLLECTORS.keys())))
        return

    if args.limit is not None and args.limit <= 0:
        raise SystemExit("--limit 은 1 이상의 정수여야 합니다.")
    if args.max_runtime_seconds is not None and args.max_runtime_seconds <= 0:
        raise SystemExit("--max-runtime-seconds 는 1 이상의 정수여야 합니다.")
    if args.reconcile_missing and not args.from_scratch:
        raise SystemExit("--reconcile-missing 는 --from-scratch 와 함께만 사용할 수 있습니다.")

    settings = Settings()
    settings.validate()

    excluded_sources = {source.strip() for source in args.exclude_source if source.strip()}
    unknown_exclusions = sorted(source for source in excluded_sources if source not in COLLECTORS)
    if unknown_exclusions:
        raise SystemExit(
            "지원하지 않는 exclude source 입니다: " + ", ".join(unknown_exclusions)
        )

    source_names: List[str]
    if args.source == "all":
        source_names = [name for name in COLLECTORS.keys() if name not in excluded_sources]
    else:
        if args.source not in COLLECTORS:
            raise SystemExit(f"지원하지 않는 source 입니다: {args.source}")
        if args.source in excluded_sources:
            raise SystemExit("--source 로 지정한 단일 소스는 --exclude-source 로 제외할 수 없습니다.")
        source_names = [args.source]

    summary: Dict[str, Any] = {}
    safe_mode = settings.safe_mode_default if args.safe is None else args.safe
    settings.runtime_safe_mode = safe_mode

    if not safe_mode:
        settings.min_request_interval_seconds = 0.0
        settings.request_interval_jitter_seconds = 0.0
        settings.batch_pause_every = 0
        settings.batch_pause_seconds = 0.0
        settings.per_source_cooldown_seconds = 0.0

    requested_limit = args.limit if args.limit is not None else settings.max_per_source
    effective_limit = requested_limit
    if safe_mode and not args.reconcile_missing:
        if args.max_runtime_seconds is not None:
            effective_limit = requested_limit
        elif effective_limit is None:
            effective_limit = settings.default_safe_limit
        elif effective_limit > settings.max_safe_limit:
            effective_limit = settings.max_safe_limit

    with Database(settings.database_url) as db:
        for idx, source_name in enumerate(source_names):
            collector_cls = COLLECTORS[source_name]
            collector = collector_cls(db=db, settings=settings)
            try:
                stats = collector.run(
                    resume=not args.from_scratch,
                    limit=effective_limit,
                    reconcile_missing=args.reconcile_missing,
                    max_runtime_seconds=args.max_runtime_seconds,
                )
                summary[source_name] = {
                    "status": "completed",
                    "collected_count": stats.collected_count,
                    "upserted_count": stats.upserted_count,
                    "deactivated_count": stats.deactivated_count,
                    "failed_count": stats.failed_count,
                    "last_saved_source_dataset_key": stats.last_saved_source_dataset_key,
                    "effective_limit": effective_limit,
                    "safe_mode": safe_mode,
                    "reconcile_missing": args.reconcile_missing,
                    "max_runtime_seconds": args.max_runtime_seconds,
                }
            except SourceRunAlreadyActiveError as exc:
                summary[source_name] = {
                    "status": "skipped",
                    "reason": "source_already_running",
                    "error": str(exc),
                    "effective_limit": effective_limit,
                    "safe_mode": safe_mode,
                    "reconcile_missing": args.reconcile_missing,
                    "max_runtime_seconds": args.max_runtime_seconds,
                }
            except Exception as exc:
                summary[source_name] = {
                    "status": "failed",
                    "error": str(exc),
                    "effective_limit": effective_limit,
                    "safe_mode": safe_mode,
                    "reconcile_missing": args.reconcile_missing,
                    "max_runtime_seconds": args.max_runtime_seconds,
                }
            if safe_mode and idx < len(source_names) - 1 and settings.per_source_cooldown_seconds > 0:
                cooldown_seconds = getattr(collector, "per_source_cooldown_seconds", settings.per_source_cooldown_seconds)
                if cooldown_seconds > 0:
                    time.sleep(cooldown_seconds)

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
