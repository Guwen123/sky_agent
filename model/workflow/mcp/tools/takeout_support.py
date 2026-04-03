import difflib
import json
import re
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List

from model.contants.contant import SKY_TAKE_OUT_BASE_URL
from model.workflow.mcp.tools.service_support import (
    DEFAULT_SKY_TAKE_OUT_SHOP_NAME,
    ORDER_CONFIRMATION_PREFIX,
    auth_failure_message,
    build_token_headers,
    get_binding,
    get_text2sql,
    request_json,
    service_error,
)


def parse_cart_items(cart_items_json: str) -> List[Dict[str, Any]]:
    try:
        cart_items = json.loads(cart_items_json or "[]")
    except Exception as exc:
        raise ValueError("cart_items_json 不是合法 JSON，请传数组。") from exc

    if not isinstance(cart_items, list) or not cart_items:
        raise ValueError('cart_items_json 不能为空，例如：[{"dishId":1,"setmealId":null,"dishFlavor":"微辣"}]')

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


def build_address_text(address_row: Dict[str, Any]) -> str:
    if not address_row:
        return ""
    return "".join(
        str(address_row.get(key) or "")
        for key in ("province_name", "city_name", "district_name", "detail")
    ).strip()


def extract_quantity(text: str) -> int:
    normalized = str(text or "")
    digit_match = re.search(r"(\d+)\s*(份|个|碗|盘|盒|只)?", normalized)
    if digit_match:
        return max(int(digit_match.group(1)), 1)

    chinese_map = {
        "一": 1,
        "二": 2,
        "两": 2,
        "三": 3,
        "四": 4,
        "五": 5,
        "六": 6,
        "七": 7,
        "八": 8,
        "九": 9,
        "十": 10,
    }
    chinese_match = re.search(r"(一|二|两|三|四|五|六|七|八|九|十)\s*(份|个|碗|盘|盒|只)?", normalized)
    if chinese_match:
        return chinese_map.get(chinese_match.group(1), 1)
    return 1


def extract_spice(text: str) -> str:
    normalized = str(text or "")
    for keyword in ("特辣", "重辣", "中辣", "微辣", "不辣"):
        if keyword in normalized:
            return keyword
    return ""


def _split_user_text_segments(text: str) -> List[str]:
    segments: List[str] = []
    for raw_line in re.split(r"[\r\n]+", str(text or "")):
        line = raw_line.strip()
        if line:
            segments.append(line)
    return segments


def _clean_candidate_dish_phrase(candidate: str) -> str:
    text = str(candidate or "").strip()
    if not text:
        return ""

    text = re.sub(r"^(?:点|来|下单|换成|改成|改点|要)\s*", "", text).strip()
    text = re.sub(
        r"(使用默认地址|默认收货地址|默认地址|要重辣|要中辣|要微辣|要特辣|不要辣|不辣)$",
        "",
        text,
    ).strip(" ，。")
    return text


def _extract_candidate_dish_phrase(text: str) -> str:
    normalized = str(text or "").strip()
    patterns = [
        r"(?:帮我|给我|我要|我想|麻烦)?(?:点|来|下单|买)?(?:一份|1份|一个|1个)?(.+?)(?:，|,|。|\.|$)",
        r"(?:换成|改成|改点)(.+?)(?:，|,|。|\.|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, normalized)
        if match:
            candidate = _clean_candidate_dish_phrase(match.group(1))
            if candidate:
                return candidate

    fallback = _clean_candidate_dish_phrase(normalized)
    if (
        fallback
        and len(fallback) <= 20
        and not any(keyword in fallback for keyword in ("默认地址", "收货地址", "湘味人家", "蜀味轩", "选择"))
    ):
        return fallback
    return ""


def match_dishes_from_text(user_text: str) -> Dict[str, Any]:
    dishes = get_text2sql().list_sky_take_out_dishes()
    if not dishes:
        return {"matched": [], "suggestions": [], "query": ""}

    exact_matches = [
        dish
        for dish in dishes
        if str(dish.get("name", "")).strip() and str(dish["name"]).strip() in user_text
    ]
    if exact_matches:
        exact_matches = sorted(exact_matches, key=lambda item: len(str(item.get("name", ""))), reverse=True)
        top_name = str(exact_matches[0]["name"])
        matched = [dish for dish in exact_matches if str(dish.get("name")) == top_name]
        return {"matched": matched, "suggestions": [], "query": top_name}

    all_names = [str(dish.get("name", "")).strip() for dish in dishes if str(dish.get("name", "")).strip()]
    candidate_queries: List[str] = []
    for segment in _split_user_text_segments(user_text):
        candidate = _extract_candidate_dish_phrase(segment)
        if candidate and candidate not in candidate_queries:
            candidate_queries.append(candidate)

    overall_candidate = _extract_candidate_dish_phrase(user_text)
    if overall_candidate and overall_candidate not in candidate_queries:
        candidate_queries.append(overall_candidate)

    for candidate in candidate_queries:
        suggestions = difflib.get_close_matches(candidate, all_names, n=5, cutoff=0.2)
        if suggestions:
            return {"matched": [], "suggestions": suggestions, "query": candidate}

    if candidate_queries:
        return {"matched": [], "suggestions": [], "query": candidate_queries[0]}
    return {"matched": [], "suggestions": [], "query": ""}


def _address_option_payload(address: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": int(address.get("id") or 0),
        "consignee": address.get("consignee") or "",
        "phone": address.get("phone") or "",
        "address": build_address_text(address),
        "label": address.get("label") or "",
        "isDefault": int(address.get("is_default") or 0) == 1,
    }


def serialize_address_options(addresses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [_address_option_payload(address) for address in addresses if address]


def select_default_address(addresses: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not addresses:
        return {}
    for address in addresses:
        try:
            if int(address.get("is_default") or 0) == 1:
                return address
        except Exception:
            continue
    return addresses[0]


def _parse_flavor_values(raw_value: Any) -> List[str]:
    if raw_value is None:
        return []
    if isinstance(raw_value, list):
        return [str(item).strip() for item in raw_value if str(item).strip()]

    text = str(raw_value).strip()
    if not text:
        return []

    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]
    except Exception:
        pass
    return [text]


def _to_decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value or 0))
    except Exception:
        return Decimal("0")


def _format_money(value: Any) -> str:
    amount = _to_decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{amount}"


def default_estimated_delivery_time() -> str:
    return (datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")


def validate_cart_items_and_amount(cart_items: List[Dict[str, Any]]) -> Dict[str, Any]:
    text2sql = get_text2sql()
    dish_ids = [item.get("dishId") for item in cart_items if item.get("dishId") is not None]
    setmeal_ids = [item.get("setmealId") for item in cart_items if item.get("setmealId") is not None]
    dish_map = text2sql.get_sky_take_out_dishes_by_ids(dish_ids)
    setmeal_map = text2sql.get_sky_take_out_setmeals_by_ids(setmeal_ids)
    flavor_map = text2sql.get_sky_take_out_dish_flavors_by_dish_ids(dish_ids)

    total_amount = Decimal("0")
    errors: List[str] = []

    for item in cart_items:
        dish_id = item.get("dishId")
        setmeal_id = item.get("setmealId")
        quantity = max(int(item.get("number") or 1), 1)
        flavor = str(item.get("dishFlavor") or "").strip()

        if dish_id is not None and setmeal_id is not None:
            errors.append("单个购物项不能同时包含 dishId 和 setmealId。")
            continue
        if dish_id is None and setmeal_id is None:
            errors.append("购物项必须包含 dishId 或 setmealId。")
            continue

        if dish_id is not None:
            dish = dish_map.get(int(dish_id))
            if not dish:
                errors.append(f"菜品 dishId={dish_id} 不存在。")
                continue
            total_amount += _to_decimal(dish.get("price")) * quantity

            allowed_flavors: List[str] = []
            for flavor_row in flavor_map.get(int(dish_id), []):
                allowed_flavors.extend(_parse_flavor_values(flavor_row.get("value")))
            allowed_flavors = [item for item in allowed_flavors if item]

            if flavor:
                if allowed_flavors and flavor not in allowed_flavors:
                    errors.append(
                        f"菜品“{dish.get('name') or dish_id}”不支持口味“{flavor}”，"
                        f"可选口味：{'、'.join(allowed_flavors)}。"
                    )
                elif not allowed_flavors:
                    errors.append(f"菜品“{dish.get('name') or dish_id}”当前没有可用口味配置，不能设置“{flavor}”。")
            continue

        setmeal = setmeal_map.get(int(setmeal_id))
        if not setmeal:
            errors.append(f"套餐 setmealId={setmeal_id} 不存在。")
            continue
        if flavor:
            errors.append(f"套餐“{setmeal.get('name') or setmeal_id}”当前不支持单独设置口味。")
            continue
        total_amount += _to_decimal(setmeal.get("price")) * quantity

    return {
        "ok": not errors,
        "errors": errors,
        "amount": float(total_amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
    }


def build_order_preview(
    user_id: str,
    address_book_id: int,
    cart_items: List[Dict[str, Any]],
    address_options: List[Dict[str, Any]] = None,
    amount: float = 0.0,
    remark: str = "",
    estimated_delivery_time: str = "",
) -> Dict[str, Any]:
    binding = get_binding(user_id=user_id)
    sky_user_id = binding.get("sky_take_out_user_id")
    text2sql = get_text2sql()

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
        flavor = str(item.get("dishFlavor") or "").strip()

        name = None
        item_type = "dish"
        if dish_id is not None:
            name = (dish_map.get(int(dish_id)) or {}).get("name")
        elif setmeal_id is not None:
            item_type = "setmeal"
            name = (setmeal_map.get(int(setmeal_id)) or {}).get("name")

        if not name:
            name = f"未识别菜品(dishId={dish_id}, setmealId={setmeal_id})"

        display_text = f"{name} x{quantity}"
        if flavor:
            display_text += f"（{flavor}）"

        preview_items.append(
            {
                "type": item_type,
                "name": name,
                "quantity": quantity,
                "flavor": flavor,
                "display_text": display_text,
            }
        )

    address_text = build_address_text(address_row)
    summary_lines = [
        "请先确认以下点单信息：",
        f"店铺：{DEFAULT_SKY_TAKE_OUT_SHOP_NAME}",
        "菜品：",
    ]
    summary_lines.extend(f"{idx}. {item['display_text']}" for idx, item in enumerate(preview_items, start=1))
    summary_lines.append(f"地址：{address_text or '-'}")
    summary_lines.append(f"收货人：{address_row.get('consignee') or '-'} {address_row.get('phone') or ''}".rstrip())
    summary_lines.append(f"实收金额：￥{_format_money(amount)}")
    summary_lines.append(f"预计送达：{estimated_delivery_time or '-'}")
    if remark:
        summary_lines.append(f"备注：{remark}")
    summary_lines.append("确认无误后，请点击“确认下单”或发送“确认下单”；若不下单，请点击“取消下单”或发送“取消下单”。")

    return {
        "shop_name": DEFAULT_SKY_TAKE_OUT_SHOP_NAME,
        "address_book_id": int(address_row.get("id") or address_book_id),
        "address": address_text,
        "consignee": address_row.get("consignee") or "",
        "phone": address_row.get("phone") or "",
        "address_options": address_options or [],
        "amount": float(amount or 0.0),
        "remark": remark or "",
        "estimated_delivery_time": estimated_delivery_time or "",
        "items": preview_items,
        "message": "\n".join(summary_lines),
    }


def order_confirmation_text(preview: Dict[str, Any]) -> str:
    return ORDER_CONFIRMATION_PREFIX + json.dumps(
        {
            "shopName": preview.get("shop_name") or DEFAULT_SKY_TAKE_OUT_SHOP_NAME,
            "addressBookId": int(preview.get("address_book_id") or 0),
            "address": preview.get("address") or "",
            "consignee": preview.get("consignee") or "",
            "phone": preview.get("phone") or "",
            "addressOptions": preview.get("address_options") or [],
            "amount": float(preview.get("amount") or 0.0),
            "remark": preview.get("remark") or "",
            "estimatedDeliveryTime": preview.get("estimated_delivery_time") or "",
            "items": preview.get("items") or [],
            "message": preview.get("message") or "",
            "confirmText": "确认下单",
            "cancelText": "取消下单",
        },
        ensure_ascii=False,
    )


def available_dish_text(limit: int = 6) -> str:
    dishes = get_text2sql().list_sky_take_out_dishes(limit=limit)
    return "、".join(
        str(dish.get("name", "")).strip()
        for dish in dishes
        if str(dish.get("name", "")).strip()
    )


def _response_data_dict(response: Dict[str, Any]) -> Dict[str, Any]:
    payload = response.get("data")
    return payload if isinstance(payload, dict) else {}


def _safe_order_id(response: Dict[str, Any]) -> int:
    order_id = _response_data_dict(response).get("id")
    try:
        return int(order_id)
    except Exception:
        return 0


def _safe_order_number(response: Dict[str, Any]) -> str:
    order_number = _response_data_dict(response).get("orderNumber")
    return str(order_number or "").strip()


def _safe_order_time(response: Dict[str, Any]) -> str:
    order_time = _response_data_dict(response).get("orderTime")
    return str(order_time or "").strip()


def _simulate_order_payment(
    headers: Dict[str, str],
    binding: Dict[str, Any],
    order_number: str,
    pay_method: int = 1,
) -> str:
    if not order_number:
        return "订单已提交，但未拿到订单号，暂时无法自动模拟付款。"

    payment_url = f"{SKY_TAKE_OUT_BASE_URL}/user/order/payment"
    payment_resp = request_json(
        "PUT",
        payment_url,
        headers=headers,
        body={"orderNumber": order_number, "payMethod": int(pay_method)},
    )
    auth_failure = auth_failure_message("sky_take_out", binding, payment_resp)
    if auth_failure:
        return f"订单已提交，但自动模拟付款失败：{auth_failure}"

    payment_error = service_error(payment_resp)
    if payment_error:
        return f"订单已提交，但自动模拟付款失败：{payment_error}"
    return ""


def _remind_shop(headers: Dict[str, str], binding: Dict[str, Any], order_id: int) -> str:
    if order_id <= 0:
        return "订单已提交并支付成功，但未拿到订单 ID，暂时无法自动提醒商家。"

    remind_url = f"{SKY_TAKE_OUT_BASE_URL}/user/order/reminder/{order_id}"
    remind_resp = request_json("GET", remind_url, headers=headers)
    auth_failure = auth_failure_message("sky_take_out", binding, remind_resp)
    if auth_failure:
        return f"订单已提交并支付成功，但提醒商家失败：{auth_failure}"

    remind_error = service_error(remind_resp)
    if remind_error:
        return f"订单已提交并支付成功，但提醒商家失败：{remind_error}"
    return ""


def format_takeout_success_message(preview: Dict[str, Any], submit_resp: Dict[str, Any]) -> str:
    items = preview.get("items") or []
    item_lines = [
        f"{idx}. {item.get('display_text') or item.get('name') or '未知菜品'}"
        for idx, item in enumerate(items, start=1)
    ]
    order_number = _safe_order_number(submit_resp)
    order_time = _safe_order_time(submit_resp)

    lines = [
        "下单成功，已为您自动完成模拟付款，并提醒商家尽快接单。",
        f"店铺：{preview.get('shop_name') or DEFAULT_SKY_TAKE_OUT_SHOP_NAME}",
        "菜品：",
    ]
    lines.extend(item_lines or ["1. 未识别菜品"])
    lines.append(f"地址：{preview.get('address') or '-'}")
    lines.append(f"实收金额：￥{_format_money(preview.get('amount') or 0)}")
    if preview.get("estimated_delivery_time"):
        lines.append(f"预计送达：{preview.get('estimated_delivery_time')}")
    if preview.get("remark"):
        lines.append(f"备注：{preview.get('remark')}")
    if order_number:
        lines.append(f"订单号：{order_number}")
    if order_time:
        lines.append(f"下单时间：{order_time}")
    return "\n".join(lines)


def submit_takeout_order(user_id: str, pending_payload: Dict[str, Any]) -> str:
    binding = get_binding(user_id=user_id)
    token = binding.get("sky_take_out_token")
    if not token:
        return "外卖下单失败：未绑定 sky_take_out token，请先绑定。"

    headers = build_token_headers(str(token))
    cart_items = pending_payload.get("cart_items") or []
    validation = validate_cart_items_and_amount(cart_items)
    if not validation.get("ok"):
        return f"外卖下单失败：{'；'.join(validation.get('errors') or ['菜品校验失败'])}"

    final_amount = float(validation.get("amount") or 0.0)
    final_remark = str(pending_payload.get("remark") or "").strip()
    final_estimated_delivery_time = str(
        pending_payload.get("estimated_delivery_time") or default_estimated_delivery_time()
    ).strip()

    add_url = f"{SKY_TAKE_OUT_BASE_URL}/user/shoppingCart/add"
    for item in cart_items:
        add_resp = request_json(
            "POST",
            add_url,
            headers=headers,
            body={
                "dishId": item.get("dishId"),
                "setmealId": item.get("setmealId"),
                "dishFlavor": item.get("dishFlavor", ""),
            },
        )
        auth_failure = auth_failure_message("sky_take_out", binding, add_resp)
        if auth_failure:
            return f"外卖下单失败：{auth_failure}"
        add_error = service_error(add_resp)
        if add_error:
            return f"外卖下单失败：购物车添加失败：{add_error}"

    submit_url = f"{SKY_TAKE_OUT_BASE_URL}/user/order/submit"
    submit_body = {
        "addressBookId": int(pending_payload["address_book_id"]),
        "payMethod": int(pending_payload.get("pay_method", 1)),
        "remark": final_remark,
        "estimatedDeliveryTime": final_estimated_delivery_time,
        "deliveryStatus": int(pending_payload.get("delivery_status", 1)),
        "tablewareNumber": int(pending_payload.get("tableware_number", 0)),
        "tablewareStatus": int(pending_payload.get("tableware_status", 1)),
        "packAmount": int(pending_payload.get("pack_amount", 0)),
        "amount": final_amount,
    }
    submit_resp = request_json("POST", submit_url, headers=headers, body=submit_body)
    auth_failure = auth_failure_message("sky_take_out", binding, submit_resp)
    if auth_failure:
        return f"外卖下单失败：{auth_failure}"
    submit_error = service_error(submit_resp)
    if submit_error:
        return f"外卖下单失败：{submit_error}"

    preview = pending_payload.get("preview") or {}
    preview["amount"] = final_amount
    preview["remark"] = final_remark
    preview["estimated_delivery_time"] = final_estimated_delivery_time
    order_number = _safe_order_number(submit_resp)
    order_id = _safe_order_id(submit_resp)
    pay_method = int(pending_payload.get("pay_method", 1) or 1)

    payment_error = _simulate_order_payment(
        headers=headers,
        binding=binding,
        order_number=order_number,
        pay_method=pay_method,
    )
    if payment_error:
        return payment_error

    remind_error = _remind_shop(headers=headers, binding=binding, order_id=order_id)
    if remind_error:
        return remind_error

    return format_takeout_success_message(preview=preview, submit_resp=submit_resp)
