import logging
from app.core.schemas import AgentState
from app.services.sandbox import execute_in_sandbox

logger = logging.getLogger("ohohops.nodes.sandbox")

async def sandbox_node(state: AgentState) -> dict:
    """
    Execution node.
    Runs the generated patch in the isolated Docker sandbox.
    """
    logger.info("--- SANDBOX VERIFICATION NODE ---")
    
    patch_code = state.get("proposed_patch", "")
    if not patch_code:
        logger.error("No patch code found to execute.")
        return {
            "execution_exit_code": 1,
            "execution_stderr": "No patch code provided by the LLM.",
            "retry_count": state.get("retry_count", 0) + 1
        }
        
    # Execute the code inside the ephemeral Docker container
    exit_code, stdout, stderr = await execute_in_sandbox(
        patch_code,
        project_path=state.get("project_path", ""),
        reproduction_command=state.get("reproduction_command", ""),
        target_file=state.get("current_target_file", "")
    )
    
    logger.info(f"Sandbox completed. Exit code: {exit_code}")
    if stderr:
        logger.warning(f"Sandbox Stderr: {stderr.strip()}")
        
    # Patch deployment is handled by the deployment_node downstream.
    # sandbox_node only verifies — it does not deploy.
                
    current_retries = state.get("retry_count", 0)
    
    return {
        "execution_exit_code": exit_code,
        "execution_stderr": stderr.strip(),
        "retry_count": current_retries + 1
    }
