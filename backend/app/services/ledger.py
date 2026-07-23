"""Operational ledger — durable audit trail in Postgres (Supabase).

Every meaningful agent action is recorded in the ``operational_logs`` table via a
non-blocking asyncpg connection pool. The ledger is observability, not part of the
critical path: if it is unconfigured or a write fails, we log a warning and carry
on rather than crashing an agent run.

Lifecycle:
    ledger = await Ledger.create(db_url)   # builds pool + ensures schema
    await ledger.log_event(entry)
    await ledger.close()
"""

from __future__ import annotations

from typing import Optional
from urllib.parse import quote

import asyncpg

from app.core.logging import get_logger
from app.core.schemas import OperationalLogEntry

logger = get_logger()


def _normalize_dsn(url: str) -> str:
    """Percent-encode the user/password in a Postgres URI.

    Supabase database passwords frequently contain characters (``@ : / +``) that
    are reserved in a URI's authority section. If pasted raw, the parser misreads
    the host/port (the classic "invalid literal for int" error). We re-encode the
    userinfo so any password works as-is.

    ``safe="%"`` preserves already-encoded sequences (``%40`` stays ``%40``) so we
    don't double-encode a string the user encoded themselves.
    """
    if "://" not in url:
        return url
    scheme, rest = url.split("://", 1)
    if "@" not in rest:
        return url
    # rsplit on the last '@' — the host section never contains '@', so anything
    # before it is the userinfo (which may itself contain '@' in the password).
    userinfo, hostpart = rest.rsplit("@", 1)
    if ":" in userinfo:
        user, password = userinfo.split(":", 1)  # split on first ':' = user:password
        userinfo_enc = f"{quote(user, safe='%')}:{quote(password, safe='%')}"
    else:
        userinfo_enc = quote(userinfo, safe="%")
    return f"{scheme}://{userinfo_enc}@{hostpart}"

# Exact schema from the system spec, made idempotent for repeated boots.
_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS operational_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    event_source VARCHAR(255) NOT NULL,
    agent_action VARCHAR(255),
    execution_payload TEXT,
    execution_status VARCHAR(50),
    token_consumption INT DEFAULT 0,
    compute_latency_ms INT DEFAULT 0,
    ragas_fidelity_score NUMERIC(4,3)
);
"""

_CREATE_API_KEYS_TABLE = """
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key_hash VARCHAR(64) UNIQUE NOT NULL,
    namespace VARCHAR(255) NOT NULL,
    label VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    revoked BOOLEAN DEFAULT FALSE,
    last_used_at TIMESTAMP WITH TIME ZONE
);
"""

_CREATE_PENDING_DEPLOYMENTS_TABLE = """
CREATE TABLE IF NOT EXISTS pending_deployments (
    patch_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    namespace VARCHAR(255) NOT NULL,
    run_id VARCHAR(255) NOT NULL,
    target_file VARCHAR(1024) NOT NULL,
    patch_code TEXT NOT NULL,
    reproduction_command VARCHAR(1024),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    status VARCHAR(50) DEFAULT 'pending'
);
"""

_INSERT = """
INSERT INTO operational_logs
    (event_source, agent_action, execution_payload, execution_status,
     token_consumption, compute_latency_ms, ragas_fidelity_score)
VALUES ($1, $2, $3, $4, $5, $6, $7);
"""

_SELECT_RECENT = """
SELECT id, timestamp, event_source, agent_action, execution_payload,
       execution_status, token_consumption, compute_latency_ms, ragas_fidelity_score
FROM operational_logs
ORDER BY timestamp DESC
LIMIT $1;
"""


class Ledger:
    """Thin async wrapper around an asyncpg pool for operational_logs."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    @classmethod
    async def create(cls, db_url: str) -> "Ledger":
        # statement_cache_size=0 keeps us compatible with Supabase's pgbouncer
        # pooler (transaction mode), which doesn't support prepared statements.
        pool = await asyncpg.create_pool(
            dsn=_normalize_dsn(db_url),
            min_size=1,
            max_size=5,
            statement_cache_size=0,
        )
        ledger = cls(pool)
        await ledger.ensure_schema()
        return ledger

    async def ensure_schema(self) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(_CREATE_TABLE)
            await conn.execute(_CREATE_API_KEYS_TABLE)
            await conn.execute(_CREATE_PENDING_DEPLOYMENTS_TABLE)
        logger.info("ledger schema ensured")

    async def log_event(self, entry: OperationalLogEntry) -> None:
        """Insert one audit record. Never raises — a ledger failure must not
        break an agent run; it is logged and swallowed."""
        try:
            async with self._pool.acquire() as conn:
                await conn.execute(
                    _INSERT,
                    entry.event_source,
                    entry.agent_action,
                    entry.execution_payload,
                    entry.execution_status,
                    entry.token_consumption,
                    entry.compute_latency_ms,
                    entry.ragas_fidelity_score,
                )
        except Exception as exc:  # noqa: BLE001 - observability is not critical-path
            logger.warning("ledger write failed", extra={"error": str(exc)})

    async def fetch_recent(self, limit: int = 20) -> list[OperationalLogEntry]:
        """Return the most recent audit records, newest first.

        Read side of the operational ledger that powers the dashboard's run
        history. Never raises — on failure it returns an empty list so the UI
        degrades gracefully rather than erroring."""
        try:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch(_SELECT_RECENT, limit)
        except Exception as exc:  # noqa: BLE001 - observability is not critical-path
            logger.warning("ledger read failed", extra={"error": str(exc)})
            return []

        return [
            OperationalLogEntry(
                id=str(row["id"]),
                timestamp=row["timestamp"].isoformat() if row["timestamp"] else None,
                event_source=row["event_source"],
                agent_action=row["agent_action"],
                execution_payload=row["execution_payload"],
                execution_status=row["execution_status"],
                token_consumption=row["token_consumption"] or 0,
                compute_latency_ms=row["compute_latency_ms"] or 0,
                ragas_fidelity_score=(
                    float(row["ragas_fidelity_score"])
                    if row["ragas_fidelity_score"] is not None
                    else None
                ),
            )
            for row in rows
        ]

    async def ping(self) -> bool:
        """Cheap readiness check for the health endpoint."""
        try:
            async with self._pool.acquire() as conn:
                await conn.execute("SELECT 1;")
            return True
        except Exception:  # noqa: BLE001
            return False

    async def close(self) -> None:
        await self._pool.close()


async def create_ledger(db_url: Optional[str]) -> Optional[Ledger]:
    """Build a Ledger if a URL is configured; return None (degraded) otherwise.
    Boot must survive a missing or unreachable database."""
    if not db_url:
        logger.info("ledger not configured (no SUPABASE_DB_URL)")
        return None
    try:
        ledger = await Ledger.create(db_url)
        logger.info("ledger initialized")
        return ledger
    except Exception as exc:  # noqa: BLE001
        logger.error("ledger init failed", extra={"error": str(exc)})
        return None
