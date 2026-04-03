import base64
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from urllib import error, request

from model.workflow.mcp.tools.binding_store import BindingStore
from model.workflow.mcp.tools.text2sql import Text2SQL


ORDER_CONFIRMATION_PREFIX = "__ORDER_CONFIRMATION__"
DEFAULT_SKY_TAKE_OUT_SHOP_NAME = "sky_take_out 商家"

_TEXT2SQL = None


def get_text2sql() -> Text2SQL:
    global _TEXT2SQL
    if _TEXT2SQL is None:
        _TEXT2SQL = Text2SQL()
    return _TEXT2SQL


def parse_response_text(text: str) -> Dict[str, Any]:
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
        return {"data": data}
    except Exception:
        return {"raw": text}


def request_json(
    method: str,
    url: str,
    headers: Dict[str, str] = None,
    body: Dict[str, Any] = None,
    timeout: int = 15,
) -> Dict[str, Any]:
    payload = None
    req_headers = headers.copy() if headers else {}
    if body is not None:
        payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
        req_headers.setdefault("Content-Type", "application/json")

    req = request.Request(url=url, data=payload, headers=req_headers, method=method)

    try:
        with request.urlopen(req, timeout=timeout) as resp:
            text = resp.read().decode("utf-8")
            result = parse_response_text(text)
            result["_statusCode"] = getattr(resp, "status", 200)
            return result
    except error.HTTPError as exc:
        text = exc.read().decode("utf-8", errors="ignore")
        result = parse_response_text(text or str(exc))
        result["_statusCode"] = exc.code
        result["_httpError"] = True
        return result


def build_token_headers(token: str) -> Dict[str, str]:
    return {
        "authentication": token,
        "Authorization": token,
        "token": token,
        "Content-Type": "application/json",
    }


def get_binding(user_id: str) -> Dict[str, Any]:
    return BindingStore().get_binding_info(user_id=user_id)


def decode_jwt_payload(token: str) -> Dict[str, Any]:
    text = str(token or "").strip()
    if not text:
        return {}

    if text.lower().startswith("bearer "):
        text = text[7:].strip()

    parts = text.split(".")
    if len(parts) < 2:
        return {}

    try:
        payload = parts[1]
        payload += "=" * (-len(payload) % 4)
        data = json.loads(base64.urlsafe_b64decode(payload.encode("utf-8")).decode("utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def expired_token_message(service_name: str, token: str) -> str:
    payload = decode_jwt_payload(token)
    exp = payload.get("exp")
    if not isinstance(exp, (int, float)):
        return ""

    tz = timezone(timedelta(hours=8))
    expire_at = datetime.fromtimestamp(float(exp), tz=tz)
    now_at = datetime.now(tz=tz)
    if expire_at > now_at:
        return ""

    expire_text = expire_at.strftime("%Y-%m-%d %H:%M:%S %z")
    now_text = now_at.strftime("%Y-%m-%d %H:%M:%S %z")
    return (
        f"{service_name} 当前绑定的 token 已过期。"
        f"过期时间是 {expire_text}，当前时间是 {now_text}。"
        f"请重新绑定 {service_name} 后再继续。"
    )


def service_error(data: Dict[str, Any]) -> str:
    if not isinstance(data, dict):
        return ""

    message = data.get("errorMsg") or data.get("message") or data.get("msg") or data.get("raw")

    if data.get("success") is False:
        return str(message or "unknown error")

    code = data.get("code")
    if isinstance(code, int) and code not in {0, 1, 200}:
        return str(message or f"code={code}")

    status_code = data.get("_statusCode")
    if isinstance(status_code, int) and status_code >= 400:
        return str(message or f"HTTP {status_code}")

    return ""


def auth_failure_message(service_name: str, binding: Dict[str, Any], data: Dict[str, Any]) -> str:
    status_code = data.get("_statusCode")
    if status_code != 401:
        return ""

    if service_name == "sky_take_out":
        token = binding.get("sky_take_out_token")
        expired_message = expired_token_message("sky_take_out", str(token or ""))
        if expired_message:
            return expired_message

        if binding.get("sky_take_out_user_id"):
            return (
                "sky_take_out 已绑定，但当前请求被外卖后端拒绝（401）。"
                "请优先检查 sky_take_out 的用户端 JWT/拦截器配置，确认 "
                "/user/user/login 和 /user/order/** 使用的是同一套用户 token 解析逻辑。"
            )
        return "sky_take_out 当前没有可用的绑定用户信息，且接口返回了 401，请先重新绑定。"

    if service_name == "hmdp":
        token = binding.get("hmdp_token")
        expired_message = expired_token_message("hmdp", str(token or ""))
        if expired_message:
            return expired_message
        return "hmdp 已绑定，但当前保存的 token 被服务端拒绝（401），请重新绑定 hmdp。"

    return "当前绑定 token 被服务端拒绝（401），请重新绑定。"


def _blog_records_container(data: Dict[str, Any]):
    payload = data.get("data")
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("records"), list):
        return payload["records"]
    return None


def enrich_blog_payload_with_shop_names(data: Dict[str, Any]) -> Dict[str, Any]:
    records = _blog_records_container(data)
    if not records:
        return data

    shop_ids = [record.get("shopId") for record in records if isinstance(record, dict)]
    shop_info_map = get_text2sql().get_hmdp_shop_info_by_ids(shop_ids)

    for record in records:
        if not isinstance(record, dict):
            continue
        shop_id = record.get("shopId")
        try:
            normalized_shop_id = int(shop_id)
        except Exception:
            normalized_shop_id = None

        shop_info = shop_info_map.get(normalized_shop_id) if normalized_shop_id is not None else None
        if shop_info:
            record["shopName"] = shop_info.get("name")
            record["shopArea"] = shop_info.get("area")
            record["shopAddress"] = shop_info.get("address")
            record["shopScore"] = shop_info.get("score")
            record["shopAvgPrice"] = shop_info.get("avg_price")
        record.pop("shopId", None)

    return data
