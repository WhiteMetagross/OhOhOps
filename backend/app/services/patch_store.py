import logging
from typing import List, Optional
import uuid
from datetime import datetime

import asyncpg

from app.core.schemas import PendingPatch

logger = logging.getLogger("ohohops.services.patch_store")

class PatchStore:
    def __init__(self, pool: Optional[asyncpg.Pool] = None):
        self._pool = pool
        self._memory_store: List[dict] = []  # Fallback for local mode without Supabase

    @classmethod
    def get_instance(cls, app_state) -> "PatchStore":
        """Get the singleton instance from app state, or create a mock one."""
        return getattr(app_state, "patch_store", None) or cls()

    async def enqueue(self, namespace: str, run_id: str, target_file: str, patch_code: str, reproduction_command: str) -> str:
        patch_id = str(uuid.uuid4())
        logger.info(f"Enqueueing patch {patch_id} for namespace {namespace}")
        
        if self._pool:
            try:
                async with self._pool.acquire() as conn:
                    await conn.execute(
                        """
                        INSERT INTO pending_deployments 
                        (patch_id, namespace, run_id, target_file, patch_code, reproduction_command, status)
                        VALUES ($1::uuid, $2, $3, $4, $5, $6, 'pending')
                        """,
                        patch_id, namespace, run_id, target_file, patch_code, reproduction_command
                    )
                return patch_id
            except Exception as e:
                logger.error(f"Failed to enqueue patch to DB: {e}")
                # Fall back to memory if db write fails (useful if db is down)
        
        # In-memory fallback
        self._memory_store.append({
            "patch_id": patch_id,
            "namespace": namespace,
            "run_id": run_id,
            "target_file": target_file,
            "patch_code": patch_code,
            "reproduction_command": reproduction_command,
            "created_at": datetime.now(),
            "status": "pending"
        })
        return patch_id

    async def poll(self, namespace: str) -> List[PendingPatch]:
        """Fetch pending patches and mark them as picked_up to prevent double-delivery."""
        patches = []
        
        if self._pool:
            try:
                async with self._pool.acquire() as conn:
                    # Fetch and update atomically (requires postgres returning clause)
                    rows = await conn.fetch(
                        """
                        UPDATE pending_deployments 
                        SET status = 'picked_up'
                        WHERE namespace IS NOT DISTINCT FROM $1 AND status = 'pending'
                        RETURNING patch_id, run_id, target_file, patch_code, reproduction_command, created_at, status
                        """,
                        namespace
                    )
                    
                    for row in rows:
                        patches.append(PendingPatch(
                            patch_id=str(row["patch_id"]),
                            run_id=row["run_id"],
                            target_file=row["target_file"],
                            patch_code=row["patch_code"],
                            reproduction_command=row["reproduction_command"] or "",
                            created_at=row["created_at"],
                            status=row["status"]
                        ))
                if patches:
                    return patches
            except Exception as e:
                logger.error(f"Failed to poll patches from DB: {e}")
                
        # In-memory fallback
        for patch in self._memory_store:
            if patch["namespace"] == namespace and patch["status"] == "pending":
                patch["status"] = "picked_up"
                patches.append(PendingPatch(**patch))
                
        return patches

    async def acknowledge(self, patch_id: str, status: str, stderr: str = "") -> None:
        """Update the final deployment status from the daemon."""
        logger.info(f"Acknowledging patch {patch_id} with status {status}")
        
        if self._pool:
            try:
                async with self._pool.acquire() as conn:
                    await conn.execute(
                        """
                        UPDATE pending_deployments
                        SET status = $1
                        WHERE patch_id = $2::uuid
                        """,
                        status, patch_id
                    )
                return
            except Exception as e:
                logger.error(f"Failed to ack patch in DB: {e}")
                
        # In-memory fallback
        for patch in self._memory_store:
            if patch["patch_id"] == patch_id:
                patch["status"] = status
                break

async def create_patch_store(ledger) -> PatchStore:
    pool = ledger._pool if ledger else None
    store = PatchStore(pool=pool)
    logger.info("PatchStore initialized")
    return store
