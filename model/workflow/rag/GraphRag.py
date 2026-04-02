from typing import List, Dict, Tuple, Optional
from pathlib import Path
import requests
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Neo4jVector
from langchain_community.graphs import Neo4jGraph
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.retrievers import BM25Retriever
from langchain_classic.retrievers import EnsembleRetriever
from langchain_classic.retrievers.document_compressors import CrossEncoderReranker
from langchain_classic.retrievers.document_compressors.cross_encoder import BaseCrossEncoder
from model.workflow.llm.llm_factory import LLMFactory
from model.workflow.prompt.graphrag_prompt import (
    GRAPHRAG_ANSWER_PROMPT,
    GRAPHRAG_ENTITY_EXTRACTION_PROMPT,
    GRAPHRAG_FILTER_EXTRACTION_PROMPT
)
from model.contants.contant import (
    MODEL_API, BASE_API, MODEL_EMBEDDING_NAME, MODEL_RERANKER_NAME,
    MODEL_RERANKER_API_KEY, MODEL_RERANKER_API_URL, MODEL_RERANKER_API_TIMEOUT,
    QUERY_NUMBER,
    NEO4J_URL, NEO4J_USERNAME, NEO4J_PASSWORD, NEO4J_DATABASE,
    MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_CHARSET
)
import json
import pymysql
from model.workflow.prompt.graphrag_prompt import SHOP_REVIEW_SUMMARY_PROMPT


class SiliconFlowCrossEncoder(BaseCrossEncoder):
    def __init__(self, api_key: str, api_url: str, model_name: str, timeout: int = 60):
        self.api_key = api_key
        self.api_url = api_url
        self.model_name = model_name
        self.timeout = timeout

    def _score_batch(self, query: str, documents: List[str]) -> List[float]:
        if not documents:
            return []

        response = requests.post(
            self.api_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model_name,
                "query": query,
                "documents": documents,
                "top_n": len(documents),
                "return_documents": False,
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        scores = [0.0] * len(documents)
        for item in payload.get("results", []):
            index = int(item.get("index", -1))
            if 0 <= index < len(documents):
                scores[index] = float(item.get("relevance_score", 0.0))
        return scores

    def score(self, text_pairs: List[Tuple[str, str]]) -> List[float]:
        if not text_pairs:
            return []

        queries = {query for query, _ in text_pairs}
        if len(queries) == 1:
            query = text_pairs[0][0]
            documents = [document for _, document in text_pairs]
            return self._score_batch(query, documents)

        return [
            self._score_batch(query, [document])[0]
            for query, document in text_pairs
        ]


class GraphRAG:
    """
    基于知识图谱的检索增强生成类
    支持从知识图谱中检索相关信息并用于回答生成
    """
    
    def __init__(
        self,
        neo4j_url: str = NEO4J_URL,
        neo4j_username: str = NEO4J_USERNAME,
        neo4j_password: str = NEO4J_PASSWORD,
        neo4j_database: str = NEO4J_DATABASE
    ):
        """
        初始化GraphRAG
        
        Args:
            neo4j_url: Neo4j数据库连接URL
            neo4j_username: Neo4j用户名
            neo4j_password: Neo4j密码
        """
        self.llm = LLMFactory.create_openai_llm()
        self._project_root = Path(__file__).resolve().parents[3]
        self._data_dir = self._project_root / "data"

        # 业务配置：Neo4j连接信息（用于图谱检索与向量索引）
        self._neo4j_url = neo4j_url
        self._neo4j_username = neo4j_username
        self._neo4j_password = neo4j_password
        self._neo4j_database = neo4j_database
        
        self.embeddings = OpenAIEmbeddings(
            api_key=MODEL_API,
            base_url=BASE_API,
            model=MODEL_EMBEDDING_NAME
        )
        
        try:
            self.graph = Neo4jGraph(
                url=neo4j_url,
                username=neo4j_username,
                password=neo4j_password,
                database=neo4j_database
            )
            print("成功连接到Neo4j数据库")
        except Exception as e:
            print(f"Neo4j连接失败: {e}")
            self.graph = None
        
        # 业务数据：ShopDocument 向量检索索引
        self.vector_store = None
        self.document_cache_path = self._data_dir / "shop_documents.jsonl"
        
        self.answer_prompt = ChatPromptTemplate.from_messages(GRAPHRAG_ANSWER_PROMPT)
        
        self.entity_prompt = ChatPromptTemplate.from_messages(GRAPHRAG_ENTITY_EXTRACTION_PROMPT)
        self.filter_prompt = ChatPromptTemplate.from_messages(GRAPHRAG_FILTER_EXTRACTION_PROMPT)
        self.reranker_model = None

    def _get_reranker_model(self) -> BaseCrossEncoder:
        if self.reranker_model is not None:
            return self.reranker_model

        self.reranker_model = SiliconFlowCrossEncoder(
            api_key=MODEL_RERANKER_API_KEY,
            api_url=MODEL_RERANKER_API_URL,
            model_name=MODEL_RERANKER_NAME,
            timeout=MODEL_RERANKER_API_TIMEOUT,
        )
        return self.reranker_model
    
    def init_vector_store(self, index_name: str = "shop_dish_embeddings"):
        """
        Args:
            index_name: 向量索引名称
        """
        if self.graph is None:
            print("未连接到Neo4j数据库，无法初始化向量存储")
            return
        
        try:
            self.vector_store = Neo4jVector.from_existing_graph(
                embedding=self.embeddings,
                url=self._neo4j_url,
                username=self._neo4j_username,
                password=self._neo4j_password,
                database=self._neo4j_database,
                index_name=index_name,
                node_label="ShopDocument",
                text_node_properties=["content"],
                embedding_node_property="embedding"
            )
            print(f"向量存储初始化完成，索引名称: {index_name}")
        except Exception as e:
            print(f"向量存储初始化失败: {e}")

    def sparse_vectors(self, top_k: int = QUERY_NUMBER, metadata_filter: Optional[Dict] = None) -> Optional[BM25Retriever]:
        """从 data 目录读取已落盘的 ShopDocument，并构建 BM25 稀疏检索器。"""
        if not self.document_cache_path.exists():
            print(f"未找到稀疏检索语料: {self.document_cache_path}")
            return None

        documents = []
        with self.document_cache_path.open("r", encoding="utf-8") as file:
            for line in file:
                line = line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                content = (payload.get("page_content") or "").strip()
                if not content:
                    continue
                documents.append(
                    Document(
                        page_content=content,
                        metadata=payload.get("metadata") or {},
                    )
                )
        if metadata_filter:
            documents = [
                doc for doc in documents
                if all(str(doc.metadata.get(key, "")).strip() == str(value).strip() for key, value in metadata_filter.items())
            ]
        if not documents:
            return None

        return BM25Retriever.from_documents(documents, k=top_k)

    def extract_entities(self, question: str) -> List[Dict]:
        """
        从问题中提取实体
        
        Args:
            question: 用户问题
            
        Returns:
            实体列表，每个实体包含name和type
        """
        chain = self.entity_prompt | self.llm | StrOutputParser()
        result = chain.invoke({"question": question})
        
        try:
            import json
            entities = json.loads(result)
            return entities
        except:
            print(f"实体提取结果解析失败: {result}")
            return []
    
    def query_graph_by_entity(self, entity_name: str, entity_type: str = None) -> List[Dict]:
        """
        根据实体名称查询图谱中的相关信息
        
        Args:
            entity_name: 实体名称
            entity_type: 实体类型（可选）
            
        Returns:
            相关的图谱信息列表
        """
        if self.graph is None:
            print("未连接到Neo4j数据库")
            return []
        
        if entity_type:
            query = f"""
            MATCH (e:{entity_type} {{name: $entity_name}})-[r]-(related)
            RETURN e as entity, type(r) as relation_type, related as related_entity
            LIMIT 20
            """
        else:
            query = """
            MATCH (e {name: $entity_name})-[r]-(related)
            RETURN e as entity, type(r) as relation_type, related as related_entity
            LIMIT 20
            """
        
        try:
            result = self.graph.query(query, {"entity_name": entity_name})
            return result
        except Exception as e:
            print(f"图谱查询失败: {e}")
            return []
    
    def search_similar_entities(self, query: str, current_shop: Optional[Dict] = None, top_k: int = QUERY_NUMBER) -> List[Document]:
        """
        根据文本相似度搜索相关的【店铺-菜品打包文档】
        
        Args:
            query: 查询文本
            current_shop: 当前会话锁定店铺
            top_k: 返回结果数量
            
        Returns:
            相关文档列表
        """
        try:
            candidate_k = max(top_k * 3, 6)
            metadata_filter = {}
            # Filter构建过滤条件
            filter_result = (self.filter_prompt | self.llm | StrOutputParser()).invoke({"question": query})
            try:
                extracted_filter = json.loads(filter_result)
                if isinstance(extracted_filter, dict):
                    metadata_filter.update({
                        key: value
                        for key, value in extracted_filter.items()
                        if key in {"shop_name", "dish_name", "cuisine_type"} and str(value).strip()
                    })
            except Exception:
                print(f"过滤条件提取结果解析失败: {filter_result}")

            if current_shop:
                current_shop_id = current_shop.get("shop_id", current_shop.get("id", ""))
                if str(current_shop_id).strip():
                    if isinstance(current_shop_id, str) and current_shop_id.isdigit():
                        current_shop_id = int(current_shop_id)
                    metadata_filter["shop_id"] = current_shop_id
                elif str(current_shop.get("name", "")).strip():
                    metadata_filter["shop_name"] = current_shop["name"]

            dense_retriever = None
            sparse_retriever = self.sparse_vectors(top_k=candidate_k, metadata_filter=metadata_filter or None)

            # 构建稀疏+密集的混合检索器
            if self.vector_store is not None:
                search_kwargs = {"k": candidate_k}
                if metadata_filter:
                    search_kwargs["filter"] = metadata_filter
                dense_retriever = self.vector_store.as_retriever(search_kwargs=search_kwargs)

            # 使用 CrossEncoderReranker 重排
            reranker = CrossEncoderReranker(model=self._get_reranker_model(), top_n=top_k)

            if dense_retriever is not None and sparse_retriever is not None:
                hybrid_retriever = EnsembleRetriever(
                    retrievers=[dense_retriever, sparse_retriever],
                    weights=[0.6, 0.4],
                )
                return list(reranker.compress_documents(hybrid_retriever.invoke(query), query))

            if dense_retriever is not None:
                return list(reranker.compress_documents(dense_retriever.invoke(query), query))

            if sparse_retriever is not None:
                return list(reranker.compress_documents(sparse_retriever.invoke(query), query))

            print("向量存储和稀疏语料都未初始化")
            return []
        except Exception as e:
            print(f"混合检索失败: {e}")
            return []

    def _refresh_from_mysql_for_query(self, question: str, current_shop: Optional[Dict] = None, max_shops: int = 5) -> int:
        """
        Neo4j未命中时，从MySQL回源补齐店铺/菜品到图谱与向量索引。
        返回本次尝试处理的店铺数量。
        """
        mysql_config = {
            "host": MYSQL_HOST,
            "port": MYSQL_PORT,
            "user": MYSQL_USER,
            "password": MYSQL_PASSWORD,
            "charset": MYSQL_CHARSET,
            "database": "hmdp",
        }

        shop_terms: List[str] = []
        dish_terms: List[str] = []

        if current_shop and current_shop.get("name"):
            shop_terms.append(str(current_shop["name"]))

        entities = self.extract_entities(question)
        for entity in entities or []:
            name = str(entity.get("name", "")).strip()
            if not name:
                continue
            e_type = str(entity.get("type", "")).lower()
            if e_type == "shop":
                shop_terms.append(name)
            elif e_type == "dish":
                dish_terms.append(name)

        # 去重并保持顺序
        shop_terms = list(dict.fromkeys(shop_terms))
        dish_terms = list(dict.fromkeys(dish_terms))

        shop_ids: List[int] = []
        try:
            conn = pymysql.connect(**mysql_config)
            try:
                with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                    for term in shop_terms:
                        cursor.execute(
                            "SELECT id FROM tb_shop WHERE name LIKE %s ORDER BY id LIMIT %s",
                            (f"%{term}%", max_shops),
                        )
                        for row in cursor.fetchall():
                            shop_ids.append(int(row["id"]))

                    for term in dish_terms:
                        cursor.execute(
                            "SELECT DISTINCT shop_id AS id FROM tb_shop_dish WHERE dish_name LIKE %s LIMIT %s",
                            (f"%{term}%", max_shops),
                        )
                        for row in cursor.fetchall():
                            shop_ids.append(int(row["id"]))

                    if not shop_ids:
                        cursor.execute(
                            "SELECT id FROM tb_shop WHERE name LIKE %s ORDER BY id LIMIT %s",
                            (f"%{question}%", max_shops),
                        )
                        for row in cursor.fetchall():
                            shop_ids.append(int(row["id"]))
            finally:
                conn.close()
        except Exception as e:
            print(f"MySQL回源失败: {e}")
            return 0

        # 去重并截断
        unique_shop_ids = list(dict.fromkeys(shop_ids))[:max_shops]
        if not unique_shop_ids:
            return 0

        processed = 0
        for shop_id in unique_shop_ids:
            try:
                self.process_shop_reviews_to_document(shop_id=shop_id, mysql_config=mysql_config)
                processed += 1
            except Exception as e:
                print(f"MySQL回源处理店铺失败 shop_id={shop_id}: {e}")
        return processed

    def _should_lock_current_shop(self, question: str, current_shop: Optional[Dict]) -> bool:
        """Decide whether the current turn should stay locked to previous shop context."""
        if not current_shop or not current_shop.get("name"):
            return False

        q = (question or "").strip()
        if not q:
            return False

        current_shop_name = str(current_shop.get("name", "")).strip()
        if current_shop_name and current_shop_name in q:
            return True

        entities = self.extract_entities(q)
        explicit_shop_names = [
            str(entity.get("name", "")).strip()
            for entity in (entities or [])
            if str(entity.get("type", "")).lower() == "shop" and str(entity.get("name", "")).strip()
        ]
        if explicit_shop_names:
            return current_shop_name in explicit_shop_names

        refer_words = [
            "\u8fd9\u5bb6", "\u8fd9\u5bb6\u5e97", "\u8fd9\u5e97", "\u8fd9\u4e2a\u5e97",
            "\u4ed6\u5bb6", "\u5b83\u5bb6", "\u521a\u624d\u90a3\u5bb6", "\u4e0a\u4e00\u5bb6", "\u8fd9\u5bb6\u9910\u5385"
        ]
        return any(word in q for word in refer_words)

    def build_graph_context(
        self,
        question: str,
        current_shop: Optional[Dict] = None,
        top_k: int = QUERY_NUMBER,
    ) -> Tuple[str, List[Document]]:
        """
        Args:
            question: 用户问题
            current_shop: 当前会话锁定的店铺信息（可选），用于精准过滤
             
        Returns:
            (graph_context: 上下文文本, similar_docs: 相关文档)
        """
        lock_current_shop = current_shop if self._should_lock_current_shop(question, current_shop) else None
        if current_shop and not lock_current_shop:
            print("Detected stale shop context; unlocked for this turn.")

        similar_docs = self.search_similar_entities(question, current_shop=lock_current_shop, top_k=top_k)
        if not similar_docs:
            refreshed = self._refresh_from_mysql_for_query(
                question,
                current_shop=lock_current_shop,
                max_shops=max(3, top_k),
            )
            if refreshed > 0:
                similar_docs = self.search_similar_entities(question, current_shop=lock_current_shop, top_k=top_k)
                print(f"MySQL回源后补齐店铺数: {refreshed}")
        print(f"混合检索到 {len(similar_docs)} 个相关文档")

        # 从候选文档中识别涉及的店铺/菜品，用于后续图谱核对
        context_data = {
            "shop_names": set(),
            "dish_names": set(),
            "shop_content_map": {}
        }
        
        for doc in similar_docs:
            shop_name = doc.metadata.get("shop_name")
            shop_id = doc.metadata.get("shop_id")
            if shop_name and shop_id:
                context_data["shop_names"].add(shop_name)
                context_data["shop_content_map"][shop_name] = doc.page_content
                parts = doc.page_content.split("；") 
                for part in parts:
                    if "菜" in part or "份" in part:
                        context_data["dish_names"].add(part.split()[0])

        # 根据上下文是否锁定店铺，选择图谱核对策略
        graph_results = []
        final_shop_names = context_data["shop_names"]
        
        # --- 场景 A：用户上一轮锁定了具体店铺（current_shop） ---
        if lock_current_shop:
            print(f"检测到锁定店铺: {lock_current_shop['name']}，仅查询此店详情")
            final_shop_names = {lock_current_shop['name']}
            
            for dish_name in context_data["dish_names"]:
                rel_result = self.query_graph_by_entity(
                    entity_name=lock_current_shop["name"],
                    entity_type="Shop",
                )
                for res in rel_result:
                    related = res.get("related_entity", {})
                    if related.get("name") == dish_name and related.get("type") == "Dish":
                        graph_results.append(res)
                        break

        # --- 场景 B：用户没有锁定店铺，且有多家店包含该菜 ---
        elif len(final_shop_names) > 1:
            print(f"检测到多家店({len(final_shop_names)})包含相关菜品，去图谱核对详情")
            for shop_name in final_shop_names:
                shop_details = self.query_graph_by_entity(entity_name=shop_name, entity_type="Shop")
                graph_results.extend(shop_details)

        # 拼接
        context_parts = []
        
        context_parts.append("【基于语义匹配的店铺-菜品参考】：")
        for shop_name, content in context_data["shop_content_map"].items():
            if lock_current_shop and shop_name != lock_current_shop['name']:
                continue
            context_parts.append(f"\n【{shop_name}】：\n{content}")

        if graph_results:
            context_parts.append("\n【结构化知识图谱事实】：")
            for idx, result in enumerate(graph_results):
                entity = result.get("entity", {})
                relation = result.get("relation_type", "")
                related = result.get("related_entity", {})
                
                entity_name = entity.get("name", "未知")
                related_name = related.get("name", "未知")
                context_parts.append(f"{idx + 1}. {entity_name} -[{relation}]-> {related_name}")

        return "\n".join(context_parts), similar_docs
    
    def add_entity(
        self,
        name: str,
        entity_type: str,
        properties: Dict = None,
        description: str = "",
        content: str = ""
    ):
        """
        添加实体到知识图谱
        Args:
            name: 实体名称
            entity_type: 实体类型（如Dish, Shop, ShopDocument等）
            properties: 实体属性字典（可选）
            description: 实体描述（普通实体用）
            content: 打包文本内容（仅 ShopDocument 使用）
        """
        if self.graph is None:
            print("未连接到Neo4j数据库")
            return
        
        properties = properties or {}
        properties["name"] = name
        properties["description"] = description
        
        if entity_type == "ShopDocument":
            properties["content"] = content
        
        # 业务约束：只为 ShopDocument 生成向量（用于“店铺-菜品打包文档”的语义检索）
        if entity_type == "ShopDocument" and content:
            embedding = self.embeddings.embed_query(content)
            properties["embedding"] = embedding
        
        query = f"""
        MERGE (e:{entity_type} {{name: $name}})
        SET e += $properties
        RETURN e
        """
        
        try:
            result = self.graph.query(query, {"name": name, "properties": properties})
            print(f"实体添加成功: {name} ({entity_type})")
            return result
        except Exception as e:
            print(f"实体添加失败: {e}")
            return None
    
    def add_relation(
        self,
        from_entity: Tuple[str, str],
        to_entity: Tuple[str, str],
        relation_type: str,
        properties: Dict = None
    ):
        """
        添加实体间的关系
        
        Args:
            from_entity: 起始实体 (名称, 类型)
            to_entity: 目标实体 (名称, 类型)
            relation_type: 关系类型（如HAS_FLAVOR, DESCRIBES等）
            properties: 关系属性（可选）
        """
        if self.graph is None:
            print("未连接到Neo4j数据库")
            return
        
        from_name, from_type = from_entity
        to_name, to_type = to_entity
        properties = properties or {}
        
        query = f"""
        MATCH (a:{from_type} {{name: $from_name}})
        MATCH (b:{to_type} {{name: $to_name}})
        MERGE (a)-[r:{relation_type}]->(b)
        SET r += $properties
        RETURN a, r, b
        """
        
        try:
            result = self.graph.query(
                query,
                {
                    "from_name": from_name,
                    "to_name": to_name,
                    "properties": properties
                }
            )
            print(f"关系添加成功: {from_name} -[{relation_type}]-> {to_name}")
            return result
        except Exception as e:
            print(f"关系添加失败: {e}")
            return None
    
    def summarize_shop_reviews(self, shop_name: str, reviews: List[str]) -> Dict:
        """
        使用大模型对店铺评价进行总结
        
        Args:
            shop_name: 店铺名称
            reviews: 评价内容列表
            
        Returns:
            包含总结信息的字典
        """
        prompt = ChatPromptTemplate.from_messages(SHOP_REVIEW_SUMMARY_PROMPT)
        chain = prompt | self.llm | StrOutputParser()
        
        reviews_text = "\n".join([f"- {review}" for review in reviews])
        
        try:
            result = chain.invoke({
                "shop_name": shop_name,
                "reviews": reviews_text
            })
            
            return json.loads(result)
        except Exception as e:
            print(f"评价总结失败: {e}")
            return {
                "cuisine_type": "其他",
                "average_rating": "暂无",
                "rating_count": len(reviews),
                "summary": "该店铺暂无有效评价总结",
                "tags": []
            }
    
    def create_shop_document(
        self,
        shop_name: str,
        shop_id: int,
        shop_open_time: str,
        review_summary: Dict,
        dish: Dict = None
    ):
        """
        创建ShopDocument实体（用于向量存储的打包文档）
        
        Args:
            shop_name: 店铺名称
            shop_open_time: 店铺营业时间
            review_summary: 评价总结结果（来自summarize_shop_reviews）
            dish: 单个菜品信息，包含name, flavor, type, description
        """
        # 构建content内容：用于向量检索的“店铺-菜品打包文本”
        content_parts = [f"店铺名称：{shop_name}"]
        content_parts.append(f"店铺营业时间：{shop_open_time}")
        content_parts.append(f"菜系类型：{review_summary.get('cuisine_type', '其他')}")
        content_parts.append(f"评分：{review_summary.get('average_rating', '暂无')}")
        content_parts.append(f"评价数：{review_summary.get('rating_count', 0)}")
        if review_summary.get("tags"):
            content_parts.append(f"标签：{', '.join(review_summary.get('tags', []))}")
        if review_summary.get("summary"):
            content_parts.append(f"评价摘要：{review_summary.get('summary')}")
        
        # 每个ShopDocument只包含一个菜品的信息
        if dish:
            dish_info = f"菜名：{dish.get('name', '未知')}"
            if dish.get('flavor'):
                dish_info += f"，口味：{dish.get('flavor')}"
            if dish.get('type'):
                dish_info += f"，类型：{dish.get('type')}"
            if dish.get('description'):
                dish_info += f"，描述：{dish.get('description')}"
            content_parts.append(dish_info)
        
        content = "\n".join(content_parts)
        
        # 构建description（简要描述）
        if dish:
            description = f"{shop_name} - {dish.get('name', '菜品')}"
            doc_name = f"{shop_name}_{dish.get('name', '菜品')}_文档"
        else:
            description = f"{shop_name} - {review_summary.get('cuisine_type', '餐饮店铺')}"
            doc_name = f"{shop_name}_店铺_文档"
            
        if review_summary.get('average_rating') != '暂无':
            description += f"，评分：{review_summary.get('average_rating')}"
        
        # 添加实体到知识图谱
        return self.add_entity(
            name=doc_name,
            entity_type="ShopDocument",
            properties={
                "shop_id": shop_id,
                "shop_name": shop_name,
                "shop_open_time": shop_open_time,
                "cuisine_type": review_summary.get("cuisine_type", "其他"),
                "average_rating": review_summary.get("average_rating", "暂无"),
                "rating_count": review_summary.get("rating_count", 0),
                "tags": ",".join(review_summary.get("tags", [])),
                "dish_name": dish.get("name", "") if dish else ""
            },
            description=description,
            content=content
        )
    
    def process_shop_reviews_to_document(
        self,
        shop_id: int,
        mysql_config: Dict,
        shop_name: str = None,
        shop_open_time: str = "00:00-00:00"
    ):
        """
        从MySQL获取店铺评价和菜品信息，创建ShopDocument
        
        Args:
            shop_id: 店铺ID
            mysql_config: MySQL配置字典
            shop_name: 店铺名称（可选，自动从数据库获取）
            shop_status: 店铺状态（默认营业中）
        """
        import pymysql
        
        conn = None
        try:
            conn = pymysql.connect(**mysql_config)
           
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                if not shop_name:
                    cursor.execute("SELECT name,open_hours FROM tb_shop WHERE id = %s", (shop_id,))
                    shop_info = cursor.fetchone()
                    if shop_info:
                        shop_name = shop_info["name"]
                        shop_open_time = shop_info["open_hours"]
                    else:
                        print(f"未找到店铺ID={shop_id}的信息")
                        return
                
                print(f"处理店铺: {shop_name} (ID={shop_id})")
                
                cursor.execute("""
                    SELECT content FROM tb_blog 
                    WHERE shop_id = %s AND content IS NOT NULL AND content != ''
                    ORDER BY create_time DESC LIMIT 20
                """, (shop_id,))
                reviews = [row["content"] for row in cursor.fetchall()]
                
                review_summary = self.summarize_shop_reviews(shop_name, reviews)
                
                cursor.execute("""
                    SELECT dish_name as name, dish_type as type, description 
                    FROM tb_shop_dish 
                    WHERE shop_id = %s
                """, (shop_id,))
                dishes = cursor.fetchall()
                
                # 业务特征：从描述里抽取一个“口味”标签用于检索/推荐
                for dish in dishes:
                    dish["flavor"] = ""
                    if dish.get("description"):
                        desc = dish["description"]
                        if "辣" in desc:
                            dish["flavor"] = "辣味"
                        elif "酸" in desc:
                            dish["flavor"] = "酸味"
                        elif "甜" in desc:
                            dish["flavor"] = "甜味"
                        elif "鲜" in desc:
                            dish["flavor"] = "鲜味"
                
                self.add_entity(
                    name=shop_name,
                    entity_type="Shop",
                    properties={
                        "shop_id": shop_id,
                        "shop_open_time": shop_open_time,
                        "cuisine_type": review_summary.get("cuisine_type", "其他"),
                        "rating": review_summary.get("average_rating", "暂无")
                    },
                    description=f"{shop_name} - {review_summary.get('cuisine_type', '餐饮店铺')}"
                )
                
                for dish in dishes:
                    self.add_entity(
                        name=dish["name"],
                        entity_type="Dish",
                        properties={
                            "type": dish.get("type", ""),
                            "flavor": dish.get("flavor", "")
                        },
                        description=dish.get("description", f"{dish['name']} - {dish.get('type', '')}")
                    )

                    self.create_shop_document(
                        shop_name=shop_name,
                        shop_id=shop_id,
                        shop_open_time=shop_open_time,
                        review_summary=review_summary,
                        dish=dish
                    )
                    
                    self.add_relation(
                        from_entity=(shop_name, "Shop"),
                        to_entity=(dish["name"], "Dish"),
                        relation_type="HAS_DISH"
                    )

                    self.add_relation(
                        from_entity=(dish["name"], "Dish"),
                        to_entity=(f"{shop_name}_{dish.get('name', '菜品')}_文档", "ShopDocument"),
                        relation_type="TO_DESCRIBES"
                    )
                
                print(f"✓ 店铺 {shop_name} 处理完成")
                
        except Exception as e:
            print(f"处理店铺评价失败: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if conn:
                conn.close()
