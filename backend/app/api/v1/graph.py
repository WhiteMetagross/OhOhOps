import uuid
import time
import logging
from fastapi import APIRouter, Request, HTTPException, Depends
from sse_starlette.sse import EventSourceResponse

from app.core.schemas import GraphRunRequest, GraphRunResponse, GraphStreamEvent, new_agent_state
from app.services.graph_runner import execute_repair, record_ledger_entry, sre_orchestrator
from app.security.auth import verify_api_key
from app.core.limiter import limiter

logger = logging.getLogger("ohohops.api.graph")
router = APIRouter()

@router.post("/run", response_model=GraphRunResponse, dependencies=[Depends(verify_api_key)])
@limiter.limit("5/minute")
async def run_graph(request: Request, payload: GraphRunRequest, auth_context=Depends(verify_api_key)):
    if auth_context.namespace:
        payload.namespace = auth_context.namespace
    """
    Triggers a full execution of the autonomous SRE repair LangGraph.
    """
    run_id = str(uuid.uuid4())
    
    try:
        final_state = await execute_repair(
            app=request.app,
            target_file=payload.target_file,
            logs=payload.logs,
            run_id=run_id,
            event_source="api/v1/graph/run",
            project_path=payload.project_path,
            reproduction_command=payload.reproduction_command,
            namespace=payload.namespace,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    return GraphRunResponse(
        run_id=run_id,
        final_exit_code=final_state.get("execution_exit_code", -1),
        retry_count=final_state.get("retry_count", 0),
        security_clearance=final_state.get("security_clearance", False),
        proposed_patch=final_state.get("proposed_patch", "")
    )


@router.post("/run/stream", dependencies=[Depends(verify_api_key)])
@limiter.limit("5/minute")
async def stream_graph(request: Request, payload: GraphRunRequest, auth_context=Depends(verify_api_key)):
    if auth_context.namespace:
        payload.namespace = auth_context.namespace
    """
    Triggers the autonomous SRE LangGraph and yields an SSE stream of node updates.
    """
    run_id = str(uuid.uuid4())
    logger.info(f"Starting Graph Stream {run_id} for target file: {payload.target_file}")
    
    initial_state = new_agent_state(
        current_target_file=payload.target_file,
        discovered_logs=payload.logs,
        project_path=payload.project_path,
        reproduction_command=payload.reproduction_command,
        namespace=payload.namespace,
        run_id=run_id,
        patch_store=getattr(request.app.state, "patch_store", None)
    )
    
    async def event_generator():
        start_time = time.time()
        final_state = initial_state
        
        try:
            async for update in sre_orchestrator.astream(initial_state, stream_mode="updates"):
                # update is a dict: {node_name: delta_state}
                node_name, delta = next(iter(update.items()))
                
                # Merge the delta to keep our local final_state up to date.
                # messages and token_consumption use operator.add reducers in the
                # graph state, so we must accumulate them here too rather than
                # overwrite — otherwise the run total reflects only the last node.
                if "messages" in delta:
                    final_state["messages"].extend(delta["messages"])
                for k, v in delta.items():
                    if k == "messages":
                        continue
                    if k == "token_consumption":
                        final_state[k] = final_state.get(k, 0) + v
                    else:
                        final_state[k] = v
                
                event = GraphStreamEvent.from_delta(run_id, node_name, delta)
                yield {"event": "node_update", "data": event.model_dump_json()}
                
            elapsed_ms = int((time.time() - start_time) * 1000)
            
            # Send final complete event
            complete_event = GraphStreamEvent(
                event="complete", 
                run_id=run_id,
                state={
                    "active_node": "END",
                    "execution_exit_code": final_state.get("execution_exit_code", -1),
                    "retry_count": final_state.get("retry_count", 0),
                    "security_clearance": final_state.get("security_clearance", False),
                    "original_code": final_state.get("original_code", ""),
                    "proposed_patch": final_state.get("proposed_patch", ""),
                    "token_consumption": final_state.get("token_consumption", 0),
                    "latency_ms": elapsed_ms,
                    "deployment_status": final_state.get("deployment_status"),
                    "deployment_pid": final_state.get("deployment_pid"),
                    "deployment_reason": final_state.get("deployment_reason"),
                    "deployment_stderr": final_state.get("deployment_stderr"),
                }
            )
            yield {"event": "complete", "data": complete_event.model_dump_json()}
            
            # Record ledger async
            await record_ledger_entry(
                app=request.app,
                target_file=payload.target_file,
                final_state=final_state,
                elapsed_ms=elapsed_ms,
                run_id=run_id,
                event_source="api/v1/graph/run/stream"
            )
            
        except Exception as e:
            logger.error(f"Stream execution fatally failed: {e}", exc_info=True)
            err_event = GraphStreamEvent(event="error", run_id=run_id, error=str(e))
            yield {"event": "error", "data": err_event.model_dump_json()}
            
    return EventSourceResponse(event_generator())
