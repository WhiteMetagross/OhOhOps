import asyncio
import logging

from app.core.schemas import AgentState
from app.core.config import get_settings
from app.services.process_manager import RestartCircuitBreaker
from app.services.restart_strategies import get_restart_strategy
from app.services.deployment_patch import (
    apply_patch_transaction,
    finalize_patch,
    rollback_patch,
)

logger = logging.getLogger("ohohops.graph.nodes.deployment")

async def deployment_node(state: AgentState) -> dict:
    """
    Post-heal deployment node.
    Restarts the target project after a verified patch has been written to disk.
    Only runs when sandbox_node has exit_code == 0.
    """
    logger.info("--- DEPLOYMENT NODE (POST-HEAL RESTART) ---")
    
    settings = get_settings()
    project_path = state.get("project_path", "")
    repro_cmd = state.get("reproduction_command", "")
    
    if not settings.enable_post_heal_restart:
        return {
            "deployment_status": "disabled",
            "deployment_reason": "Post-heal restart is disabled in config"
        }
    
    # ── Cloud/SaaS mode: enqueue patch for daemon pickup ──────────────────
    # In cloud mode, the backend has no local process to restart.
    # The patch must be enqueued in PatchStore so the remote daemon can poll it.
    if settings.is_cloud:
        patch_store = state.get("patch_store")
        namespace = state.get("namespace") or ""
        target_file = state.get("current_target_file", "")
        patch_code = state.get("proposed_patch", "")
        run_id = state.get("run_id", "")
        
        if not patch_store:
            logger.warning("No patch_store available — cannot enqueue for daemon.")
            return {
                "deployment_status": "skipped",
                "deployment_reason": "PatchStore not initialized"
            }
        
        if not patch_code:
            logger.warning("No proposed_patch to deploy.")
            return {
                "deployment_status": "skipped",
                "deployment_reason": "No patch code to deploy"
            }
        
        try:
            patch_id = await patch_store.enqueue(
                namespace=namespace,
                run_id=run_id,
                target_file=target_file,
                patch_code=patch_code,
                reproduction_command=repro_cmd,
            )
            logger.info(f"OK: Patch {patch_id} enqueued for daemon pickup (namespace={namespace})")
            return {
                "deployment_status": "pending_daemon",
                "deployment_reason": f"Patch {patch_id} queued for daemon pickup"
            }
        except Exception as e:
            logger.error(f"Failed to enqueue patch: {e}", exc_info=True)
            return {
                "deployment_status": "error",
                "deployment_reason": f"Failed to enqueue patch: {e}"
            }
    
    # ── Local mode: direct process restart ────────────────────────────────
    if not project_path or not repro_cmd:
        logger.warning("No project_path or reproduction_command — skipping restart.")
        return {
            "deployment_status": "skipped",
            "deployment_reason": "Missing project_path or command"
        }
    
    circuit_breaker = RestartCircuitBreaker.get_instance()
    if not circuit_breaker.can_restart(project_path):
        logger.critical(f"Circuit breaker OPEN for {project_path}. Too many restart failures.")
        return {
            "deployment_status": "circuit_breaker_open",
            "deployment_reason": "Too many restart failures in time window"
        }
    
    strategy = get_restart_strategy(settings)
    transaction = None
    try:
        transaction = apply_patch_transaction(
            project_path,
            state.get("current_target_file", ""),
            state.get("proposed_patch", ""),
        )
        circuit_breaker.record_attempt(project_path)
        logger.info(f"Triggering restart for {project_path} via {strategy.__class__.__name__}...")
        
        result = await strategy.restart(project_path, command=repro_cmd)
        
        if result.get("status") == "pending_daemon":
            return {
                "deployment_status": "pending_daemon",
                "deployment_reason": result.get("reason", "Patch queued for daemon pickup")
            }
        
        # Wait for the process to hopefully crash if it's still broken
        await asyncio.sleep(settings.restart_health_check_delay)
        health = await strategy.health_check(project_path)
        
        if health["alive"]:
            finalize_patch(transaction)
            circuit_breaker.record_success(project_path)
            logger.info(f"OK: Project restarted and healthy. PID={health.get('pid')}")
            return {
                "deployment_status": "success",
                "deployment_pid": health.get("pid"),
                "deployment_reason": "Restart successful and passed health check"
            }
        else:
            logger.error(f"ERROR: Project restarted but failed health check.")
            rollback_patch(transaction)
            await strategy.restart(project_path, command=repro_cmd)
            await asyncio.sleep(settings.restart_health_check_delay)
            restored_health = await strategy.health_check(project_path)
            return {
                "deployment_status": "rolled_back",
                "deployment_stderr": health.get("last_stderr", ""),
                "deployment_reason": (
                    "Patched process failed health check. Original file restored. "
                    f"Restored process healthy: {bool(restored_health.get('alive'))}"
                ),
            }
    except Exception as e:
        logger.error(f"Restart failed: {e}", exc_info=True)
        if transaction is not None:
            try:
                rollback_patch(transaction)
                return {
                    "deployment_status": "rolled_back",
                    "deployment_reason": f"Deployment failed and original file was restored: {e}",
                }
            except Exception as rollback_error:
                logger.critical("Automatic rollback failed: %s", rollback_error)
                return {
                    "deployment_status": "rollback_failed",
                    "deployment_reason": (
                        f"Deployment error: {e}. Rollback error: {rollback_error}"
                    ),
                }
        return {
            "deployment_status": "error",
            "deployment_reason": str(e)
        }

