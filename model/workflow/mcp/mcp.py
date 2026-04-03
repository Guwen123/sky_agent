from model.workflow.mcp.tools.knowledge_tools import queryKnowledge
from model.workflow.mcp.tools.service_tools import (
    cancelPendingTakeoutOrder,
    confirmPendingTakeoutOrder,
    getHotBlogs,
    getMyBlogHistory,
    getOrderHistory,
    prepareTakeoutOrderFromText,
    placeTakeoutOrder,
)


MCP_TOOLS = [
    queryKnowledge,
    getHotBlogs,
    getMyBlogHistory,
    getOrderHistory,
    prepareTakeoutOrderFromText,
    placeTakeoutOrder,
    confirmPendingTakeoutOrder,
    cancelPendingTakeoutOrder,
]


class MCP:
    def __init__(self):
        self.tools = MCP_TOOLS

    def get_tools(self):
        return self.tools
