import json
from typing import Any, Dict, Optional

import pymysql
from urllib import error, request

from model.contants.contant import HMDP_BASE_URL, MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_CHARSET


class BindingStore:
    """读取 agent 用户绑定信息（token/用户名）"""

    def _conn(self, database: str):
        return pymysql.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            charset=MYSQL_CHARSET,
            database=database,
            cursorclass=pymysql.cursors.DictCursor,
        )

    def _resolve_hmdp_user_id(self, token: str) -> Optional[int]:
        if not str(token or "").strip():
            return None

        req = request.Request(
            url=f"{HMDP_BASE_URL}/user/me",
            headers={
                "Authorization": str(token),
                "token": str(token),
                "authentication": str(token),
            },
            method="GET",
        )
        try:
            with request.urlopen(req, timeout=5) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
                data = payload.get("data") or {}
                user_id = data.get("id")
                return int(user_id) if user_id is not None else None
        except (error.URLError, ValueError, TypeError, json.JSONDecodeError):
            return None

    def get_binding_info(self, user_id: str) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "agent_user_id": user_id,
            "agent_username": None,
            "hmdp_user_id": None,
            "hmdp_token": None,
            "sky_take_out_user_id": None,
            "sky_take_out_token": None,
        }

        # 1) 从 sky_agent 读取 agent 用户名 + 绑定 token
        with self._conn("sky_agent") as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id, username FROM user WHERE id = %s LIMIT 1", (user_id,))
                user_row: Optional[Dict[str, Any]] = cursor.fetchone()
                if user_row:
                    result["agent_username"] = user_row.get("username")

                cursor.execute(
                    """
                    SELECT hmdp_user_id, hmdp_token, sky_take_out_user_id, sky_take_out_token
                    FROM user_account_binding
                    WHERE agent_user_id = %s
                    LIMIT 1
                    """,
                    (user_id,),
                )
                binding_row: Optional[Dict[str, Any]] = cursor.fetchone()
                if binding_row:
                    result["hmdp_user_id"] = binding_row.get("hmdp_user_id")
                    result["hmdp_token"] = binding_row.get("hmdp_token")
                    result["sky_take_out_user_id"] = binding_row.get("sky_take_out_user_id")
                    result["sky_take_out_token"] = binding_row.get("sky_take_out_token")

                    if result["hmdp_user_id"] is None and result["hmdp_token"]:
                        resolved_hmdp_user_id = self._resolve_hmdp_user_id(result["hmdp_token"])
                        if resolved_hmdp_user_id is not None:
                            result["hmdp_user_id"] = resolved_hmdp_user_id
                            cursor.execute(
                                """
                                UPDATE user_account_binding
                                SET hmdp_user_id = %s
                                WHERE agent_user_id = %s
                                """,
                                (resolved_hmdp_user_id, user_id),
                            )
                            conn.commit()

        return result
