"""
Background scheduler — auto-fetches orders at 15:00 and 16:00 every day.
Uses APScheduler's BackgroundScheduler so it runs alongside Streamlit.
"""

import logging
from datetime import date, datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

_scheduler = None


def _fetch_today(config: dict, db):
    """Job executed at scheduled times."""
    from api_client import AliExpressAPI

    app_key = config.get("app_key", "")
    app_secret = config.get("app_secret", "")

    if not app_key or not app_secret:
        logger.warning("Scheduler: API keys not configured, skipping auto-fetch.")
        return

    today = date.today()
    start = f"{today} 00:00:00"
    end   = f"{today} 23:59:59"

    logger.info("Scheduler: starting auto-fetch for %s", today)
    try:
        api = AliExpressAPI(app_key, app_secret)
        orders = api.fetch_all_orders(start, end)
        db.upsert_orders(orders)
        logger.info("Scheduler: fetched %d orders.", len(orders))
    except Exception as exc:
        logger.error("Scheduler: fetch failed — %s", exc)


def start_scheduler(config: dict, db):
    """
    Start the background scheduler.
    Call once at app startup; safe to call multiple times (idempotent).
    """
    global _scheduler

    if _scheduler is not None and _scheduler.running:
        return  # already running

    _scheduler = BackgroundScheduler(timezone="Asia/Ho_Chi_Minh")

    # 15:00 daily
    _scheduler.add_job(
        _fetch_today,
        trigger=CronTrigger(hour=15, minute=0),
        args=[config, db],
        id="auto_fetch_15",
        replace_existing=True,
    )

    # 16:00 daily
    _scheduler.add_job(
        _fetch_today,
        trigger=CronTrigger(hour=16, minute=0),
        args=[config, db],
        id="auto_fetch_16",
        replace_existing=True,
    )

    _scheduler.start()
    logger.info("Scheduler started — jobs at 15:00 and 16:00 (Asia/Ho_Chi_Minh).")


def stop_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        _scheduler = None
