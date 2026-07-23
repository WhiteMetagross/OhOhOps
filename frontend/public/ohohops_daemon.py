import argparse
import time
import subprocess
import requests
import psutil
import sys
import os
import threading
from collections import deque

class DaemonCircuitBreaker:
    def __init__(self, max_failures=3, time_window=60):
        self.max_failures = max_failures
        self.time_window = time_window
        self.failure_timestamps = []

    def record_failure(self):
        now = time.time()
        self.failure_timestamps.append(now)
        self.failure_timestamps = [t for t in self.failure_timestamps if now - t <= self.time_window]

    def is_open(self):
        now = time.time()
        self.failure_timestamps = [t for t in self.failure_timestamps if now - t <= self.time_window]
        return len(self.failure_timestamps) >= self.max_failures

    def reset(self):
        self.failure_timestamps.clear()

class ProcessSupervisor:
    def __init__(self, command: str, cwd: str = None):
        self.command = command
        self.cwd = cwd
        self.process = None
        self.stderr_lines = deque(maxlen=100)
        self._stop_event = threading.Event()
        self.crashed = False

    def start(self):
        self.crashed = False
        self._stop_event.clear()
        self.stderr_lines.clear()
        print(f"Starting supervised process: {self.command}")
        
        self.process = subprocess.Popen(
            self.command,
            shell=True,
            stdout=subprocess.DEVNULL, # Focus on errors for anomalies
            stderr=subprocess.PIPE,
            text=True,
            cwd=self.cwd
        )
        
        def _read_stderr():
            for line in self.process.stderr:
                if line.strip():
                    self.stderr_lines.append(line.strip())
            
            self.process.wait()
            if self.process.returncode != 0 and not self._stop_event.is_set():
                self.crashed = True
                print(f"\nSupervised process crashed with exit code {self.process.returncode}!")
        
        self.monitor_thread = threading.Thread(target=_read_stderr, daemon=True)
        self.monitor_thread.start()

    def stop(self):
        self._stop_event.set()
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
        print("Supervised process stopped.")

    def restart(self, new_command=None):
        if new_command:
            self.command = new_command
        self.stop()
        self.start()

    def get_crash_logs(self):
        if self.crashed:
            logs = list(self.stderr_lines)
            self.crashed = False
            self.stderr_lines.clear()
            return logs
        return None

def apply_patch(project_dir: str, target_file: str, patch_code: str):
    if not project_dir:
        print("ERROR: Cannot apply patch: --project-dir not provided.")
        return None
        
    rel_path = target_file
    if os.path.isabs(rel_path):
        rel_path = os.path.relpath(rel_path, project_dir)
        if rel_path.startswith(".."):
            basename = os.path.basename(target_file)
            rel_path = basename

    target_path = os.path.join(project_dir, rel_path)
    
    project_root = os.path.abspath(project_dir)
    target_root = os.path.abspath(target_path)
    if os.path.commonpath((project_root, target_root)) != project_root:
        print(f"ERROR: Security violation: Path {target_path} is outside project dir!")
        return None

    if not os.path.exists(target_path):
        basename = os.path.basename(rel_path)
        found = False
        for root, _, files in os.walk(project_dir):
            if basename in files:
                target_path = os.path.join(root, basename)
                found = True
                break
        if not found:
            print(f"ERROR: Could not locate file {basename} in project directory.")
            return None

    try:
        backup_path = f"{target_path}.bak"
        if os.path.exists(target_path):
            with open(target_path, 'r', encoding='utf-8') as src, open(backup_path, 'w', encoding='utf-8') as dst:
                dst.write(src.read())
                
        with open(target_path, 'w', encoding='utf-8') as f:
            f.write(patch_code)
        print(f"OK: Applied patch to {target_path} (backup saved as .bak)")
        return {"target": target_path, "backup": backup_path}
    except Exception as e:
        print(f"ERROR: Failed to write patch: {e}")
        return None

def rollback_patch(transaction) -> bool:
    if not transaction:
        return False
    try:
        backup_path = transaction["backup"]
        target_path = transaction["target"]
        if not os.path.exists(backup_path):
            print(f"ERROR: Rollback backup missing: {backup_path}")
            return False
        os.replace(backup_path, target_path)
        print(f"OK: Automatic rollback restored {target_path}")
        return True
    except Exception as e:
        print(f"ERROR: Automatic rollback failed: {e}")
        return False

def finalize_patch(transaction):
    if transaction and os.path.exists(transaction["backup"]):
        os.remove(transaction["backup"])

def main():
    parser = argparse.ArgumentParser(description="OhOhOps SaaS Bidirectional Daemon")
    parser.add_argument("--api-key", required=True, help="Your oh_ops_ API key")
    parser.add_argument("--server-url", required=True, help="The Render backend URL")
    parser.add_argument("--project-dir", type=str, help="Absolute path to the user's local project directory (needed for patching)")
    parser.add_argument("--watch", type=str, help="A command to monitor, e.g. 'python buggy_script.py'")
    parser.add_argument("--simulate-anomaly", action="store_true", help="Send a fake anomaly on startup.")
    parser.add_argument("--no-auto-restart", action="store_true", help="Apply patch but do not restart watched process.")
    args = parser.parse_args()

    print("Starting OhOhOps Daemon...")
    print(f"Connected to: {args.server_url}")
    if args.project_dir:
        print(f"Project Dir: {args.project_dir}")
    else:
        print("WARNING: No --project-dir provided. Daemon will report telemetry but cannot apply patches.")
    
    supervisor = None
    circuit_breaker = DaemonCircuitBreaker()
    
    if args.watch:
        supervisor = ProcessSupervisor(args.watch, cwd=args.project_dir)
        supervisor.start()

    print("Press Ctrl+C to stop.\n")

    anomaly_sent = False
    
    while True:
        try:
            # 1. Gather Telemetry
            cpu = psutil.cpu_percent(interval=1)
            mem = psutil.virtual_memory().percent
            logs_to_send = []

            # 2. Check for process crash
            if supervisor:
                crash_logs = supervisor.get_crash_logs()
                if crash_logs:
                    circuit_breaker.record_failure()
                    if circuit_breaker.is_open():
                        print("\n[CIRCUIT BREAKER OPEN] Too many crashes in 60s! Manual intervention required. Suppressing further anomalies.")
                    else:
                        print("\nSENDING ANOMALY: crash logs from watched command...")
                        logs_to_send = crash_logs
                        anomaly_sent = True

            # Fake anomaly fallback
            if args.simulate_anomaly and not anomaly_sent and not logs_to_send:
                print("\nSIMULATING ANOMALY: sending spike + crash logs...")
                logs_to_send = [
                    "Traceback (most recent call last):",
                    '  File "buggy_data_processor.py", line 19, in process_data',
                    "TypeError: unsupported operand type(s) for +=: 'int' and 'str'",
                ]
                anomaly_sent = True

            # Extract target file from crash traceback if available
            crashed_file = ""
            source_code = ""
            if logs_to_send:
                import re
                file_matches = re.findall(r'File "([^"]+)"', "\n".join(logs_to_send))
                if file_matches:
                    crashed_file = os.path.basename(file_matches[-1])
                    if args.project_dir:
                        # Try to read the file from the project directory
                        for root, _, files in os.walk(args.project_dir):
                            if crashed_file in files:
                                try:
                                    with open(os.path.join(root, crashed_file), 'r', encoding='utf-8') as f:
                                        source_code = f.read()
                                    break
                                except Exception:
                                    pass

            payload = {
                "cpu": 98.5 if logs_to_send else cpu,
                "mem": 94.2 if logs_to_send else mem,
                "error_rate": 1.0 if logs_to_send else 0.0,
                "logs": logs_to_send,
                "reproduction_command": (args.watch or "") if logs_to_send else "",
                "target_file": crashed_file,
                "source_code": source_code,
            }

            # 3. Send Telemetry
            headers = {"Authorization": f"Bearer {args.api_key}"}
            res = requests.post(f"{args.server_url}/api/v1/telemetry/ingest", json=payload, headers=headers, timeout=30)
            if res.ok:
                data = res.json()
                if data.get("status") == "anomaly_detected":
                    print(f"\n[ANOMALY] Backend queued autonomous repair! run_id={data.get('run_id')}")
                elif not logs_to_send:
                    sys.stdout.write(f"\r[OK] Telemetry sent | CPU: {cpu}% | RAM: {mem}%  ")
                    sys.stdout.flush()
            else:
                print(f"\n[ERROR] Backend rejected telemetry: {res.status_code}")

            # 4. Poll for Patches
            if args.project_dir:
                poll_res = requests.get(f"{args.server_url}/api/v1/deployments/pending", headers=headers, timeout=30)
                if poll_res.ok:
                    patches = poll_res.json().get("patches", [])
                    for patch in patches:
                        print(f"\nReceived patch {patch['patch_id']} from cloud!")
                        
                        transaction = apply_patch(
                            args.project_dir,
                            patch["target_file"],
                            patch["patch_code"],
                        )
                        
                        status = "failed"
                        stderr_msg = ""
                        if transaction:
                            status = "applied"
                            if supervisor and not args.no_auto_restart:
                                if circuit_breaker.is_open():
                                    print("Circuit breaker is OPEN. Skipping auto-restart.")
                                    status = "circuit_breaker_open"
                                    stderr_msg = "Daemon circuit breaker open. Too many crashes."
                                else:
                                    print("Restarting watched process...")
                                    original_cmd = supervisor.command
                                    new_cmd = patch.get("reproduction_command") or supervisor.command
                                    supervisor.restart(new_cmd)
                                    
                                    # Brief health check to see if it immediately crashes
                                    time.sleep(3)
                                    if supervisor.crashed:
                                        print("ERROR: Process crashed immediately after restart!")
                                        crash_logs = supervisor.get_crash_logs()
                                        stderr_msg = "\n".join(crash_logs) if crash_logs else "Unknown crash"
                                        circuit_breaker.record_failure()
                                        if rollback_patch(transaction):
                                            supervisor.restart(original_cmd)
                                            time.sleep(3)
                                            status = (
                                                "rollback_unhealthy"
                                                if supervisor.crashed
                                                else "rolled_back"
                                            )
                                        else:
                                            status = "rollback_failed"
                                    else:
                                        print("OK: Process verified healthy.")
                                        status = "restarted"
                                        circuit_breaker.reset()
                                        finalize_patch(transaction)

                        ack_payload = {"patch_id": patch["patch_id"], "status": status, "stderr": stderr_msg}
                        ack_res = requests.post(f"{args.server_url}/api/v1/deployments/ack", json=ack_payload, headers=headers, timeout=30)
                        if ack_res.ok:
                            print(f"Acknowledged patch {patch['patch_id']} as {status}")
                
        except requests.exceptions.RequestException as e:
            pass # Suppress noisy connection errors if server is down temporarily
        except Exception as e:
            print(f"\n[WARNING] Daemon loop error: {e}")

        time.sleep(5)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nShutting down daemon.")
        sys.exit(0)
