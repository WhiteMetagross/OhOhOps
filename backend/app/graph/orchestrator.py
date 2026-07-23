import logging
from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph

from app.core.schemas import AgentState
from app.graph.nodes.evaluation_node import evaluation_node
from app.graph.nodes.context_node import context_node
from app.graph.nodes.modification_node import modification_node
from app.graph.nodes.arbitration_node import arbitration_node
from app.graph.nodes.sandbox_node import sandbox_node
from app.graph.nodes.deployment_node import deployment_node
from app.graph.routing import route_execution, route_security

logger = logging.getLogger("ohohops.orchestrator")

def create_sre_orchestrator() -> CompiledStateGraph:
    """
    Builds and compiles the cyclic LangGraph execution pipeline.
    """
    workflow = StateGraph(AgentState)
    
    # 1. Register Nodes
    workflow.add_node("evaluation_node", evaluation_node)
    workflow.add_node("context_node", context_node)
    workflow.add_node("modification_node", modification_node)
    workflow.add_node("arbitration_node", arbitration_node)
    workflow.add_node("sandbox_node", sandbox_node)
    workflow.add_node("deployment_node", deployment_node)
    
    # 2. Set Entry Point
    workflow.set_entry_point("evaluation_node")
    
    # 3. Define Standard Forward Edges
    workflow.add_edge("evaluation_node", "context_node")
    workflow.add_edge("context_node", "modification_node")
    workflow.add_edge("modification_node", "arbitration_node")
    
    # 4. Define Conditional Edges (Security & Retry Loop)
    workflow.add_conditional_edges(
        "arbitration_node",
        route_security,
        {
            "sandbox_node": "sandbox_node",
            "__end__": END
        }
    )
    
    workflow.add_conditional_edges(
        "sandbox_node",
        route_execution,
        {
            "modification_node": "modification_node",
            "deployment_node": "deployment_node",
            "__end__": END
        }
    )
    
    workflow.add_edge("deployment_node", END)
    
    # 5. Compile into a runnable application
    app = workflow.compile()
    logger.info("SRE Orchestrator LangGraph compiled successfully.")
    
    return app
