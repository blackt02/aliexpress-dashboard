"""
AliExpress Affiliate Order Dashboard
Run:  streamlit run app.py
"""

import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta

from config import load_config, save_config
from database import Database
from scheduler import start_scheduler

# ── Password protection ───────────────────────────────────────────────────────
import os
def _check_password():
    pwd = os.environ.get("APP_PASSWORD", "admin123")
    if st.session_state.get("authenticated"):
        return True
    with st.form("login"):
        st.markdown("## 🔐 AliExpress Dashboard")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        if submitted:
            if password == pwd:
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("Wrong password!")
    st.stop()

st.set_page_config(
    page_title="AliExpress Affiliate Dashboard",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
[data-testid="metric-container"] {
    background: #f8f9fb; border: 1px solid #e2e8f0;
    border-radius: 12px; padding: 16px 20px;
    box-shadow: 0 1px 3px rgba(0,0,0,.06);
}
[data-testid="metric-container"] label { font-size: 13px !important; color: #64748b; }
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    font-size: 28px !important; font-weight: 700;
}
</style>
""", unsafe_allow_html=True)

_check_password()

@st.cache_resource
def get_db():
    return Database()

db = get_db()
config = load_config()

if "scheduler_started" not in st.session_state:
    start_scheduler(config, db)
    st.session_state.scheduler_started = True

# ── Auto token refresh check ──────────────────────────────────────────────────
def _auto_refresh_token():
    import time as _t
    cfg = load_config()
    expires = cfg.get("token_expires", "")
    token   = cfg.get("access_token", "")
    refresh = cfg.get("refresh_token", "")
    if not token or not refresh or not expires:
        return
    try:
        expire_ms = int(expires)
        now_ms    = int(_t.time() * 1000)
        # Refresh if token expires within 24 hours
        if expire_ms - now_ms < 86400 * 1000:
            from api_client import refresh_access_token
            r = refresh_access_token(cfg["app_key"], cfg["app_secret"], refresh)
            if r.get("access_token"):
                cfg["access_token"]  = r["access_token"]
                cfg["refresh_token"] = r.get("refresh_token", refresh)
                cfg["token_expires"] = str(r.get("expire_time", ""))
                save_config(cfg)
                st.toast("🔄 Token auto-refreshed!", icon="✅")
    except Exception:
        pass

_auto_refresh_token()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Configuration")

    with st.expander("🔑 API Keys & Token", expanded=not config.get("access_token")):
        app_key     = st.text_input("App Key",    value=config.get("app_key", ""))
        app_secret  = st.text_input("App Secret", value=config.get("app_secret", ""), type="password")
        default_tid = st.text_input("Default Tracking ID", value=config.get("tracking_id", ""))

        if st.button("💾 Save Keys", use_container_width=True):
            new_cfg = {**config, "app_key": app_key, "app_secret": app_secret, "tracking_id": default_tid}
            save_config(new_cfg)
            config = new_cfg
            st.success("Saved!")

        st.divider()
        st.markdown("**Step 1 — Authorize App**")
        if app_key:
            from api_client import get_auth_url
            auth_url = get_auth_url(config.get("app_key", app_key))
            st.markdown(f"[🔗 Click here to authorize]({auth_url})", unsafe_allow_html=True)
            st.caption("After authorizing, copy the `code=` value from the redirect URL.")
        else:
            st.warning("Enter App Key first, then Save Keys.")

        st.markdown("**Step 2 — Paste Auth Code**")
        auth_code = st.text_input("Auth Code (from redirect URL)")
        if st.button("🔄 Exchange for Token", use_container_width=True):
            if auth_code and app_key and app_secret:
                from api_client import exchange_code_for_token
                try:
                    token_data    = exchange_code_for_token(app_key, app_secret, auth_code)
                    access_token  = token_data.get("access_token", "")
                    refresh_token = token_data.get("refresh_token", "")
                    expires       = token_data.get("expire_time", "")
                    if access_token:
                        new_cfg = {
                            **config,
                            "app_key": app_key, "app_secret": app_secret,
                            "access_token": access_token,
                            "refresh_token": refresh_token,
                            "token_expires": str(expires),
                        }
                        save_config(new_cfg)
                        config = new_cfg
                        st.success(f"Token saved! Expires: {expires}")
                        st.rerun()
                    else:
                        st.error(f"No token in response: {token_data}")
                except Exception as e:
                    st.error(f"Exchange failed: {e}")
            else:
                st.warning("Fill App Key, App Secret, and Auth Code.")

        st.divider()
        tok = config.get("access_token", "")
        if tok:
            st.success(f"Token: `{tok[:20]}…`")
            exp = config.get("token_expires", "")
            if exp:
                st.caption(f"Expires: {exp}")
            col_t, col_r = st.columns(2)
            with col_t:
                if st.button("🔌 Test", use_container_width=True):
                    from api_client import AliExpressAPI
                    ok, msg = AliExpressAPI(config["app_key"], config["app_secret"], tok).test_connection()
                    st.success(msg) if ok else st.error(msg)
            with col_r:
                if st.button("♻️ Refresh", use_container_width=True):
                    from api_client import refresh_access_token
                    try:
                        r = refresh_access_token(config["app_key"], config["app_secret"], config["refresh_token"])
                        new_cfg = {
                            **config,
                            "access_token":  r.get("access_token", ""),
                            "refresh_token": r.get("refresh_token", config["refresh_token"]),
                            "token_expires": str(r.get("expire_time", "")),
                        }
                        save_config(new_cfg)
                        config = new_cfg
                        st.success("Token refreshed!")
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))
        else:
            st.warning("⚠️ No access token yet.")

    st.divider()
    st.markdown("### 🔍 Filters")

    preset = st.selectbox("Quick range", ["Today", "Yesterday", "Last 7 days", "Last 30 days", "Custom"])
    today = date.today()
    if preset == "Today":
        default_range = (today, today)
    elif preset == "Yesterday":
        y = today - timedelta(days=1)
        default_range = (y, y)
    elif preset == "Last 7 days":
        default_range = (today - timedelta(days=6), today)
    elif preset == "Last 30 days":
        default_range = (today - timedelta(days=29), today)
    else:
        default_range = (today, today)

    date_range = st.date_input("Date range", value=default_range, max_value=today)

    regions      = ["All"] + db.get_distinct_values("region")
    tracking_ids = ["All"] + db.get_distinct_values("tracking_id")
    statuses     = ["All"] + db.get_distinct_values("order_status")

    region      = st.selectbox("Region",       regions)
    tracking_id = st.selectbox("Tracking ID",  tracking_ids)
    status      = st.selectbox("Order Status", statuses)
    order_id_q  = st.text_input("Search by Order ID")

    st.divider()
    refresh_clicked = st.button("🔄  Refresh Data", use_container_width=True, type="primary")

    last_refresh = db.get_last_refresh()
    if last_refresh:
        st.caption(f"🕐 Last refresh: {last_refresh}")
    st.caption("⏰ Auto-refresh at **15:00** and **16:00**")

# ── Manual refresh ─────────────────────────────────────────────────────────────
if refresh_clicked:
    _key    = config.get("app_key", "")
    _secret = config.get("app_secret", "")
    _token  = config.get("access_token", "")

    if not _key or not _secret:
        st.error("❌ Please configure and save API keys first.")
    elif not _token:
        st.error("❌ No access token — complete the OAuth flow in the sidebar (Step 1 & 2).")
    else:
        from api_client import AliExpressAPI
        _dates    = date_range if isinstance(date_range, (list, tuple)) else [date_range]
        start_str = f"{_dates[0]} 00:00:00"
        end_str   = f"{_dates[-1]} 23:59:59"

        prog_bar  = st.progress(0, text="Connecting to AliExpress API…")
        status_ph = st.empty()

        def _progress(fetched, total):
            pct = min(fetched / total, 1.0) if total > 0 else 0
            prog_bar.progress(pct, text=f"Fetching… {fetched} / {total} orders")

        try:
            api    = AliExpressAPI(_key, _secret, _token)
            orders = api.fetch_all_orders(start_str, end_str, progress_callback=_progress)
            db.upsert_orders(orders)
            prog_bar.progress(1.0, text="Done!")
            status_ph.success(f"✅ {len(orders)} orders fetched and saved.")
        except Exception as e:
            prog_bar.empty()
            status_ph.error(f"❌ {e}")

# ── Filters ────────────────────────────────────────────────────────────────────
_dates = date_range if isinstance(date_range, (list, tuple)) else [date_range]
filters: dict = {"start_date": str(_dates[0]), "end_date": str(_dates[-1])}
if region      != "All": filters["region"]       = region
if tracking_id != "All": filters["tracking_id"]  = tracking_id
if status      != "All": filters["order_status"] = status
if order_id_q:           filters["order_id"]     = order_id_q

df = db.get_orders(filters)

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown(
    "<div style='display:flex;align-items:center;gap:12px'>"
    "<span style='font-size:2rem'>🛒</span>"
    "<h1 style='margin:0'>AliExpress Affiliate Dashboard</h1>"
    "</div>",
    unsafe_allow_html=True,
)
date_label = str(_dates[0]) if _dates[0] == _dates[-1] else f"{_dates[0]}  →  {_dates[-1]}"
st.caption(f"📅 Showing: **{date_label}**   |   🗄️ Records in DB: **{len(df)}**")
st.divider()

# ── Summary metrics ────────────────────────────────────────────────────────────
total_orders     = len(df)
total_amount     = df["completed_payments_amount"].sum()     if not df.empty else 0.0
total_commission = df["estimated_payments_commission"].sum() if not df.empty else 0.0
avg_rate         = df["commission_rate"].mean()              if not df.empty else 0.0

c1, c2, c3, c4 = st.columns(4)
c1.metric("📦 Total Orders",        f"{total_orders:,}")
c2.metric("💰 Total Sales",         f"${total_amount:,.2f}")
c3.metric("🏆 Est. Commission",     f"${total_commission:,.2f}")
c4.metric("📊 Avg Commission Rate", f"{avg_rate:.2f}%")
st.divider()

# ── Table ──────────────────────────────────────────────────────────────────────
if df.empty:
    if not config.get("access_token"):
        st.warning("⚠️ Complete the OAuth setup in the sidebar to connect to the API.")
    else:
        st.info("No orders found. Click **🔄 Refresh Data** to fetch from the API.")
else:
    COL_MAP = {
        "completed_payments_time":       "Time",
        "product_title":                 "Product",
        "order_id":                      "Order ID",
        "sub_order_id":                  "Sub-Order ID",
        "product_id":                    "Product ID",
        "seller_id":                     "Seller ID",
        "completed_payments_amount":     "Amount (USD)",
        "commission_rate":               "Comm. Rate %",
        "estimated_payments_commission": "Commission (USD)",
        "order_status":                  "Status",
        "region":                        "Region",
        "tracking_id":                   "Tracking ID",
        "order_platform":                "Platform",
        "category_id":                   "Category ID",
        "product_url":                   "Product URL",
    }
    avail_cols = [c for c in COL_MAP if c in df.columns]
    display_df = df[avail_cols].rename(columns=COL_MAP)

    st.dataframe(
        display_df,
        use_container_width=True,
        height=520,
        column_config={
            "Amount (USD)":      st.column_config.NumberColumn(format="$%.2f"),
            "Commission (USD)":  st.column_config.NumberColumn(format="$%.2f"),
            "Comm. Rate %":      st.column_config.NumberColumn(format="%.2f%%"),
            "Product URL":       st.column_config.LinkColumn("Product URL", display_text="🔗 Open"),
            "Time":              st.column_config.DatetimeColumn("Time", format="YYYY-MM-DD HH:mm"),
        },
        hide_index=True,
    )

    csv_bytes = display_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "📥 Export to CSV", data=csv_bytes,
        file_name=f"aliexpress_orders_{_dates[0]}_{_dates[-1]}.csv",
        mime="text/csv",
    )

st.divider()
st.caption("AliExpress Affiliate Dashboard  •  Data stored locally in orders.db  •  Auto-refresh: 15:00 & 16:00")
# patch applied via fix script
