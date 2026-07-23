from typing import Protocol, Dict, Any

class RestartStrategy(Protocol):
    """Unified interface for restarting a project process."""
    
    async def restart(self, project_path: str, command: str) -> Dict[str, Any]:
        """
        Restart the process.
        Returns a dictionary with at least {"pid": int | None}.
        """
        ...
        
    async def health_check(self, project_path: str) -> Dict[str, Any]:
        """
        Check the health of the restarted process.
        Returns a dictionary with at least {"alive": bool, "last_stderr": str, "pid": int | None}.
        """
        ...

def get_restart_strategy(settings) -> RestartStrategy:
    """Returns the appropriate restart strategy based on deployment config."""
    if settings.is_cloud:
        from .daemon_strategy import DaemonRestartStrategy
        return DaemonRestartStrategy()
        
    if settings.cloud_restart_strategy == "docker_compose":
        from .docker_strategy import DockerComposeRestartStrategy
        return DockerComposeRestartStrategy()
        
    from .subprocess_strategy import SubprocessRestartStrategy
    return SubprocessRestartStrategy()
