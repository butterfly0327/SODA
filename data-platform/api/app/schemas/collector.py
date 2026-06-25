from pydantic import BaseModel, Field


class StartDatasetCollectionRunRequest(BaseModel):
    datasetSourceId: str | None = Field(default=None, description="수집 대상 소스 키(all 또는 개별 소스)")
    parserVersion: str | None = Field(default=None, description="이번 수집 실행에 사용할 파서 버전")
    limit: int | None = Field(None, ge=1, description="소스별 최대 upsert 건수")
    maxRuntimeSeconds: int | None = Field(None, ge=1, description="이 시간(초) 안에서 최대한 수집하고 종료")
    fromScratch: bool = Field(False, description="체크포인트 무시 여부")
    safe: bool | None = Field(None, description="안전 모드 강제 지정(true/false)")
    excludeSourceIds: list[str] | None = Field(
        default=None,
        description="all 수집 시 제외할 소스 키 목록",
    )
    reconcileMissing: bool = Field(False, description="이번 full from-scratch run에서 missing row를 INACTIVE 처리")


class StartDatasetCollectionRunResponse(BaseModel):
    status: int = Field(..., description="상태 코드")
    message: str = Field(..., description="추가 설명")
    taskId: str = Field(..., description="Celery 비동기 작업 식별자")
    datasetSourceId: str = Field(..., description="수집 소스")
    parserVersion: str = Field(..., description="파서 버전")


class ErrorResponse(BaseModel):
    status: int = Field(..., description="상태 코드")
    message: str = Field(..., description="추가 설명")


class StartDatasetEmbeddingRunRequest(BaseModel):
    datasetId: int | None = Field(default=None, ge=1, description="특정 dataset.id만 임베딩할 때 사용")
    limit: int = Field(default=100, ge=1, description="최대 처리 dataset 개수")
    reembed: bool = Field(False, description="기존 chunk가 있어도 다시 임베딩할지 여부")


class StartDatasetEmbeddingRunResponse(BaseModel):
    status: int = Field(..., description="상태 코드")
    message: str = Field(..., description="추가 설명")
    runId: str = Field(..., description="비동기 임베딩 실행 식별자")
