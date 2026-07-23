"""Health endpoint — reports per-dependency readiness.

Checks are intentionally cheap so the dashboard can poll this frequently.
Only the vector provider selected by the deployment mode is required.
"""

import httpx
from fastapi import APIRouter, Request

from app.core.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    state = request.app.state
    settings = state.settings
    deps: dict[str, str] = {}

    has_model = bool(
        settings.use_mock_llm
        or settings.anthropic_api_key
        or settings.gemini_api_key_chat
        or settings.gemini_api_key
        or settings.openrouter_api_key
    )
    deps["model"] = "ok" if has_model else "not_configured"
    security_models: set[str] = set()
    if settings.use_mock_llm:
        security_models.update(("mock:static-reviewer", "mock:runtime-reviewer"))
    if settings.anthropic_api_key:
        security_models.add(f"anthropic:{settings.anthropic_chat_model}")
    if settings.gemini_api_key_security or settings.gemini_api_key:
        security_models.add(f"gemini:{settings.gemini_security_model}")
        security_models.add(f"gemini:{settings.gemini_chat_model}")
    if settings.openrouter_api_key:
        security_models.add(f"openrouter:{settings.openrouter_security_model}")
        security_models.add(f"openrouter:{settings.openrouter_chat_model}")
    deps["security_arbiters"] = (
        "ok" if len(security_models) >= 2 else "not_configured"
    )
    has_embeddings = bool(
        settings.use_mock_llm
        or settings.use_local_embeddings
        or settings.openai_api_key
        or settings.gemini_api_key
    )
    deps["embeddings"] = "ok" if has_embeddings else "not_configured"
    deps["embedding_dimension"] = str(settings.embedding_dimension)

    vector_status = "error"
    if settings.is_local:
        deps["pinecone"] = "not_configured"
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(
                    f"http://{settings.chroma_host}:{settings.chroma_port}/api/v2/heartbeat"
                )
                response.raise_for_status()
            vector_status = "ok"
        except Exception:
            vector_status = "error"
        deps["chroma"] = vector_status
    else:
        deps["chroma"] = "not_configured"
        pinecone_client = getattr(state, "pinecone", None)
        if pinecone_client is None:
            deps["pinecone"] = "error"
        else:
            try:
                pinecone_client.list_indexes()
                deps["pinecone"] = "ok"
            except Exception:
                deps["pinecone"] = "error"
        vector_status = deps["pinecone"]

    docker_client = getattr(state, "docker_client", None)
    if docker_client is None:
        deps["docker"] = "not_configured"
    else:
        try:
            docker_client.ping()
            deps["docker"] = "ok"
        except Exception:
            deps["docker"] = "error"

    ledger = getattr(state, "ledger", None)
    if ledger is None:
        deps["ledger"] = "not_configured"
    else:
        deps["ledger"] = "ok" if await ledger.ping() else "error"

    required = [
        deps["model"],
        deps["security_arbiters"],
        deps["embeddings"],
        vector_status,
    ]
    if settings.is_local:
        required.append(deps["docker"])
    overall = "ok" if all(value == "ok" for value in required) else "degraded"
    return HealthResponse(status=overall, dependencies=deps)
