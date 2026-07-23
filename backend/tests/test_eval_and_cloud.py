"""Offline contract tests for optional cloud and evaluation integrations."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pandas as pd
import pytest


@pytest.mark.asyncio
async def test_ragas_scores_are_computed_and_persisted(monkeypatch):
    from app.eval import ragas_suite

    dataset = object()
    result = SimpleNamespace(
        to_pandas=lambda: pd.DataFrame(
            {
                "faithfulness": [0.8, 1.0],
                "context_recall": [0.6, 1.0],
            }
        )
    )
    ledger = AsyncMock()

    monkeypatch.setattr(ragas_suite, "ChatGoogleGenerativeAI", MagicMock())
    monkeypatch.setattr(ragas_suite, "GoogleGenerativeAIEmbeddings", MagicMock())
    monkeypatch.setattr(
        ragas_suite,
        "build_ragas_dataset",
        AsyncMock(return_value=dataset),
    )
    evaluate = MagicMock(return_value=result)
    monkeypatch.setattr(ragas_suite, "evaluate", evaluate)
    monkeypatch.setattr(
        ragas_suite,
        "create_ledger",
        AsyncMock(return_value=ledger),
    )

    await ragas_suite.run_evaluation(namespace="production", samples=2)

    assert evaluate.call_args.args[0] is dataset
    entry = ledger.log_event.await_args.args[0]
    assert entry.ragas_fidelity_score == pytest.approx(0.9)
    assert "Context Recall: 0.8" in entry.execution_payload
    ledger.close.assert_awaited_once()


def test_pinecone_index_uses_configured_embedding_dimension(monkeypatch):
    from app.services import vectorstore

    pinecone = MagicMock()
    pinecone.list_indexes.return_value = []
    monkeypatch.setattr(vectorstore, "PineconeVectorStore", MagicMock())
    monkeypatch.setattr(vectorstore, "get_embeddings", MagicMock())

    service = vectorstore.PineconeVectorStoreService(pinecone)

    assert service.index_name == "ohohops-3072"
    assert pinecone.create_index.call_args.kwargs["dimension"] == 3072
    assert pinecone.create_index.call_args.kwargs["metric"] == "cosine"
