from pydantic import BaseModel, Field


class ConversationHistoryItem(BaseModel):
    role: str = Field(..., min_length=1, description="대화 역할(USER/ASSISTANT 등)")
    content: str = Field(..., min_length=1, description="대화 내용")


class RecommendDatasetsRequest(BaseModel):
    conversationId: int | None = Field(default=None, ge=1, description="대화 ID")
    userId: int | None = Field(default=None, ge=1, description="호출 사용자 ID")
    userTurnId: int | None = Field(
        default=None,
        ge=1,
        description="Spring Boot가 전달하는 사용자 턴 ID",
    )
    prompt: str | None = Field(
        default=None, min_length=1, description="사용자 데이터셋 추천 프롬프트"
    )
    message: str | None = Field(
        default=None, min_length=1, description="Spring Boot 메시지 본문"
    )
    history: list[ConversationHistoryItem] = Field(
        default_factory=list, description="동일 대화 히스토리"
    )
    datasetRecommendationId: int | None = Field(
        default=None,
        ge=1,
        description="기존 dataset_recommendation ID(백엔드 선생성 레코드 재사용)",
    )
    topN: int | None = Field(
        default=None,
        ge=1,
        le=20,
        description="최종 추천 개수(기본값 10, 최대 20)",
    )
    debugUserTurnId: int | None = Field(
        default=None,
        ge=1,
        description="Spring 미구현 환경 테스트용 userTurnId 대체값",
    )


class RecommendedDatasetItem(BaseModel):
    datasetId: int = Field(..., description="추천 데이터셋 ID")
    rank: int = Field(..., ge=1, description="추천 순위")
    suitabilityScore: float = Field(..., ge=0, le=1, description="적합도 점수")
    reason: str = Field(..., description="추천 사유(한국어)")


class RecommendDatasetsResponse(BaseModel):
    status: int = Field(..., description="상태 코드")
    message: str = Field(..., description="추가 설명(한글)")
    recommendationId: int = Field(..., description="dataset_recommendation ID")
    datasetRecommendationId: int = Field(..., description="dataset_recommendation ID")
    userTurnId: int = Field(..., description="사용자 턴 ID")
    prompt: str = Field(..., description="입력 프롬프트")
    summaryReason: str = Field(..., description="추천 결과 요약 사유")
    reasonText: str = Field(..., description="추천 결과 요약 사유")
    candidateCount: int = Field(..., description="LLM에 전달된 후보 개수")
    llmModel: str = Field(..., description="추천 생성에 사용한 LLM 모델")
    recommendedItems: list[RecommendedDatasetItem] = Field(
        ..., description="최종 추천 목록"
    )


class RecommendOpenApiRequest(BaseModel):
    conversationId: int | None = Field(default=None, ge=1, description="대화 ID")
    userId: int | None = Field(default=None, ge=1, description="호출 사용자 ID")
    userTurnId: int | None = Field(default=None, ge=1, description="사용자 턴 ID")
    debugUserTurnId: int | None = Field(
        default=None, ge=1, description="테스트용 사용자 턴 ID"
    )
    prompt: str | None = Field(
        default=None, min_length=1, description="사용자 Open API 추천 프롬프트"
    )
    message: str | None = Field(
        default=None, min_length=1, description="Spring Boot 메시지 본문"
    )
    history: list[ConversationHistoryItem] = Field(
        default_factory=list, description="동일 대화 히스토리"
    )
    openapiRecommendationId: int | None = Field(
        default=None,
        ge=1,
        description="기존 openapi_recommendation ID(백엔드 선생성 레코드 재사용)",
    )


class RecommendedOpenApiItem(BaseModel):
    openApiId: int = Field(..., description="추천 Open API ID")
    name: str = Field(..., description="API 이름")
    description: str | None = Field(None, description="API 설명")
    provider: str | None = Field(None, description="제공자")
    baseUrl: str = Field(..., description="Base URL")
    docsUrl: str | None = Field(None, description="문서 URL")
    authType: str = Field(..., description="인증 방식")
    category: str | None = Field(None, description="카테고리")
    tags: list[str] = Field(..., description="태그 목록")
    isFree: bool | None = Field(None, description="무료 여부")
    score: float = Field(..., description="유사도 점수")


class RecommendOpenApiResponse(BaseModel):
    status: int = Field(..., description="상태 코드")
    message: str = Field(..., description="추가 설명(한글)")
    recommendationId: int = Field(..., description="openapi_recommendation ID")
    openapiRecommendationId: int = Field(..., description="openapi_recommendation ID")
    userTurnId: int = Field(..., description="사용자 턴 ID")
    prompt: str = Field(..., description="입력 프롬프트")
    summaryReason: str = Field(..., description="추천 결과 요약")
    reasonText: str = Field(..., description="추천 결과 요약")
    candidateCount: int = Field(..., description="추천된 API 개수")
    llmModel: str = Field(..., description="추천 생성에 사용한 LLM 모델")
    recommendedItems: list[RecommendedOpenApiItem] = Field(
        ..., description="최종 추천 목록"
    )


class MergeRecommendationReasonRequest(BaseModel):
    conversationId: int | None = Field(default=None, ge=1, description="대화 ID")
    userId: int | None = Field(default=None, ge=1, description="호출 사용자 ID")
    userTurnId: int | None = Field(default=None, ge=1, description="사용자 턴 ID")
    debugUserTurnId: int | None = Field(
        default=None, ge=1, description="테스트용 사용자 턴 ID"
    )
    prompt: str | None = Field(
        default=None, min_length=1, description="사용자 원본 프롬프트"
    )
    message: str | None = Field(
        default=None, min_length=1, description="Spring Boot 메시지 본문"
    )
    history: list[ConversationHistoryItem] = Field(
        default_factory=list, description="동일 대화 히스토리"
    )
    recommendationId: int | None = Field(
        default=None, ge=1, description="recommendation ID"
    )
    datasetRecommendationId: int | None = Field(
        default=None, ge=1, description="dataset_recommendation ID"
    )
    openapiRecommendationId: int | None = Field(
        default=None, ge=1, description="openapi_recommendation ID"
    )
    datasetReason: str | None = Field(default=None, description="데이터셋 추천 사유")
    openapiReason: str | None = Field(default=None, description="Open API 추천 사유")


class MergeRecommendationReasonResponse(BaseModel):
    status: int = Field(..., description="상태 코드")
    message: str = Field(..., description="추가 설명(한글)")
    recommendationId: int = Field(..., description="recommendation ID")
    userTurnId: int = Field(..., description="사용자 턴 ID")
    datasetRecommendationId: int = Field(..., description="dataset_recommendation ID")
    openapiRecommendationId: int = Field(..., description="openapi_recommendation ID")
    prompt: str = Field(..., description="입력 프롬프트")
    mergedReasonText: str = Field(..., description="최종 통합 추천 사유")
    llmModel: str = Field(..., description="추천 이유 병합에 사용한 LLM 모델")


class ErrorResponse(BaseModel):
    status: int = Field(..., description="상태 코드")
    message: str = Field(..., description="추가 설명(한글)")


class InferRecommendationModeRequest(BaseModel):
    conversationId: int | None = Field(default=None, ge=1, description="대화 ID")
    userId: int | None = Field(default=None, ge=1, description="호출 사용자 ID")
    userTurnId: int | None = Field(default=None, ge=1, description="사용자 턴 ID")
    prompt: str | None = Field(
        default=None,
        min_length=1,
        description="의도 판별 대상 프롬프트",
    )
    message: str | None = Field(
        default=None,
        min_length=1,
        description="Spring Boot 메시지 본문",
    )
    history: list[ConversationHistoryItem] = Field(
        default_factory=list,
        description="동일 대화 히스토리",
    )


class InferRecommendationModeResponse(BaseModel):
    status: int = Field(..., description="상태 코드")
    message: str = Field(..., description="추가 설명(한글)")
    mode: str = Field(
        ..., description="판별 모드(CHAT_ONLY/DATASET_ONLY/OPENAPI_ONLY/BOTH)"
    )
    llmModel: str = Field(..., description="판별에 사용한 LLM 모델")


class ChatAnswerRequest(BaseModel):
    conversationId: int | None = Field(default=None, ge=1, description="대화 ID")
    userId: int | None = Field(default=None, ge=1, description="호출 사용자 ID")
    userTurnId: int | None = Field(default=None, ge=1, description="사용자 턴 ID")
    prompt: str | None = Field(
        default=None,
        min_length=1,
        description="채팅 응답 생성 대상 프롬프트",
    )
    message: str | None = Field(
        default=None,
        min_length=1,
        description="Spring Boot 메시지 본문",
    )
    history: list[ConversationHistoryItem] = Field(
        default_factory=list,
        description="동일 대화 히스토리",
    )


class ChatAnswerResponse(BaseModel):
    status: int = Field(..., description="상태 코드")
    message: str = Field(..., description="추가 설명(한글)")
    answer: str = Field(..., description="생성된 채팅 답변")
    llmModel: str = Field(..., description="답변 생성에 사용한 LLM 모델")
