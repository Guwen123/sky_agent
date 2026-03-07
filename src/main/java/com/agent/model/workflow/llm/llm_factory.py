from langchain_openai import OpenAI
from com.agent.model.contants.contant import MODEL_API, BASE_API, MODEL_NAME

class LLMFactory:
    """LLM 工厂类，负责创建和管理语言模型实例"""
    
    @staticmethod
    def create_openai_llm() -> OpenAI:
        """创建 OpenAI 语言模型实例
        
        Returns:
            OpenAI: 配置好的 OpenAI 实例
        """
        return OpenAI(
            api_key=MODEL_API,
            base_url=BASE_API,
            model_name=MODEL_NAME,
            temperature=0.5
        )