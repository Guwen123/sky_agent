from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Optional


_PENDING_TAKEOUT_ORDERS: Dict[str, Dict[str, Any]] = {}


class PendingTakeoutOrderStore:
    def get(self, user_id: str) -> Optional[Dict[str, Any]]:
        payload = _PENDING_TAKEOUT_ORDERS.get(str(user_id))
        return deepcopy(payload) if payload is not None else None

    def set(self, user_id: str, payload: Dict[str, Any]) -> None:
        _PENDING_TAKEOUT_ORDERS[str(user_id)] = deepcopy(payload)

    def pop(self, user_id: str) -> Optional[Dict[str, Any]]:
        payload = _PENDING_TAKEOUT_ORDERS.pop(str(user_id), None)
        return deepcopy(payload) if payload is not None else None

    def clear(self, user_id: str) -> None:
        _PENDING_TAKEOUT_ORDERS.pop(str(user_id), None)
