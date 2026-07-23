import logging
from dataclasses import dataclass
from typing import Any

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessageChunk
from langchain_openai import ChatOpenAI

from app.core.config import get_settings

logger = logging.getLogger("ohohops.llm")


@dataclass(frozen=True)
class NamedModel:
    name: str
    model: Any


class DeterministicChatModel:
    """Minimal streaming model used by self contained mock mode."""

    async def astream(self, _messages):
        text = (
            "Mock mode is active. Retrieved context is available and no "
            "external model request was made."
        )
        for token in text.split():
            yield AIMessageChunk(content=f"{token} ")


def _create_gemini_model(
    api_key_override: str | None = None,
    model_override: str | None = None,
) -> ChatGoogleGenerativeAI:
    settings = get_settings()
    key_to_use = api_key_override or settings.gemini_api_key
    
    if not key_to_use:
        raise ValueError("GEMINI_API_KEY is not configured")

    return ChatGoogleGenerativeAI(
        model=model_override or settings.gemini_chat_model,
        google_api_key=key_to_use,
        temperature=0.0,
        max_retries=settings.max_retries,
    )


def _create_anthropic_model() -> ChatAnthropic:
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise ValueError("ANTHROPIC_API_KEY is not configured")
        
    return ChatAnthropic(
        model_name=settings.anthropic_chat_model,
        anthropic_api_key=settings.anthropic_api_key,
        temperature=0.0,
        max_tokens=8192,
        max_retries=settings.max_retries,
    )


def _create_openrouter_model(model_override: str | None = None) -> ChatOpenAI:
    settings = get_settings()
    if not settings.openrouter_api_key:
        raise ValueError("OPENROUTER_API_KEY is not configured")

    headers = {"X-Title": settings.openrouter_title}
    if settings.openrouter_referer:
        headers["HTTP-Referer"] = settings.openrouter_referer
    return ChatOpenAI(
        model=model_override or settings.openrouter_chat_model,
        api_key=settings.openrouter_api_key,
        base_url="https://openrouter.ai/api/v1",
        default_headers=headers,
        temperature=0.0,
        max_retries=settings.max_retries,
    )


def get_chat_model() -> Any:
    """
    Returns a configured chat model for inference.
    Prefers Anthropic if configured, falls back to Gemini.
    We use temperature=0 for deterministic SRE reasoning.
    """
    settings = get_settings()
    if settings.use_mock_llm:
        logger.info("Using deterministic mock chat model")
        return DeterministicChatModel()
    if settings.anthropic_api_key:
        logger.info("Using Anthropic for chat inference")
        return _create_anthropic_model()
    
    if settings.gemini_api_key_chat or settings.gemini_api_key:
        logger.info("Using Gemini for chat inference")
        return _create_gemini_model(api_key_override=settings.gemini_api_key_chat)

    logger.info("Using OpenRouter for chat inference")
    return _create_openrouter_model()


def get_security_models() -> list[NamedModel]:
    """Return two distinct model configurations for unanimous arbitration."""
    settings = get_settings()
    candidates: list[NamedModel] = []

    if settings.anthropic_api_key:
        candidates.append(
            NamedModel(
                f"anthropic:{settings.anthropic_chat_model}",
                _create_anthropic_model(),
            )
        )

    gemini_key = settings.gemini_api_key_security or settings.gemini_api_key
    if gemini_key:
        candidates.append(
            NamedModel(
                f"gemini:{settings.gemini_security_model}",
                _create_gemini_model(gemini_key, settings.gemini_security_model),
            )
        )

    if settings.openrouter_api_key:
        candidates.append(
            NamedModel(
                f"openrouter:{settings.openrouter_security_model}",
                _create_openrouter_model(settings.openrouter_security_model),
            )
        )

    if len(candidates) < 2 and gemini_key:
        chat_name = f"gemini:{settings.gemini_chat_model}"
        if all(candidate.name != chat_name for candidate in candidates):
            candidates.append(
                NamedModel(
                    chat_name,
                    _create_gemini_model(gemini_key, settings.gemini_chat_model),
                )
            )

    if len(candidates) < 2 and settings.openrouter_api_key:
        chat_name = f"openrouter:{settings.openrouter_chat_model}"
        if all(candidate.name != chat_name for candidate in candidates):
            candidates.append(
                NamedModel(
                    chat_name,
                    _create_openrouter_model(settings.openrouter_chat_model),
                )
            )

    if len(candidates) < 2:
        raise ValueError(
            "Dual model arbitration requires two distinct configured model IDs"
        )

    selected = candidates[:2]
    logger.info(
        "Using dual security arbitration: %s",
        ", ".join(candidate.name for candidate in selected),
    )
    return selected


def get_security_model() -> Any:
    """Compatibility accessor for integrations expecting one model."""
    return get_security_models()[0].model
