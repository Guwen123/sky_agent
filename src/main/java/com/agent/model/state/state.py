from typing import TypedDict, Annotated
import operator
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from typing import List
from com.agent.model.contants.contant import MODEL_NAME, MODEL_API, BASE_API

class AgentState(TypedDict):
    # 用户的原始问题
    question: str
    # 思考-行动-观察的历史记录（对话消息格式）
    messages: Annotated[List, operator.add]
    # 用户Id
    user_id: str