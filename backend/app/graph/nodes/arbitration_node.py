import logging
import asyncio
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage
from app.core.schemas import AgentState
from app.services.llm import NamedModel, get_security_models
from app.security.blocklist import check_blocklist

logger = logging.getLogger("ohohops.nodes.arbitration")

class SecurityDecision(BaseModel):
    is_safe: bool = Field(description="True if the code is safe. False if it contains destructive or unauthorized operations.")
    reason: str = Field(description="Brief explanation of the security decision.")


async def _collect_vote(
    candidate: NamedModel,
    messages: list[SystemMessage | HumanMessage],
) -> tuple[str, SecurityDecision, int]:
    structured = candidate.model.with_structured_output(
        SecurityDecision,
        include_raw=True,
    )
    result = await structured.ainvoke(messages)
    if isinstance(result, dict):
        if result.get("parsing_error"):
            raise ValueError(
                f"{candidate.name} parsing failed: {result['parsing_error']}"
            )
        decision = result.get("parsed")
        raw = result.get("raw")
    else:
        decision = result
        raw = None
    if not isinstance(decision, SecurityDecision):
        raise TypeError(f"{candidate.name} returned an invalid security decision")
    usage = getattr(raw, "usage_metadata", None) or {}
    return candidate.name, decision, int(usage.get("total_tokens", 0))


async def arbitration_node(state: AgentState) -> dict:
    """
    Security gate. Analyzes the proposed patch for destructive commands before allowing sandboxing.
    """
    logger.info("--- SECURITY ARBITRATION NODE ---")
    
    patch = state.get("proposed_patch", "")
    if not patch:
        logger.warning("No patch found to arbitrate.")
        return {"security_clearance": False}
        
    # 1. Fast, deterministic static analysis (Regex Blocklist)
    is_safe_static, static_reason = check_blocklist(patch)
    if not is_safe_static:
        logger.warning(f"ERROR: Blocklist triggered: {static_reason}")
        return {"security_clearance": False}
        
    from app.core.config import get_settings
    if get_settings().use_mock_llm:
        logger.info("Using two deterministic mock security arbiters")
        return {
            "security_clearance": True,
            "token_consumption": 0,
            "security_votes": [
                {"model": "mock:static-reviewer", "decision": "safe", "reason": "Mock approval"},
                {"model": "mock:runtime-reviewer", "decision": "safe", "reason": "Mock approval"},
            ],
        }
        
    # 2. Independent model arbitration. Both models must approve.
    target_file = state.get("current_target_file", "")
    system_instruction = "You are a strict DevSecOps AI. Analyze source code in any language for destructive operations."
    prompt = f"""
    Analyze the following source code (file: {target_file or 'unknown'}). Infer the language from the file extension and contents.
    If the code contains destructive operations (e.g., shell calls like 'rm -rf', malicious subprocess/exec calls, unauthorized network exfiltration), mark it as UNSAFE (is_safe=False).
    If it is a standard application logic fix, mark it as SAFE (is_safe=True).

    Code to evaluate:
    ```
    {patch}
    ```
    """
    
    try:
        candidates = get_security_models()
        messages = [
            SystemMessage(content=system_instruction),
            HumanMessage(content=prompt)
        ]
        results = await asyncio.gather(
            *(_collect_vote(candidate, messages) for candidate in candidates)
        )
        tokens_used = sum(tokens for _, _, tokens in results)
        votes = [
            {
                "model": name,
                "decision": "safe" if decision.is_safe else "unsafe",
                "reason": decision.reason,
            }
            for name, decision, _ in results
        ]
        approved = len(results) >= 2 and all(
            decision.is_safe for _, decision, _ in results
        )

        logger.info(
            "Security consensus: %s [votes=%s, tokens=%s]",
            "SAFE" if approved else "UNSAFE",
            len(votes),
            tokens_used,
        )
        return {
            "security_clearance": approved,
            "token_consumption": tokens_used,
            "security_votes": votes,
        }
    except Exception as e:
        # Security decisions fail closed when model arbitration is unavailable.
        logger.warning(
            f"LLM security check failed ({type(e).__name__}: {e}). "
            "Security clearance denied."
        )
        return {
            "security_clearance": False,
            "token_consumption": 0,
            "security_votes": [],
        }
