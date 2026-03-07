from com.agent.model.workflow.runner import WorkflowRunner
from com.agent.model.state.state import AgentState

if __name__ == "__main__":
    # 初始化工作流运行器
    runner = WorkflowRunner()
    
    # 运行工作流
    initial_state = {
        "question": "你的问题",
        "messages": [],
        "user_id": "user123"
    }
    
    result = runner.run(initial_state)
    print("工作流执行结果:", result)