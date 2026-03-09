import inspect
from langgraph.prebuilt import ToolNode
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage
from com.agent.model.workflow.rag.vector import Vector
from com.agent.model.workflow.prompt.systemPrompt import SYSTEM_PROMPT
from com.agent.model.workflow.llm.llm_factory import LLMFactory
from com.agent.model.state.state import AgentState
from com.agent.model.workflow.mcp.tools.compressionHandle import CompressionHandle


class MCP:
    def __init__(self):
        self.tools = [self.addDocuments, self.queryRag]
        self.llm_with_tools = LLMFactory.create_openai_llm().bind_tools(self.tools)

    def _auto_discover_tools(self) -> list:
        tools = []
        for name, member in inspect.getmembers(self, predicate=inspect.ismethod):
            if hasattr(member, '_langchain_tool'):
                bound_tool = member.__get__(self, self.__class__)
                tools.append(bound_tool)
        return tools
    
    def get_tools(self):
        return self.tools
        
    @tool(description="查询rag数据库，返回查询结果") 
    def queryRag( question: str) -> str:
        """查询rag数据库，返回查询结果"""
        vector = Vector()
        result = vector.query(question)
        return f"RAG查询结果：{result}"
    
    @tool(description="添加文档到rag数据库")
    def addDocuments( file_path: str) :
        """添加文档到rag数据库"""  
        vector = Vector()
        vector.add_documents(file_path)
        print("="*20)
        print(f"文件路径：{file_path}")
        print("="*20)
        print(f"文档添加成功")
        print("="*20)

    def compressMessages( self, state: AgentState) -> AgentState:
        compressionHandle = CompressionHandle()
        state["messages"] = compressionHandle.compressMessages(state["messages"])
        return state
    
    def handleLlm(self, state: AgentState) -> AgentState:
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
        response = self.llm_with_tools.invoke(messages)
        state["messages"].append( response )
        return state
    
