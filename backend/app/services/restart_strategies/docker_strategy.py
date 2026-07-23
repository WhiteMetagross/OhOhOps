import asyncio
import json
import logging
from typing import Dict, Any

from app.services.restart_strategies import RestartStrategy

logger = logging.getLogger("ohohops.strategies.docker")

class DockerComposeRestartStrategy(RestartStrategy):
    """
    Restarts a service defined in docker-compose.yml by calling:
      docker compose restart <service_name>
    """
    
    async def restart(self, project_path: str, command: str) -> Dict[str, Any]:
        """
        `command` is interpreted as the docker-compose service name.
        """
        service_name = command.strip()
        if not service_name:
            raise ValueError("Docker Compose strategy requires the service name as the 'command'.")
            
        logger.info(f"Restarting docker compose service '{service_name}' in {project_path}")
        
        proc = await asyncio.create_subprocess_exec(
            "docker", "compose", "restart", service_name,
            cwd=project_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await proc.communicate()
        
        if proc.returncode != 0:
            err_msg = stderr.decode()
            logger.error(f"Docker restart failed: {err_msg}")
            raise RuntimeError(f"Docker compose restart failed: {err_msg}")
            
        return {"pid": None} # PID is managed inside the container

    async def health_check(self, project_path: str) -> Dict[str, Any]:
        """
        Checks health of containers in the compose file.
        """
        proc = await asyncio.create_subprocess_exec(
            "docker", "compose", "ps", "--format", "json",
            cwd=project_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await proc.communicate()
        
        if proc.returncode != 0:
            return {"alive": False, "last_stderr": stderr.decode(), "pid": None}
            
        try:
            output = stdout.decode().strip()
            if not output:
                return {"alive": False, "last_stderr": "No containers found", "pid": None}
                
            containers = []
            if output.startswith("["):
                containers = json.loads(output)
            else:
                for line in output.splitlines():
                    containers.append(json.loads(line))
                    
            # Check if any container is in a bad state (exited, restarting, dead)
            all_running = all(c.get("State", "").lower() == "running" for c in containers)
            
            if not all_running:
                bad_states = [c for c in containers if c.get("State", "").lower() != "running"]
                err_summary = ", ".join([f"{c.get('Service', 'unknown')}: {c.get('State', 'unknown')}" for c in bad_states])
                return {"alive": False, "last_stderr": f"Containers not running: {err_summary}", "pid": None}
                
            return {"alive": True, "pid": None}
            
        except Exception as e:
            logger.error(f"Failed to parse docker compose ps output: {e}")
            return {"alive": False, "last_stderr": str(e), "pid": None}
