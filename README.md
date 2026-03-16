# 🛒 AliExpress Affiliate Dashboard

A local macOS dashboard to track AliExpress affiliate orders in real-time — no manual CSV exports needed.

---

## ✨ Features

| Feature | Detail |
|---|---|
| 📡 Live data | Pulls from `aliexpress.affiliate.order.get` API |
| ⏰ Auto-refresh | Automatically fetches at **15:00** and **16:00** daily |
| 🔄 Manual refresh | One-click refresh from sidebar |
| 🗄️ Local history | SQLite DB — keeps all fetched orders forever |
| 🔍 Filters | Date range, Region, Tracking ID, Order Status, Order ID search |
| 📊 Summary bar | Total orders · Total sales · Est. commission · Avg rate |
| 📥 CSV export | Export any filtered view to CSV |

---

## 🚀 Quick Start

### 1 — Prerequisites

- macOS (tested on Ventura / Sonoma)
- Python 3.10 or newer → [python.org](https://www.python.org/downloads/)

### 2 — First run

```bash
# Make scripts executable (one time only)
chmod +x run.sh open_dashboard.command

# Launch
./run.sh
```

Or **double-click `open_dashboard.command`** in Finder (first time: right-click → Open).

The script will:
1. Create a Python virtual environment (`.venv/`)
2. Install all dependencies
3. Open the dashboard at `http://localhost:8501`

### 3 — Enter API credentials

Open the sidebar **⚙️ Configuration → 🔑 API Keys** and fill in:

| Field | Where to find it |
|---|---|
| **App Key** | [AliExpress Affiliate Portal](https://portals.aliexpress.com) → Tools → API |
| **App Secret** | Same page, keep it secret! |
| **Tracking ID** | Optional default tracking ID |

Click **💾 Save** then **🔌 Test** to verify.

---

## 📁 Project Structure

```
aliexpress-dashboard/
├── app.py                  ← Streamlit UI (main entry point)
├── api_client.py           ← AliExpress API + signing logic
├── database.py             ← SQLite read/write helpers
├── scheduler.py            ← APScheduler jobs (15:00 & 16:00)
├── config.py               ← Config load/save (config.json)
├── requirements.txt        ← Python dependencies
├── run.sh                  ← Terminal launcher
├── open_dashboard.command  ← Finder double-click launcher
├── config.json             ← Created on first save (gitignored)
└── orders.db               ← SQLite database (created automatically)
```

---

## 🔧 How Auto-Refresh Works

`APScheduler` runs a background thread inside the Streamlit process.
Jobs fire at **15:00** and **16:00** (Asia/Ho_Chi_Minh timezone) and:
1. Call the API for today's `payment_completed` orders
2. Upsert results into `orders.db`

The UI auto-detects the new data on the next browser interaction or manual page refresh.

---

## 🌐 API Reference

- **Endpoint:** `aliexpress.affiliate.order.get`
- **Base URL:** `https://api-sg.aliexpress.com/sync`
- **Signing:** MD5/TOP protocol (`HMAC` over sorted key-value pairs)
- **Pagination:** 50 orders/page, auto-paginated up to 1 000 rows

---

## 🛟 Troubleshooting

| Problem | Fix |
|---|---|
| `python3` not found | Install Python 3.10+ from python.org |
| API error 27 / invalid signature | Double-check App Key & Secret (no extra spaces) |
| No orders returned | Verify the date range; API only returns `payment_completed` |
| Port 8501 in use | `lsof -ti:8501 \| xargs kill` then re-run |
