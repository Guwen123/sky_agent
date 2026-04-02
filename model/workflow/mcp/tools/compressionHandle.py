from typing import List

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, RemoveMessage, SystemMessage
from langgraph.graph.message import REMOVE_ALL_MESSAGES

from model.contants.contant import COMPRESSION_MODEL, COMPRESSED_MESSAGES_COUNT, MAX_MESSAGES
from model.state.state import AgentState
from model.workflow.llm.llm_factory import LLMFactory
from model.workflow.prompt.compressionPrompt import COMPRESSION_PROMPT


def _msg_to_str(message: BaseMessage) -> str:
    if isinstance(message, HumanMessage):
        return f"User: {message.content}"
    if isinstance(message, AIMessage):
        return f"AI: {message.content}"
    return f"Other: {message.content}"


def compress_messages(messages: List[BaseMessage]) -> List[BaseMessage]:
    if len(messages) <= MAX_MESSAGES:
        return messages

    system_messages = [message for message in messages if isinstance(message, SystemMessage)]
    chat_messages = [message for message in messages if not isinstance(message, SystemMessage)]
    keep_recent = chat_messages[-COMPRESSED_MESSAGES_COUNT:]
    to_compress = chat_messages[:-COMPRESSED_MESSAGES_COUNT]

    if COMPRESSION_MODEL != 1 or not to_compress:
        return system_messages + keep_recent

    text_history = "\n".join(_msg_to_str(message) for message in to_compress)
    prompt = COMPRESSION_PROMPT.format(messages=text_history)
    compressed_summary = LLMFactory.create_openai_llm().invoke(prompt)
    compressed_message = SystemMessage(content=f"History summary: {compressed_summary.content}")
    return system_messages + [compressed_message] + keep_recent


def compress_messages_node(state: AgentState) -> AgentState:
    original_messages = state["messages"]
    compressed_messages = compress_messages(original_messages)
    if compressed_messages == original_messages:
        return {}
    return {"messages": [RemoveMessage(id=REMOVE_ALL_MESSAGES), *compressed_messages]}
