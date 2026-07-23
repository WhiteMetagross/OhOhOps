from pathlib import Path
from types import SimpleNamespace
import importlib.util

import pytest
from langchain_core.embeddings import Embeddings

from app.core.schemas import new_agent_state
from app.graph.nodes.deployment_node import deployment_node
from app.services.ast_chunker import split_source_by_ast
from app.services.deployment_patch import resolve_target
from app.services.embeddings import DeterministicEmbeddings, FixedDimensionEmbeddings


class TinyEmbeddings(Embeddings):
    def embed_documents(self, texts):
        return [[1.0, 2.0, 3.0] for _ in texts]

    def embed_query(self, text):
        return [1.0, 2.0, 3.0]

    async def aembed_documents(self, texts):
        return self.embed_documents(texts)

    async def aembed_query(self, text):
        return self.embed_query(text)


def test_ast_chunker_uses_function_boundaries():
    source = """
import os

def first():
    return 1

def second():
    return 2
""".strip()
    chunks = split_source_by_ast(
        source,
        "service.py",
        ".py",
        chunk_size=45,
        chunk_overlap=5,
    )

    assert chunks
    assert all(chunk.metadata["chunker"] == "tree_sitter_ast" for chunk in chunks)
    assert any("function_definition" in chunk.metadata["ast_node_types"] for chunk in chunks)
    assert "def first" in "".join(chunk.page_content for chunk in chunks)


def test_daemon_rollback_restores_original_file(tmp_path):
    daemon_path = (
        Path(__file__).parents[2]
        / "frontend"
        / "public"
        / "ohohops_daemon.py"
    )
    spec = importlib.util.spec_from_file_location("ohohops_daemon", daemon_path)
    assert spec and spec.loader
    daemon = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(daemon)

    target = tmp_path / "service.py"
    target.write_text("print('stable')\n", encoding="utf-8")
    transaction = daemon.apply_patch(
        str(tmp_path),
        "service.py",
        "raise RuntimeError('broken')\n",
    )

    assert transaction
    assert daemon.rollback_patch(transaction) is True
    assert target.read_text(encoding="utf-8") == "print('stable')\n"


def test_patch_target_cannot_escape_project(tmp_path):
    with pytest.raises(ValueError, match="escapes project"):
        resolve_target(str(tmp_path), "../outside.py")


@pytest.mark.asyncio
async def test_embedding_adapter_always_returns_3072_values():
    embeddings = FixedDimensionEmbeddings(TinyEmbeddings(), 3072)

    assert len(embeddings.embed_query("query")) == 3072
    assert len((await embeddings.aembed_documents(["one"]))[0]) == 3072


def test_mock_embeddings_are_stable_and_distinct():
    embeddings = DeterministicEmbeddings(3072)

    first = embeddings.embed_query("same input")
    second = embeddings.embed_query("same input")
    different = embeddings.embed_query("different input")

    assert first == second
    assert first != different
    assert len(first) == 3072


class FakeRestartStrategy:
    def __init__(self, health_results):
        self.health_results = iter(health_results)
        self.restart_calls = 0

    async def restart(self, project_path, command):
        self.restart_calls += 1
        return {"pid": 1234}

    async def health_check(self, project_path):
        return next(self.health_results)


def _settings():
    return SimpleNamespace(
        enable_post_heal_restart=True,
        is_cloud=False,
        restart_health_check_delay=0,
    )


@pytest.mark.asyncio
async def test_unhealthy_deployment_restores_original_file(tmp_path, monkeypatch):
    target = tmp_path / "service.py"
    target.write_text("print('stable')\n", encoding="utf-8")
    strategy = FakeRestartStrategy(
        [
            {"alive": False, "last_stderr": "crashed"},
            {"alive": True, "pid": 4321},
        ]
    )
    monkeypatch.setattr(
        "app.graph.nodes.deployment_node.get_settings",
        _settings,
    )
    monkeypatch.setattr(
        "app.graph.nodes.deployment_node.get_restart_strategy",
        lambda _settings: strategy,
    )

    state = new_agent_state(
        project_path=str(tmp_path),
        current_target_file="service.py",
        reproduction_command="python service.py",
    )
    state["proposed_patch"] = "raise RuntimeError('broken')\n"

    result = await deployment_node(state)

    assert result["deployment_status"] == "rolled_back"
    assert target.read_text(encoding="utf-8") == "print('stable')\n"
    assert strategy.restart_calls == 2
    assert not list(Path(tmp_path).glob("*.bak"))


@pytest.mark.asyncio
async def test_healthy_deployment_keeps_patch_and_removes_backup(tmp_path, monkeypatch):
    target = tmp_path / "service.py"
    target.write_text("print('old')\n", encoding="utf-8")
    strategy = FakeRestartStrategy([{"alive": True, "pid": 1234}])
    monkeypatch.setattr(
        "app.graph.nodes.deployment_node.get_settings",
        _settings,
    )
    monkeypatch.setattr(
        "app.graph.nodes.deployment_node.get_restart_strategy",
        lambda _settings: strategy,
    )

    state = new_agent_state(
        project_path=str(tmp_path),
        current_target_file="service.py",
        reproduction_command="python service.py",
    )
    state["proposed_patch"] = "print('fixed')\n"

    result = await deployment_node(state)

    assert result["deployment_status"] == "success"
    assert target.read_text(encoding="utf-8") == "print('fixed')\n"
    assert not list(Path(tmp_path).glob("*.bak"))
