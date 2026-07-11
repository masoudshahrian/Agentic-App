# -*- coding: utf-8 -*-
"""
Sends the generated report to the factory manager.
The delivery channel is read from config/settings.json: console | telegram | webhook
"""
import requests

from .accounting import load_settings


def send_report(text: str):
    settings = load_settings()["notifier"]
    channel = settings.get("channel", "console")

    if channel == "telegram":
        _send_telegram(text, settings.get("telegram", {}))
    elif channel == "webhook":
        _send_webhook(text, settings.get("webhook", {}))
    else:
        _send_console(text)


def _send_console(text: str):
    print("\n" + "=" * 60)
    print(text)
    print("=" * 60 + "\n")


def _send_telegram(text: str, cfg: dict):
    token = cfg.get("bot_token")
    chat_id = cfg.get("chat_id")
    if not token or not chat_id:
        print("[notifier] Telegram settings are incomplete; printing report to console instead.")
        _send_console(text)
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        # Telegram has a message length limit; long reports are sent in chunks.
        chunk_size = 3500
        for i in range(0, len(text), chunk_size):
            requests.post(url, json={"chat_id": chat_id, "text": text[i:i + chunk_size]}, timeout=15)
    except requests.RequestException as e:
        print(f"[notifier] Telegram delivery failed: {e}")
        _send_console(text)


def _send_webhook(text: str, cfg: dict):
    url = cfg.get("url")
    if not url:
        print("[notifier] Webhook URL is not configured; printing report to console instead.")
        _send_console(text)
        return
    try:
        requests.post(url, json={"report": text}, timeout=15)
    except requests.RequestException as e:
        print(f"[notifier] Webhook delivery failed: {e}")
        _send_console(text)
