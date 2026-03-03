from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, TextLoader, CSVLoader
from com.agent.model.contants.contant import SEPARATORS, CHUNK_SIZE, CHUNK_OVERLAP

# 文档处理类
class DocumentHanlde:
    def __init__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(
            separators=SEPARATORS,
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
        )

    def get_documents(self,file_path: str) -> list:
        # 获取文件扩展名
        file_extension = file_path.split(".")[-1].lower()
        
        if file_extension == "txt":
            # 处理txt文件
            loader = TextLoader(file_path)
        elif file_extension == "pdf":
            # 处理pdf文件
            loader = PyPDFLoader(file_path)
        elif file_extension == "csv":
            # 处理csv文件
            loader = CSVLoader(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_extension}. Only txt, pdf, csv files are supported.")
        
        documents = loader.load()
        documents = self.text_splitter.split_documents(documents)

        return documents