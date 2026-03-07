from com.agent.model.workflow.graph_builder import GraphBuilder
from com.agent.model.state.state import AgentState

class WorkflowRunner:
    """工作流运行器，负责执行 LangGraph 工作流"""
    
    def __init__(self):
        # 构建并编译图
        graph = GraphBuilder.build_graph()
        self.app = graph.compile()
    
    def run(self, initial_state: dict) -> dict:
        """运行工作流
        
        Args:
            initial_state: 初始状态
            
        Returns:
            dict: 执行结果
        """
        return self.app.invoke(initial_state)