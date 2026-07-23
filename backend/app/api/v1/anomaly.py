import logging
from fastapi import APIRouter, Request, BackgroundTasks, Depends

from app.core.schemas import AnomalyPayload
from app.services.graph_runner import execute_repair
from app.security.auth import verify_webhook_signature

logger = logging.getLogger("ohohops.api.anomaly")
router = APIRouter()

@router.post("/trigger", dependencies=[Depends(verify_webhook_signature)])
async def trigger_anomaly(
    request: Request,
    payload: AnomalyPayload,
    background_tasks: BackgroundTasks
):
    """
    Webhook endpoint for external alerting tools (Datadog, PagerDuty, Sentry).
    Immediately acknowledges the alert with HTTP 200 to prevent webhook timeouts,
    and dispatches the autonomous LangGraph repair cycle into the background.
    """
    logger.warning(f"Received ANOMALY ALERT [{payload.alert_id}] for service '{payload.service_name}'")
    
    # Dispatch the repair process to the background
    background_tasks.add_task(
        execute_repair, 
        app=request.app, 
        target_file=payload.target_file, 
        logs=payload.logs, 
        run_id=payload.alert_id,
        event_source="api/v1/anomaly/trigger"
    )
    
    return {
        "status": "accepted",
        "message": "Anomaly received. Autonomous SRE repair dispatched in background.",
        "alert_id": payload.alert_id
    }

@router.post("/simulate")
async def simulate_outlier():
    """
    Simulates a proactive anomaly detection event and returns mock telemetry, 
    scorecard metrics, and a resolved incident payload for the UI.
    """
    import datetime
    
    now = datetime.datetime.now()
    telemetry = []
    # Generate 10 normal data points
    for i in range(10):
        t = now - datetime.timedelta(minutes=10 - i)
        telemetry.append({
            "timestamp": t.strftime("%H:%M"),
            "cpu": 30 + (i % 3) * 5,
            "errorRate": 1 + (i % 2),
            "isAnomaly": False
        })
    # Add anomaly data point
    telemetry.append({
        "timestamp": now.strftime("%H:%M"),
        "cpu": 98,
        "errorRate": 85,
        "isAnomaly": True
    })

    return {
        "telemetry": telemetry,
        "scorecard": {
            "faithfulness": 98.5,
            "contextRecall": 96.2,
            "tokenCost": 0.014,
            "latency": "1.8"
        },
        "incident": {
            "originalCode": "def process_data(data):\n    # Potential divide by zero\n    return 100 / len(data)",
            "proposedPatch": "def process_data(data):\n    if not data:\n        return 0\n    return 100 / len(data)",
            "securityPassed": True,
            "regexPassed": True
        }
    }
