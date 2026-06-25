from fastapi import APIRouter

from .endpoints.collector import router as collector_router
from .endpoints.health import router as health_router
from .endpoints.rag import internal_router as llm_internal_router
from .endpoints.rag import router as rag_router


api_v1_router = APIRouter()
api_v1_router.include_router(health_router, tags=["health"])
api_v1_router.include_router(rag_router, prefix="/rag", tags=["rag"])
api_v1_router.include_router(llm_internal_router, prefix="/internal/llm", tags=["llm"])
api_v1_router.include_router(collector_router, prefix="/collector", tags=["collector"])
