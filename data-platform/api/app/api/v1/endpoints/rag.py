from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from ....schemas.rag import RagQueryRequest, RagQueryResponse
from ....schemas.recommendation import (
    ChatAnswerRequest,
    ChatAnswerResponse,
    ConversationHistoryItem,
    ErrorResponse,
    InferRecommendationModeRequest,
    InferRecommendationModeResponse,
    MergeRecommendationReasonRequest,
    MergeRecommendationReasonResponse,
    RecommendDatasetsRequest,
    RecommendDatasetsResponse,
    RecommendOpenApiRequest,
    RecommendOpenApiResponse,
    RecommendedDatasetItem,
    RecommendedOpenApiItem,
)
from ....services.chat_intent_service import (
    ChatIntentInputError,
    ChatIntentUpstreamError,
    chat_intent_service,
)
from ....services.dataset_recommendation_service import (
    RecommendationInputError,
    RecommendationNoCandidateError,
    RecommendationUpstreamError,
    dataset_recommendation_service,
)
from ....services.merge_recommendation_service import (
    MergeRecommendationInputError,
    MergeRecommendationUpstreamError,
    merge_recommendation_service,
)
from ....services.llm_router import llm_router
from ....services.openapi_recommendation_service import (
    OpenApiRecommendationInputError,
    OpenApiRecommendationUpstreamError,
    openapi_recommendation_service,
)
from ....services.rag_service import rag_service


router = APIRouter()
internal_router = APIRouter()


def _resolve_prompt(prompt: str | None, message: str | None) -> str:
    value = (prompt or message or "").strip()
    if not value:
        raise ValueError("prompt 또는 message 중 하나는 반드시 필요합니다.")
    return value


def _convert_history_items(
    history: list[ConversationHistoryItem],
) -> list[dict[str, str]]:
    converted: list[dict[str, str]] = []
    for item in history:
        role = item.role.strip()
        content = item.content.strip()
        if not role or not content:
            continue
        converted.append({"role": role, "content": content})
    return converted


@internal_router.get("/status")
async def llm_status() -> dict[str, object]:
    return await llm_router.get_status_snapshot()


@router.post("/query", response_model=RagQueryResponse)
async def rag_query(payload: RagQueryRequest) -> RagQueryResponse:
    answer, retrieved, _llm_model = await rag_service.query(
        query_text=payload.query, top_k=payload.top_k
    )
    return RagQueryResponse(query=payload.query, answer=answer, retrieved=retrieved)


@router.post(
    "/infer-recommendation-mode",
    response_model=InferRecommendationModeResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "잘못된 요청"},
        500: {"model": ErrorResponse, "description": "내부 처리 오류"},
        502: {"model": ErrorResponse, "description": "외부 LLM 호출 오류"},
    },
)
async def infer_recommendation_mode(
    payload: InferRecommendationModeRequest,
) -> InferRecommendationModeResponse | JSONResponse:
    try:
        prompt = _resolve_prompt(payload.prompt, payload.message)
    except ValueError as exc:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"status": 400, "message": str(exc)},
        )

    try:
        result = await chat_intent_service.infer_recommendation_mode(
            prompt=prompt,
            history=_convert_history_items(payload.history),
        )
    except ChatIntentInputError as exc:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"status": 400, "message": str(exc)},
        )
    except ChatIntentUpstreamError as exc:
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={"status": 502, "message": str(exc)},
        )
    except Exception as exc:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": f"추천 모드 판별 중 내부 오류가 발생했습니다: {exc}",
            },
        )

    return InferRecommendationModeResponse(
        status=200,
        message="추천 모드 판별을 완료했습니다.",
        mode=result.mode,
        llmModel=result.llm_model,
    )


@router.post(
    "/chat-answer",
    response_model=ChatAnswerResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "잘못된 요청"},
        500: {"model": ErrorResponse, "description": "내부 처리 오류"},
        502: {"model": ErrorResponse, "description": "외부 LLM 호출 오류"},
    },
)
async def generate_chat_answer(
    payload: ChatAnswerRequest,
) -> ChatAnswerResponse | JSONResponse:
    try:
        prompt = _resolve_prompt(payload.prompt, payload.message)
    except ValueError as exc:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"status": 400, "message": str(exc)},
        )

    try:
        result = await chat_intent_service.generate_chat_answer(
            prompt=prompt,
            history=_convert_history_items(payload.history),
        )
    except ChatIntentInputError as exc:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"status": 400, "message": str(exc)},
        )
    except ChatIntentUpstreamError as exc:
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={"status": 502, "message": str(exc)},
        )
    except Exception as exc:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": f"채팅 응답 생성 중 내부 오류가 발생했습니다: {exc}",
            },
        )

    return ChatAnswerResponse(
        status=200,
        message="채팅 응답 생성을 완료했습니다.",
        answer=result.answer,
        llmModel=result.llm_model,
    )


@router.post(
    "/recommend-openapi",
    response_model=RecommendOpenApiResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "잘못된 요청"},
        500: {"model": ErrorResponse, "description": "내부 처리 오류"},
        502: {"model": ErrorResponse, "description": "외부 LLM/Embedding 호출 오류"},
    },
)
@router.post(
    "/recommend-open-apis",
    response_model=RecommendOpenApiResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "잘못된 요청"},
        500: {"model": ErrorResponse, "description": "내부 처리 오류"},
        502: {"model": ErrorResponse, "description": "외부 LLM/Embedding 호출 오류"},
    },
)
async def recommend_openapi(
    payload: RecommendOpenApiRequest,
) -> RecommendOpenApiResponse | JSONResponse:
    try:
        prompt = _resolve_prompt(payload.prompt, payload.message)
    except ValueError as exc:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"status": 400, "message": str(exc)},
        )

    try:
        result = await openapi_recommendation_service.generate_recommendation(
            user_turn_id=payload.userTurnId,
            debug_user_turn_id=payload.debugUserTurnId,
            openapi_recommendation_id=payload.openapiRecommendationId,
            prompt=prompt,
            history=_convert_history_items(payload.history),
        )
    except OpenApiRecommendationInputError as exc:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"status": 400, "message": str(exc)},
        )
    except OpenApiRecommendationUpstreamError as exc:
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={"status": 502, "message": str(exc)},
        )
    except Exception as exc:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": f"추천 생성 중 오류가 발생했습니다: {exc}",
            },
        )

    return RecommendOpenApiResponse(
        status=200,
        message="Open API 추천을 생성했습니다.",
        recommendationId=result.recommendation_id,
        openapiRecommendationId=result.recommendation_id,
        userTurnId=result.user_turn_id,
        prompt=result.prompt,
        summaryReason=result.summary_reason,
        reasonText=result.summary_reason,
        candidateCount=len(result.recommended_items),
        llmModel=result.llm_model,
        recommendedItems=[
            RecommendedOpenApiItem(
                openApiId=item.id,
                name=item.name,
                description=item.description,
                provider=item.provider,
                baseUrl=item.base_url,
                docsUrl=item.docs_url,
                authType=item.auth_type,
                category=item.category,
                tags=item.tags,
                isFree=item.is_free,
                score=item.score,
            )
            for item in result.recommended_items
        ],
    )


@router.post(
    "/recommend-datasets",
    response_model=RecommendDatasetsResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "잘못된 요청"},
        404: {"model": ErrorResponse, "description": "후보 데이터 없음"},
        422: {"model": ErrorResponse, "description": "요청 검증 실패"},
        500: {"model": ErrorResponse, "description": "내부 처리 오류"},
        502: {"model": ErrorResponse, "description": "외부 LLM/Embedding 호출 오류"},
    },
)
def generate_dataset_recommendation(
    payload: RecommendDatasetsRequest,
) -> RecommendDatasetsResponse | JSONResponse:
    try:
        prompt = _resolve_prompt(payload.prompt, payload.message)
    except ValueError as exc:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"status": 400, "message": str(exc)},
        )

    try:
        result = dataset_recommendation_service.generate_recommendation(
            user_turn_id=payload.userTurnId,
            debug_user_turn_id=payload.debugUserTurnId,
            dataset_recommendation_id=payload.datasetRecommendationId,
            prompt=prompt,
            top_n=payload.topN,
            history=_convert_history_items(payload.history),
        )
    except RecommendationInputError as exc:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"status": 400, "message": str(exc)},
        )
    except RecommendationNoCandidateError as exc:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"status": 404, "message": str(exc)},
        )
    except RecommendationUpstreamError as exc:
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={"status": 502, "message": str(exc)},
        )
    except Exception as exc:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": f"추천 생성 중 내부 오류가 발생했습니다: {exc}",
            },
        )

    return RecommendDatasetsResponse(
        status=200,
        message="내부 데이터셋 추천을 생성했습니다.",
        recommendationId=result.recommendation_id,
        datasetRecommendationId=result.recommendation_id,
        userTurnId=result.user_turn_id,
        prompt=result.prompt,
        summaryReason=result.summary_reason,
        reasonText=result.summary_reason,
        candidateCount=result.candidate_count,
        llmModel=result.llm_model,
        recommendedItems=[
            RecommendedDatasetItem(
                datasetId=item.dataset_id,
                rank=item.rank,
                suitabilityScore=item.suitability_score,
                reason=item.reason,
            )
            for item in result.recommended_items
        ],
    )


@router.post(
    "/merge-recommendation-reason",
    response_model=MergeRecommendationReasonResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "잘못된 요청"},
        500: {"model": ErrorResponse, "description": "내부 처리 오류"},
        502: {"model": ErrorResponse, "description": "외부 LLM 호출 오류"},
    },
)
def merge_recommendation_reasons(
    payload: MergeRecommendationReasonRequest,
) -> MergeRecommendationReasonResponse | JSONResponse:
    try:
        prompt = _resolve_prompt(payload.prompt, payload.message)
    except ValueError as exc:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"status": 400, "message": str(exc)},
        )

    try:
        result = merge_recommendation_service.merge_recommendation_reasons(
            user_turn_id=payload.userTurnId,
            debug_user_turn_id=payload.debugUserTurnId,
            prompt=prompt,
            history=payload.history,
            recommendation_id=payload.recommendationId,
            dataset_recommendation_id=payload.datasetRecommendationId,
            openapi_recommendation_id=payload.openapiRecommendationId,
            dataset_reason=payload.datasetReason,
            openapi_reason=payload.openapiReason,
        )
    except MergeRecommendationInputError as exc:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"status": 400, "message": str(exc)},
        )
    except MergeRecommendationUpstreamError as exc:
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={"status": 502, "message": str(exc)},
        )
    except Exception as exc:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": f"추천 이유 병합 중 내부 오류가 발생했습니다: {exc}",
            },
        )

    return MergeRecommendationReasonResponse(
        status=200,
        message="추천 이유 병합을 완료했습니다.",
        recommendationId=result.recommendation_id,
        userTurnId=result.user_turn_id,
        datasetRecommendationId=result.dataset_recommendation_id,
        openapiRecommendationId=result.openapi_recommendation_id,
        prompt=result.prompt,
        mergedReasonText=result.merged_reason_text,
        llmModel=result.llm_model,
    )
