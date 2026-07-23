import asyncio
import logging
import os
import shutil
import stat
import time
import zipfile
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse
from fastapi import APIRouter, Request, HTTPException, Depends, UploadFile, File, Form
from pydantic import BaseModel

from app.core.schemas import IngestRequest, IngestResponse, OperationalLogEntry

class GitHubIngestRequest(BaseModel):
    github_url: str
    namespace: str | None = None
from app.services.ingestion import ingest_directory
from app.services.vectorstore import get_vectorstore_service
from app.security.auth import verify_api_key
from app.core.config import get_settings
from app.core.limiter import limiter

logger = logging.getLogger("ohohops.api.ingest")
router = APIRouter()

@router.post("/ingest", response_model=IngestResponse, dependencies=[Depends(verify_api_key)])
@limiter.limit("2/minute")
async def ingest_codebase(request: Request, payload: IngestRequest):
    """
    Ingests a local directory, splitting the code into language-aware chunks
    and upserting them into the Pinecone vectorstore.
    """
    start_time = time.perf_counter()
    
    # 1. Read and chunk the directory
    try:
        chunks = await ingest_directory(payload.directory_path)
    except ValueError as ve:
        # Directory not found
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error("Ingestion chunking failed", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to ingest directory: {e}")
        
    if not chunks:
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        return IngestResponse(files_processed=0, chunks_indexed=0, elapsed_ms=elapsed_ms)

    # 2. Upsert chunks into VectorStore
    try:
        vectorstore_service = get_vectorstore_service()
        # Pass namespace if provided
        await vectorstore_service.aupsert_documents(chunks, namespace=payload.namespace)
    except Exception as e:
        logger.error("Vectorstore upsert failed", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to upsert chunks: {e}")
        
    elapsed_ms = int((time.perf_counter() - start_time) * 1000)
    unique_files = len(set(chunk.metadata.get("path") for chunk in chunks if chunk.metadata.get("path")))
    
    response_data = IngestResponse(
        files_processed=unique_files,
        chunks_indexed=len(chunks),
        elapsed_ms=elapsed_ms
    )
    
    # 3. Log to operational ledger
    ledger = getattr(request.app.state, "ledger", None)
    if ledger:
        entry = OperationalLogEntry(
            event_source="api/v1/ingest",
            agent_action="ingest_codebase",
            execution_payload=f"directory: {payload.directory_path} | namespace: {payload.namespace}",
            execution_status="success",
            compute_latency_ms=elapsed_ms
        )
        # Log asynchronously (awaited because it uses asyncpg and is very fast)
        await ledger.log_event(entry)
        
    return response_data

@router.get("/ingest/files", dependencies=[Depends(verify_api_key)])
@limiter.limit("30/minute")
async def list_ingested_files(request: Request, namespace: str = None):
    """
    Returns a list of unique file paths currently ingested in the given namespace.
    """
    try:
        vectorstore_service = get_vectorstore_service()
        files = await vectorstore_service.aget_unique_files(namespace=namespace)
        return {"files": files}
    except Exception as e:
        logger.error("Failed to list ingested files", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

WORKSPACE_BASE = os.path.join(os.getcwd(), "workspaces")

def get_workspace_dir(namespace: str | None) -> str:
    ns = namespace or "default"
    ns = "".join(c for c in ns if c.isalnum() or c in ("-", "_")) or "default"
    return os.path.join(WORKSPACE_BASE, ns)


def _extract_zip_safely(archive: zipfile.ZipFile, destination: str) -> None:
    root = Path(destination).resolve()
    for member in archive.infolist():
        normalized_name = member.filename.replace("\\", "/")
        member_path = PurePosixPath(normalized_name)
        mode = member.external_attr >> 16
        if (
            member_path.is_absolute()
            or ".." in member_path.parts
            or stat.S_ISLNK(mode)
        ):
            raise ValueError(f"Unsafe ZIP entry: {member.filename}")

        resolved = (root / Path(*member_path.parts)).resolve()
        if os.path.commonpath((str(root), str(resolved))) != str(root):
            raise ValueError(f"Unsafe ZIP entry: {member.filename}")

    archive.extractall(root)


def _validate_github_url(value: str) -> str:
    parsed = urlparse(value)
    if (
        parsed.scheme != "https"
        or parsed.hostname not in {"github.com", "www.github.com"}
        or parsed.username
        or parsed.password
        or not parsed.path.strip("/")
    ):
        raise ValueError("GitHub URL must be an HTTPS github.com repository URL")
    return value


@router.post("/ingest/upload", response_model=IngestResponse, dependencies=[Depends(verify_api_key)])
@limiter.limit("2/minute")
async def ingest_upload(request: Request, file: UploadFile = File(...), namespace: str = Form(None)):
    """Ingests a ZIP file containing codebase and saves it to a persistent workspace."""
    start_time = time.perf_counter()
    ns_dir = get_workspace_dir(namespace)
    
    try:
        if os.path.exists(ns_dir):
            def remove_readonly(func, path, _):
                os.chmod(path, stat.S_IWRITE)
                func(path)
            shutil.rmtree(ns_dir, onerror=remove_readonly)
        os.makedirs(ns_dir, exist_ok=True)

        zip_path = os.path.join(ns_dir, "upload.zip")
        with open(zip_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        
        extract_dir = os.path.join(ns_dir, "codebase")
        os.makedirs(extract_dir, exist_ok=True)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            _extract_zip_safely(zip_ref, extract_dir)
            
        os.remove(zip_path) # cleanup zip

        chunks = await ingest_directory(extract_dir)
        if not chunks:
            return IngestResponse(files_processed=0, chunks_indexed=0, elapsed_ms=int((time.perf_counter() - start_time) * 1000))
        
        vectorstore_service = get_vectorstore_service()
        await vectorstore_service.aupsert_documents(chunks, namespace=namespace)
        
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        unique_files = len(set(chunk.metadata.get("path") for chunk in chunks if chunk.metadata.get("path")))
        
        ledger = getattr(request.app.state, "ledger", None)
        if ledger:
            await ledger.log_event(OperationalLogEntry(event_source="api/v1/ingest/upload", agent_action="ingest_upload", execution_payload=f"filename: {file.filename} | namespace: {namespace}", execution_status="success", compute_latency_ms=elapsed_ms))
        
        return IngestResponse(files_processed=unique_files, chunks_indexed=len(chunks), elapsed_ms=elapsed_ms)
    except Exception as e:
        logger.error("ZIP ingestion failed", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to ingest zip: {e}")

@router.post("/ingest/github", response_model=IngestResponse, dependencies=[Depends(verify_api_key)])
@limiter.limit("2/minute")
async def ingest_github(request: Request, payload: GitHubIngestRequest):
    """Ingests a GitHub repository and saves it to a persistent workspace."""
    start_time = time.perf_counter()
    ns_dir = get_workspace_dir(payload.namespace)
    
    try:
        github_url = _validate_github_url(payload.github_url)
        if os.path.exists(ns_dir):
            def remove_readonly(func, path, _):
                os.chmod(path, stat.S_IWRITE)
                func(path)
            shutil.rmtree(ns_dir, onerror=remove_readonly)
        
        extract_dir = os.path.join(ns_dir, "codebase")
        os.makedirs(ns_dir, exist_ok=True)
        
        env = os.environ.copy()
        env["GIT_TERMINAL_PROMPT"] = "0"
        github_token = get_settings().github_token
        if github_token:
            env.update(
                {
                    "GIT_CONFIG_COUNT": "1",
                    "GIT_CONFIG_KEY_0": "http.extraHeader",
                    "GIT_CONFIG_VALUE_0": f"Authorization: Bearer {github_token}",
                }
            )
        process = await asyncio.create_subprocess_exec(
            "git",
            "clone",
            "--depth",
            "1",
            "--",
            github_url,
            extract_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        _, stderr = await process.communicate()
        if process.returncode != 0:
            error = stderr.decode("utf-8", errors="replace").strip()
            raise ValueError(f"Git clone failed: {error}")
            
        chunks = await ingest_directory(extract_dir)
        if not chunks:
            return IngestResponse(files_processed=0, chunks_indexed=0, elapsed_ms=int((time.perf_counter() - start_time) * 1000))
            
        vectorstore_service = get_vectorstore_service()
        await vectorstore_service.aupsert_documents(chunks, namespace=payload.namespace)
        
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        unique_files = len(set(chunk.metadata.get("path") for chunk in chunks if chunk.metadata.get("path")))
        
        ledger = getattr(request.app.state, "ledger", None)
        if ledger:
            await ledger.log_event(OperationalLogEntry(event_source="api/v1/ingest/github", agent_action="ingest_github", execution_payload=f"url: {payload.github_url} | namespace: {payload.namespace}", execution_status="success", compute_latency_ms=elapsed_ms))
            
        return IngestResponse(files_processed=unique_files, chunks_indexed=len(chunks), elapsed_ms=elapsed_ms)
    except Exception as e:
        logger.error("GitHub ingestion failed", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to ingest github: {e}")
