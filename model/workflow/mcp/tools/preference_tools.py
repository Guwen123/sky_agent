import json
from typing import Any, Dict, List, Tuple

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser


def default_preferences() -> Dict[str, Any]:
    return {
        "liked_cuisines": [],
        "liked_dishes": [],
        "disliked_items": [],
        "spice_level": "",
        "price_range": "",
    }


def normalize_preferences(preferences: Dict[str, Any] = None) -> Dict[str, Any]:
    normalized = default_preferences()
    if not isinstance(preferences, dict):
        return normalized

    for key in ("liked_cuisines", "liked_dishes", "disliked_items"):
        values = preferences.get(key, [])
        if isinstance(values, list):
            normalized[key] = list(
                dict.fromkeys(
                    str(value).strip()
                    for value in values
                    if str(value).strip()
                )
            )
        elif str(values).strip():
            normalized[key] = [str(values).strip()]

    for key in ("spice_level", "price_range"):
        value = str(preferences.get(key, "")).strip()
        if value:
            normalized[key] = value

    return normalized


def format_preferences(preferences: Dict[str, Any], injection_prompt: str) -> str:
    preferences = normalize_preferences(preferences)
    summary_parts = []
    if preferences["liked_cuisines"]:
        summary_parts.append(f"偏好菜系：{', '.join(preferences['liked_cuisines'])}")
    if preferences["liked_dishes"]:
        summary_parts.append(f"偏好菜品：{', '.join(preferences['liked_dishes'])}")
    if preferences["disliked_items"]:
        summary_parts.append(f"忌口或不喜欢：{', '.join(preferences['disliked_items'])}")
    if preferences["spice_level"]:
        summary_parts.append(f"口味偏好：{preferences['spice_level']}")
    if preferences["price_range"]:
        summary_parts.append(f"价格偏好：{preferences['price_range']}")
    if not summary_parts:
        return ""
    return injection_prompt.format(preference_summary="\n".join(summary_parts))


def merge_preferences(current_preferences: Dict[str, Any], delta: Dict[str, Any]) -> Dict[str, Any]:
    merged = normalize_preferences(current_preferences)
    delta = delta if isinstance(delta, dict) else {}

    for key in ("liked_cuisines", "liked_dishes", "disliked_items"):
        values = delta.get(key, [])
        if not isinstance(values, list):
            values = [values] if str(values).strip() else []
        for value in values:
            value = str(value).strip()
            if value and value not in merged[key]:
                merged[key].append(value)

    for key in ("spice_level", "price_range"):
        value = str(delta.get(key, "")).strip()
        if value:
            merged[key] = value

    return merged


def chunk_text(chunk: Any) -> str:
    content = getattr(chunk, "content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        texts = []
        for item in content:
            if isinstance(item, str):
                texts.append(item)
            elif isinstance(item, dict) and item.get("text"):
                texts.append(str(item["text"]))
        return "".join(texts)
    return str(content) if content else ""


def extract_round_messages(messages: List[Any]) -> Tuple[str, str]:
    user_message = ""
    assistant_message = ""

    for message in reversed(messages):
        if not assistant_message and isinstance(message, AIMessage):
            assistant_message = chunk_text(message)
        if not user_message and isinstance(message, HumanMessage):
            user_message = str(message.content).strip()
        if user_message and assistant_message:
            break

    return user_message, assistant_message


def update_preferences_with_llm(
    llm: Any,
    preference_prompt: Any,
    current_preferences: Dict[str, Any],
    messages: List[Any],
) -> Dict[str, Any]:
    current_preferences = normalize_preferences(current_preferences)
    user_message, assistant_message = extract_round_messages(messages)
    if not user_message:
        return current_preferences

    chain = preference_prompt | llm | StrOutputParser()
    result = chain.invoke(
        {
            "current_preferences": json.dumps(current_preferences, ensure_ascii=False),
            "user_message": user_message,
            "assistant_message": assistant_message,
        }
    )

    try:
        preference_delta = json.loads(result)
    except Exception:
        print(f"偏好更新结果解析失败: {result}")
        preference_delta = {}

    return merge_preferences(current_preferences, preference_delta)
