import asyncio
import psutil
import logging
import uuid
from fastapi import FastAPI

from app.anomaly.detector import AnomalyDetector
from app.anomaly.log_counter import LogErrorCounter
from app.services.graph_runner import execute_repair

logger = logging.getLogger("ohohops.anomaly.telemetry")
detector = AnomalyDetector(contamination=0.05)

async def telemetry_loop(app: FastAPI):
    """
    Background worker that continuously samples system metrics.
    When the Isolation Forest flags an anomaly, it fires the repair graph.

    The three-dimensional telemetry vector is:
      1. cpu_usage    — psutil physical CPU utilisation (real)
      2. mem_usage    — psutil virtual memory utilisation (real)
      3. error_rate   — fraction of ERROR/CRITICAL log records in the last 60 s
                        (real, derived from the app's own structured logging via
                        LogErrorCounter rather than simulated with random.uniform)
    """
    logger.info("Starting background telemetry loop (PyOD IForest)...")
    
    # Initial CPU read to prime psutil (first call always returns 0.0)
    psutil.cpu_percent(interval=None)
    
    # Grab the singleton counter that was installed by lifespan
    log_counter = LogErrorCounter.get_instance()
    
    while True:
        try:
            # 1. Sample physical metrics
            cpu_usage = psutil.cpu_percent(interval=None)
            mem_usage = psutil.virtual_memory().percent
            
            # 2. Real application error rate: fraction of ERROR+ records in
            #    the last 60 seconds.  Returns 0.0 on clean startup (no window
            #    data yet), which is the correct conservative baseline.
            error_rate = log_counter.error_rate(window_seconds=60.0)
                
            # 3. Feed 3D vector into PyOD
            is_anomaly = detector.add_data_point(cpu_usage, mem_usage, error_rate)
            
            if is_anomaly:
                logger.warning(
                    f"ANOMALY DETECTED! CPU: {cpu_usage}%, "
                    f"Mem: {mem_usage}%, ErrRate: {error_rate:.3f}"
                )
                
                # 4. Trigger self-healing
                logs = [
                    f"SYSTEM ANOMALY TRIPPED: Elevated resource usage or error rate detected. "
                    f"CPU={cpu_usage:.1f}%, Mem={mem_usage:.1f}%, ErrRate={error_rate:.3f}"
                ]
                run_id = str(uuid.uuid4())
                
                logger.info("Proactive telemetry triggered repair cycle started.")
                
                # Run graph without awaiting so telemetry loop isn't blocked
                asyncio.create_task(
                    execute_repair(
                        app=app,
                        target_file="system_metrics",
                        logs=logs,
                        run_id=run_id,
                        event_source="background/telemetry"
                    )
                )
                
                # Sleep a bit longer after firing to avoid trigger storms
                await asyncio.sleep(30)
                
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Telemetry loop error: {e}")
            
        # Sample every 2 seconds
        await asyncio.sleep(2)
