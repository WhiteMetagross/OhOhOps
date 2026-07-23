import logging
from fastapi import APIRouter, Request, Depends

from app.core.schemas import PendingDeploymentsResponse, AckPayload
from app.security.auth import verify_api_key

logger = logging.getLogger("ohohops.api.deployments")
router = APIRouter()

@router.get("/pending", response_model=PendingDeploymentsResponse, dependencies=[Depends(verify_api_key)])
async def get_pending(request: Request, auth_context=Depends(verify_api_key)):
    patch_store = getattr(request.app.state, "patch_store", None)
    if not patch_store:
        return {"patches": []}
        
    patches = await patch_store.poll(auth_context.namespace)
    return {"patches": patches}

@router.post("/ack", dependencies=[Depends(verify_api_key)])
async def acknowledge_patch(request: Request, payload: AckPayload, auth_context=Depends(verify_api_key)):
    patch_store = getattr(request.app.state, "patch_store", None)
    if not patch_store:
        return {"status": "error", "message": "PatchStore not initialized"}
        
    await patch_store.acknowledge(payload.patch_id, payload.status, payload.stderr)
    
    # Write to operational ledger so the dashboard shows the final status
    ledger = getattr(request.app.state, "ledger", None)
    if ledger:
        import json
        from app.core.schemas import OperationalLogEntry
        
        # If the daemon restarted it successfully, it's 'fixed' or 'restarted'.
        # If it failed, it's 'failed' or 'unhealthy'.
        display_status = "fixed" if payload.status == "restarted" else "failed"
        
        entry = OperationalLogEntry(
            event_source="daemon/ack",
            agent_action="autonomous_repair",
            execution_status=display_status,
            execution_payload=json.dumps({
                "patch_id": payload.patch_id,
                "deployment_status": payload.status,
                "sandbox_stderr": payload.stderr,
                "deployment_reason": f"Daemon reported status: {payload.status}"
            }),
            compute_latency_ms=0,
            token_consumption=0
        )
        try:
            await ledger.log_event(entry)
        except Exception as e:
            logger.warning(f"Failed to log ack to ledger: {e}")

    return {"status": "ok"}
