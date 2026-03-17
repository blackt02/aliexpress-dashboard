"""
AliExpress Affiliate API client - SHA256 signing
"""

import hashlib, hmac, time, requests, json
from typing import Tuple

BASE_URL = "https://api-sg.aliexpress.com/sync"


def _sign(secret: str, params: dict) -> str:
    sorted_kv = sorted(params.items())
    sign_str = "".join(f"{k}{v}" for k, v in sorted_kv)
    return (
        hmac.new(secret.encode("utf-8"), sign_str.encode("utf-8"), hashlib.sha256)
        .hexdigest()
        .upper()
    )


def _base_params(app_key, access_token, method):
    return {
        "app_key": app_key,
        "timestamp": str(int(time.time() * 1000)),
        "sign_method": "sha256",
        "access_token": access_token,
        "method": method,
    }


def _parse_custom_params(raw_str: str) -> str:
    """Parse custom_parameters JSON → human-readable string.
    e.g. '{"af_sub":"post_abc"}' → 'post_abc'
    Returns the most meaningful value, or raw string if unparseable.
    """
    if not raw_str or raw_str in ("{}", ""):
        return ""
    try:
        d = json.loads(raw_str)
        # Priority: af_sub > sub_id > first value
        val = d.get("af_sub") or d.get("sub_id") or d.get("subId") or ""
        if not val and d:
            val = str(list(d.values())[0])
        return val
    except Exception:
        return raw_str


def _parse_order(raw: dict) -> dict:
    custom_raw = raw.get("custom_parameters", "{}")
    return {
        "sub_order_id": str(raw.get("sub_order_id", "")),
        "order_id": str(raw.get("order_id", raw.get("parent_order_number", ""))),
        "completed_payments_time": raw.get("paid_time", ""),
        "product_id": str(raw.get("product_id", "")),
        "product_title": raw.get("product_title", ""),
        "product_url": raw.get("product_detail_url", ""),
        "seller_id": str(raw.get("seller_id", "")),
        "order_status": raw.get("order_status", ""),
        "commission_rate": float(
            str(raw.get("commission_rate", "0")).replace("%", "") or 0
        ),
        "completed_payments_amount": float(raw.get("paid_amount", 0) or 0) / 100,
        "estimated_payments_commission": float(
            raw.get("estimated_paid_commission", 0) or 0
        )
        / 100,
        "region": raw.get("ship_to_country", ""),
        "category_id": str(raw.get("category_id", "")),
        "tracking_id": raw.get("tracking_id", ""),
        "order_platform": raw.get("order_platform", ""),
        # Sub-tracking: parsed from custom_parameters
        "sub_tracking": _parse_custom_params(str(custom_raw)),
        "custom_parameters": str(custom_raw),
    }


def get_auth_url(app_key: str, redirect_uri: str = "https://besttopzone.com/") -> str:
    return (
        f"https://api-sg.aliexpress.com/oauth/authorize"
        f"?response_type=code&force_auth=true&redirect_uri={redirect_uri}&client_id={app_key}"
    )


def exchange_code_for_token(app_key: str, app_secret: str, auth_code: str) -> dict:
    api_path = "/auth/token/create"
    params = {
        "app_key": app_key,
        "timestamp": str(int(time.time() * 1000)),
        "sign_method": "sha256",
        "code": auth_code,
    }
    sign_str = api_path + "".join(f"{k}{v}" for k, v in sorted(params.items()))
    params["sign"] = (
        hmac.new(app_secret.encode(), sign_str.encode(), hashlib.sha256)
        .hexdigest()
        .upper()
    )
    resp = requests.post(
        "https://api-sg.aliexpress.com/rest" + api_path,
        data=params,
        headers={"Content-Type": "application/x-www-form-urlencoded;charset=utf-8"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def refresh_access_token(app_key: str, app_secret: str, refresh_token: str) -> dict:
    api_path = "/auth/token/refresh"
    params = {
        "app_key": app_key,
        "timestamp": str(int(time.time() * 1000)),
        "sign_method": "sha256",
        "refresh_token": refresh_token,
    }
    sign_str = api_path + "".join(f"{k}{v}" for k, v in sorted(params.items()))
    params["sign"] = (
        hmac.new(app_secret.encode(), sign_str.encode(), hashlib.sha256)
        .hexdigest()
        .upper()
    )
    resp = requests.post(
        "https://api-sg.aliexpress.com/rest" + api_path,
        data=params,
        headers={"Content-Type": "application/x-www-form-urlencoded;charset=utf-8"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


class AliExpressAPI:
    def __init__(self, app_key: str, app_secret: str, access_token: str):
        self.app_key = app_key
        self.app_secret = app_secret
        self.access_token = access_token

    def _post(self, extra: dict) -> dict:
        params = _base_params(
            self.app_key,
            self.access_token,
            extra.pop("method", "aliexpress.affiliate.order.list"),
        )
        params.update(extra)
        params["sign"] = _sign(self.app_secret, params)
        resp = requests.post(
            BASE_URL,
            data=params,
            headers={"Content-Type": "application/x-www-form-urlencoded;charset=utf-8"},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    def fetch_page(
        self,
        start_time: str,
        end_time: str,
        status: str = "Payment Completed",
        page_no: int = 1,
    ) -> Tuple[list, int]:
        data = self._post(
            {
                "method": "aliexpress.affiliate.order.list",
                "start_time": start_time,
                "end_time": end_time,
                "status": status,
                "time_type": "Payment Completed Time",
                "page_no": str(page_no),
                "page_size": "50",
            }
        )
        result = data.get("aliexpress_affiliate_order_list_response", {}).get(
            "resp_result", {}
        )
        if result.get("resp_code") not in (200, "200"):
            raise ValueError(
                f"API error {result.get('resp_code')}: {result.get('resp_msg')}"
            )
        body = result.get("result", {})
        total = int(body.get("total_record_count", 0))
        raw_orders = body.get("orders", [])
        if isinstance(raw_orders, dict):
            raw_orders = raw_orders.get("order", [])
        if isinstance(raw_orders, dict):
            raw_orders = [raw_orders]
        return [_parse_order(o) for o in raw_orders], total

    def fetch_all_orders(
        self,
        start_time: str,
        end_time: str,
        status: str = "Payment Completed",
        progress_callback=None,
    ) -> list:
        from datetime import datetime, timedelta

        fmt = "%Y-%m-%d %H:%M:%S"
        start_dt = datetime.strptime(start_time, fmt)
        end_dt = datetime.strptime(end_time, fmt)
        all_orders = []
        chunk_start = start_dt
        while chunk_start < end_dt:
            chunk_end = min(chunk_start + timedelta(days=7), end_dt)
            page = 1
            while page <= 20:
                try:
                    orders, total = self.fetch_page(
                        chunk_start.strftime(fmt), chunk_end.strftime(fmt), status, page
                    )
                    all_orders.extend(orders)
                    if progress_callback:
                        progress_callback(len(all_orders), total)
                    if not orders or len(all_orders) >= total:
                        break
                    page += 1
                    time.sleep(0.3)
                except ValueError:
                    break
            chunk_start = chunk_end + timedelta(seconds=1)
        return all_orders

    def fetch_by_ids(self, order_ids: list) -> list:
        all_orders = []
        for i in range(0, len(order_ids), 50):
            chunk = order_ids[i : i + 50]
            data = self._post(
                {
                    "method": "aliexpress.affiliate.order.get",
                    "order_ids": ",".join(str(x) for x in chunk),
                }
            )
            result = data.get("aliexpress_affiliate_order_get_response", {}).get(
                "resp_result", {}
            )
            if result.get("resp_code") in (200, "200"):
                raw = result.get("result", {}).get("orders", {}).get("order", [])
                if isinstance(raw, dict):
                    raw = [raw]
                all_orders.extend([_parse_order(o) for o in raw])
        return all_orders

    def test_connection(self) -> Tuple[bool, str]:
        try:
            from datetime import date

            today = date.today()
            orders, total = self.fetch_page(f"{today} 00:00:00", f"{today} 23:59:59")
            return True, f"Connected ✅  —  {total} orders today"
        except Exception as e:
            return False, str(e)
