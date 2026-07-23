import logging
import uuid
from fastapi import APIRouter, Request, BackgroundTasks, Depends

from app.core.schemas import TelemetryIngestPayload, OperationalLogEntry
from app.security.auth import verify_api_key

logger = logging.getLogger("ohohops.api.telemetry")
router = APIRouter()

# Anomaly thresholds — only fire the repair pipeline if these are breached
CPU_THRESHOLD = 90.0   # percent
MEM_THRESHOLD = 90.0   # percent
ERROR_RATE_THRESHOLD = 0.1  # 10%


@router.post("/ingest", dependencies=[Depends(verify_api_key)])
async def ingest_telemetry(
    request: Request,
    payload: TelemetryIngestPayload,
    background_tasks: BackgroundTasks,
    auth_context=Depends(verify_api_key),
):
    """
    Cloud-managed telemetry webhook. Receives metric payloads from the client daemon.
    Logs all metrics to the ledger. Only triggers an autonomous repair run if
    anomaly thresholds are breached, to avoid overloading the server on every ping.
    """
    namespace = auth_context.namespace
    logger.info(
        f"Telemetry from namespace={namespace} | "
        f"CPU={payload.cpu}% MEM={payload.mem}% ERR={payload.error_rate}"
    )

    # Always log the metric to the ledger
    ledger = getattr(request.app.state, "ledger", None)
    if ledger:
        entry = OperationalLogEntry(
            event_source="daemon/telemetry",
            agent_action="telemetry_ingest",
            execution_payload=(
                f"namespace={namespace} cpu={payload.cpu} "
                f"mem={payload.mem} error_rate={payload.error_rate}"
            ),
            execution_status="ok",
        )
        try:
            await ledger.log_event(entry)
        except Exception as e:
            logger.warning(f"Failed to log telemetry to ledger: {e}")

    # Check if anomaly thresholds are breached
    is_anomaly = (
        payload.cpu > CPU_THRESHOLD
        or payload.mem > MEM_THRESHOLD
        or payload.error_rate > ERROR_RATE_THRESHOLD
    )

    if is_anomaly and payload.logs:
        logger.warning(
            f"Anomaly detected for namespace={namespace}! "
            f"CPU={payload.cpu}% MEM={payload.mem}% ERR={payload.error_rate} — queuing repair."
        )
        try:
            from app.services.graph_runner import execute_repair
            run_id = "telemetry_" + str(uuid.uuid4())
            
            # Use target_file from daemon if provided, else AUTO_DETECT
            target = payload.target_file or "AUTO_DETECT"
            
            background_tasks.add_task(
                execute_repair,
                app=request.app,
                target_file=target,
                logs=payload.logs,
                run_id=run_id,
                event_source="daemon/telemetry",
                project_path="",
                reproduction_command=payload.reproduction_command,
                namespace=namespace,
                source_code=payload.source_code,
            )
            return {
                "status": "anomaly_detected",
                "message": "Anomaly thresholds breached. Repair cycle queued.",
                "run_id": run_id,
            }
        except Exception as e:
            logger.error(f"Failed to queue repair task: {e}", exc_info=True)

    return {"status": "ok", "message": "Telemetry received and logged."}
