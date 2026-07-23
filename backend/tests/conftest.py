"""Shared pytest fixtures — make the suite run fully offline.

Every external dependency (Gemini, Pinecone, Docker, the ledger) is mocked, and
the FastAPI lifespan's client construction is stubbed so ``TestClient`` can boot
without secrets or network access. Mocks are applied *where each name is imported*
(node/endpoint modules bind their imports at import time, so patching the source
module alone would not take effect).
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.documents import Document
from langchain_core.messages import AIMessage, AIMessageChunk

from app.graph.nodes.modification_node import PatchProposal
from app.graph.nodes.arbitration_node import SecurityDecision
from app.services.llm import NamedModel

# A benign, blocklist-clean patch the fake model "generates" for every run.
SAFE_PATCH = (
    "import math\n\n\n"
    "def main():\n"
    "    print(math.sqrt(16))\n\n\n"
    'if __name__ == "__main__":\n'
    "    main()\n"
)


class _StructuredRunner:
    """Mimics ``model.with_structured_output(Schema, include_raw=...)``.

    When ``include_raw=True`` (the new default for token-accounting), returns
    ``{"parsed": <schema>, "raw": <AIMessage>}`` — exactly what the nodes now
    unpack.  When ``include_raw=False`` (legacy / not set), returns the schema
    directly so any code path that bypasses ``include_raw`` still works.
    """

    def __init__(self, result, include_raw: bool = False):
        self._result = result
        self._include_raw = include_raw

    async def ainvoke(self, *_args, **_kwargs):
        if self._include_raw:
            # Build a fake AIMessage that looks like it carries usage_metadata.
            fake_raw = AIMessage(
                content="",
                usage_metadata={"input_tokens": 10, "output_tokens": 15, "total_tokens": 25},
            )
            return {"parsed": self._result, "raw": fake_raw, "parsing_error": None}
        return self._result


class FakeChatModel:
    """Stand-in for ``ChatGoogleGenerativeAI``.

    Supports the only two shapes the code uses: structured output (modification /
    arbitration nodes) and token streaming (the context endpoint).
    """

    def __init__(self, structured_result, stream_text: str = "mocked response text"):
        self._structured_result = structured_result
        self._stream_text = stream_text

    def with_structured_output(self, _schema, include_raw: bool = False, **_kwargs):
        return _StructuredRunner(self._structured_result, include_raw=include_raw)

    async def astream(self, *_args, **_kwargs):
        for token in self._stream_text.split():
            yield AIMessageChunk(content=token + " ")


@pytest.fixture
def mock_ledger():
    from app.core.schemas import OperationalLogEntry

    ledger = AsyncMock()
    ledger._pool = None
    ledger.ping = AsyncMock(return_value=True)
    ledger.fetch_recent = AsyncMock(
        return_value=[
            OperationalLogEntry(
                id="00000000-0000-0000-0000-000000000001",
                timestamp="2026-01-01T00:00:00+00:00",
                event_source="api/v1/graph/run/stream",
                agent_action="autonomous_repair",
                execution_payload="Target: demo/buggy_server.py | Retries: 1",
                execution_status="success",
                token_consumption=42,
                compute_latency_ms=2400,
            )
        ]
    )
    return ledger


@pytest.fixture
def fake_vectorstore():
    vectorstore = AsyncMock()
    vectorstore.asearch = AsyncMock(
        return_value=[
            Document(
                page_content="def process_metrics():\n    return 1",
                metadata={"path": "demo/buggy_server.py", "language": "python"},
            )
        ]
    )
    vectorstore.aupsert_documents = AsyncMock()
    vectorstore.aget_unique_files = AsyncMock(return_value=[])
    return vectorstore


@pytest.fixture(autouse=True)
def patch_services(monkeypatch, mock_ledger, fake_vectorstore):
    """Patch every external dependency so nodes, endpoints, and the lifespan run
    deterministically offline. Autouse so even pure-logic tests stay isolated."""

    chat_model = FakeChatModel(
        PatchProposal(
            reasoning="Add the missing import.",
            target_file="demo/buggy_server.py",
            code=SAFE_PATCH,
        )
    )
    security_model = FakeChatModel(
        SecurityDecision(is_safe=True, reason="Standard application logic fix.")
    )

    # ── LLM bindings (patched where imported) ──────────────────────────────
    monkeypatch.setattr(
        "app.graph.nodes.modification_node.get_chat_model", lambda: chat_model
    )
    monkeypatch.setattr(
        "app.graph.nodes.arbitration_node.get_security_models",
        lambda: [
            NamedModel("mock:security-a", security_model),
            NamedModel("mock:security-b", security_model),
        ],
    )
    monkeypatch.setattr("app.api.v1.context.get_chat_model", lambda: chat_model)

    # ── Vectorstore bindings ───────────────────────────────────────────────
    vs_factory = lambda *args, **kwargs: fake_vectorstore  # noqa: E731
    monkeypatch.setattr("app.graph.nodes.context_node.get_vectorstore_service", vs_factory)
    monkeypatch.setattr("app.api.v1.ingest.get_vectorstore_service", vs_factory)
    monkeypatch.setattr("app.api.v1.context.get_vectorstore_service", vs_factory)

    # ── Sandbox: simulate a clean run ──────────────────────────────────────
    monkeypatch.setattr(
        "app.graph.nodes.sandbox_node.execute_in_sandbox",
        AsyncMock(return_value=(0, "Success\n", "")),
    )

    # ── Lifespan externals → boot with no network / IO ─────────────────────
    monkeypatch.setattr("app.core.lifespan.Pinecone", lambda **kwargs: MagicMock())
    monkeypatch.setattr(
        "app.core.lifespan.create_ledger", AsyncMock(return_value=mock_ledger)
    )

    async def _noop_telemetry_loop(_app):
        return

    monkeypatch.setattr("app.core.lifespan.telemetry_loop", _noop_telemetry_loop)
    monkeypatch.setattr("docker.from_env", lambda **_kwargs: MagicMock())
    # LogErrorCounter.install is a no-op in tests — the singleton stays clean.
    monkeypatch.setattr("app.core.lifespan.LogErrorCounter", MagicMock())


@pytest.fixture
def client(patch_services):
    """Context-managed TestClient so the (mocked) lifespan runs and populates
    ``app.state`` before requests are served."""
    from fastapi.testclient import TestClient
    from sse_starlette.sse import AppStatus

    from app.main import app

    AppStatus.should_exit_event = None
    with TestClient(app) as test_client:
        yield test_client
    AppStatus.should_exit_event = None
