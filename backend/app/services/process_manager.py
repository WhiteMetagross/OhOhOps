import asyncio
from datetime import datetime
from collections import deque
import logging
from typing import Dict, Literal, Optional
import os
import signal
import subprocess
import time

logger = logging.getLogger("ohohops.services.process_manager")

class ManagedProcess:
    """Represents a single managed project process."""
    def __init__(self, project_path: str, command: str):
        self.project_path = project_path
        self.command = command
        self.process: Optional[asyncio.subprocess.Process] = None
        self.status: Literal["running", "stopped", "restarting", "crashed"] = "stopped"
        self.started_at: Optional[datetime] = None
        self.restart_count: int = 0
        self.last_output: deque[str] = deque(maxlen=100)
        self._monitor_task: Optional[asyncio.Task] = None

class ProcessManager:
    """Singleton that manages the lifecycle of monitored project processes."""
    _instance: Optional["ProcessManager"] = None
    
    def __init__(self):
        self._processes: Dict[str, ManagedProcess] = {}
        
    @classmethod
    def get_instance(cls) -> "ProcessManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def _read_stream(self, stream: asyncio.StreamReader, mp: ManagedProcess, is_stderr: bool):
        try:
            while not stream.at_eof():
                line = await stream.readline()
                if not line:
                    break
                decoded = line.decode('utf-8', errors='replace').strip()
                if decoded:
                    if is_stderr:
                        mp.last_output.append(decoded)
        except Exception as e:
            logger.debug(f"Stream read error for {mp.project_path}: {e}")

    async def _monitor(self, mp: ManagedProcess):
        if not mp.process:
            return
            
        await asyncio.gather(
            self._read_stream(mp.process.stdout, mp, is_stderr=False),
            self._read_stream(mp.process.stderr, mp, is_stderr=True)
        )
        
        returncode = await mp.process.wait()
        if returncode != 0 and mp.status not in ("stopped", "restarting"):
            mp.status = "crashed"
            logger.warning(f"Process for {mp.project_path} crashed with exit code {returncode}")
        elif mp.status not in ("stopped", "restarting"):
            mp.status = "stopped"

    async def start(self, project_path: str, command: str) -> ManagedProcess:
        if project_path in self._processes:
            mp = self._processes[project_path]
            if mp.status == "running" and mp.process and mp.process.returncode is None:
                logger.info(f"Process for {project_path} is already running.")
                return mp
        else:
            mp = ManagedProcess(project_path, command)
            self._processes[project_path] = mp

        logger.info(f"Starting process for {project_path}: {command}")
        mp.command = command
        mp.last_output.clear()
        
        kwargs = {
            "stdout": asyncio.subprocess.PIPE,
            "stderr": asyncio.subprocess.PIPE,
            "cwd": project_path
        }
        
        if os.name == 'nt':
            kwargs["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200)
        else:
            kwargs["start_new_session"] = True
            
        mp.process = await asyncio.create_subprocess_shell(command, **kwargs)
        
        mp.status = "running"
        mp.started_at = datetime.now()
        mp._monitor_task = asyncio.create_task(self._monitor(mp))
        
        return mp

    async def stop(self, project_path: str, graceful_timeout: float = 10.0) -> bool:
        if project_path not in self._processes:
            return True
            
        mp = self._processes[project_path]
        if not mp.process or mp.process.returncode is not None:
            mp.status = "stopped"
            return True

        logger.info(f"Stopping process for {project_path}...")
        mp.status = "stopped"
        
        try:
            if os.name == 'nt':
                mp.process.terminate()
            else:
                os.killpg(os.getpgid(mp.process.pid), signal.SIGTERM)
        except ProcessLookupError:
            pass
            
        try:
            await asyncio.wait_for(mp.process.wait(), timeout=graceful_timeout)
        except asyncio.TimeoutError:
            logger.warning(f"Process {project_path} ignoring SIGTERM, sending SIGKILL...")
            try:
                if os.name == 'nt':
                    os.system(f"taskkill /T /F /PID {mp.process.pid}")
                else:
                    os.killpg(os.getpgid(mp.process.pid), signal.SIGKILL)
            except ProcessLookupError:
                pass
            await mp.process.wait()
            
        return True

    async def restart(self, project_path: str, command: str = None) -> ManagedProcess:
        mp = self._processes.get(project_path)
        if mp:
            mp.status = "restarting"
            mp.restart_count += 1
            await self.stop(project_path)
            cmd = command or mp.command
        else:
            cmd = command
            
        return await self.start(project_path, cmd)

    async def health_check(self, project_path: str) -> dict:
        mp = self._processes.get(project_path)
        if not mp or not mp.process:
            return {"alive": False, "status": "not_found", "last_stderr": ""}
            
        alive = mp.process.returncode is None
        
        return {
            "alive": alive,
            "status": mp.status,
            "pid": mp.process.pid if alive else None,
            "last_stderr": "\n".join(mp.last_output) if mp.last_output else ""
        }

    def get_status(self, project_path: str) -> Optional[ManagedProcess]:
        return self._processes.get(project_path)

class RestartCircuitBreaker:
    """Prevents infinite restart loops by tracking recent restart failures."""
    _instance: Optional["RestartCircuitBreaker"] = None

    def __init__(self, max_attempts: int = 3, cooldown_seconds: float = 300.0):
        self._attempts: Dict[str, list[float]] = {}
        self.max_attempts = max_attempts
        self.cooldown = cooldown_seconds

    @classmethod
    def get_instance(cls) -> "RestartCircuitBreaker":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _cleanup_old(self, project_path: str):
        if project_path not in self._attempts:
            return
        now = time.time()
        self._attempts[project_path] = [
            ts for ts in self._attempts[project_path] 
            if now - ts <= self.cooldown
        ]

    def can_restart(self, project_path: str) -> bool:
        self._cleanup_old(project_path)
        attempts = len(self._attempts.get(project_path, []))
        return attempts < self.max_attempts

    def record_attempt(self, project_path: str) -> None:
        self._cleanup_old(project_path)
        if project_path not in self._attempts:
            self._attempts[project_path] = []
        self._attempts[project_path].append(time.time())
        logger.debug(f"Recorded restart attempt for {project_path}. Total in window: {len(self._attempts[project_path])}")

    def record_success(self, project_path: str) -> None:
        if project_path in self._attempts:
            self._attempts.pop(project_path)
            logger.debug(f"Reset circuit breaker for {project_path} due to successful health check.")
