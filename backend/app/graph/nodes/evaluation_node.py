import logging
from app.core.schemas import AgentState

logger = logging.getLogger("ohohops.nodes.evaluation")

async def evaluation_node(state: AgentState) -> dict:
    """
    Initial triage node. 
    It receives the initial logs and target file and seeds the conversation.
    """
    logger.info("--- EVALUATION NODE ---")
    
    logs = "\n".join(state.get("discovered_logs", []))
    target = state.get("current_target_file", "Unknown")
    
    # We add the initial problem to the messages array
    initial_message = {
        "role": "user",
        "content": f"The infrastructure encountered an error.\nTarget File: {target}\n\nLogs:\n{logs}"
    }
    
    return {
        "messages": [initial_message],
        "security_clearance": True  # Assumed true for Phase 2; Phase 3 will introduce arbitration
    }
