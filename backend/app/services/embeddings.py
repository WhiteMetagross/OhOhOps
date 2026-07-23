"""Provider independent embedding contract."""

from __future__ import annotations

import hashlib
import logging
import math
from typing import Any

from langchain_core.embeddings import Embeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_openai import OpenAIEmbeddings

from app.core.config import get_settings

logger = logging.getLogger("ohohops.embeddings")


def normalize_dimension(vector: list[float], target_dimension: int) -> list[float]:
    """Return a deterministic vector with exactly ``target_dimension`` values."""
    if target_dimension <= 0:
        raise ValueError("target_dimension must be positive")
    if len(vector) == target_dimension:
        return vector
    if len(vector) < target_dimension:
        return [*vector, *([0.0] * (target_dimension - len(vector)))]

    folded = [0.0] * target_dimension
    for index, value in enumerate(vector):
        bucket = index % target_dimension
        sign = 1.0 if (index // target_dimension) % 2 == 0 else -1.0
        folded[bucket] += value * sign
    norm = math.sqrt(sum(value * value for value in folded))
    return [value / norm for value in folded] if norm else folded


class FixedDimensionEmbeddings(Embeddings):
    """Adapter enforcing one vector width across all configured providers."""

    def __init__(self, inner: Embeddings, target_dimension: int):
        self.inner = inner
        self.target_dimension = target_dimension

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [
            normalize_dimension(vector, self.target_dimension)
            for vector in self.inner.embed_documents(texts)
        ]

    def embed_query(self, text: str) -> list[float]:
        return normalize_dimension(
            self.inner.embed_query(text),
            self.target_dimension,
        )

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors = await self.inner.aembed_documents(texts)
        return [
            normalize_dimension(vector, self.target_dimension)
            for vector in vectors
        ]

    async def aembed_query(self, text: str) -> list[float]:
        vector = await self.inner.aembed_query(text)
        return normalize_dimension(vector, self.target_dimension)


class DeterministicEmbeddings(Embeddings):
    """Offline embeddings for tests and mock demonstrations."""

    def __init__(self, dimension: int):
        self.dimension = dimension

    def _embed(self, text: str) -> list[float]:
        seed = hashlib.sha256(text.encode("utf-8")).digest()
        vector = [
            (seed[index % len(seed)] / 127.5) - 1.0
            for index in range(self.dimension)
        ]
        norm = math.sqrt(sum(value * value for value in vector))
        return [value / norm for value in vector] if norm else vector

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.embed_documents(texts)

    async def aembed_query(self, text: str) -> list[float]:
        return self.embed_query(text)


def get_embeddings() -> Any:
    """Build configured provider and enforce a 3072 value vector contract."""
    settings = get_settings()

    if settings.use_mock_llm:
        logger.info("Using deterministic offline embeddings")
        provider: Embeddings = DeterministicEmbeddings(
            settings.embedding_dimension
        )
    elif settings.use_local_embeddings:
        from langchain_community.embeddings.fastembed import FastEmbedEmbeddings

        logger.info("Using local FastEmbed embeddings with 3072 dimension adapter")
        provider = FastEmbedEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
    elif settings.openai_api_key:
        provider = OpenAIEmbeddings(
            model=settings.openai_embedding_model,
            dimensions=settings.embedding_dimension,
            openai_api_key=settings.openai_api_key,
            max_retries=settings.max_retries,
            timeout=60.0,
        )
    else:
        if not settings.gemini_api_key:
            raise ValueError(
                "Either USE_LOCAL_EMBEDDINGS, OPENAI_API_KEY or GEMINI_API_KEY "
                "must be configured for embeddings"
            )
        provider = GoogleGenerativeAIEmbeddings(
            model=settings.gemini_embedding_model,
            google_api_key=settings.gemini_api_key,
            max_retries=5,
        )

    return FixedDimensionEmbeddings(provider, settings.embedding_dimension)
