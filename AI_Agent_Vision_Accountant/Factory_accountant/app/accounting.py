"""
Factory accounting engine.

Important note about the incoming data:
The computer-vision app (main.py) posts total_entered / total_exit / total_internal
for a "batch" every time that batch finishes (i.e. no new object has been seen for
a while), and immediately resets its own counters right after sending.
So every JSON payload received here is the "delta" (increase) for that batch,
not a cumulative value since the start of the day. This agent is responsible for
accumulating these deltas over each hour/day itself.

Sample input JSON structure (actual output of main.py):
{
  "akhal_3": {... per-track details ...},
  "forklift_1": {...},
  "total_entered": {"forklift": 1, "akhal": 4},
  "total_exit":    {"forklift": 1, "akhal": 2},
  "total_internal":{"forklift": 0, "akhal": 1},
  "total": 4
}
"""
import json
import os
from datetime import datetime, timezone

from . import database as db

CONFIG_DIR = os.path.join(os.path.dirname(__file__), "..", "config")
PRICES_PATH = os.path.abspath(os.path.join(CONFIG_DIR, "prices.json"))
SETTINGS_PATH = os.path.abspath(os.path.join(CONFIG_DIR, "settings.json"))


def load_prices():
    with open(PRICES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_settings():
    with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def now_iso():
    return datetime.now().isoformat(timespec="microseconds")


def process_payload(payload: dict) -> dict:
    """
    Takes a raw payload from the vision counter, creates financial transactions,
    updates warehouse inventory, and flags audit anomalies.
    Returns: a summary of what was processed (for logging/debugging).
    """
    prices = load_prices()["products"]
    settings = load_settings()["business_rules"]
    ts = now_iso()

    event_id = db.insert_raw_event(payload, ts)

    total_entered = payload.get("total_entered", {}) or {}
    total_exit = payload.get("total_exit", {}) or {}
    total_internal = payload.get("total_internal", {}) or {}

    processed = {"purchases": [], "sales": [], "internal": [], "anomalies": []}

    all_classes = set(total_entered) | set(total_exit) | set(total_internal)

    for cls in all_classes:
        price_info = prices.get(cls, {"is_valued": False, "purchase_unit_price": 0,
                                       "sale_unit_price": 0, "display_name": cls, "unit": "unit"})
        entered_qty = int(total_entered.get(cls, 0))
        exited_qty = int(total_exit.get(cls, 0))
        internal_qty = int(total_internal.get(cls, 0))

        # --- entry = purchase (as configured) ---
        if entered_qty > 0:
            unit_price = price_info.get("purchase_unit_price", 0) if price_info.get("is_valued") else 0
            value = unit_price * entered_qty
            db.insert_transaction(event_id, ts, cls, "purchase", entered_qty, unit_price, value)
            db.adjust_inventory(cls, +entered_qty, ts)
            processed["purchases"].append({"class": cls, "qty": entered_qty, "value": value})

        # --- exit = sale (as configured) ---
        if exited_qty > 0:
            unit_price = price_info.get("sale_unit_price", 0) if price_info.get("is_valued") else 0
            value = unit_price * exited_qty
            current_stock = db.get_inventory(cls)
            is_anomaly = exited_qty > current_stock
            note = None
            if is_anomaly:
                en_name = price_info.get("display_name_en", cls)
                note = (f"Exit of {exited_qty} unit(s) of '{en_name}' exceeds current stock "
                        f"({current_stock}). Possible camera miscount or missing prior entry.")
                processed["anomalies"].append(note)
            db.insert_transaction(event_id, ts, cls, "sale", exited_qty, unit_price, value,
                                   is_anomaly=is_anomaly, anomaly_note=note)
            db.adjust_inventory(cls, -exited_qty, ts)
            processed["sales"].append({"class": cls, "qty": exited_qty, "value": value})

        # --- internal movement: only logged, no financial value or inventory effect ---
        if internal_qty > 0:
            db.insert_transaction(event_id, ts, cls, "internal", internal_qty, 0, 0)
            processed["internal"].append({"class": cls, "qty": internal_qty})

    return processed
