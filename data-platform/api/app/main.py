from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator

from .api.v1.router import api_v1_router
from .core.config import settings
from .observability.dataset_collection_metrics import (
    register_dataset_collection_metrics,
)
from .services.dataset_recommendation_service import dataset_recommendation_service
from .services.llm_router import llm_router
from .services.psycopg_connection_pool import close_recommendation_connection_pool
from .services.rag_service import rag_service


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        yield
    finally:
        dataset_recommendation_service.close()
        close_recommendation_connection_pool()
        await rag_service.close()
        await llm_router.close()


app = FastAPI(
    title=settings.app_name,
    debug=settings.app_debug,
    lifespan=lifespan,
)

register_dataset_collection_metrics(settings.database_url, settings.app_env)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_v1_router, prefix="/v1")

Instrumentator().instrument(app).expose(app, include_in_schema=False)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    _request: Request,
    _exc: RequestValidationError,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "status": 422,
            "message": "요청 본문 검증에 실패했습니다.",
        },
    )


@app.get("/")
def root() -> dict[str, str]:
    return {
        "name": settings.app_name,
        "environment": settings.app_env,
        "status": "ok",
    }
