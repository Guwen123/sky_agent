import sys
from pathlib import Path

current_file = Path(__file__).resolve()
src_main_java = current_file.parents[4]
sys.path.insert(0, str(src_main_java))

from fastapi import FastAPI,HTTPException
from pydantic import BaseModel,Field
from typing import Optional,List,Dict,Any
from com.agent.model.workflow.runner import WorkflowRunner
from com.agent.model.state.state import AgentState
from langchain_core.messages import HumanMessage

app = FastAPI(title="Agent API",version="1.0")

print("Agent API 正在启动")
runner = WorkflowRunner()
print("Agent API 已启动")

class UserRequest(BaseModel):
    user_id: str = Field(..., description="用户ID")
    question: str = Field(..., description="消息列表")

@app.post("/chat")
async def run_workflow(request: UserRequest):
    """运行工作流
    Args:
        request: 用户请求
    Returns:
        str: 执行结果
    """
    initial_state = AgentState(
        user_id=request.user_id,
        messages=[HumanMessage(content=request.question)]
    )
    
    result = runner.run(initial_state)
    return {"result": result}