from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

import pymysql

from model.contants.contant import MYSQL_CHARSET, MYSQL_HOST, MYSQL_PASSWORD, MYSQL_PORT, MYSQL_USER
from model.workflow.llm.llm_factory import LLMFactory
from model.workflow.prompt.text2sql_prompt import (
    HMDP_ALL_SHOP_COMMENTS_PROMPT,
    HMDP_SHOP_COMMENTS_BY_ID_PROMPT,
    SKY_TAKE_OUT_SQL_PROMPT,
)


class Text2SQL:
    def __init__(self):
        self._model = None

    def _get_model(self):
        if self._model is None:
            self._model = LLMFactory.create_openai_llm()
        return self._model

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

    def execute_query(self, database: str, sql: str, params: Optional[Iterable[Any]] = None) -> List[Dict[str, Any]]:
        with self._conn(database) as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, tuple(params or ()))
                return list(cursor.fetchall() or [])

    def execute_one(self, database: str, sql: str, params: Optional[Iterable[Any]] = None) -> Optional[Dict[str, Any]]:
        rows = self.execute_query(database, sql, params=params)
        return rows[0] if rows else None

    def text2sql_sky_take_out(self, user_query: str) -> str:
        prompt = SKY_TAKE_OUT_SQL_PROMPT.format(user_query=user_query)
        response = self._get_model().invoke(prompt)
        return response.content.strip()

    def get_hmdp_shop_comments(self, shop_id: Optional[int] = None) -> str:
        if shop_id:
            prompt = HMDP_SHOP_COMMENTS_BY_ID_PROMPT.format(shop_id=shop_id)
        else:
            prompt = HMDP_ALL_SHOP_COMMENTS_PROMPT
        response = self._get_model().invoke(prompt)
        return response.content.strip()

    def get_hmdp_shop_info_by_ids(self, shop_ids: Iterable[Any]) -> Dict[int, Dict[str, Any]]:
        normalized_ids = [int(shop_id) for shop_id in shop_ids if shop_id is not None]
        if not normalized_ids:
            return {}

        placeholders = ",".join(["%s"] * len(normalized_ids))
        sql = (
            f"SELECT id, name, area, address, score, avg_price "
            f"FROM tb_shop WHERE id IN ({placeholders})"
        )
        rows = self.execute_query("hmdp", sql, normalized_ids)
        return {int(row["id"]): row for row in rows if row.get("id") is not None}

    def get_sky_take_out_address(self, address_book_id: int, user_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        sql = (
            "SELECT id, user_id, consignee, phone, province_name, city_name, district_name, detail, label "
            "FROM address_book WHERE id = %s"
        )
        params: List[Any] = [int(address_book_id)]
        if user_id is not None:
            sql += " AND user_id = %s"
            params.append(int(user_id))
        sql += " LIMIT 1"
        return self.execute_one("sky_take_out", sql, params=params)

    def get_sky_take_out_dishes_by_ids(self, dish_ids: Iterable[Any]) -> Dict[int, Dict[str, Any]]:
        normalized_ids = [int(dish_id) for dish_id in dish_ids if dish_id is not None]
        if not normalized_ids:
            return {}

        placeholders = ",".join(["%s"] * len(normalized_ids))
        sql = (
            f"SELECT id, name, price, image, description "
            f"FROM dish WHERE id IN ({placeholders})"
        )
        rows = self.execute_query("sky_take_out", sql, normalized_ids)
        return {int(row["id"]): row for row in rows if row.get("id") is not None}

    def get_sky_take_out_setmeals_by_ids(self, setmeal_ids: Iterable[Any]) -> Dict[int, Dict[str, Any]]:
        normalized_ids = [int(setmeal_id) for setmeal_id in setmeal_ids if setmeal_id is not None]
        if not normalized_ids:
            return {}

        placeholders = ",".join(["%s"] * len(normalized_ids))
        sql = (
            f"SELECT id, name, price, image, description "
            f"FROM setmeal WHERE id IN ({placeholders})"
        )
        rows = self.execute_query("sky_take_out", sql, normalized_ids)
        return {int(row["id"]): row for row in rows if row.get("id") is not None}
