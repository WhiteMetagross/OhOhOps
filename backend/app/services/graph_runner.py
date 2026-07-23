import time
import logging
from typing import List

from app.core.schemas import AgentState, new_agent_state, OperationalLogEntry
from app.graph.orchestrator import create_sre_orchestrator

logger = logging.getLogger("ohohops.services.graph_runner")

# Instantiate the orchestrator once (it acts as a stateless workflow template)
sre_orchestrator = create_sre_orchestrator()

async def record_ledger_entry(app, target_file: str, final_state: AgentState, elapsed_ms: int, run_id: str, event_source: str):
    """Helper to write a finished run to the ledger."""
    ledger = getattr(app.state, "ledger", None)
    if not ledger:
        return

    exit_code = final_state.get("execution_exit_code", -1)
    clearance = final_state.get("security_clearance", False)
    retry_count = final_state.get("retry_count", 0)
    total_tokens = final_state.get("token_consumption", 0)
    
    status = "success" if exit_code == 0 else "failed"
    if not clearance:
        status = "blocked_security"
    elif exit_code == 0:
        deploy_status = final_state.get("deployment_status")
        if deploy_status and deploy_status not in ("skipped", "disabled", "pending"):
            status = deploy_status
        
    patch = final_state.get("proposed_patch", "")
    payload_str = f"Target: {target_file} | Retries: {retry_count}"
    if patch:
        payload_str += f"\n\n--- Proposed Patch ---\n{patch}"
        
    deploy_reason = final_state.get("deployment_reason")
    deploy_stderr = final_state.get("deployment_stderr")
    if deploy_reason:
        payload_str += f"\n\n--- Deployment Reason ---\n{deploy_reason}"
    if deploy_stderr:
        payload_str += f"\n\n--- Deployment Stderr ---\n{deploy_stderr}"

    entry = OperationalLogEntry(
        event_source=event_source,
        agent_action="autonomous_repair",
        execution_payload=payload_str,
        execution_status=status,
        token_consumption=total_tokens,
        compute_latency_ms=elapsed_ms
    )
    try:
        await ledger.log_event(entry)
    except Exception as ledger_err:
        logger.error(f"Failed to record to ledger: {ledger_err}")


async def execute_repair(
    app,
    target_file: str,
    logs: list[str],
    run_id: str,
    event_source: str = "api/v1/graph/run",
    project_path: str = "",
    reproduction_command: str = "",
    namespace: str = None,
    source_code: str = ""
) -> AgentState:
    """
    Executes the SRE orchestrator LangGraph.
    """
    start_time = time.perf_counter()
    
    logger.info(f"Starting Graph Run {run_id} for target file: {target_file}")
    
    initial_state = new_agent_state(
        current_target_file=target_file,
        discovered_logs=logs,
        project_path=project_path,
        reproduction_command=reproduction_command,
        namespace=namespace,
        run_id=run_id,
        patch_store=getattr(app.state, "patch_store", None),
        source_code=source_code
    )
    try:
        final_state = await sre_orchestrator.ainvoke(initial_state)
    except Exception as e:
        logger.error(f"Graph execution fatally failed: {e}", exc_info=True)
        raise

    elapsed_ms = int((time.perf_counter() - start_time) * 1000)
    await record_ledger_entry(app, target_file, final_state, elapsed_ms, run_id, event_source)

    # Inject latency so the frontend scorecard can display execution time.
    final_state["latency_ms"] = elapsed_ms
    return final_state
