import io
import zipfile
from unittest.mock import AsyncMock


AUTH = {"Authorization": "Bearer ohohops-dev-key"}


def test_system_and_simulation_endpoints(client):
    mode = client.get("/api/v1/system/mode")
    simulation = client.post("/api/v1/anomaly/simulate")

    assert mode.status_code == 200
    assert mode.json()["deployment_mode"] == "local"
    assert simulation.status_code == 200
    assert simulation.json()["telemetry"][-1]["isAnomaly"] is True


def test_context_stream_endpoint(client):
    response = client.post(
        "/api/v1/context/query",
        json={"prompt": "Where is retry routing?", "namespace": "test"},
        headers=AUTH,
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: message" in response.text
    assert "event: done" in response.text


def test_directory_ingestion_and_file_listing(
    client,
    tmp_path,
    fake_vectorstore,
):
    source = tmp_path / "service.py"
    source.write_text("def healthy():\n    return True\n", encoding="utf-8")
    fake_vectorstore.aget_unique_files = AsyncMock(
        return_value=["service.py"]
    )

    ingested = client.post(
        "/api/v1/ingest",
        json={"directory_path": str(tmp_path), "namespace": "test"},
        headers=AUTH,
    )
    files = client.get(
        "/api/v1/ingest/files?namespace=test",
        headers=AUTH,
    )

    assert ingested.status_code == 200
    assert ingested.json()["files_processed"] == 1
    assert ingested.json()["chunks_indexed"] >= 1
    assert files.status_code == 200
    assert files.json() == {"files": ["service.py"]}


def test_zip_ingestion_endpoint(client, tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.api.v1.ingest.WORKSPACE_BASE",
        str(tmp_path / "workspaces"),
    )
    archive_bytes = io.BytesIO()
    with zipfile.ZipFile(archive_bytes, "w") as archive:
        archive.writestr("app/main.py", "print('healthy')\n")
    archive_bytes.seek(0)

    response = client.post(
        "/api/v1/ingest/upload",
        files={"file": ("source.zip", archive_bytes, "application/zip")},
        data={"namespace": "upload-test"},
        headers=AUTH,
    )

    assert response.status_code == 200
    assert response.json()["files_processed"] == 1


def test_key_endpoints(client, monkeypatch):
    monkeypatch.setattr(
        "app.api.v1.keys.ApiKeyService.generate_key",
        AsyncMock(return_value="oh_ops_test"),
    )
    monkeypatch.setattr(
        "app.api.v1.keys.ApiKeyService.list_keys",
        AsyncMock(return_value=[{"namespace": "production"}]),
    )

    verified = client.get("/api/v1/keys/verify", headers=AUTH)
    generated = client.post(
        "/api/v1/keys",
        json={"namespace": "production", "label": "daemon"},
        headers=AUTH,
    )
    listed = client.get("/api/v1/keys", headers=AUTH)

    assert verified.json() == {"valid": True, "namespace": "admin"}
    assert generated.json()["raw_key"] == "oh_ops_test"
    assert listed.json() == [{"namespace": "production"}]


def test_telemetry_and_deployment_endpoints(client, monkeypatch):
    repair = AsyncMock()
    monkeypatch.setattr(
        "app.services.graph_runner.execute_repair",
        repair,
    )

    telemetry = client.post(
        "/api/v1/telemetry/ingest",
        json={
            "cpu": 99,
            "mem": 20,
            "error_rate": 0,
            "logs": ["crash"],
            "target_file": "service.py",
        },
        headers=AUTH,
    )
    pending = client.get("/api/v1/deployments/pending", headers=AUTH)
    acknowledged = client.post(
        "/api/v1/deployments/ack",
        json={
            "patch_id": "00000000-0000-0000-0000-000000000001",
            "status": "restarted",
            "stderr": "",
        },
        headers=AUTH,
    )

    assert telemetry.status_code == 200
    assert telemetry.json()["status"] == "anomaly_detected"
    assert repair.await_count == 1
    assert pending.json() == {"patches": []}
    assert acknowledged.json() == {"status": "ok"}
