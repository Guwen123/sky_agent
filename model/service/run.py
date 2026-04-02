import sys
from pathlib import Path

current_file = Path(__file__).resolve()
root_dir = current_file.parents[2]
sys.path.insert(0, str(root_dir))

from fastapi import FastAPI,HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel,Field
from typing import Optional,List,Dict,Any
from model.workflow.runner import WorkflowRunner
from model.state.state import AgentState
from langchain_core.messages import HumanMessage

app = FastAPI(title="Agent API",version="1.0")

# uvicorn run:app --reload --host 0.0.0.0 --port 8000
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


@app.post("/chat/stream")
async def run_workflow_stream(request: UserRequest):
    initial_state = AgentState(
        user_id=request.user_id,
        messages=[HumanMessage(content=request.question)]
    )

    def generate():
        try:
            for chunk in runner.stream(initial_state):
                if chunk:
                    yield chunk
        except Exception as exc:
            yield f"请求失败: {exc}"

    return StreamingResponse(generate(), media_type="text/plain; charset=utf-8")

