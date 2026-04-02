from typing import Annotated, Dict, List, TypedDict

from langgraph.graph.message import add_messages
from typing_extensions import NotRequired


class AgentState(TypedDict):
    question: NotRequired[str]
    messages: Annotated[List, add_messages]
    user_id: str
    preferences: NotRequired[Dict]
