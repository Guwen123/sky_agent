import hashlib
import json
import re
from typing import Any, Dict, Optional

from langchain_core.tools import tool
from redis import Redis

from model.contants.contant import (
    REDIS_HOST,
    REDIS_PORT,
    REDIS_DB,
    REDIS_PASSWORD,
    RAG_CACHE_VERSION,
    RAG_CACHE_TTL_SECONDS,
    RAG_HOT_CACHE_TTL_SECONDS,
    RAG_HOT_QUERY_WINDOW_SECONDS,
    RAG_HOT_QUERY_THRESHOLD,
)
from model.workflow.rag.GraphRag import GraphRAG
from model.workflow.rag.vector import Vector


_GRAPH_RAG_SINGLETON = None
_REDIS_CLIENT = None


def _get_graph_rag() -> GraphRAG:
    global _GRAPH_RAG_SINGLETON
    if _GRAPH_RAG_SINGLETON is None:
        engine = GraphRAG()
        engine.init_vector_store("shop_dish_embeddings")
        _GRAPH_RAG_SINGLETON = engine
    return _GRAPH_RAG_SINGLETON


def _get_redis_client() -> Optional[Redis]:
    global _REDIS_CLIENT
    if _REDIS_CLIENT is False:
        return None

    if _REDIS_CLIENT is None:
        try:
            _REDIS_CLIENT = Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=REDIS_DB,
                password=REDIS_PASSWORD or None,
                decode_responses=True,
            )
            _REDIS_CLIENT.ping()
        except Exception as e:
            print(f"Redis连接失败: {e}")
            _REDIS_CLIENT = False
            return None

    return _REDIS_CLIENT


def _normalize_public_query(question: str, current_shop: str = "") -> Dict[str, Any]:
    raw_question = (question or "").strip()
    if not raw_question:
        return {"is_public": False, "cache_key": "", "normalized_query": "", "intent": "unknown"}

    private_keywords = (
        "我的", "我上次", "上次点", "历史订单", "订单", "地址", "手机号",
        "绑定", "账号", "支付", "配送", "购物车", "优惠券", "余额",
    )
    if any(keyword in raw_question for keyword in private_keywords):
        return {"is_public": False, "cache_key": "", "normalized_query": raw_question, "intent": "private"}

    normalized = raw_question.lower()
    if current_shop:
        normalized = re.sub(r"(这家店|这家|这店|他家|它家|刚才那家|上一家)", current_shop.lower(), normalized)

    intent = "general"
    intent_patterns = [
        ("recommend", r"(有什么推荐|推荐点什么|推荐什么|有啥推荐|必点|招牌菜?|特色菜?|值得点|吃什么|点什么)"),
        ("rating", r"(评分|评价|口碑|好吃吗|怎么样)"),
        ("business_hours", r"(营业时间|几点关门|几点开门|营业到几点|开门时间|关门时间)"),
        ("comparison", r"(对比|比较|哪个好|哪家更好)"),
    ]
    for intent_name, pattern in intent_patterns:
        if re.search(pattern, normalized):
            intent = intent_name
            normalized = re.sub(pattern, f" {intent_name} ", normalized)
            break

    stop_words = ("请问", "一下", "可以", "帮我", "看看", "呢", "吗", "呀", "吧")
    for word in stop_words:
        normalized = normalized.replace(word, " ")

    normalized = re.sub(r"[？?！!，,。.;；:：、\s]+", " ", normalized).strip()
    normalized = re.sub(r"\s+", " ", normalized)
    if not normalized:
        normalized = intent

    cache_hash = hashlib.md5(normalized.encode("utf-8")).hexdigest()
    return {
        "is_public": True,
        "cache_key": normalized,
        "cache_hash": cache_hash,
        "normalized_query": normalized,
        "intent": intent,
    }


def _build_graphrag_cache_meta(question: str, current_shop: str = "", top_k: int = 5) -> Dict[str, Any]:
    normalized = _normalize_public_query(question, current_shop=current_shop)
    if not normalized.get("is_public"):
        return {"normalized": normalized}

    cache_hash = normalized["cache_hash"]
    return {
        "normalized": normalized,
        "freq_key": f"agent:graphrag:hot:freq:{cache_hash}",
        "base_cache_key": f"agent:graphrag:cache:{RAG_CACHE_VERSION}:{top_k}:{cache_hash}",
        "hot_cache_key": f"agent:graphrag:hot:cache:{RAG_CACHE_VERSION}:{top_k}:{cache_hash}",
    }


def _read_graphrag_cache(cache_meta: Dict[str, Any]) -> Optional[str]:
    redis_client = _get_redis_client()
    base_cache_key = cache_meta.get("base_cache_key")
    hot_cache_key = cache_meta.get("hot_cache_key")
    freq_key = cache_meta.get("freq_key")
    if not redis_client or not base_cache_key or not hot_cache_key or not freq_key:
        return None

    try:
        freq = redis_client.incr(freq_key)
        if freq == 1:
            redis_client.expire(freq_key, RAG_HOT_QUERY_WINDOW_SECONDS)

        hot_payload = redis_client.get(hot_cache_key)
        if hot_payload:
            print(f"GraphRAG热点缓存命中: {cache_meta['normalized']['cache_key']}")
            return json.loads(hot_payload).get("result")

        base_payload = redis_client.get(base_cache_key)
        if not base_payload:
            return None

        if freq >= RAG_HOT_QUERY_THRESHOLD:
            redis_client.setex(hot_cache_key, RAG_HOT_CACHE_TTL_SECONDS, base_payload)
        print(f"GraphRAG缓存命中: {cache_meta['normalized']['cache_key']}")
        return json.loads(base_payload).get("result")
    except Exception as e:
        print(f"读取GraphRAG缓存失败: {e}")
        return None


def _write_graphrag_cache(cache_meta: Dict[str, Any], result: str):
    redis_client = _get_redis_client()
    base_cache_key = cache_meta.get("base_cache_key")
    hot_cache_key = cache_meta.get("hot_cache_key")
    freq_key = cache_meta.get("freq_key")
    if not redis_client or not base_cache_key or not hot_cache_key or not freq_key:
        return

    payload = json.dumps(
        {
            "result": result,
            "normalized_query": cache_meta["normalized"].get("normalized_query", ""),
            "intent": cache_meta["normalized"].get("intent", "general"),
        },
        ensure_ascii=False,
    )
    try:
        redis_client.setex(base_cache_key, RAG_CACHE_TTL_SECONDS, payload)
        freq = int(redis_client.get(freq_key) or 0)
        if freq >= RAG_HOT_QUERY_THRESHOLD:
            redis_client.setex(hot_cache_key, RAG_HOT_CACHE_TTL_SECONDS, payload)
    except Exception as e:
        print(f"写入GraphRAG缓存失败: {e}")


def queryRag(question: str) -> str:
    vector = Vector()
    result = vector.query(question)
    return f"RAG查询结果: {result}"


def queryGraphRag(question: str, current_shop: str = "", top_k: int = 5) -> str:
    try:
        cache_meta = _build_graphrag_cache_meta(question, current_shop=current_shop, top_k=top_k)
        cached_result = _read_graphrag_cache(cache_meta)
        if cached_result:
            return cached_result

        engine = _get_graph_rag()
        shop_ctx = {"name": current_shop, "id": 0} if current_shop else None
        graph_context, docs = engine.build_graph_context(question, current_shop=shop_ctx, top_k=top_k)
        result = f"GraphRAG上下文:\n{graph_context}\n\n候选文档数: {len(docs)}"
        _write_graphrag_cache(cache_meta, result)
        return result
    except Exception as e:
        return f"GraphRAG查询失败: {e}"


@tool(description="RAG路由工具：quality=fast|quality|auto，自动选择向量RAG或GraphRAG")
def queryKnowledge(question: str, quality: str = "auto", current_shop: str = "") -> str:
    q = (question or "").strip()
    quality_l = (quality or "auto").strip().lower()

    def _use_graph_auto() -> bool:
        triggers = ["对比", "比较", "营业", "评分", "高评分", "招牌", "推荐", "哪家"]
        return any(t in q for t in triggers)

    if quality_l in {"quality", "high", "graphrag", "graph"}:
        return queryGraphRag(question=q, current_shop=current_shop)
    if quality_l in {"fast", "vector", "chroma"}:
        return queryRag(question=q)
    if _use_graph_auto():
        return queryGraphRag(question=q, current_shop=current_shop)
    return queryRag(question=q)
