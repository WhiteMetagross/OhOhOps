from typing import Dict, Any
from app.services.process_manager import ProcessManager
from app.services.restart_strategies import RestartStrategy

class SubprocessRestartStrategy(RestartStrategy):
    """
    Restarts the project by delegating to the ProcessManager.
    Used in local/development deployments where the backend natively controls processes.
    """
    def __init__(self):
        self.pm = ProcessManager.get_instance()

    async def restart(self, project_path: str, command: str) -> Dict[str, Any]:
        managed_process = await self.pm.restart(project_path, command=command)
        pid = managed_process.process.pid if (managed_process and managed_process.process) else None
        return {"pid": pid}

    async def health_check(self, project_path: str) -> Dict[str, Any]:
        return await self.pm.health_check(project_path)
