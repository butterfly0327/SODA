from __future__ import annotations

import argparse
import asyncio
import json
import logging
from typing import Any, Dict, List

from .config import Settings
from .db import Database
from .sources import COLLECTORS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Open API 메타데이터 수집기")
    parser.add_argument(
        "--source",
        default="all",
        help="수집 소스. all 또는 " + ", ".join(sorted(COLLECTORS.keys())),
    )
    parser.add_argument("--list-sources", action="store_true", help="지원 소스 목록 출력 후 종료")
    # datagokr 전용 옵션
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="처리할 최대 건수 (datagokr 전용)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="체크포인트에서 이어서 실행 (datagokr 전용)",
    )
    return parser


async def _async_main(args: argparse.Namespace) -> None:
    if args.list_sources:
        print("\n".join(["all"] + sorted(COLLECTORS.keys())))
        return

    settings = Settings()
    settings.validate()

    source_names: List[str]
    if args.source == "all":
        source_names = list(COLLECTORS.keys())
    else:
        if args.source not in COLLECTORS:
            raise SystemExit(f"지원하지 않는 source 입니다: {args.source!r}")
        source_names = [args.source]

    summary: Dict[str, Any] = {}

    async with Database(settings.asyncpg_dsn) as db:
        for name in source_names:
            collector_cls = COLLECTORS[name]
            collector = collector_cls(db=db, settings=settings)

            run_kwargs: Dict[str, Any] = {}
            if name == "datagokr":
                if args.limit is not None:
                    run_kwargs["limit"] = args.limit
                run_kwargs["resume"] = args.resume

            logger.info(f"=== [{name}] 수집 시작 ===")
            try:
                stats = await collector.run(**run_kwargs)
                summary[name] = {
                    "status": "completed",
                    "collected_count": stats.collected_count,
                    "upserted_count": stats.upserted_count,
                    "failed_count": stats.failed_count,
                }
                if stats.errors:
                    summary[name]["errors"] = stats.errors[:5]
                logger.info(
                    f"=== [{name}] 완료: {stats.upserted_count}건 upsert "
                    f"(실패 {stats.failed_count}건) ==="
                )
            except Exception as exc:
                summary[name] = {"status": "failed", "error": str(exc)}
                logger.exception(f"[{name}] 수집 실패: {exc}")

    print(json.dumps(summary, ensure_ascii=False, indent=2))


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    asyncio.run(_async_main(args))


if __name__ == "__main__":
    main()
