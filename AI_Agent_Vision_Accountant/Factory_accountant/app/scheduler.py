# -*- coding: utf-8 -*-
"""
Scheduling of hourly and daily reports.
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from .accounting import load_settings
from .reporting import generate_hourly_report, generate_daily_report
from .notifier import send_report

_scheduler = None


def _run_hourly_job():
    text = generate_hourly_report()
    send_report(text)


def _run_daily_job():
    text = generate_daily_report()
    send_report(text)


def start_scheduler():
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    settings = load_settings()
    tz = settings.get("timezone", "Asia/Tehran")
    _scheduler = BackgroundScheduler(timezone=tz)

    hourly_cfg = settings.get("hourly_report", {})
    if hourly_cfg.get("enabled", True):
        _scheduler.add_job(
            _run_hourly_job,
            CronTrigger(minute=hourly_cfg.get("run_at_minute", 0), timezone=tz),
            id="hourly_report",
            replace_existing=True,
        )

    daily_cfg = settings.get("daily_report", {})
    if daily_cfg.get("enabled", True):
        _scheduler.add_job(
            _run_daily_job,
            CronTrigger(hour=daily_cfg.get("run_at_hour", 23),
                        minute=daily_cfg.get("run_at_minute", 59), timezone=tz),
            id="daily_report",
            replace_existing=True,
        )

    _scheduler.start()
    return _scheduler
