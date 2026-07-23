import io
import os
import uuid
import zipfile

import httpx


API_BASE = os.getenv("OHOHOPS_API_BASE_URL", "http://127.0.0.1:8000")
API_KEY = os.getenv("OHOHOPS_API_KEY", "ohohops-test-key")
AUTH = {"Authorization": f"Bearer {API_KEY}"}
NAMESPACE = f"smoke-{uuid.uuid4().hex[:8]}"


def require_ok(response: httpx.Response) -> httpx.Response:
    response.raise_for_status()
    return response


def source_archive() -> io.BytesIO:
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w") as archive:
        archive.writestr(
            "buggy_server.py",
            "import math\nprint(math.sqrt(16))\n",
        )
    payload.seek(0)
    return payload


def main() -> None:
    with httpx.Client(base_url=API_BASE, timeout=180.0) as client:
        health = require_ok(client.get("/api/v1/health")).json()
        assert health["status"] == "ok", health
        assert health["dependencies"]["chroma"] == "ok"
        assert health["dependencies"]["docker"] == "ok"
        assert health["dependencies"]["ledger"] == "ok"

        require_ok(client.get("/api/v1/system/mode"))
        require_ok(client.post("/api/v1/anomaly/simulate"))
        require_ok(client.get("/api/v1/keys/verify", headers=AUTH))

        archive = source_archive()
        upload = require_ok(
            client.post(
                "/api/v1/ingest/upload",
                files={"file": ("source.zip", archive, "application/zip")},
                data={"namespace": NAMESPACE},
                headers=AUTH,
            )
        ).json()
        assert upload["files_processed"] == 1
        assert upload["chunks_indexed"] >= 1

        files = require_ok(
            client.get(
                "/api/v1/ingest/files",
                params={"namespace": NAMESPACE},
                headers=AUTH,
            )
        ).json()["files"]
        assert any(path.endswith("buggy_server.py") for path in files)

        with client.stream(
            "POST",
            "/api/v1/context/query",
            json={
                "prompt": "What does buggy_server.py print?",
                "namespace": NAMESPACE,
            },
            headers=AUTH,
        ) as response:
            require_ok(response)
            context_stream = "\n".join(response.iter_lines())
        assert "event: message" in context_stream
        assert "event: done" in context_stream

        project_path = f"/app/workspaces/{NAMESPACE}/codebase"
        with client.stream(
            "POST",
            "/api/v1/graph/run/stream",
            json={
                "target_file": "buggy_server.py",
                "logs": ["RuntimeError: smoke incident"],
                "project_path": project_path,
                "reproduction_command": "python buggy_server.py",
                "namespace": NAMESPACE,
            },
            headers=AUTH,
        ) as response:
            require_ok(response)
            graph_stream = "\n".join(response.iter_lines())
        assert "event: node_update" in graph_stream
        assert "event: complete" in graph_stream
        assert "sandbox_node" in graph_stream

        key = require_ok(
            client.post(
                "/api/v1/keys",
                json={"namespace": NAMESPACE, "label": "smoke"},
                headers=AUTH,
            )
        ).json()["raw_key"]
        assert key.startswith("oh_ops_")
        require_ok(client.get("/api/v1/keys", headers=AUTH))

        telemetry = require_ok(
            client.post(
                "/api/v1/telemetry/ingest",
                json={"cpu": 10, "mem": 20, "error_rate": 0, "logs": []},
                headers=AUTH,
            )
        ).json()
        assert telemetry["status"] == "ok"

        require_ok(client.get("/api/v1/deployments/pending", headers=AUTH))
        require_ok(client.get("/api/v1/ledger/logs", headers=AUTH))

    print("Full stack smoke passed")


if __name__ == "__main__":
    main()
