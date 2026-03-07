from langgraph.graph import StateGraph, END, START
from com.agent.model.state.state import AgentState
from com.agent.model.workflow.mcp.mcp import MCP
from com.agent.model.workflow.prompt.system import SYSTEM_PROMPT
from langgraph.prebuilt import ToolNode

class GraphBuilder:
    """工作流图构建器，负责创建 LangGraph 工作流"""
    
    @staticmethod
    def build_graph() -> StateGraph:
        """构建工作流图
        Returns:
            StateGraph: 配置好的状态图
        """
        # 创建图
        graph = StateGraph(AgentState)
        
        # 初始化 MCP 并获取工具
        mcp = MCP()
        tools = mcp.get_tools()
        tool_node = ToolNode(tools)
        
        # 添加节点
        graph.add_node("tool_node", tool_node)
        graph.add_node("handleLlm", mcp.handleLlm)

        # 设置条件边
        graph.set_entry_point("handleLlm")
        graph.add_conditional_edges(
            "handleLlm",
            lambda state: "tools" if "tool_calls" in state["messages"][-1]
                    and state["messages"][-1].tool_calls else "end",
            {
                "tools": "tool_node",
                "end": END
            }
        )
        graph.add_edge("tool_node", "handleLlm")
        
        return graph
