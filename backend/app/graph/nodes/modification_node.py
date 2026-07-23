import os
import logging
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, SystemMessage

from app.core.schemas import AgentState
from app.services.llm import get_chat_model

logger = logging.getLogger("ohohops.nodes.modification")


def _read_original_code(project_path: str, target_file: str) -> str:
    """Best-effort read of the target file's current contents from the workspace.

    Used to populate ``original_code`` so the dashboard can render a real
    before/after diff. Mirrors the path-resolution that ``sandbox_node`` uses on
    deploy: try the direct path, then fall back to walking the tree by basename.
    Returns "" if the file can't be located (e.g. AUTO_DETECT of a new file).
    """
    if not project_path or not target_file:
        return ""

    rel_target = (
        os.path.relpath(target_file, project_path)
        if os.path.isabs(target_file)
        else target_file
    )
    candidate = os.path.join(project_path, rel_target)

    if not os.path.exists(candidate):
        basename = os.path.basename(rel_target)
        for root, _dirs, files in os.walk(project_path):
            if basename in files:
                candidate = os.path.join(root, basename)
                break

    try:
        with open(candidate, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""

class PatchProposal(BaseModel):
    reasoning: str = Field(description="Explanation of what caused the bug and how the patch fixes it.")
    target_file: str = Field(description="The exact relative path of the file you are modifying. If the user provided AUTO_DETECT or a blank target, you MUST deduce the correct filename from the retrieved codebase context.")
    code: str = Field(description="The complete, updated content of the target file. It MUST be the full file content, not just a diff or snippet.")

async def modification_node(state: AgentState) -> dict:
    """
    Code generation node.
    Reviews the context and previous errors to generate a full-file patch.
    """
    logger.info("--- CODE MODIFICATION NODE ---")

    from app.core.config import get_settings
    if get_settings().use_mock_llm:
        logger.info("Using mock patch generation (quota-free mode)")
        mock_patch = """import sys
import time
import math

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
        raise SystemExit(1)

if __name__ == "__main__":
    main()"""
        assistant_message = {
            "role": "assistant",
            "content": "Proposed Fix (MOCKED): Imported math and updated the square root logic inside process_metrics."
        }
        return {
            "proposed_patch": mock_patch,
            "current_target_file": "buggy_server.py",
            "original_code": _read_original_code(state.get("project_path", ""), "buggy_server.py"),
            "messages": [assistant_message],
            "token_consumption": 0,
        }

    chat_model = get_chat_model()
    structured_llm = chat_model.with_structured_output(PatchProposal, include_raw=True)

    sys_content = "You are an autonomous polyglot SRE agent. Your goal is to review the crash logs and the provided codebase context, and rewrite the COMPLETE target file with a fix. Determine the programming language from the file extension. Return the FULL updated file content in the 'code' field and the exact relative path in 'target_file'. DO NOT return a standalone snippet or diffs, return the entire modified file so it can be overwritten safely."

    user_messages = []
    for msg in state.get("messages", []):
        if msg["role"] == "system":
            sys_content += f"\n\n{msg['content']}"
        else:
            user_messages.append(HumanMessage(content=msg["content"]))

    langchain_messages = [SystemMessage(content=sys_content)] + user_messages

    # Inject previous execution failure if we are in a retry loop
    if state.get("execution_exit_code", -1) not in (-1, 0):
        error_msg = f"PREVIOUS ATTEMPT FAILED with stderr:\n{state.get('execution_stderr')}\n\nPlease analyze the error and provide a corrected version of the complete file (in its original language)."
        langchain_messages.append(HumanMessage(content=error_msg))

    try:
        result = await structured_llm.ainvoke(langchain_messages)
        if isinstance(result, dict):
            if result.get("parsing_error"):
                raise ValueError(f"Structured output parsing failed: {result['parsing_error']}")
            response = result.get("parsed")
            raw = result.get("raw")
        else:
            response = result
            raw = None

        if not isinstance(response, PatchProposal):
            raise TypeError("Model did not return a valid patch proposal")

        usage = getattr(raw, "usage_metadata", None) or {}
        tokens_used = int(usage.get("total_tokens", 0))

        logger.info(f"Generated patch (tokens={tokens_used}). Reasoning: {response.reasoning}")

        assistant_message = {
            "role": "assistant",
            "content": f"Proposed Fix for {response.target_file}: {response.reasoning}\n\nCode:\n{response.code}"
        }

        # Capture the pre-patch contents so the UI can show a real diff. Only do
        # this on the first attempt — on retries the original is already in state
        # and the on-disk file is unchanged (deploy only happens on success).
        original_code = state.get("original_code", "") or _read_original_code(
            state.get("project_path", ""), response.target_file
        )

        return {
            "proposed_patch": response.code,
            "current_target_file": response.target_file,
            "original_code": original_code,
            "messages": [assistant_message],
            "token_consumption": tokens_used,
        }
    except Exception as e:
        logger.error(f"Modification generation failed: {e}", exc_info=True)
        return {
            "execution_exit_code": -1,
            "execution_stderr": f"LLM generation failed: {e}",
            "messages": [{"role": "system", "content": f"Modification generation failed: {e}"}]
        }
