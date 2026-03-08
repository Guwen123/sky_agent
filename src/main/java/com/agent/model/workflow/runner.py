from com.agent.model.workflow.graph_builder import GraphBuilder
from com.agent.model.state.state import AgentState
from langgraph.checkpoint.sqlite import SqliteSaver
import os

class WorkflowRunner:
    """工作流运行器，负责执行 LangGraph 工作流"""
    
    def __init__(self):
        # 1. 确保 SQLite 目录存在
        os.makedirs("./data", exist_ok=True)
        # 2. 初始化 LangGraph（原生 Checkpoint）
        print("[初始化] 正在加载 LangGraph...")
        sqlite_checkpointer = SqliteSaver.from_conn_string("./data/native_memory.db")
        # 构建并编译图
        graph = GraphBuilder.build_graph()
        self.app = graph.compile(checkpointer=sqlite_checkpointer)
    
    def run(self, initial_state: AgentState) -> str:
        """运行工作流
        Args:
            initial_state: 初始状态
            
        Returns:
            str: 执行结果
        """
        config = {"configurable": {"thread_id": initial_state["user_id"]}}
        
        final_state = self.app.invoke(initial_state, config=config)
        ai_response = final_state["messages"][-1].content
        sqlite_checkpointer.put(initial_state["user_id"], final_state)

        return ai_response
