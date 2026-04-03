import json
from urllib import parse

from langchain_core.tools import tool

from model.contants.contant import HMDP_BASE_URL, SKY_TAKE_OUT_BASE_URL
from model.workflow.mcp.tools.pending_order_store import PendingTakeoutOrderStore
from model.workflow.mcp.tools.service_support import (
    auth_failure_message,
    build_token_headers,
    enrich_blog_payload_with_shop_names,
    get_binding,
    get_text2sql,
    request_json,
    service_error,
)
from model.workflow.mcp.tools.takeout_support import (
    available_dish_text,
    build_order_preview,
    default_estimated_delivery_time,
    extract_quantity,
    extract_spice,
    match_dishes_from_text,
    order_confirmation_text,
    parse_cart_items,
    select_default_address,
    serialize_address_options,
    submit_takeout_order,
    validate_cart_items_and_amount,
)


def _join_errors(validation: dict, default_message: str) -> str:
    return "；".join(validation.get("errors") or [default_message])


@tool(description="根据自然语言点单请求准备外卖订单，自动识别菜品、默认地址和口味；仅生成确认单，不会直接提交订单")
def prepareTakeoutOrderFromText(user_id: str, user_text: str) -> str:
    try:
        binding = get_binding(user_id=user_id)
        token = binding.get("sky_take_out_token")
        if not token:
            return "未绑定 sky_take_out token，请先绑定。"

        sky_user_id = binding.get("sky_take_out_user_id")
        if not sky_user_id:
            return "当前账号缺少 sky_take_out_user_id，暂时无法自动点单，请先重新绑定 sky_take_out。"

        match_result = match_dishes_from_text(user_text)
        matched = match_result.get("matched") or []
        candidate_query = str(match_result.get("query") or "").strip()
        suggestions = match_result.get("suggestions") or []

        if not matched:
            available_text = available_dish_text()
            if candidate_query:
                if suggestions:
                    return (
                        "当前外卖系统是单商家下单，不支持“湘味人家 / 蜀味轩”这类店铺切换。\n"
                        f"另外未找到“{candidate_query}”，你可以改点这些更接近的菜：{'、'.join(suggestions)}。"
                    )
                if available_text:
                    return (
                        "当前外卖系统是单商家下单，不支持“湘味人家 / 蜀味轩”这类店铺切换。\n"
                        f"另外未找到“{candidate_query}”，目前可选菜品示例：{available_text}。"
                    )
                return f"当前外卖系统未找到“{candidate_query}”，请换一道菜试试。"
            return "我还没识别出你要点的具体菜品，请直接说菜名，例如：帮我点一份老坛酸菜鱼。"

        selected_dish = matched[0]
        quantity = extract_quantity(user_text)
        spice = extract_spice(user_text)
        cart_items = [
            {
                "dishId": int(selected_dish["id"]),
                "setmealId": None,
                "dishFlavor": spice,
                "number": quantity,
            }
        ]
        validation = validate_cart_items_and_amount(cart_items)
        if not validation.get("ok"):
            return f"外卖点单准备失败：{_join_errors(validation, '菜品校验失败')}"

        addresses = get_text2sql().list_sky_take_out_addresses(int(sky_user_id))
        if not addresses:
            return "当前账号下没有可用收货地址，请先在外卖系统里新增地址。"

        address_row = select_default_address(addresses)
        address_options = serialize_address_options(addresses)
        estimated_delivery_time = default_estimated_delivery_time()

        preview = build_order_preview(
            user_id=user_id,
            address_book_id=int(address_row["id"]),
            cart_items=cart_items,
            address_options=address_options,
            amount=float(validation.get("amount") or 0.0),
            remark="",
            estimated_delivery_time=estimated_delivery_time,
        )

        PendingTakeoutOrderStore().set(
            user_id=user_id,
            payload={
                "address_book_id": int(address_row["id"]),
                "cart_items": cart_items,
                "address_options": address_options,
                "pay_method": 1,
                "remark": "",
                "estimated_delivery_time": estimated_delivery_time,
                "delivery_status": 1,
                "tableware_number": 0,
                "tableware_status": 1,
                "pack_amount": 0,
                "amount": float(validation.get("amount") or 0.0),
                "preview": preview,
            },
        )
        return order_confirmation_text(preview)
    except Exception as e:
        return f"外卖点单准备失败: {e}"


@tool(description="查看热门博客：调用 hmdp 的 /blog/hot 接口，并补充店铺名称")
def getHotBlogs(current: int = 1) -> str:
    try:
        query = parse.urlencode({"current": int(current)})
        url = f"{HMDP_BASE_URL}/blog/hot?{query}"
        data = request_json("GET", url)
        error_text = service_error(data)
        if error_text:
            return f"获取热门博客失败: {error_text}"
        data = enrich_blog_payload_with_shop_names(data)
        return json.dumps(data, ensure_ascii=False)
    except Exception as e:
        return f"获取热门博客失败: {e}"


@tool(description="查看我的历史博客：根据绑定的 hmdp_user_id 调用 hmdp 的 /blog/of/user，并补充店铺名称")
def getMyBlogHistory(user_id: str, current: int = 1) -> str:
    try:
        binding = get_binding(user_id=user_id)
        hmdp_user_id = binding.get("hmdp_user_id")
        if not hmdp_user_id:
            return "您尚未绑定 hmdp 用户账号，无法查看历史博客。是否需要协助绑定？请提供您的 hmdp 绑定 ID 或用户名，我将为您完成绑定操作。"

        query = parse.urlencode({"current": int(current), "id": int(hmdp_user_id)})
        url = f"{HMDP_BASE_URL}/blog/of/user?{query}"

        headers = {}
        token = binding.get("hmdp_token")
        if token:
            headers = build_token_headers(str(token))

        data = request_json("GET", url, headers=headers)
        auth_failure = auth_failure_message("hmdp", binding, data)
        if auth_failure:
            return f"获取历史博客失败: {auth_failure}"
        error_text = service_error(data)
        if error_text:
            return f"获取历史博客失败: {error_text}"
        data = enrich_blog_payload_with_shop_names(data)
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
        binding = get_binding(user_id=user_id)
        token = binding.get("sky_take_out_token")
        if not token:
            return "未绑定 sky_take_out token，请先绑定。"

        headers = build_token_headers(str(token))
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
        data = request_json("GET", url, headers=headers)
        auth_failure = auth_failure_message("sky_take_out", binding, data)
        if auth_failure:
            return f"获取历史订单失败: {auth_failure}"
        error_text = service_error(data)
        if error_text:
            return f"获取历史订单失败: {error_text}"
        return json.dumps(data, ensure_ascii=False)
    except Exception as e:
        return f"获取历史订单失败: {e}"


@tool(description="准备外卖订单：先生成店铺、菜品、地址预览并等待用户确认，不会直接提交订单")
def placeTakeoutOrder(
    user_id: str,
    address_book_id: int,
    cart_items_json: str = "",
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
        binding = get_binding(user_id=user_id)
        token = binding.get("sky_take_out_token")
        if not token:
            return "未绑定 sky_take_out token，请先绑定。"

        pending_payload = PendingTakeoutOrderStore().get(user_id=user_id) or {}
        if str(cart_items_json or "").strip():
            cart_items = parse_cart_items(cart_items_json)
        else:
            cart_items = pending_payload.get("cart_items") or []
            if not cart_items:
                return "缺少待下单菜品信息，请重新告诉我要点什么。"

        validation = validate_cart_items_and_amount(cart_items)
        if not validation.get("ok"):
            return f"外卖下单预览失败：{_join_errors(validation, '菜品校验失败')}"

        resolved_address_book_id = int(address_book_id or pending_payload.get("address_book_id") or 0)
        if resolved_address_book_id <= 0:
            return "缺少收货地址，请先选择地址后再确认下单。"

        final_remark = str(remark or pending_payload.get("remark") or "").strip()
        final_estimated_delivery_time = str(
            estimated_delivery_time or pending_payload.get("estimated_delivery_time") or default_estimated_delivery_time()
        ).strip()
        final_amount = float(validation.get("amount") or amount or 0.0)
        address_options = pending_payload.get("address_options") or []

        preview = build_order_preview(
            user_id=user_id,
            address_book_id=int(resolved_address_book_id),
            cart_items=cart_items,
            address_options=address_options,
            amount=final_amount,
            remark=final_remark,
            estimated_delivery_time=final_estimated_delivery_time,
        )

        PendingTakeoutOrderStore().set(
            user_id=user_id,
            payload={
                "address_book_id": int(resolved_address_book_id),
                "cart_items": cart_items,
                "address_options": address_options,
                "pay_method": int(pay_method),
                "remark": final_remark,
                "estimated_delivery_time": final_estimated_delivery_time,
                "delivery_status": int(delivery_status),
                "tableware_number": int(tableware_number),
                "tableware_status": int(tableware_status),
                "pack_amount": int(pack_amount),
                "amount": final_amount,
                "preview": preview,
            },
        )
        return order_confirmation_text(preview)
    except Exception as e:
        return f"外卖下单预览失败: {e}"


@tool(description="确认提交待确认的外卖订单。仅当用户明确表示确认下单后调用")
def confirmPendingTakeoutOrder(user_id: str, address_book_id: int = 0, remark: str = "") -> str:
    try:
        pending_payload = PendingTakeoutOrderStore().get(user_id=user_id)
        if not pending_payload:
            return "当前没有待确认的外卖订单。"

        final_address_book_id = int(address_book_id or pending_payload.get("address_book_id") or 0)
        if final_address_book_id <= 0:
            return "缺少收货地址，请重新选择地址后再确认下单。"

        validation = validate_cart_items_and_amount(pending_payload.get("cart_items") or [])
        if not validation.get("ok"):
            return f"外卖下单失败：{_join_errors(validation, '菜品校验失败')}"

        final_remark = str(remark or pending_payload.get("remark") or "").strip()
        final_estimated_delivery_time = str(
            pending_payload.get("estimated_delivery_time") or default_estimated_delivery_time()
        ).strip()
        final_amount = float(validation.get("amount") or pending_payload.get("amount") or 0.0)

        preview = build_order_preview(
            user_id=user_id,
            address_book_id=final_address_book_id,
            cart_items=pending_payload.get("cart_items") or [],
            address_options=pending_payload.get("address_options") or [],
            amount=final_amount,
            remark=final_remark,
            estimated_delivery_time=final_estimated_delivery_time,
        )

        pending_payload["address_book_id"] = final_address_book_id
        pending_payload["remark"] = final_remark
        pending_payload["estimated_delivery_time"] = final_estimated_delivery_time
        pending_payload["amount"] = final_amount
        pending_payload["preview"] = preview
        PendingTakeoutOrderStore().set(user_id=user_id, payload=pending_payload)

        result = submit_takeout_order(user_id=user_id, pending_payload=pending_payload)
        if not result.startswith("外卖下单失败"):
            PendingTakeoutOrderStore().clear(user_id=user_id)
        return result
    except Exception as e:
        return f"外卖下单失败: {e}"


@tool(description="取消当前待确认的外卖订单")
def cancelPendingTakeoutOrder(user_id: str) -> str:
    pending_payload = PendingTakeoutOrderStore().pop(user_id=user_id)
    if not pending_payload:
        return "当前没有待确认的外卖订单，无需取消。"
    return "已取消本次待确认的外卖订单。"
