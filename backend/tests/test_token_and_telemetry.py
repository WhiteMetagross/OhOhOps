"""Unit tests for P1 (token accounting) and P2 (real telemetry signal).

These tests run fully offline — no LLM, no Docker, no Pinecone.
They verify the specific behaviour added in each feature.
"""

import logging
import time
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage

from app.graph.nodes.modification_node import PatchProposal, modification_node
from app.graph.nodes.arbitration_node import SecurityDecision, arbitration_node
from app.core.schemas import new_agent_state
from app.anomaly.log_counter import LogErrorCounter
from app.services.llm import NamedModel


# ── Helper: build a fake AIMessage with realistic usage_metadata ────────────
def _fake_raw(total_tokens: int = 42) -> AIMessage:
    return AIMessage(
        content="",
        usage_metadata={"input_tokens": 10, "output_tokens": total_tokens - 10, "total_tokens": total_tokens},
    )


# ═══════════════════════════════════════════════════════════════════════════
# P1 — Token Accounting
# ═══════════════════════════════════════════════════════════════════════════


class TestModificationNodeTokens:
    """modification_node must propagate token_consumption from usage_metadata."""

    @pytest.mark.asyncio
    async def test_tokens_extracted_from_usage_metadata(self, monkeypatch):
        """When the raw AIMessage has usage_metadata, the node returns its total_tokens."""
        patch_result = PatchProposal(reasoning="Fix it.", target_file="main.py", code="print('ok')")

        class _FakeStructured:
            async def ainvoke(self, *_a, **_k):
                return {"parsed": patch_result, "raw": _fake_raw(total_tokens=99), "parsing_error": None}

        class _FakeModel:
            def with_structured_output(self, _schema, include_raw=False, **_kw):
                return _FakeStructured()

        monkeypatch.setattr("app.graph.nodes.modification_node.get_chat_model", lambda: _FakeModel())

        state = new_agent_state(
            current_target_file="demo/buggy_server.py",
            discovered_logs=["ImportError: missing module"],
        )
        delta = await modification_node(state)

        assert delta["token_consumption"] == 99
        assert delta["proposed_patch"] == "print('ok')"

    @pytest.mark.asyncio
    async def test_tokens_default_to_zero_when_usage_metadata_absent(self, monkeypatch):
        """If usage_metadata is None (some model configs omit it), fall back to 0."""
        patch_result = PatchProposal(reasoning="Fix it.", target_file="main.py", code="print('ok')")

        raw_no_meta = AIMessage(content="", usage_metadata=None)

        class _FakeStructured:
            async def ainvoke(self, *_a, **_k):
                return {"parsed": patch_result, "raw": raw_no_meta, "parsing_error": None}

        class _FakeModel:
            def with_structured_output(self, _schema, include_raw=False, **_kw):
                return _FakeStructured()

        monkeypatch.setattr("app.graph.nodes.modification_node.get_chat_model", lambda: _FakeModel())

        state = new_agent_state(
            current_target_file="demo/buggy_server.py",
            discovered_logs=["Error"],
        )
        delta = await modification_node(state)

        assert delta["token_consumption"] == 0


class TestArbitrationNodeTokens:
    """arbitration_node must also propagate token_consumption."""

    @pytest.mark.asyncio
    async def test_tokens_extracted(self, monkeypatch):
        decision_result = SecurityDecision(is_safe=True, reason="Looks fine.")

        class _FakeStructured:
            async def ainvoke(self, *_a, **_k):
                return {"parsed": decision_result, "raw": _fake_raw(total_tokens=55), "parsing_error": None}

        class _FakeSecModel:
            def with_structured_output(self, _schema, include_raw=False, **_kw):
                return _FakeStructured()

        monkeypatch.setattr(
            "app.graph.nodes.arbitration_node.get_security_models",
            lambda: [
                NamedModel("test:model-a", _FakeSecModel()),
                NamedModel("test:model-b", _FakeSecModel()),
            ],
        )
        monkeypatch.setattr(
            "app.graph.nodes.arbitration_node.check_blocklist",
            lambda _patch: (True, "ok"),
        )

        state = new_agent_state()
        state["proposed_patch"] = "print('hello')"
        delta = await arbitration_node(state)

        assert delta["security_clearance"] is True
        assert delta["token_consumption"] == 110
        assert len(delta["security_votes"]) == 2

    @pytest.mark.asyncio
    async def test_one_unsafe_vote_denies_clearance(self, monkeypatch):
        class _FakeStructured:
            def __init__(self, safe):
                self.safe = safe

            async def ainvoke(self, *_a, **_k):
                decision = SecurityDecision(
                    is_safe=self.safe,
                    reason="vote",
                )
                return {
                    "parsed": decision,
                    "raw": _fake_raw(total_tokens=10),
                    "parsing_error": None,
                }

        class _FakeSecModel:
            def __init__(self, safe):
                self.safe = safe

            def with_structured_output(self, *_args, **_kwargs):
                return _FakeStructured(self.safe)

        monkeypatch.setattr(
            "app.graph.nodes.arbitration_node.get_security_models",
            lambda: [
                NamedModel("test:safe", _FakeSecModel(True)),
                NamedModel("test:unsafe", _FakeSecModel(False)),
            ],
        )
        monkeypatch.setattr(
            "app.graph.nodes.arbitration_node.check_blocklist",
            lambda _patch: (True, "ok"),
        )

        state = new_agent_state()
        state["proposed_patch"] = "print('hello')"
        delta = await arbitration_node(state)

        assert delta["security_clearance"] is False
        assert len(delta["security_votes"]) == 2

    @pytest.mark.asyncio
    async def test_no_tokens_when_blocklist_rejects(self, monkeypatch):
        """When the blocklist blocks early, token_consumption key should be absent
        (we never called the LLM), or it defaults to 0 from operator.add."""
        monkeypatch.setattr(
            "app.graph.nodes.arbitration_node.check_blocklist",
            lambda _patch: (False, "rm -rf found"),
        )

        state = new_agent_state()
        state["proposed_patch"] = "import os; os.system('rm -rf /')"
        delta = await arbitration_node(state)

        assert delta["security_clearance"] is False
        # token_consumption is not emitted by the early return — that's fine,
        # operator.add will treat the absence as 0.
        assert "token_consumption" not in delta

    @pytest.mark.asyncio
    async def test_model_failure_denies_clearance(self, monkeypatch):
        class _FailingStructured:
            async def ainvoke(self, *_a, **_k):
                raise RuntimeError("provider unavailable")

        class _FailingModel:
            def with_structured_output(self, *_args, **_kwargs):
                return _FailingStructured()

        monkeypatch.setattr(
            "app.graph.nodes.arbitration_node.get_security_models",
            lambda: [
                NamedModel("test:ok", _FailingModel()),
                NamedModel("test:fail", _FailingModel()),
            ],
        )
        monkeypatch.setattr(
            "app.graph.nodes.arbitration_node.check_blocklist",
            lambda _patch: (True, "ok"),
        )

        state = new_agent_state()
        state["proposed_patch"] = "print('hello')"
        delta = await arbitration_node(state)

        assert delta["security_clearance"] is False
        assert delta["token_consumption"] == 0


class TestAgentStateAccumulation:
    """token_consumption in AgentState is initialized to 0."""

    def test_new_state_has_zero_tokens(self):
        state = new_agent_state()
        assert state["token_consumption"] == 0


# ═══════════════════════════════════════════════════════════════════════════
# P2 — Real Telemetry Signal
# ═══════════════════════════════════════════════════════════════════════════


class TestLogErrorCounter:
    """LogErrorCounter must compute real error rates from captured log records."""

    def setup_method(self):
        """Each test gets a fresh counter (avoid singleton state bleed)."""
        self.counter = LogErrorCounter()

    def test_empty_window_returns_zero(self):
        assert self.counter.error_rate() == 0.0

    def test_all_info_records_returns_zero(self):
        for _ in range(10):
            self.counter.inject(logging.INFO)
        assert self.counter.error_rate() == 0.0

    def test_all_error_records_returns_one(self):
        for _ in range(5):
            self.counter.inject(logging.ERROR)
        assert self.counter.error_rate() == 1.0

    def test_mixed_records_computes_correct_fraction(self):
        """5 ERROR + 5 INFO in window → rate = 0.5"""
        for _ in range(5):
            self.counter.inject(logging.ERROR)
        for _ in range(5):
            self.counter.inject(logging.INFO)
        rate = self.counter.error_rate()
        assert abs(rate - 0.5) < 1e-9

    def test_critical_counts_as_error(self):
        """CRITICAL should count as an error (levelno >= ERROR)."""
        self.counter.inject(logging.CRITICAL)
        self.counter.inject(logging.INFO)
        assert abs(self.counter.error_rate() - 0.5) < 1e-9

    def test_warning_does_not_count_as_error(self):
        """WARNING (30) is below ERROR (40) — should not inflate the error rate."""
        self.counter.inject(logging.WARNING)
        self.counter.inject(logging.INFO)
        assert self.counter.error_rate() == 0.0

    def test_old_records_outside_window_excluded(self):
        """Records older than window_seconds should not contribute."""
        old_ts = time.monotonic() - 120  # 2 minutes ago, outside 60s window
        self.counter.inject(logging.ERROR, ts=old_ts)
        # Only a fresh INFO within the window
        self.counter.inject(logging.INFO)
        # The old ERROR should be excluded → rate = 0.0
        assert self.counter.error_rate(window_seconds=60.0) == 0.0

    def test_reset_clears_all_records(self):
        for _ in range(5):
            self.counter.inject(logging.ERROR)
        self.counter.reset()
        assert self.counter.error_rate() == 0.0

    def test_singleton_is_same_instance(self):
        a = LogErrorCounter.get_instance()
        b = LogErrorCounter.get_instance()
        assert a is b

    def test_telemetry_does_not_import_random(self):
        """Confirm the random module is no longer used in telemetry.py."""
        import importlib
        import ast
        import pathlib

        telemetry_path = pathlib.Path(__file__).parent.parent / "app" / "anomaly" / "telemetry.py"
        tree = ast.parse(telemetry_path.read_text(encoding="utf-8"))
        imported_names = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in getattr(node, "names", []) + ([ast.alias(name=getattr(node, "module", "") or "")] if isinstance(node, ast.ImportFrom) else [])
        }
        assert "random" not in imported_names, (
            "telemetry.py still imports 'random' — the simulated error_rate was not removed"
        )
