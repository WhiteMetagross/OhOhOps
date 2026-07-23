import asyncio
from app.core.schemas import new_agent_state
from app.graph.nodes.evaluation_node import evaluation_node
from app.graph.nodes.context_node import context_node
from app.graph.nodes.modification_node import modification_node
from app.graph.nodes.sandbox_node import sandbox_node

async def main():
    print("Initializing dummy state...")
    # 1. Initialize safe state using the helper from schemas
    state = new_agent_state(
        current_target_file="test_script.py",
        discovered_logs=["Error: Need a script that prints 'Hello World!' to stdout. Please provide it."]
    )
    
    print("\n[Node 1] Running evaluation_node...")
    res = await evaluation_node(state)
    # LangGraph normally merges this automatically using operator.add, but we do it manually for this test:
    state["messages"].extend(res.get("messages", []))
    state.update({k:v for k,v in res.items() if k != "messages"})
    print(f"Added {len(res.get('messages', []))} evaluation message.")
    
    print("\n[Node 2] Running context_node...")
    res = await context_node(state)
    state["messages"].extend(res.get("messages", []))
    print(f"Added {len(res.get('messages', []))} context message.")
    
    print("\n[Node 3] Running modification_node...")
    res = await modification_node(state)
    state.update({k:v for k,v in res.items() if k != "messages"})
    if "messages" in res:
        state["messages"].extend(res["messages"])
        
    print(f"\n[Proposed Patch]\n{state.get('proposed_patch')}")
    
    print("\n[Node 4] Running sandbox_node (Executing in Docker)...")
    res = await sandbox_node(state)
    state.update(res)
    
    print(f"\n[Final Sandbox Exit Code]: {state.get('execution_exit_code')}")
    print(f"[Final Sandbox Stderr]: {state.get('execution_stderr', 'None')}")

if __name__ == "__main__":
    asyncio.run(main())
