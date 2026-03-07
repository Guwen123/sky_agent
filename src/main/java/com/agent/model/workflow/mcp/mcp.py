from langgraph.prebuilt import ToolNode
from langchain_core.tools import tool
from com.agent.model.workflow.rag.vector import Vector
from com.agent.model.workflow.prompt.systemPrompt import SYSTEM_PROMPT

class MCP:
    def __init__(self):
        self.tools = self._auto_discover_tools()
        self.vector = Vector()
        self.llm_with_tools = LLMFactory.create_openai_llm().bind_tools(self.tools)

    def _auto_discover_tools(self) -> List[BaseTool]:
        tools = []
        for name, member in inspect.getmembers(self, predicate=inspect.ismethod):
            if hasattr(member, '_langchain_tool'):
                bound_tool = member.__get__(self, self.__class__)
                tools.append(bound_tool)
        return tools
    
    def get_tools(self):
        return self.tools
        
    @tool(name="queryRag", description="查询rag数据库，返回查询结果") 
    def queryRag(state: AgentState) -> AgentState:
        question = state["messages"][-1]["content"]
        result = self.vector.query(question)
        state["messages"].append({"role": "assistant", "content": f"RAG查询结果：{result}"})
        return state

    @tool(name="addDocuments", description="添加文档到rag数据库")
    def addDocuments(state: AgentState) -> AgentState:
        file_path = state["messages"][-1]["content"]
        self.vector.add_documents(file_path)
        state["messages"].append({"role": "assistant", "content": "文档添加成功"})
        return state
    
    def handleLlm(state: AgentState) -> AgentState:
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
        response = self.llm_with_tools.invoke(messages)
        state["messages"].append( response )
        return state
    
