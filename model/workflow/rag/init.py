"""
RAG系统初始化脚本
从hmdp和sky_take_out数据库获取数据，初始化知识图谱和向量存储
"""
import sys
import os
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from model.workflow.rag.GraphRag import GraphRAG
from model.workflow.mcp.tools.text2sql import Text2SQL
from model.contants.contant import (
    MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_CHARSET,
    NEO4J_URL, NEO4J_USERNAME, NEO4J_PASSWORD, NEO4J_DATABASE,
    MODEL_API, BASE_API, MODEL_EMBEDDING_NAME
)
import pymysql
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document


class RAGInitializer:
    """RAG系统初始化器"""
    
    def __init__(self):
        # MySQL配置 - 从contant.py导入
        self.mysql_config = {
            "host": MYSQL_HOST,
            "port": MYSQL_PORT,
            "user": MYSQL_USER,
            "password": MYSQL_PASSWORD,
            "charset": MYSQL_CHARSET
        }
        
        # Neo4j配置 - 从contant.py导入
        self.neo4j_config = {
            "neo4j_url": NEO4J_URL,
            "neo4j_username": NEO4J_USERNAME,
            "neo4j_password": NEO4J_PASSWORD,
            "neo4j_database": NEO4J_DATABASE
        }
        
        # 初始化GraphRAG（使用默认配置，已从contant.py导入）
        self.graph_rag = GraphRAG()
        
        # 初始化Text2SQL
        self.text2sql = Text2SQL()

        # Chroma vector store (optional baseline / legacy vector RAG)
        self._chroma = None
        self.document_cache_path = str(self.graph_rag.document_cache_path)

    def connect_mysql(self, database: str = None):
        """连接MySQL数据库"""
        config = self.mysql_config.copy()
        if database:
            config["database"] = database
        
        try:
            conn = pymysql.connect(**config)
            return conn
        except Exception as e:
            print(f"MySQL连接失败: {e}")
            return None
    
    def init_hmdp_data(self, batch_size: int = 10):
        """从hmdp数据库导入店铺和评价数据"""
        print("\n" + "="*60)
        print("开始导入 hmdp 店铺数据...")
        print("="*60)
        
        conn = self.connect_mysql("hmdp")
        if not conn:
            return
        
        try:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                # 获取所有店铺ID
                cursor.execute("SELECT id FROM tb_shop ORDER BY id LIMIT %s", (batch_size,))
                shop_ids = [row["id"] for row in cursor.fetchall()]
                
                print(f"\n将处理前 {len(shop_ids)} 个店铺...")
                
                # 批量处理店铺
                for idx, shop_id in enumerate(shop_ids, 1):
                    print(f"\n处理店铺 {idx}/{len(shop_ids)}: ID={shop_id}")
                    
                    # 使用graph_rag的方法处理店铺评价
                    mysql_config = self.mysql_config.copy()
                    mysql_config["database"] = "hmdp"
                    
                    self.graph_rag.process_shop_reviews_to_document(
                        shop_id=shop_id,
                        mysql_config=mysql_config
                    )
                
                print("\n✓ hmdp 数据导入完成!")
                
        except Exception as e:
            print(f"hmdp数据导入失败: {e}")
            import traceback
            traceback.print_exc()
        finally:
            conn.close()
    
    def init_vector_store(self):
        """初始化 GraphRAG 的 Neo4jVector 向量索引"""
        print("\n" + "="*60)
        print("初始化 GraphRAG 向量索引(Neo4jVector)...")
        print("="*60)
        
        try:
            # Keep consistent with restaurant_rag_perf.py / GraphRAG default.
            self.graph_rag.init_vector_store("shop_dish_embeddings")
            print("\n✓ GraphRAG 向量索引初始化完成!")
        except Exception as e:
            print(f"GraphRAG 向量索引初始化失败: {e}")

    def init_chroma_vector_store_from_neo4j(self, persist_directory: str = "./rag_db", collection_name: str = "rag"):
        """用 Neo4j 中的 ShopDocument 初始化/刷新 Chroma 向量库（用于纯向量RAG对比/兜底）。"""
        print("\n" + "="*60)
        print("初始化 Vector 向量库(Chroma)...")
        print("="*60)

        if self.graph_rag.graph is None:
            print("未连接到Neo4j数据库，无法初始化Chroma向量库")
            return

        if not MODEL_API:
            print("MODEL_API 为空：无法生成 embeddings。请先在 model/contants/contant.py 配置 MODEL_API。")
            return

        embeddings = OpenAIEmbeddings(
            openai_api_key=MODEL_API,
            model=MODEL_EMBEDDING_NAME,
            openai_api_base=BASE_API,
        )
        self._chroma = Chroma(
            collection_name=collection_name,
            embedding_function=embeddings,
            persist_directory=persist_directory,
        )

        docs = self.load_shop_documents_from_neo4j()

        if not docs:
            print("Neo4j 中没有可用的 ShopDocument.content，Chroma 不做写入。")
            return

        self._chroma.add_documents(docs)
        print(f"✓ Chroma 初始化完成: 写入 {len(docs)} 条 ShopDocument")

    def load_shop_documents_from_neo4j(self) -> list:
        if self.graph_rag.graph is None:
            return []

        rows = self.graph_rag.graph.query(
            """
            MATCH (d:ShopDocument)
            RETURN d.name AS name,
                   d.content AS content,
                   d.shop_id AS shop_id,
                   d.shop_name AS shop_name,
                   d.dish_name AS dish_name,
                   d.cuisine_type AS cuisine_type,
                   d.average_rating AS average_rating,
                   d.rating_count AS rating_count,
                   d.shop_open_time AS shop_open_time
            """
        )

        docs = []
        for r in rows or []:
            content = r.get("content") or ""
            if not content.strip():
                continue
            meta = {
                "name": r.get("name", ""),
                "shop_id": r.get("shop_id", ""),
                "shop_name": r.get("shop_name", ""),
                "dish_name": r.get("dish_name", ""),
                "cuisine_type": r.get("cuisine_type", ""),
                "average_rating": r.get("average_rating", ""),
                "rating_count": r.get("rating_count", 0),
                "shop_open_time": r.get("shop_open_time", ""),
                "source": "neo4j:ShopDocument",
            }
            docs.append(Document(page_content=content, metadata=meta))
        return docs

    def persist_shop_documents_to_data(self, file_path: str = None):
        target_path = file_path or self.document_cache_path
        docs = self.load_shop_documents_from_neo4j()
        if not docs:
            print("没有可写入 data 目录的 ShopDocument")
            return

        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        with open(target_path, "w", encoding="utf-8") as file:
            for doc in docs:
                payload = {
                    "page_content": doc.page_content,
                    "metadata": doc.metadata,
                }
                file.write(json.dumps(payload, ensure_ascii=False) + "\n")
        print(f"✓ 已将 {len(docs)} 条 ShopDocument 写入 {target_path}")
    
    def show_statistics(self):
        """显示知识图谱统计信息"""
        print("\n" + "="*60)
        print("知识图谱统计信息")
        print("="*60)
        
        if self.graph_rag.graph is None:
            print("未连接到Neo4j数据库")
            return
        
        try:
            # 统计各类型节点数量
            result = self.graph_rag.graph.query("""
                MATCH (n)
                RETURN labels(n) as labels, count(*) as count
                ORDER BY count DESC
            """)
            
            print("\n节点统计:")
            for row in result:
                labels = ", ".join(row["labels"])
                print(f"  {labels}: {row['count']} 个")
            
            # 统计关系数量
            result = self.graph_rag.graph.query("""
                MATCH ()-[r]->()
                RETURN type(r) as type, count(*) as count
                ORDER BY count DESC
            """)
            
            print("\n关系统计:")
            for row in result:
                print(f"  {row['type']}: {row['count']} 个")

            # 关键节点与向量情况
            result = self.graph_rag.graph.query("""
                MATCH (d:ShopDocument)
                RETURN count(d) AS shopdoc_count,
                       count(d.embedding) AS shopdoc_with_embedding
            """)
            if result:
                print("\nShopDocument统计:")
                print(f"  ShopDocument: {result[0].get('shopdoc_count', 0)} 个")
                print(f"  ShopDocument(有embedding): {result[0].get('shopdoc_with_embedding', 0)} 个")
            
        except Exception as e:
            print(f"统计失败: {e}")
    
    def run_full_init(self, import_hmdp: bool = True, 
                      hmdp_batch_size: int = 10, init_vector: bool = True, init_chroma: bool = True):
        """
        运行完整的初始化流程
        
        Args:
            import_hmdp: 是否导入hmdp数据
            hmdp_batch_size: hmdp店铺处理数量
            init_vector: 是否初始化向量存储
            init_chroma: 是否初始化Chroma向量库（Vector）
        """
        print("\n" + "*"*70)
        print("RAG系统 完整初始化开始".center(70))
        print("*"*70)
        
        # 2. 导入hmdp数据
        if import_hmdp:
            self.init_hmdp_data(batch_size=hmdp_batch_size)
        
        # 3. 初始化向量存储
        if init_vector:
            self.init_vector_store()

        # 3.1 为 GraphRAG 在线混合检索落盘文档语料
        self.persist_shop_documents_to_data()

        # 3.2 初始化 Chroma（用于纯向量RAG基线/兜底）
        if init_chroma:
            self.init_chroma_vector_store_from_neo4j()
        
        # 4. 显示统计信息
        self.show_statistics()
        
        print("\n" + "*"*70)
        print("RAG系统 初始化完成!".center(70))
        print("*"*70)


def main():
    initializer = RAGInitializer()
    
    initializer.run_full_init(
        import_hmdp=True,      
        hmdp_batch_size=20,  
        init_vector=True,
        init_chroma=True,
    )

if __name__ == "__main__":
    main()
