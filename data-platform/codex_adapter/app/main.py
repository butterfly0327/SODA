from fastapi import FastAPI, HTTPException

from .config import settings
from .runner import CodexRunner, CodexRunnerError
from .schemas import (
    AdapterChatCompletionRequest,
    AdapterChatCompletionResponse,
    AdapterStatusResponse,
)


app = FastAPI(title="Codex Adapter", debug=False)
runner = CodexRunner(settings)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/status", response_model=AdapterStatusResponse)
def status() -> AdapterStatusResponse:
    return AdapterStatusResponse(
        primaryProvider="codex",
        codex=runner.get_status_snapshot(),
    )


@app.post("/v1/chat/completions", response_model=AdapterChatCompletionResponse)
async def create_chat_completion(
    payload: AdapterChatCompletionRequest,
) -> AdapterChatCompletionResponse:
    try:
        result = await runner.run_chat_completion(payload.model_dump())
    except CodexRunnerError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return AdapterChatCompletionResponse(**result)
