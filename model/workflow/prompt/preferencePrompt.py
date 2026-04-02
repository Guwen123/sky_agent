PREFERENCE_INJECTION_PROMPT = """
当前用户偏好参考如下：
{preference_summary}

要求：
1. 这些偏好只作为辅助参考，不可覆盖本轮用户的明确要求。
2. 如果本轮用户表达与偏好冲突，以本轮用户要求为准。
3. 当信息不足时，可以结合这些偏好给出更贴近用户的保底推荐。
"""


PREFERENCE_UPDATE_PROMPT = [
    ("system", """
你是一个用户偏好提取专家。请根据当前轮的用户输入和系统已有偏好，只提取用户明确表达或可以高度确定的偏好增量。
不要根据助手的推荐内容臆测用户偏好，不要删除旧偏好，不要重写整份偏好。

请严格返回 JSON 对象，字段只允许来自以下集合：
liked_cuisines: string[]
liked_dishes: string[]
disliked_items: string[]
spice_level: string
price_range: string

如果当前轮没有新的明确偏好，返回空对象 {{}}。

当前已知偏好：
{current_preferences}
"""),
    ("human", """
用户输入：
{user_message}

助手回复：
{assistant_message}
"""),
]
