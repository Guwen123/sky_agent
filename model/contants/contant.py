# Model constants
MODEL_API = "sk-mdvlkugikryjgnyekngnbgyqlypyjjckfzadtvnfefecxjix"
MODEL_NAME = "Qwen/Qwen3-8B"
BASE_API = "https://api.siliconflow.cn/v1"

MODEL_EMBEDDING_NAME = "BAAI/bge-m3"
MODEL_RERANKER_NAME = "BAAI/bge-reranker-v2-m3"
MODEL_RERANKER_API_KEY = MODEL_API
MODEL_RERANKER_API_URL = "https://api.siliconflow.cn/v1/rerank"
MODEL_RERANKER_API_TIMEOUT = 60

# Document constants
SEPARATORS = ["\n\n", "\n", "!", "?", ".", "。", ";"]
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 100

# Retrieval constants
QUERY_NUMBER = 2
RAG_CACHE_VERSION = "v1"
RAG_CACHE_TTL_SECONDS = 600
RAG_HOT_CACHE_TTL_SECONDS = 3600
RAG_HOT_QUERY_WINDOW_SECONDS = 3600
RAG_HOT_QUERY_THRESHOLD = 3

# MySQL config
MYSQL_HOST = "localhost"
MYSQL_PORT = 3306
MYSQL_USER = "root"
MYSQL_PASSWORD = "1234"
MYSQL_CHARSET = "utf8mb4"

# Redis config
REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB = 0
REDIS_PASSWORD = ""

# External service config
HMDP_BASE_URL = "http://localhost:8081"
SKY_TAKE_OUT_BASE_URL = "http://localhost:8086"

# Neo4j config
NEO4J_URL = "neo4j://127.0.0.1:7687"
NEO4J_USERNAME = "neo4j"
NEO4J_PASSWORD = "neo4j123456"
NEO4J_DATABASE = "sky"

# Message compression
COMPRESSION_MODEL = 0
MAX_MESSAGES = 5
COMPRESSED_MESSAGES_COUNT = 3
