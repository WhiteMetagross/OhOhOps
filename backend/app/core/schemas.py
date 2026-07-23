"""Shared data shapes for OhOhOps.

This module is the single source of truth for every structure that crosses a
boundary in the system:

* ``AgentState`` — the central memory object passed through the LangGraph
  execution graph (defined exactly to the system spec).
* The Pydantic request/response models that define the API contracts and the
  ledger record.

Graph nodes, API endpoints, and services all import from here so the state, the
HTTP contracts, and the database records never drift apart.
"""

import operator
from datetime import datetime
from typing import Any, Dict, List, Optional

from typing_extensions import Annotated, TypedDict

from pydantic import BaseModel, Field


# ───────────────────────── LangGraph orchestrator state ──────────────────────
class AgentState(TypedDict):
    """Central memory tracked through the SRE execution graph.

    ``messages`` uses an ``operator.add`` reducer so that each node can return a
    partial ``{"messages": [...]}`` and LangGraph appends rather than overwrites —
    this is how the conversation/log trail accumulates across the cyclic graph.
    All other keys are plain values that nodes overwrite as the run progresses.
    """

    messages: Annotated[List[Dict[str, str]], operator.add]
    current_target_file: str
    discovered_logs: List[str]
    project_path: str
    reproduction_command: str
    original_code: str
    proposed_patch: str
    execution_exit_code: int
    execution_stderr: str
    security_clearance: bool
    security_votes: List[Dict[str, str]]
    retry_count: int
    namespace: Optional[str]
    run_id: str
    telemetry_metrics: Dict[str, Any]
    source_code: str
    # Accumulated LLM token spend across all nodes in this run.
    # Uses operator.add so each node returns a partial count and LangGraph
    # appends rather than overwrites — same pattern as ``messages``.
    token_consumption: Annotated[int, operator.add]
    patch_store: Optional[Any]
    deployment_status: str
    deployment_pid: Optional[int]
    deployment_reason: str
    deployment_stderr: str


def new_agent_state(
    *,
    current_target_file: str = "",
    discovered_logs: Optional[List[str]] = None,
    messages: Optional[List[Dict[str, str]]] = None,
    project_path: str = "",
    reproduction_command: str = "",
    namespace: Optional[str] = None,
    run_id: str = "",
    patch_store: Optional[Any] = None,
    source_code: str = "",
) -> AgentState:
    """Build a fully-initialized ``AgentState`` with safe defaults.

    TypedDicts have no constructor, and every entry point into the graph (the
    /graph/run endpoint and the anomaly trigger) needs the state seeded the same
    way. Centralizing it here prevents missing-key errors inside the nodes.

    ``execution_exit_code`` starts at -1 to mean "not yet executed" — distinct
    from 0 (success), which the routing logic treats as a terminal condition.
    """
    return AgentState(
        messages=messages or [],
        current_target_file=current_target_file,
        discovered_logs=discovered_logs or [],
        project_path=project_path,
        reproduction_command=reproduction_command,
        original_code="",
        proposed_patch="",
        execution_exit_code=-1,
        execution_stderr="",
        security_clearance=False,
        security_votes=[],
        retry_count=0,
        namespace=namespace,
        run_id=run_id,
        telemetry_metrics={},
        token_consumption=0,
        patch_store=patch_store,
        deployment_status="pending",
        deployment_pid=None,
        deployment_reason="",
        deployment_stderr="",
        source_code=source_code,
    )


# ───────────────────────────── API: health ───────────────────────────────────
class HealthResponse(BaseModel):
    status: str
    dependencies: Dict[str, str] = Field(
        default_factory=dict,
        description="Per-dependency readiness, e.g. {'pinecone': 'ok', 'docker': 'ok'}.",
    )


# ───────────────────────────── API: anomaly webhook ──────────────────────────
class AnomalyPayload(BaseModel):
    alert_id: str = Field(..., description="Unique ID from the external alerting system.")
    service_name: str = Field(..., description="Name of the affected service/container.")
    target_file: str = Field(..., description="The source code file suspected of causing the anomaly.")
    logs: List[str] = Field(..., description="The crash logs or stack trace that triggered the alert.")


# ───────────────────────────── API: ingestion ────────────────────────────────
class IngestRequest(BaseModel):
    directory_path: str = Field(..., description="Absolute path to the codebase to ingest.")
    namespace: Optional[str] = Field(
        default=None, description="Optional Pinecone namespace to isolate this codebase."
    )


class IngestResponse(BaseModel):
    files_processed: int
    chunks_indexed: int
    elapsed_ms: int


# ───────────────────────────── API: context query ────────────────────────────
class ContextQueryRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="Raw user/system prompt to answer.")
    namespace: Optional[str] = Field(default=None, description="Pinecone namespace to search.")
    top_k: Optional[int] = Field(
        default=None, ge=1, le=50, description="Override for retrieval depth; defaults to settings."
    )


# ───────────────────────────── API: graph run ────────────────────────────────
class GraphRunRequest(BaseModel):
    target_file: str = Field(..., description="File the agent should focus its repair on.")
    logs: List[str] = Field(
        default_factory=list, description="Error/log lines that triggered this run."
    )
    project_path: str = Field(..., description="Absolute path to the user's project directory.")
    reproduction_command: str = Field(..., description="Command to reproduce the error (e.g., 'python main.py').")
    namespace: Optional[str] = Field(default=None, description="Pinecone namespace to search.")


class GraphRunResponse(BaseModel):
    run_id: str
    final_exit_code: int
    retry_count: int
    security_clearance: bool
    proposed_patch: str

class TelemetryIngestPayload(BaseModel):
    cpu: float = Field(..., description="CPU usage percent (0-100)")
    mem: float = Field(..., description="Memory usage percent (0-100)")
    error_rate: float = Field(..., description="Error rate fraction (0-1)")
    logs: List[str] = Field(default_factory=list, description="Optional list of log lines or messages")
    reproduction_command: str = Field(default="", description="The command to reproduce the crash (from daemon --watch)")
    target_file: str = Field(default="", description="The file that crashed (extracted from traceback)")
    source_code: str = Field(default="", description="The contents of the crashed file from the daemon")


# ───────────────────────── Patch Delivery (Phase 0) ──────────────────────────
class PendingPatch(BaseModel):
    patch_id: str
    run_id: str
    target_file: str          # relative path within project
    patch_code: str           # full file contents
    reproduction_command: str  # how to restart
    created_at: datetime
    status: str               # "pending" | "picked_up" | "applied" | "restarted" | "failed"

class PendingDeploymentsResponse(BaseModel):
    patches: List[PendingPatch]

class AckPayload(BaseModel):
    patch_id: str
    status: str
    stderr: str = ""


# ───────────────────────────── API: graph run stream ─────────────────────────
class GraphStreamEvent(BaseModel):
    event: str = Field(..., description="'node_update', 'complete', or 'error'")
    run_id: str
    node: Optional[str] = None
    state: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    @classmethod
    def from_delta(cls, run_id: str, node_name: str, delta: dict) -> "GraphStreamEvent":
        state_payload = {"active_node": node_name}
        for key in [
            "retry_count",
            "execution_exit_code",
            "security_clearance",
            "proposed_patch",
            "original_code",
            "token_consumption",
            "deployment_status",
            "deployment_pid",
            "deployment_reason",
            "deployment_stderr",
        ]:
            if key in delta:
                state_payload[key] = delta[key]
                
        messages = delta.get("messages", [])
        if messages:
            last_msg = messages[-1]
            if hasattr(last_msg, "content"):
                state_payload["latest_message"] = last_msg.content
            elif isinstance(last_msg, dict):
                state_payload["latest_message"] = last_msg.get("content", "")
                
        return cls(event="node_update", run_id=run_id, node=node_name, state=state_payload)


# ───────────────────────── Operational ledger record ─────────────────────────
class OperationalLogEntry(BaseModel):
    """Mirrors the ``operational_logs`` table. ``id`` and ``timestamp`` are
    generated by the database, so they are optional on writes."""

    id: Optional[str] = None
    timestamp: Optional[str] = None
    event_source: str
    agent_action: Optional[str] = None
    execution_payload: Optional[str] = None
    execution_status: Optional[str] = None
    token_consumption: int = 0
    compute_latency_ms: int = 0
    ragas_fidelity_score: Optional[float] = None
