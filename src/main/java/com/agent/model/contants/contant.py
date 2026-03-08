# 模型常量
MODEL_API = ""
MODEL_NAME = "Qwen/Qwen3-8B"
BASE_API = "https://api.siliconflow.cn/v1"

MODEL_EMBEDDING_NAME = "BAAI/bge-m3"

# 文档处理常量
SEPARATORS = ["\n\n", "\n","!","?",".","。",";"] 
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 100 

# 向量数据库常量
QUERY_NUMBER = 3

# 压缩消息
COMPRESSION_MODEL = 0 # 0:消息修剪 1:历史总结
MAX_MESSAGES = 15 # 超过这个数开始压缩
COMPRESSED_MESSAGES_COUNT = 6 # 压缩后的消息数
