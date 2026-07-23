import secrets
import hashlib
import logging
from typing import Optional, List, Dict, Any

from app.services.ledger import Ledger

logger = logging.getLogger("ohohops.api_keys")

class ApiKeyService:
    def __init__(self, ledger: Ledger):
        self.ledger = ledger

    def _hash_key(self, raw_key: str) -> str:
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    async def generate_key(self, namespace: str, label: str = "") -> str:
        """Generates a new oh_ops_ key, persists the hash, and returns the raw key."""
        raw_token = secrets.token_urlsafe(32)
        raw_key = f"oh_ops_{raw_token}"
        key_hash = self._hash_key(raw_key)

        try:
            async with self.ledger._pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO api_keys (key_hash, namespace, label)
                    VALUES ($1, $2, $3);
                    """,
                    key_hash, namespace, label
                )
            logger.info(f"Generated new API key for namespace '{namespace}'")
            return raw_key
        except Exception as e:
            logger.error(f"Failed to generate API key: {e}")
            raise

    async def resolve_key(self, raw_key: str) -> Optional[str]:
        """Resolves a raw key to its namespace, updating last_used_at. Returns None if invalid or revoked."""
        if not raw_key.startswith("oh_ops_"):
            return None

        key_hash = self._hash_key(raw_key)
        
        try:
            async with self.ledger._pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT namespace, revoked FROM api_keys WHERE key_hash = $1
                    """,
                    key_hash
                )
                
                if row and not row["revoked"]:
                    # Update last_used_at asynchronously
                    await conn.execute(
                        "UPDATE api_keys SET last_used_at = NOW() WHERE key_hash = $1",
                        key_hash
                    )
                    return row["namespace"]
            return None
        except Exception as e:
            logger.error(f"Failed to resolve API key: {e}")
            return None

    async def list_keys(self) -> List[Dict[str, Any]]:
        """Lists metadata for all API keys (never returns raw keys)."""
        try:
            async with self.ledger._pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT id, namespace, label, created_at, revoked, last_used_at 
                    FROM api_keys ORDER BY created_at DESC
                    """
                )
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to list API keys: {e}")
            return []
            
    async def revoke_key(self, key_id: str) -> bool:
        """Revokes an API key by ID."""
        try:
            async with self.ledger._pool.acquire() as conn:
                result = await conn.execute(
                    "UPDATE api_keys SET revoked = TRUE WHERE id = $1::uuid",
                    key_id
                )
                return result == "UPDATE 1"
        except Exception as e:
            logger.error(f"Failed to revoke API key: {e}")
            return False
