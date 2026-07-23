import logging
from typing import List

from fastapi import APIRouter, Request, Depends, Query

from app.core.schemas import OperationalLogEntry
from app.security.auth import verify_api_key
from app.core.limiter import limiter

logger = logging.getLogger("ohohops.api.ledger")
router = APIRouter()


@router.get(
    "/ledger/logs",
    response_model=List[OperationalLogEntry],
    dependencies=[Depends(verify_api_key)],
)
@limiter.limit("30/minute")
async def list_operational_logs(
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
) -> List[OperationalLogEntry]:
    """Return the most recent operational-ledger entries (run history).

    The ledger is observability, not critical-path: if it is unconfigured or
    unreachable we return an empty list rather than erroring, so the dashboard
    simply shows 'no history yet' instead of breaking.
    """
    ledger = getattr(request.app.state, "ledger", None)
    if ledger is None:
        return []
    return await ledger.fetch_recent(limit=limit)
