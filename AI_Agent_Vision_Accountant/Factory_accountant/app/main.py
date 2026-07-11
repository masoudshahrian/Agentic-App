# -*- coding: utf-8 -*-
"""
Main server for the Factory Accountant Agent.

This server implements the same endpoint that the vision counter app
(main.py in akhal_position_base) posts to:  POST /receive_data/

That means all you need to do is point the following line in the vision app's
main.py to this server's address:
    requests.post(f"http://<this-server-IP>:6008/receive_data/", json=GLOBAL_OUTPUT)
"""
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse, HTMLResponse
import os

from . import database as db
from .accounting import process_payload, load_settings
from .scheduler import start_scheduler
from .reporting import generate_hourly_report, generate_daily_report, get_live_summary
from . import vision_control

app = FastAPI(title="Factory Accountant Agent")

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


@app.on_event("startup")
def on_startup():
    db.init_db()
    start_scheduler()


@app.get("/", response_class=HTMLResponse)
def dashboard():
    with open(os.path.join(STATIC_DIR, "dashboard.html"), "r", encoding="utf-8") as f:
        return f.read()


@app.post("/vision/start")
def vision_start():
    return vision_control.start_vision()


@app.post("/vision/stop")
def vision_stop():
    return vision_control.stop_vision()


@app.get("/vision/status")
def vision_status():
    return vision_control.status()


@app.get("/live/summary")
def live_summary():
    return get_live_summary()


@app.post("/receive_data/")
async def receive_data(request: Request):
    payload = await request.json()
    result = process_payload(payload)
    return {"status": "ok", "processed": result}


@app.get("/health")
def health():
    return {"status": "up"}


@app.get("/inventory")
def inventory():
    return db.all_inventory()


@app.get("/reports/hourly/run", response_class=PlainTextResponse)
def run_hourly_now():
    """Manually trigger the hourly report (for testing) - builds it and sends it."""
    from .notifier import send_report
    text = generate_hourly_report()
    send_report(text)
    return text


@app.get("/reports/daily/run", response_class=PlainTextResponse)
def run_daily_now():
    """Manually trigger the end-of-day report (for testing)."""
    from .notifier import send_report
    text = generate_daily_report()
    send_report(text)
    return text


@app.get("/reports/hourly/latest", response_class=PlainTextResponse)
def latest_hourly():
    r = db.latest_report("hourly")
    return r["content"] if r else "No report has been generated yet."


@app.get("/reports/daily/latest", response_class=PlainTextResponse)
def latest_daily():
    r = db.latest_report("daily")
    return r["content"] if r else "No report has been generated yet."
