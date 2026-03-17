import sqlite3
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
import pandas as pd

DB_PATH = os.path.join(os.path.dirname(__file__), "orders.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS orders (
    sub_order_id                TEXT PRIMARY KEY,
    order_id                    TEXT,
    completed_payments_time     TEXT,
    product_id                  TEXT,
    product_title               TEXT,
    product_url                 TEXT,
    seller_id                   TEXT,
    order_status                TEXT,
    commission_rate             REAL,
    completed_payments_amount   REAL,
    estimated_payments_commission REAL,
    region                      TEXT,
    category_id                 TEXT,
    tracking_id                 TEXT,
    order_platform              TEXT,
    sub_tracking                TEXT,
    custom_parameters           TEXT,
    fetched_at                  TEXT
);

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);
"""

# Map full country names → region codes stored in DB
REGION_NAME_TO_CODE = {
    "Austria": "AT",
    "Belgium": "BE",
    "Bulgaria": "BG",
    "Switzerland": "CH",
    "Czech Republic": "CZ",
    "Germany": "DE",
    "Denmark": "DK",
    "Spain": "ES",
    "Finland": "FI",
    "France": "FR",
    "United Kingdom": "UK",
    "Greece": "GR",
    "Hungary": "HU",
    "Ireland": "IE",
    "Italy": "IT",
    "Netherlands": "NL",
    "Norway": "NO",
    "Poland": "PL",
    "Portugal": "PT",
    "Sweden": "SE",
    "Slovakia": "SK",
}


class Database:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _connect(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._connect() as conn:
            conn.executescript(SCHEMA)
            # Migrate: add new columns if not exist
            for col, coltype in [
                ("sub_tracking", "TEXT"),
                ("custom_parameters", "TEXT"),
            ]:
                try:
                    conn.execute(f"ALTER TABLE orders ADD COLUMN {col} {coltype}")
                except Exception:
                    pass

    # ── Write ────────────────────────────────────────────────────────────────

    def upsert_orders(self, orders: List[Dict[str, Any]]):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        rows = []
        for o in orders:
            rows.append(
                (
                    o.get("sub_order_id", ""),
                    o.get("order_id", ""),
                    o.get("completed_payments_time", ""),
                    o.get("product_id", ""),
                    o.get("product_title", ""),
                    o.get("product_url", ""),
                    o.get("seller_id", ""),
                    o.get("order_status", ""),
                    float(o.get("commission_rate", 0) or 0),
                    float(o.get("completed_payments_amount", 0) or 0),
                    float(o.get("estimated_payments_commission", 0) or 0),
                    o.get("region", ""),
                    o.get("category_id", ""),
                    o.get("tracking_id", ""),
                    o.get("order_platform", ""),
                    o.get("sub_tracking", ""),
                    o.get("custom_parameters", "{}"),
                    now,
                )
            )

        with self._connect() as conn:
            conn.executemany(
                """
                INSERT OR REPLACE INTO orders VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
                rows,
            )
            conn.execute(
                "INSERT OR REPLACE INTO meta VALUES ('last_refresh', ?)", (now,)
            )

    # ── Read ─────────────────────────────────────────────────────────────────

    def get_orders(self, filters: Optional[dict] = None) -> pd.DataFrame:
        query = "SELECT * FROM orders WHERE 1=1"
        params: list = []

        if filters:
            if filters.get("start_date"):
                query += " AND DATE(completed_payments_time) >= ?"
                params.append(filters["start_date"])
            if filters.get("end_date"):
                query += " AND DATE(completed_payments_time) <= ?"
                params.append(filters["end_date"])

            # Multi-region filter: convert full names → codes, then IN (?,?...)
            regions_selected = filters.get("regions", [])
            if regions_selected:
                codes = [REGION_NAME_TO_CODE.get(r, r) for r in regions_selected]
                placeholders = ",".join("?" * len(codes))
                query += f" AND region IN ({placeholders})"
                params.extend(codes)

            if filters.get("tracking_id"):
                query += " AND tracking_id = ?"
                params.append(filters["tracking_id"])
            if filters.get("order_status"):
                query += " AND order_status = ?"
                params.append(filters["order_status"])
            if filters.get("order_id"):
                query += " AND (order_id LIKE ? OR sub_order_id LIKE ?)"
                val = f"%{filters['order_id']}%"
                params.extend([val, val])

        query += " ORDER BY completed_payments_time DESC"

        with self._connect() as conn:
            df = pd.read_sql_query(query, conn, params=params)
        return df

    def get_distinct_values(self, column: str) -> list:
        safe_cols = {
            "region",
            "tracking_id",
            "order_status",
            "order_platform",
            "category_id",
        }
        if column not in safe_cols:
            return []
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT DISTINCT {column} FROM orders WHERE {column} != '' ORDER BY {column}"
            ).fetchall()
        return [r[0] for r in rows if r[0]]

    def get_last_refresh(self) -> Optional[str]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT value FROM meta WHERE key = 'last_refresh'"
            ).fetchone()
        return row[0] if row else None

    def get_summary(self, filters: Optional[dict] = None) -> dict:
        df = self.get_orders(filters)
        return {
            "total_orders": len(df),
            "total_amount": (
                df["completed_payments_amount"].sum() if not df.empty else 0.0
            ),
            "total_commission": (
                df["estimated_payments_commission"].sum() if not df.empty else 0.0
            ),
            "avg_rate": df["commission_rate"].mean() if not df.empty else 0.0,
        }
