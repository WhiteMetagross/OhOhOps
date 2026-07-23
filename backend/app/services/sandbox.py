import os
import sys
import tempfile
import asyncio
import subprocess
import logging
import shutil
from typing import Tuple

from app.core.config import get_settings

logger = logging.getLogger("ohohops.sandbox")

def _get_language_env(target_file: str) -> dict:
    """Detect language from file extension and return the appropriate execution environment."""
    ext = os.path.splitext(target_file)[1].lower() if target_file else ".py"
    
    mapping = {
        ".js": {"ext": ".js", "cmd": "node {file}", "image": "node:22-slim"},
        ".ts": {"ext": ".ts", "cmd": "node {file}", "image": "node:22-slim"},
        ".cpp": {"ext": ".cpp", "cmd": "g++ -o /tmp/ohohops-app {file} && /tmp/ohohops-app", "image": "gcc:14"},
        ".c": {"ext": ".c", "cmd": "gcc -o /tmp/ohohops-app {file} && /tmp/ohohops-app", "image": "gcc:14"},
        ".go": {"ext": ".go", "cmd": "go run {file}", "image": "golang:1.24-alpine"},
        ".py": {"ext": ".py", "cmd": "python {file}", "image": "python:3.12-slim"},
    }
    
    return mapping.get(ext, mapping[".py"])


# ── Subprocess-based sandbox (works everywhere, no Docker needed) ─────────

def _run_subprocess_sandbox(
    code: str,
    project_path: str = "",
    reproduction_command: str = "",
    target_file: str = ""
) -> Tuple[int, str, str]:
    """
    Runs the patched code in a local subprocess.
    Uses a temporary copy of the project so the original files are never mutated.
    This is the reliable fallback for development / Windows environments where
    Docker Desktop's Named Pipe connection is unreliable.
    """
    settings = get_settings()
    temp_dir = tempfile.mkdtemp(prefix="ohohops_sandbox_")

    try:
        if project_path and os.path.exists(project_path):
            # Copy only source code (skip heavy dependency dirs)
            ignore = shutil.ignore_patterns(
                "node_modules", ".next", "venv", ".venv",
                "__pycache__", ".git", "*.pyc"
            )
            shutil.copytree(project_path, temp_dir, dirs_exist_ok=True, ignore=ignore)

            # Apply the patch to the target file in the temp copy
            if target_file:
                rel_target = (
                    os.path.relpath(target_file, project_path)
                    if os.path.isabs(target_file)
                    else target_file
                )
                target_dest = os.path.join(temp_dir, rel_target)

                # If the direct path doesn't exist, the user likely provided
                # just a filename (e.g. "buggy_data_processor.py" instead of
                # "demo/buggy_data_processor.py").  Walk the tree to find it.
                if not os.path.exists(target_dest):
                    basename = os.path.basename(rel_target)
                    for root, _dirs, files in os.walk(temp_dir):
                        if basename in files:
                            target_dest = os.path.join(root, basename)
                            logger.info(f"Resolved target file to: {os.path.relpath(target_dest, temp_dir)}")
                            break

                os.makedirs(os.path.dirname(target_dest), exist_ok=True)
                with open(target_dest, "w", encoding="utf-8") as f:
                    f.write(code)

            repro_cmd = reproduction_command or "python main.py"
            cwd = temp_dir
        else:
            # Standalone script mode
            env = _get_language_env(target_file)
            filename = f"script{env['ext']}"
            script_path = os.path.join(temp_dir, filename)
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(code)
            repro_cmd = env["cmd"].format(file=filename)
            cwd = temp_dir

        logger.info(f"Subprocess sandbox: running '{repro_cmd}' in {cwd}")

        result = subprocess.run(
            repro_cmd,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=settings.sandbox_timeout_seconds,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )

        return result.returncode, result.stdout, result.stderr

    except subprocess.TimeoutExpired:
        logger.error("Subprocess sandbox timed out.")
        return -1, "", f"Execution timed out after {settings.sandbox_timeout_seconds}s"
    except Exception as e:
        logger.error(f"Subprocess sandbox failed: {e}")
        return -1, "", str(e)
    finally:
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass


# ── Docker-based sandbox (production isolation) ───────────────────────────

def _run_docker_sandbox(
    code: str,
    project_path: str = "",
    reproduction_command: str = "",
    target_file: str = ""
) -> Tuple[int, str, str]:
    """
    Runs the patched code inside an ephemeral Docker container for full isolation.
    Used in production environments where Docker is stable.
    """
    import docker

    settings = get_settings()

    try:
        client = docker.from_env(version="1.41")
    except Exception as e:
        logger.error(f"Failed to connect to Docker daemon: {e}")
        return -1, "", f"Failed to connect to Docker daemon: {e}"

    mounts = {}
    container_cmd = []
    working_dir = "/app"
    container = None

    if settings.is_local:
        import uuid
        unique_id = uuid.uuid4().hex[:8]
        temp_dir = f"/sandbox/ohohops_sandbox_{unique_id}"
        os.makedirs(temp_dir, exist_ok=True)
    else:
        temp_dir = tempfile.mkdtemp(prefix="ohohops_sandbox_")

    try:
        if project_path and os.path.exists(project_path):
            ignore = shutil.ignore_patterns(
                "node_modules", ".next", "venv", ".venv",
                "__pycache__", ".git", "*.pyc"
            )
            shutil.copytree(project_path, temp_dir, dirs_exist_ok=True, ignore=ignore)

            if target_file:
                rel_target = (
                    os.path.relpath(target_file, project_path)
                    if os.path.isabs(target_file)
                    else target_file
                )
                target_dest = os.path.join(temp_dir, rel_target)

                if not os.path.exists(target_dest):
                    basename = os.path.basename(rel_target)
                    for root, _dirs, files in os.walk(temp_dir):
                        if basename in files:
                            target_dest = os.path.join(root, basename)
                            break

                os.makedirs(os.path.dirname(target_dest), exist_ok=True)
                with open(target_dest, "w", encoding="utf-8") as f:
                    f.write(code)

            if settings.is_local:
                mounts = {"sandbox_workspaces": {"bind": "/sandbox", "mode": "rw"}}
                working_dir = temp_dir
            else:
                mounts = {temp_dir: {"bind": "/app/workspace", "mode": "rw"}}
                working_dir = "/app/workspace"
            
            lang_env = _get_language_env(target_file)
            image_to_use = lang_env["image"]
            
            repro_cmd = reproduction_command or lang_env["cmd"].format(file=target_file)
            
            # Setup container command with optional dependency installation based on language
            setup_cmd = ""
            if lang_env["ext"] == ".py":
                setup_cmd = "if [ -f requirements.txt ]; then pip install --disable-pip-version-check -r requirements.txt || true; fi;"
            elif lang_env["ext"] in [".js", ".ts"]:
                setup_cmd = "if [ -f package.json ]; then npm install || true; fi;"
                
            container_cmd = ["/bin/sh", "-c", f"{setup_cmd} {repro_cmd}"]
        else:
            lang_env = _get_language_env(target_file)
            image_to_use = lang_env["image"]
            filename = f"script{lang_env['ext']}"
            temp_path = os.path.join(temp_dir, filename)
            
            with open(temp_path, "w", encoding="utf-8") as f:
                f.write(code)
                
            if settings.is_local:
                mounts = {"sandbox_workspaces": {"bind": "/sandbox", "mode": "ro"}}
                run_cmd = f"cd {temp_dir} && " + lang_env["cmd"].format(file=filename)
            else:
                mounts = {temp_path: {"bind": f"/app/{filename}", "mode": "ro"}}
                run_cmd = lang_env["cmd"].format(file=f"/app/{filename}")
                
            container_cmd = ["/bin/sh", "-c", run_cmd]

        container = client.containers.run(
            image=image_to_use,
            command=container_cmd,
            volumes=mounts,
            working_dir=working_dir,
            network_mode=settings.sandbox_network_mode,
            mem_limit=settings.sandbox_mem_limit,
            nano_cpus=settings.sandbox_nano_cpus,
            detach=True,
            remove=False,
        )

        try:
            result = container.wait(timeout=settings.sandbox_timeout_seconds)
            exit_code = result.get("StatusCode", -1)
            stdout = container.logs(stdout=True, stderr=False)
            stderr = container.logs(stdout=False, stderr=True)
            stdout_str = stdout.decode("utf-8", errors="replace") if stdout else ""
            stderr_str = stderr.decode("utf-8", errors="replace") if stderr else ""
        except Exception as wait_exc:
            logger.error(f"Container wait error or timeout: {wait_exc}")
            container.kill()
            exit_code = -1
            stdout_str = ""
            stderr_str = f"Execution timed out or failed to wait: {wait_exc}"

    except docker.errors.ImageNotFound:
        logger.error(f"Sandbox image {image_to_use} not found.")
        return -1, "", f"Sandbox image '{image_to_use}' not found locally. Please run 'docker pull {image_to_use}'."
    except Exception as e:
        logger.error(f"Docker sandbox execution failed: {e}")
        return -1, "", str(e)
    finally:
        if container is not None:
            try:
                container.remove(force=True)
            except Exception as e:
                logger.warning(f"Failed to remove container: {e}")
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass

    return exit_code, stdout_str, stderr_str


# ── Public async entry point ──────────────────────────────────────────────

async def execute_in_sandbox(
    code: str,
    docker_client=None,
    project_path: str = "",
    reproduction_command: str = "",
    target_file: str = ""
) -> Tuple[int, str, str]:
    """
    Async wrapper for sandbox execution.
    Dispatches to either Docker or subprocess based on SANDBOX_MODE setting.
    Cloud environments automatically fall back to subprocess since Docker-in-Docker
    is not available on platforms like Render/Heroku.
    Returns (exit_code, stdout, stderr).
    """
    settings = get_settings()
    mode = settings.sandbox_mode

    # Cloud platforms (Render, Heroku, etc.) don't support Docker-in-Docker.
    # Auto-fallback to subprocess to prevent silent sandbox failures.
    if settings.is_cloud and mode == "docker":
        logger.info("Cloud environment detected — auto-falling back to subprocess sandbox.")
        mode = "subprocess"

    if mode == "docker":
        logger.info("Dispatching code to Docker sandbox...")
        return await asyncio.to_thread(
            _run_docker_sandbox, code, project_path,
            reproduction_command, target_file
        )
    else:
        logger.info("Dispatching code to subprocess sandbox...")
        return await asyncio.to_thread(
            _run_subprocess_sandbox, code, project_path,
            reproduction_command, target_file
        )

