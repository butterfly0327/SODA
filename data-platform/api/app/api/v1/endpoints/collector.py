from celery.result import AsyncResult
from fastapi import APIRouter, Header, status
from fastapi.responses import JSONResponse

from ....tasks.platform_tasks import collect_dataset_metadata
from ....schemas.collector import (
    ErrorResponse,
    StartDatasetEmbeddingRunRequest,
    StartDatasetEmbeddingRunResponse,
    StartDatasetCollectionRunRequest,
    StartDatasetCollectionRunResponse,
)
from ....services.collector_service import (
    CollectorRunRequest,
    EmbeddingRunRequest,
    collector_service,
)


router = APIRouter()


def enqueue_dataset_collection(run_request: CollectorRunRequest) -> str:
    async_result: AsyncResult = collect_dataset_metadata.apply_async(
        kwargs={
            "source": run_request.dataset_source_id,
            "limit": run_request.limit,
            "max_runtime_seconds": run_request.max_runtime_seconds,
            "from_scratch": run_request.from_scratch,
            "safe": run_request.safe,
            "exclude_sources": run_request.exclude_source_ids,
            "reconcile_missing": run_request.reconcile_missing,
            "parser_version": run_request.parser_version,
        }
    )
    return async_result.id


@router.post(
    "/datasets/runs",
    response_model=StartDatasetCollectionRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        400: {"model": ErrorResponse, "description": "잘못된 요청"},
        500: {"model": ErrorResponse, "description": "수집 시작 실패"},
    },
)
def start_dataset_collection_run(
    payload: StartDatasetCollectionRunRequest,
    x_triggered_by: str | None = Header(default=None, alias="X-Triggered-By"),
) -> StartDatasetCollectionRunResponse | JSONResponse:
    dataset_source_id = (payload.datasetSourceId or "").strip()
    parser_version = (payload.parserVersion or "").strip()
    exclude_source_ids = [source.strip() for source in (payload.excludeSourceIds or []) if source and source.strip()]

    if not dataset_source_id or not parser_version:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"status": 400, "message": "datasetSourceId와 parserVersion은 필수입니다."},
        )

    if exclude_source_ids and dataset_source_id != "all":
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "status": 400,
                "message": "excludeSourceIds는 datasetSourceId가 all일 때만 사용할 수 있습니다.",
            },
        )

    run_request = CollectorRunRequest(
        dataset_source_id=dataset_source_id,
        parser_version=parser_version,
        limit=payload.limit,
        max_runtime_seconds=payload.maxRuntimeSeconds,
        from_scratch=payload.fromScratch,
        safe=payload.safe,
        exclude_source_ids=exclude_source_ids,
        reconcile_missing=payload.reconcileMissing,
        triggered_by=x_triggered_by.strip() if x_triggered_by else "unknown",
    )

    try:
        task_id = enqueue_dataset_collection(run_request)
    except Exception as exc:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": f"수집 시작 중 내부 오류가 발생했습니다: {exc}"},
        )

    return StartDatasetCollectionRunResponse(
        status=202,
        message="데이터셋 메타데이터 수집 작업을 큐에 등록했습니다.",
        taskId=task_id,
        datasetSourceId=dataset_source_id,
        parserVersion=parser_version,
    )


@router.post(
    "/datasets/embeddings/runs",
    response_model=StartDatasetEmbeddingRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        409: {"model": ErrorResponse, "description": "이미 작업 실행 중"},
        500: {"model": ErrorResponse, "description": "임베딩 시작 실패"},
    },
)
def start_dataset_embedding_run(
    payload: StartDatasetEmbeddingRunRequest,
    x_triggered_by: str | None = Header(default=None, alias="X-Triggered-By"),
) -> StartDatasetEmbeddingRunResponse | JSONResponse:
    run_request = EmbeddingRunRequest(
        dataset_id=payload.datasetId,
        limit=payload.limit,
        reembed=payload.reembed,
        triggered_by=x_triggered_by.strip() if x_triggered_by else "unknown",
    )

    try:
        state = collector_service.start_embedding_run(run_request)
    except RuntimeError as exc:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"status": 409, "message": str(exc)},
        )
    except Exception as exc:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": 500, "message": f"임베딩 시작 중 내부 오류가 발생했습니다: {exc}"},
        )

    return StartDatasetEmbeddingRunResponse(
        status=202,
        message=state.message,
        runId=state.run_id,
    )
