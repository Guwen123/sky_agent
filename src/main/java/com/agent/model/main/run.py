import sys
import os

# 原文件路径：src/main/java/com/agent/model/main/run.py
current_dir = os.path.dirname(os.path.abspath(__file__))
# 向上回退 4 层到 src/main/java/
java_root = os.path.abspath(os.path.join(current_dir, "..", "..", "..", ".."))
sys.path.insert(0, java_root)

from com.agent.model.workflow.runner import WorkflowRunner
from com.agent.model.state.state import AgentState

if __name__ == "__main__":
    # 初始化工作流运行器
    runner = WorkflowRunner()
    
    # 运行工作流
    initial_state = AgentState(
        question="把我路径下的文件添加到rag数据库，文件路径是：C:/Users/86130/Desktop/1/简历/简历-2.3.pdf",
        messages=[{"role": "user", "content": "把我路径下的文件添加到rag数据库，文件路径是：C:/Users/86130/Desktop/1/简历/简历-2.3.pdf"}],
        user_id="user123"
    )
    
    result = runner.run(initial_state)
    print("工作流执行结果:", result)