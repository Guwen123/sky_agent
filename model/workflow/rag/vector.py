from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from model.contants.contant import MODEL_API, BASE_API, MODEL_EMBEDDING_NAME, QUERY_NUMBER
from model.workflow.mcp.tools.md5Vality import Md5Vality
from model.workflow.mcp.tools.documentHanlde import DocumentHanlde

class Vector:
    def __init__(self):
        self.vector_db = Chroma(
            collection_name="rag",
            embedding_function=OpenAIEmbeddings(
                openai_api_key=MODEL_API,
                model=MODEL_EMBEDDING_NAME,
                openai_api_base=BASE_API,
            ),
            persist_directory="./rag_db",
        )
        self.document_hanlde = DocumentHanlde()
        self.md5 = Md5Vality()

    def add_documents(self,file_path: str) -> list:
        documents:list[Document] = self.document_hanlde.get_documents(file_path)
        for document in documents:
            result = self.md5.md5Vality(document.page_content)
            if result:
                self.vector_db.add_documents([document])
    
    def query(self,query: str) -> list:
        results = self.vector_db.similarity_search(
            query,
            k=QUERY_NUMBER,
        )
        return results