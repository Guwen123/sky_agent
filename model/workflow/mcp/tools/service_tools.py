import json
from typing import Any, Dict, List
from urllib import error, parse, request

from langchain_core.tools import tool

from model.contants.contant import HMDP_BASE_URL, SKY_TAKE_OUT_BASE_URL
from model.workflow.mcp.tools.binding_store import BindingStore
from model.workflow.mcp.tools.pending_order_store import PendingTakeoutOrderStore
from model.workflow.mcp.tools.text2sql import Text2SQL


ORDER_CONFIRMATION_PREFIX = "__ORDER_CONFIRMATION__"
DEFAULT_SKY_TAKE_OUT_SHOP_NAME = "sky_take_out 商家"

_TEXT2SQL = None


def _get_text2sql() -> Text2SQL:
    global _TEXT2SQL
    if _TEXT2SQL is None:
        _TEXT2SQL = Text2SQL()
    return _TEXT2SQL


def _parse_response_text(text: str) -> Dict[str, Any]:
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
        return {"data": data}
    except Exception:
        return {"raw": text}


def _request_json(
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
            result = _parse_response_text(text)
            result["_statusCode"] = getattr(resp, "status", 200)
            return result
    except error.HTTPError as exc:
        text = exc.read().decode("utf-8", errors="ignore")
        result = _parse_response_text(text or str(exc))
        result["_statusCode"] = exc.code
        result["_httpError"] = True
        return result


def _build_token_headers(token: str) -> Dict[str, str]:
    return {
        "authentication": token,
        "Authorization": token,
        "token": token,
        "Content-Type": "application/json",
    }


def _binding(user_id: str) -> Dict[str, Any]:
    return BindingStore().get_binding_info(user_id=user_id)


def _service_error(data: Dict[str, Any]) -> str:
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


def _auth_failure_message(service_name: str, binding: Dict[str, Any], data: Dict[str, Any]) -> str:
    status_code = data.get("_statusCode")
    if status_code != 401:
        return ""

    if service_name == "sky_take_out":
        user_id = binding.get("sky_take_out_user_id")
        if user_id:
            return (
                "sky_take_out 已绑定，但当前请求被外卖后端拒绝（401）。"
                "请优先检查 sky_take_out 的用户端 JWT/拦截器配置，确认 /user/user/login "
                "和 /user/order/** 使用的是同一套用户 token 解析逻辑。"
            )
        return "sky_take_out 当前没有可用的绑定用户信息，且接口返回了 401，请先重新绑定。"

    if service_name == "hmdp":
        return "hmdp 已绑定，但当前保存的 token 被服务端拒绝（401），请重新绑定 hmdp。"

    return "当前绑定 token 被服务端拒绝（401），请重新绑定。"


def _blog_records_container(data: Dict[str, Any]):
    payload = data.get("data")
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("records"), list):
        return payload["records"]
    return None


def _enrich_blog_payload_with_shop_names(data: Dict[str, Any]) -> Dict[str, Any]:
    records = _blog_records_container(data)
    if not records:
        return data

    shop_ids = [record.get("shopId") for record in records if isinstance(record, dict)]
    shop_info_map = _get_text2sql().get_hmdp_shop_info_by_ids(shop_ids)

    for record in records:
        if not isinstance(record, dict):
            continue
        shop_id = record.get("shopId")
        shop_info = shop_info_map.get(int(shop_id)) if shop_id is not None and int(shop_id) in shop_info_map else None
        if shop_info:
            record["shopName"] = shop_info.get("name")
            record["shopArea"] = shop_info.get("area")
            record["shopAddress"] = shop_info.get("address")
            record["shopScore"] = shop_info.get("score")
            record["shopAvgPrice"] = shop_info.get("avg_price")
        record.pop("shopId", None)

    return data


def _parse_cart_items(cart_items_json: str) -> List[Dict[str, Any]]:
    try:
        cart_items = json.loads(cart_items_json or "[]")
    except Exception as exc:
        raise ValueError("cart_items_json 不是合法 JSON，请传数组。") from exc

    if not isinstance(cart_items, list) or not cart_items:
        raise ValueError('cart_items_json 不能为空，例如 [{"dishId":1,"setmealId":null,"dishFlavor":"微辣"}]')

    normalized_items: List[Dict[str, Any]] = []
    for item in cart_items:
        if not isinstance(item, dict):
            raise ValueError("cart_items_json 中每个元素都必须是对象。")
        normalized_items.append(
            {
                "dishId": item.get("dishId"),
                "setmealId": item.get("setmealId"),
                "dishFlavor": item.get("dishFlavor", ""),
                "number": int(item.get("number") or 1),
            }
        )
    return normalized_items


def _build_address_text(address_row: Dict[str, Any]) -> str:
    if not address_row:
        return ""
    return "".join(
        str(address_row.get(key) or "")
        for key in ("province_name", "city_name", "district_name", "detail")
    ).strip()


def _build_order_preview(user_id: str, address_book_id: int, cart_items: List[Dict[str, Any]]) -> Dict[str, Any]:
    binding = _binding(user_id=user_id)
    sky_user_id = binding.get("sky_take_out_user_id")
    text2sql = _get_text2sql()

    address_row = text2sql.get_sky_take_out_address(address_book_id=int(address_book_id), user_id=sky_user_id)
    if not address_row:
        raise ValueError("未找到对应的收货地址，请检查 address_book_id 是否正确。")

    dish_ids = [item.get("dishId") for item in cart_items if item.get("dishId") is not None]
    setmeal_ids = [item.get("setmealId") for item in cart_items if item.get("setmealId") is not None]

    dish_map = text2sql.get_sky_take_out_dishes_by_ids(dish_ids)
    setmeal_map = text2sql.get_sky_take_out_setmeals_by_ids(setmeal_ids)

    preview_items: List[Dict[str, Any]] = []
    for item in cart_items:
        dish_id = item.get("dishId")
        setmeal_id = item.get("setmealId")
        quantity = int(item.get("number") or 1)
        flavor = (item.get("dishFlavor") or "").strip()

        name = None
        item_type = "dish"
        if dish_id is not None:
            name = (dish_map.get(int(dish_id)) or {}).get("name")
        elif setmeal_id is not None:
            item_type = "setmeal"
            name = (setmeal_map.get(int(setmeal_id)) or {}).get("name")

        if not name:
            name = f"未识别菜品(dishId={dish_id}, setmealId={setmeal_id})"

        preview_items.append(
            {
                "type": item_type,
                "name": name,
                "quantity": quantity,
                "flavor": flavor,
                "display_text": f"{name} x{quantity}" + (f"（{flavor}）" if flavor else ""),
            }
        )

    address_text = _build_address_text(address_row)
    summary_lines = [
        "请先确认以下点单信息：",
        f"店铺：{DEFAULT_SKY_TAKE_OUT_SHOP_NAME}",
        "菜品：",
    ]
    summary_lines.extend(f"{idx}. {item['display_text']}" for idx, item in enumerate(preview_items, start=1))
    summary_lines.append(f"地址：{address_text or '-'}")
    summary_lines.append(
        f"收货人：{address_row.get('consignee') or '-'} {address_row.get('phone') or ''}".rstrip()
    )
    summary_lines.append("确认无误后，请点击“确认下单”或发送“确认下单”；若不下单，请点击“取消下单”或发送“取消下单”。")

    return {
        "shop_name": DEFAULT_SKY_TAKE_OUT_SHOP_NAME,
        "address": address_text,
        "consignee": address_row.get("consignee") or "",
        "phone": address_row.get("phone") or "",
        "items": preview_items,
        "message": "\n".join(summary_lines),
    }


def _order_confirmation_text(preview: Dict[str, Any]) -> str:
    return ORDER_CONFIRMATION_PREFIX + json.dumps(
        {
            "shopName": preview.get("shop_name") or DEFAULT_SKY_TAKE_OUT_SHOP_NAME,
            "address": preview.get("address") or "",
            "consignee": preview.get("consignee") or "",
            "phone": preview.get("phone") or "",
            "items": preview.get("items") or [],
            "message": preview.get("message") or "",
            "confirmText": "确认下单",
            "cancelText": "取消下单",
        },
        ensure_ascii=False,
    )


def _submit_takeout_order(user_id: str, pending_payload: Dict[str, Any]) -> str:
    binding = _binding(user_id=user_id)
    token = binding.get("sky_take_out_token")
    if not token:
        return "外卖下单失败：未绑定 sky_take_out token，请先绑定。"

    headers = _build_token_headers(str(token))
    cart_items = pending_payload.get("cart_items") or []
    add_url = f"{SKY_TAKE_OUT_BASE_URL}/user/shoppingCart/add"
    for item in cart_items:
        add_resp = _request_json(
            "POST",
            add_url,
            headers=headers,
            body={
                "dishId": item.get("dishId"),
                "setmealId": item.get("setmealId"),
                "dishFlavor": item.get("dishFlavor", ""),
            },
        )
        auth_failure = _auth_failure_message("sky_take_out", binding, add_resp)
        if auth_failure:
            return f"外卖下单失败：{auth_failure}"
        service_error = _service_error(add_resp)
        if service_error:
            return f"外卖下单失败：购物车添加失败：{service_error}"

    submit_url = f"{SKY_TAKE_OUT_BASE_URL}/user/order/submit"
    submit_body = {
        "addressBookId": int(pending_payload["address_book_id"]),
        "payMethod": int(pending_payload.get("pay_method", 1)),
        "remark": pending_payload.get("remark", "") or "",
        "estimatedDeliveryTime": pending_payload.get("estimated_delivery_time") or None,
        "deliveryStatus": int(pending_payload.get("delivery_status", 1)),
        "tablewareNumber": int(pending_payload.get("tableware_number", 0)),
        "tablewareStatus": int(pending_payload.get("tableware_status", 1)),
        "packAmount": int(pending_payload.get("pack_amount", 0)),
        "amount": float(pending_payload.get("amount", 0.0)),
    }
    data = _request_json("POST", submit_url, headers=headers, body=submit_body)
    auth_failure = _auth_failure_message("sky_take_out", binding, data)
    if auth_failure:
        return f"外卖下单失败：{auth_failure}"
    service_error = _service_error(data)
    if service_error:
        return f"外卖下单失败：{service_error}"

    preview = pending_payload.get("preview") or {}
    return json.dumps(
        {
            "message": "外卖下单成功",
            "shopName": preview.get("shop_name") or DEFAULT_SKY_TAKE_OUT_SHOP_NAME,
            "address": preview.get("address") or "",
            "items": preview.get("items") or [],
            "result": data,
        },
        ensure_ascii=False,
    )


@tool(description="查看热门博客：调用 hmdp 的 /blog/hot 接口，并补充店铺名称")
def getHotBlogs(current: int = 1) -> str:
    try:
        query = parse.urlencode({"current": int(current)})
        url = f"{HMDP_BASE_URL}/blog/hot?{query}"
        data = _request_json("GET", url)
        service_error = _service_error(data)
        if service_error:
            return f"获取热门博客失败: {service_error}"
        data = _enrich_blog_payload_with_shop_names(data)
        return json.dumps(data, ensure_ascii=False)
    except Exception as e:
        return f"获取热门博客失败: {e}"


@tool(description="查看我的历史博客：根据绑定的 hmdp_user_id 调用 hmdp 的 /blog/of/user，并补充店铺名称")
def getMyBlogHistory(user_id: str, current: int = 1) -> str:
    try:
        binding = _binding(user_id=user_id)
        hmdp_user_id = binding.get("hmdp_user_id")
        if not hmdp_user_id:
            return "未绑定 hmdp 用户，请先绑定。"

        query = parse.urlencode({"current": int(current), "id": int(hmdp_user_id)})
        url = f"{HMDP_BASE_URL}/blog/of/user?{query}"

        headers = {}
        token = binding.get("hmdp_token")
        if token:
            headers = _build_token_headers(str(token))

        data = _request_json("GET", url, headers=headers)
        auth_failure = _auth_failure_message("hmdp", binding, data)
        if auth_failure:
            return f"获取历史博客失败: {auth_failure}"
        service_error = _service_error(data)
        if service_error:
            return f"获取历史博客失败: {service_error}"
        data = _enrich_blog_payload_with_shop_names(data)
        return json.dumps(data, ensure_ascii=False)
    except Exception as e:
        return f"获取历史博客失败: {e}"


@tool(description="查看历史订单信息：调用 sky_take_out 的 /user/order/historyOrders")
def getOrderHistory(
    user_id: str,
    page: int = 1,
    page_size: int = 10,
    number: str = "",
    phone: str = "",
    status: int = 0,
    begin_time: str = "",
    end_time: str = "",
) -> str:
    try:
        binding = _binding(user_id=user_id)
        token = binding.get("sky_take_out_token")
        if not token:
            return "未绑定 sky_take_out token，请先绑定。"

        headers = _build_token_headers(str(token))
        query_params = {
            "page": int(page),
            "pageSize": int(page_size),
        }
        if number:
            query_params["number"] = number
        if phone:
            query_params["phone"] = phone
        if status:
            query_params["status"] = int(status)
        if begin_time:
            query_params["beginTime"] = begin_time
        if end_time:
            query_params["endTime"] = end_time

        url = f"{SKY_TAKE_OUT_BASE_URL}/user/order/historyOrders?{parse.urlencode(query_params)}"
        data = _request_json("GET", url, headers=headers)
        auth_failure = _auth_failure_message("sky_take_out", binding, data)
        if auth_failure:
            return f"获取历史订单失败: {auth_failure}"
        service_error = _service_error(data)
        if service_error:
            return f"获取历史订单失败: {service_error}"
        return json.dumps(data, ensure_ascii=False)
    except Exception as e:
        return f"获取历史订单失败: {e}"


@tool(description="准备外卖订单：先生成店铺、菜品、地址预览并等待用户确认，不会直接提交订单")
def placeTakeoutOrder(
    user_id: str,
    address_book_id: int,
    cart_items_json: str,
    pay_method: int = 1,
    remark: str = "",
    estimated_delivery_time: str = "",
    delivery_status: int = 1,
    tableware_number: int = 0,
    tableware_status: int = 1,
    pack_amount: int = 0,
    amount: float = 0.0,
) -> str:
    try:
        binding = _binding(user_id=user_id)
        token = binding.get("sky_take_out_token")
        if not token:
            return "未绑定 sky_take_out token，请先绑定。"

        cart_items = _parse_cart_items(cart_items_json)
        preview = _build_order_preview(user_id=user_id, address_book_id=int(address_book_id), cart_items=cart_items)

        PendingTakeoutOrderStore().set(
            user_id=user_id,
            payload={
                "address_book_id": int(address_book_id),
                "cart_items": cart_items,
                "pay_method": int(pay_method),
                "remark": remark or "",
                "estimated_delivery_time": estimated_delivery_time or "",
                "delivery_status": int(delivery_status),
                "tableware_number": int(tableware_number),
                "tableware_status": int(tableware_status),
                "pack_amount": int(pack_amount),
                "amount": float(amount),
                "preview": preview,
            },
        )
        return _order_confirmation_text(preview)
    except Exception as e:
        return f"外卖下单预览失败: {e}"


@tool(description="确认提交待确认的外卖订单。仅当用户明确表示确认下单后调用")
def confirmPendingTakeoutOrder(user_id: str) -> str:
    pending_payload = PendingTakeoutOrderStore().get(user_id=user_id)
    if not pending_payload:
        return "当前没有待确认的外卖订单。"

    result = _submit_takeout_order(user_id=user_id, pending_payload=pending_payload)
    if not result.startswith("外卖下单失败"):
        PendingTakeoutOrderStore().clear(user_id=user_id)
    return result


@tool(description="取消当前待确认的外卖订单")
def cancelPendingTakeoutOrder(user_id: str) -> str:
    pending_payload = PendingTakeoutOrderStore().pop(user_id=user_id)
    if not pending_payload:
        return "当前没有待确认的外卖订单，无需取消。"
    return "已取消本次待确认的外卖订单。"
