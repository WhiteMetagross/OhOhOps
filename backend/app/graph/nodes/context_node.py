import logging
from app.core.schemas import AgentState
from app.services.vectorstore import get_vectorstore_service

logger = logging.getLogger("ohohops.nodes.context")

async def context_node(state: AgentState) -> dict:
    """
    Retrieval node.
    Uses the discovered logs and target to query the vectorstore for context.
    """
    logger.info("--- CONTEXT RETRIEVAL NODE ---")
    
    logs = "\n".join(state.get("discovered_logs", []))
    query = f"Error in {state.get('current_target_file')}: {logs}"
    
    from app.core.config import get_settings
    if get_settings().use_mock_llm:
        logger.info("Using mock context retrieval (quota-free mode)")
        mock_context = """--- File: buggy_server.py ---
import sys
import time

def process_metrics():
    metrics = [10, 20, -5, 40]
    for m in metrics:
        if m < 0:
            val = math.sqrt(abs(m))
            print(f"Processed absolute metric: {val}")
        else:
            print(f"Processed metric: {m}")
        time.sleep(0.5)

def main():
    print("Starting OhOhOps Demo Server...")
    try:
        process_metrics()
        print("Server running successfully!")
    except Exception as e:
        print(f"FATAL CRASH: {type(e).__name__}: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()"""
        return {"messages": [{"role": "system", "content": f"Retrieved Context from Codebase:\n{mock_context}"}]}

    try:
        context_blocks = []
        source_code = state.get("source_code")
        if source_code:
            context_blocks.append(f"--- File: {state.get('current_target_file', 'unknown')} (From Daemon) ---\n{source_code}")

        vectorstore = get_vectorstore_service()
        # Fetch top relevant chunks
        docs = await vectorstore.asearch(query, top_k=3, namespace=state.get("namespace"))
        
        for doc in docs:
            path = doc.metadata.get("path", "Unknown")
            # Don't duplicate if we already have the exact file from the daemon
            if state.get("current_target_file") and path.endswith(state.get("current_target_file")):
                continue
            context_blocks.append(f"--- File: {path} ---\n{doc.page_content}")
            
        assembled_context = "\n\n".join(context_blocks)
        
        context_message = {
            "role": "system",
            "content": f"Retrieved Context from Codebase:\n{assembled_context}"
        }
        
        return {"messages": [context_message]}
    except Exception as e:
        logger.warning(f"Vector search failed ({e}). Falling back to traceback regex extraction + dummy vector query...")
        
        # Fallback: if Gemini embeddings are exhausted, we can't embed the query.
        # But we can regex the file name from the traceback, and query Pinecone 
        # using a dummy vector [0]*3072 and a metadata filter!
        import re
        matches = re.findall(r'File "([^"]+)", line', logs)
        if matches:
            target_filename = matches[-1].replace("\\", "/").split("/")[-1] # Get basename
            logger.info(f"Fallback extracted filename: {target_filename}")
            
            try:
                # Use global imports
                vstore_service = get_vectorstore_service()
                
                # If running on cloud (Pinecone)
                if not get_settings().is_local:
                    index = vstore_service.pc.Index(vstore_service.index_name)
                    # Query Pinecone directly bypassing LangChain's embedding step
                    res = index.query(
                        vector=[0.0] * get_settings().embedding_dimension,
                        top_k=20,
                        include_metadata=True
                    )
                    
                    # Filter locally since Pinecone metadata filters on string 'ends_with' is complex
                    context_blocks = []
                    for match in res.get("matches", []):
                        path = match.get("metadata", {}).get("path", "")
                        if path.endswith(target_filename):
                            text = match.get("metadata", {}).get("text", "")
                            context_blocks.append(f"--- File: {path} ---\n{text}")
                            
                    if context_blocks:
                        assembled_context = "\n\n".join(context_blocks)
                        logger.info("Fallback successful: Retrieved context using zero-vector Pinecone query.")
                        return {"messages": [{"role": "system", "content": f"Retrieved Context from Codebase:\n{assembled_context}"}]}
            except Exception as fallback_err:
                logger.error(f"Fallback dummy vector query failed: {fallback_err}")
                
        logger.error(f"Fallback extraction failed.")
        
        # At the very least, if we have source code, return that!
        if context_blocks:
            assembled = "\n\n".join(context_blocks)
            return {"messages": [{"role": "system", "content": f"Retrieved Context from Codebase:\n{assembled}"}]}
            
        return {"messages": [{"role": "system", "content": f"Failed to retrieve context (embeddings exhausted, and fallback query failed): {e}"}]}
