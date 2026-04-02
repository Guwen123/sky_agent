from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from model.state.state import AgentState
from model.workflow.mcp.mcp import MCP
from model.workflow.mcp.tools.compressionHandle import compress_messages_node
from model.workflow.mcp.tools.workflow_tools import handle_llm_node, update_preference_node


class GraphBuilder:
    """工作流图构建器，负责创建 LangGraph 工作流。"""

    @staticmethod
    def build_graph() -> StateGraph:
        graph = StateGraph(AgentState)
        tools = MCP().get_tools()
        tool_node = ToolNode(tools)

        graph.add_node("tool_node", tool_node)
        graph.add_node("handleLlm", handle_llm_node)
        graph.add_node("compressMessages", compress_messages_node)
        graph.add_node("updatePreference", update_preference_node)

        graph.set_entry_point("compressMessages")
        graph.add_edge("compressMessages", "handleLlm")
        graph.add_conditional_edges(
            "handleLlm",
            lambda state: "tools" if state["messages"][-1].tool_calls else "updatePreference",
            {
                "tools": "tool_node",
                "updatePreference": "updatePreference",
            },
        )
        graph.add_edge("tool_node", "handleLlm")
        graph.add_edge("updatePreference", END)
        return graph
