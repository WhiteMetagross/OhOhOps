import json
import logging
from fastapi import APIRouter, Request, HTTPException, Depends
from sse_starlette.sse import EventSourceResponse
from langchain_core.messages import HumanMessage, SystemMessage

from app.core.schemas import ContextQueryRequest, OperationalLogEntry
from app.services.vectorstore import get_vectorstore_service
from app.services.llm import get_chat_model
from app.security.auth import verify_api_key
from app.core.limiter import limiter

logger = logging.getLogger("ohohops.api.context")
router = APIRouter()

SYSTEM_PROMPT = """You are OhOhOps, an autonomous SRE assistant.
Use the provided codebase context to answer the user's prompt accurately. 
If the context doesn't contain the answer, state that you cannot find the answer in the codebase.
"""

@router.post("/context/query", dependencies=[Depends(verify_api_key)])
@limiter.limit("20/minute")
async def context_query(request: Request, payload: ContextQueryRequest):
    """
    RAG inference loop:
    1. Embed prompt and retrieve relevant codebase chunks.
    2. Assemble context window with explicit file paths.
    3. Stream response via SSE.
    """
    vectorstore = get_vectorstore_service()
    
    # 1. Retrieve chunks
    try:
        docs = await vectorstore.asearch(
            payload.prompt, 
            top_k=payload.top_k, 
            namespace=payload.namespace
        )
    except Exception as e:
        logger.error(f"Vector search failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve context")

    # 2. Assemble context
    context_blocks = []
    for doc in docs:
        path = doc.metadata.get("path", "Unknown")
        context_blocks.append(f"--- File: {path} ---\n{doc.page_content}")
    
    assembled_context = "\n\n".join(context_blocks)
    
    user_message = f"Context:\n{assembled_context}\n\nPrompt:\n{payload.prompt}"

    # 3. Stream inference
    chat_model = get_chat_model()
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_message)
    ]
    
    async def event_generator():
        try:
            # astream yields AIMessageChunks; usage_metadata is delivered on the
            # final chunk once the model finishes. We track it as we go.
            tokens_used = 0
            async for chunk in chat_model.astream(messages):
                if chunk.content:
                    yield {
                        "event": "message",
                        "data": json.dumps({"text": chunk.content})
                    }
                # The last chunk carries usage_metadata; earlier ones have it as None.
                meta = getattr(chunk, "usage_metadata", None)
                if meta is not None:
                    tokens_used = int(meta.get("total_tokens", 0))
            
            # Log to operational ledger at the end of the stream
            ledger = getattr(request.app.state, "ledger", None)
            if ledger:
                entry = OperationalLogEntry(
                    event_source="api/v1/context/query",
                    agent_action="rag_inference",
                    execution_payload=f"prompt: {payload.prompt}",
                    execution_status="success",
                    token_consumption=tokens_used,
                )
                await ledger.log_event(entry)
                
            # Signal the client that the stream is finished
            yield {"event": "done", "data": "[DONE]"}
            
        except Exception as e:
            logger.error(f"Streaming error: {e}", exc_info=True)
            yield {"event": "error", "data": str(e)}

    return EventSourceResponse(event_generator())
