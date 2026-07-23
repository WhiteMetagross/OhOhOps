import pytest
from app.core.schemas import new_agent_state
from app.graph.routing import route_security, route_execution

def test_route_security():
    # If clearance is false, it routes to END
    state = new_agent_state()
    state["security_clearance"] = False
    assert route_security(state) == "__end__"
    
    # If clearance is true, it routes to sandbox
    state["security_clearance"] = True
    assert route_security(state) == "sandbox_node"

def test_route_execution():
    # route_execution is only reached after the sandbox runs, which only happens
    # once the patch has security clearance — so every case sets it True.
    state = new_agent_state()
    state["security_clearance"] = True

    # If exit code is 0, route to deployment for restart or daemon handoff.
    state["execution_exit_code"] = 0
    assert route_execution(state) == "deployment_node"

    # If exit code is non-zero and retries < max, routes to modification for another attempt
    state["execution_exit_code"] = 1
    state["retry_count"] = 1
    assert route_execution(state) == "modification_node"

    # If exit code is non-zero and retries >= max, routes to END to prevent infinite loops
    state["execution_exit_code"] = 1
    state["retry_count"] = 3
    assert route_execution(state) == "__end__"

    # No security clearance always ends the run, regardless of exit code
    state["security_clearance"] = False
    state["execution_exit_code"] = 1
    state["retry_count"] = 0
    assert route_execution(state) == "__end__"
