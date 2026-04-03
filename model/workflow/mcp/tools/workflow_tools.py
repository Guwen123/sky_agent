import re
import uuid
from urllib import parse as urlparse

from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.messages.utils import message_chunk_to_message
from langchain_core.prompts import ChatPromptTemplate
from langgraph.config import get_stream_writer

from model.state.state import AgentState
from model.workflow.llm.llm_factory import LLMFactory
from model.workflow.mcp.mcp import MCP_TOOLS
from model.workflow.mcp.tools.preference_tools import (
    chunk_text,
    format_preferences,
    normalize_preferences,
    update_preferences_with_llm,
)
from model.workflow.prompt.preferencePrompt import (
    PREFERENCE_INJECTION_PROMPT,
    PREFERENCE_UPDATE_PROMPT,
)
from model.workflow.prompt.systemPrompt import SYSTEM_PROMPT


_LLM = None
_LLM_WITH_TOOLS = None
_PREFERENCE_PROMPT = ChatPromptTemplate.from_messages(PREFERENCE_UPDATE_PROMPT)
_ORDER_CONFIRMATION_PREFIX = "__ORDER_CONFIRMATION__"
_DIRECT_ORDER_TOOLS = {
    "prepareTakeoutOrderFromText",
    "placeTakeoutOrder",
    "confirmPendingTakeoutOrder",
    "cancelPendingTakeoutOrder",
}


def _get_llm():
    global _LLM
    if _LLM is None:
        _LLM = LLMFactory.create_openai_llm()
    return _LLM


def _get_llm_with_tools():
    global _LLM_WITH_TOOLS
    if _LLM_WITH_TOOLS is None:
        _LLM_WITH_TOOLS = _get_llm().bind_tools(MCP_TOOLS)
    return _LLM_WITH_TOOLS


def _message_text(message) -> str:
    content = getattr(message, "content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(item.get("text", ""))
            elif isinstance(item, str):
                parts.append(item)
        return "".join(parts)
    return str(content or "")


def _contains_any(text: str, keywords) -> bool:
    return any(keyword in text for keyword in keywords)


def _extract_confirm_address_book_id(text: str) -> int:
    normalized = str(text or "")
    digit_match = re.search(r"address_book_id\s*=\s*(\d+)", normalized, flags=re.IGNORECASE)
    if digit_match:
        try:
            return int(digit_match.group(1))
        except Exception:
            return 0
    return 0


def _extract_confirm_remark(text: str) -> str:
    normalized = str(text or "")
    match = re.search(r"remark=([^\s]+)", normalized, flags=re.IGNORECASE)
    if not match:
        return ""
    return urlparse.unquote(match.group(1)).strip()


def _recent_human_text(state: AgentState, limit: int = 2) -> str:
    texts = []
    for message in reversed(state.get("messages", [])):
        if getattr(message, "type", "") == "human":
            text = _message_text(message).strip()
            if text:
                texts.append(text)
            if len(texts) >= limit:
                break
    return "\n".join(reversed(texts))


def _build_direct_service_tool_call(state: AgentState):
    if not state.get("messages"):
        return None

    latest_message = state["messages"][-1]
    if getattr(latest_message, "type", "") != "human":
        return None

    normalized = re.sub(r"\s+", "", _message_text(latest_message))
    if not normalized:
        return None

    user_id = str(state.get("user_id") or "")
    recent_human_text = _recent_human_text(state)
    recent_human_normalized = re.sub(r"\s+", "", recent_human_text)
    tool_name = None
    args = None

    if _contains_any(normalized, ("确认下单", "确认点单", "确认提交订单", "提交刚才的订单")):
        tool_name = "confirmPendingTakeoutOrder"
        args = {
            "user_id": user_id,
            "address_book_id": _extract_confirm_address_book_id(_message_text(latest_message)),
            "remark": _extract_confirm_remark(_message_text(latest_message)),
        }
    elif _contains_any(normalized, ("取消下单", "取消点单", "取消订单", "放弃下单")):
        tool_name = "cancelPendingTakeoutOrder"
        args = {"user_id": user_id}
    elif _contains_any(normalized, ("历史订单", "订单历史", "我的订单", "下单记录", "历史下单")):
        tool_name = "getOrderHistory"
        args = {"user_id": user_id, "page": 1, "page_size": 10}
    elif "博客" in normalized and _contains_any(normalized, ("热门", "最热", "热榜")):
        tool_name = "getHotBlogs"
        args = {"current": 1}
    elif "博客" in normalized and _contains_any(normalized, ("历史", "记录", "以前", "发过", "写过")):
        tool_name = "getMyBlogHistory"
        args = {"user_id": user_id, "current": 1}
    elif _contains_any(recent_human_normalized, ("帮我点", "点一份", "来一份", "来个", "下单", "我要点", "我想点", "订一份")):
        tool_name = "prepareTakeoutOrderFromText"
        args = {"user_id": user_id, "user_text": recent_human_text}

    if not tool_name or args is None:
        return None

    return AIMessage(
        content="",
        tool_calls=[
            {
                "name": tool_name,
                "args": args,
                "id": f"direct_{tool_name}_{uuid.uuid4().hex}",
                "type": "tool_call",
            }
        ],
    )


def handle_llm_node(state: AgentState) -> AgentState:
    stream_writer = get_stream_writer()
    preferences = normalize_preferences(state.get("preferences"))

    if state.get("messages"):
        latest_message = state["messages"][-1]
        if getattr(latest_message, "type", "") == "tool":
            latest_text = _message_text(latest_message)
            latest_tool_name = str(getattr(latest_message, "name", "") or "")
            if latest_text.startswith(_ORDER_CONFIRMATION_PREFIX) or latest_tool_name in _DIRECT_ORDER_TOOLS:
                stream_writer(latest_text)
                return {"messages": [AIMessage(content=latest_text)], "preferences": preferences}

    direct_tool_call = _build_direct_service_tool_call(state)
    if direct_tool_call is not None:
        return {"messages": [direct_tool_call], "preferences": preferences}

    messages = [SystemMessage(content=SYSTEM_PROMPT)]
    preference_message = format_preferences(preferences, PREFERENCE_INJECTION_PROMPT)
    if preference_message:
        messages.append(SystemMessage(content=preference_message))
    messages.extend(state["messages"])

    response_chunk = None
    for chunk in _get_llm_with_tools().stream(messages):
        response_chunk = chunk if response_chunk is None else response_chunk + chunk
        text = chunk_text(chunk)
        if text:
            stream_writer(text)

    response = (
        message_chunk_to_message(response_chunk)
        if response_chunk is not None
        else _get_llm_with_tools().invoke(messages)
    )
    return {"messages": [response], "preferences": preferences}


def update_preference_node(state: AgentState) -> AgentState:
    preferences = update_preferences_with_llm(
        llm=_get_llm(),
        preference_prompt=_PREFERENCE_PROMPT,
        current_preferences=state.get("preferences"),
        messages=state["messages"],
    )
    return {"preferences": preferences}
