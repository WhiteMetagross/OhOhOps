import os
import tempfile

import httpx


def main():
    api_base = os.getenv("OHOHOPS_API_BASE_URL", "http://127.0.0.1:8000")
    api_key = os.getenv("OHOHOPS_API_KEY", "ohohops-dev-key")

    with tempfile.TemporaryDirectory() as project_path:
        payload = {
            "target_file": "service.py",
            "logs": ["FATAL CRASH: test incident"],
            "project_path": project_path,
            "reproduction_command": "python service.py",
        }
        headers = {"Authorization": f"Bearer {api_key}"}
        with httpx.stream(
            "POST",
            f"{api_base}/api/v1/graph/run/stream",
            json=payload,
            headers=headers,
            timeout=120.0,
        ) as response:
            response.raise_for_status()
            completed = False
            for line in response.iter_lines():
                if line:
                    print(line)
                if line.startswith("event: complete"):
                    completed = True

        if not completed:
            raise SystemExit("Stream closed without a complete event")


if __name__ == "__main__":
    main()
