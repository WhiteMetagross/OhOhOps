import logging
from typing import Dict, Any

from app.services.restart_strategies import RestartStrategy

logger = logging.getLogger("ohohops.strategies.daemon")

class DaemonRestartStrategy(RestartStrategy):
    """
    Delegates restart execution to the remote ohohops_daemon.py client.
    Used in Cloud/SaaS mode.
    """
    
    async def restart(self, project_path: str, command: str) -> Dict[str, Any]:
        """
        The patch has already been enqueued into the PatchStore by sandbox_node.
        The daemon will poll for it and apply it.
        We return a special status indicating the daemon is pending.
        """
        logger.info(f"Delegating restart of {project_path} to remote daemon.")
        return {
            "pid": None,
            "status": "pending_daemon",
            "reason": "Patch queued for daemon pickup"
        }

    async def health_check(self, project_path: str) -> Dict[str, Any]:
        """
        The backend cannot health check the remote user process natively.
        The daemon's internal ProcessSupervisor performs continuous health checks
        and will report any post-restart crashes back to the telemetry ingest endpoint.
        Therefore, we assume it's alive from the graph's synchronous perspective.
        """
        return {"alive": True, "pid": None}
