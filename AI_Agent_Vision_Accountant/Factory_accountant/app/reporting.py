# -*- coding: utf-8 -*-
"""
Generates hourly and daily reports from the transactions stored in the database.

Note: build_report_text() below produces the report in Persian (Farsi) on purpose -
it is the report meant for the factory manager (saved to the daily .txt file and
sent via Telegram/webhook). build_report_text_en() produces the English version used
for plain console/cmd output (see console_report_language in settings.json), since
Windows cmd often can't render Persian glyphs correctly.
"""
import os
from datetime import datetime, timedelta
from collections import defaultdict

from . import database as db
from .accounting import load_prices

try:
    import jdatetime
    def fa_date(dt: datetime) -> str:
        return jdatetime.datetime.fromgregorian(datetime=dt).strftime("%Y/%m/%d %H:%M")
except ImportError:
    def fa_date(dt: datetime) -> str:
        return dt.strftime("%Y-%m-%d %H:%M")

REPORTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "reports"))


def _fmt_money(v):
    return f"{v:,.0f}"


def _aggregate(transactions):
    purchases = defaultdict(lambda: {"qty": 0, "value": 0.0})
    sales = defaultdict(lambda: {"qty": 0, "value": 0.0})
    internal = defaultdict(int)
    anomalies = []

    for tx in transactions:
        cls = tx["product_class"]
        if tx["tx_type"] == "purchase":
            purchases[cls]["qty"] += tx["quantity"]
            purchases[cls]["value"] += tx["value"]
        elif tx["tx_type"] == "sale":
            sales[cls]["qty"] += tx["quantity"]
            sales[cls]["value"] += tx["value"]
            if tx["is_anomaly"]:
                anomalies.append(tx["anomaly_note"])
        elif tx["tx_type"] == "internal":
            internal[cls] += tx["quantity"]

    total_purchase_value = sum(p["value"] for p in purchases.values())
    total_sale_value = sum(s["value"] for s in sales.values())
    return purchases, sales, internal, anomalies, total_purchase_value, total_sale_value


def _display_name(cls, prices):
    return prices.get(cls, {}).get("display_name", cls)


def build_report_text(period_label: str, start: datetime, end: datetime) -> str:
    prices = load_prices()["products"]
    currency = load_prices().get("currency", "IRR")
    txs = db.transactions_between(start.isoformat(timespec="microseconds"),
                                   end.isoformat(timespec="microseconds"))
    purchases, sales, internal, anomalies, total_purchase, total_sale = _aggregate(txs)
    profit = total_sale - total_purchase
    inventory = db.all_inventory()

    lines = []
    lines.append(f"📊 گزارش حسابداری کارخانه — {period_label}")
    lines.append(f"بازه: {fa_date(start)} تا {fa_date(end)}")
    lines.append("")

    lines.append("🟢 خریدها (ورود از خط تشخیص):")
    if purchases:
        for cls, d in sorted(purchases.items()):
            lines.append(f"  • {_display_name(cls, prices)}: {d['qty']} واحد — {_fmt_money(d['value'])} {currency}")
    else:
        lines.append("  چیزی ثبت نشده است.")
    lines.append(f"  جمع ارزش خرید: {_fmt_money(total_purchase)} {currency}")
    lines.append("")

    lines.append("🔴 فروش‌ها (خروج از خط تشخیص):")
    if sales:
        for cls, d in sorted(sales.items()):
            lines.append(f"  • {_display_name(cls, prices)}: {d['qty']} واحد — {_fmt_money(d['value'])} {currency}")
    else:
        lines.append("  چیزی ثبت نشده است.")
    lines.append(f"  جمع ارزش فروش: {_fmt_money(total_sale)} {currency}")
    lines.append("")

    lines.append(f"💰 سود/زیان ناخالص این بازه: {_fmt_money(profit)} {currency}")
    lines.append("")

    if internal:
        lines.append("🔁 جابجایی داخلی (بدون اثر مالی):")
        for cls, qty in sorted(internal.items()):
            lines.append(f"  • {_display_name(cls, prices)}: {qty} واحد")
        lines.append("")

    lines.append("📦 موجودی فعلی انبار:")
    if inventory:
        for row in inventory:
            lines.append(f"  • {_display_name(row['product_class'], prices)}: {row['quantity']} واحد")
    else:
        lines.append("  اطلاعاتی ثبت نشده است.")
    lines.append("")

    if anomalies:
        lines.append("⚠️ هشدارهای حسابرسی:")
        for a in anomalies:
            lines.append(f"  • {a}")
    else:
        lines.append("✅ هیچ ناهنجاری حسابرسی در این بازه یافت نشد.")

    return "\n".join(lines)


def build_report_text_en(period_label: str, start: datetime, end: datetime) -> str:
    """English version, safe to print in a plain Windows cmd window (no UTF-8/RTL issues)."""
    prices = load_prices()["products"]
    currency = load_prices().get("currency", "IRR")
    txs = db.transactions_between(start.isoformat(timespec="microseconds"),
                                   end.isoformat(timespec="microseconds"))
    purchases, sales, internal, anomalies, total_purchase, total_sale = _aggregate(txs)
    profit = total_sale - total_purchase
    inventory = db.all_inventory()

    def name(cls):
        return prices.get(cls, {}).get("display_name_en", cls)

    lines = []
    lines.append(f"Factory Accounting Report - {period_label}")
    lines.append(f"Period: {start.strftime('%Y-%m-%d %H:%M')} to {end.strftime('%Y-%m-%d %H:%M')}")
    lines.append("")

    lines.append("PURCHASES (entries):")
    if purchases:
        for cls, d in sorted(purchases.items()):
            lines.append(f"  - {name(cls)}: {d['qty']} units -- {_fmt_money(d['value'])} {currency}")
    else:
        lines.append("  (none)")
    lines.append(f"  Total purchase value: {_fmt_money(total_purchase)} {currency}")
    lines.append("")

    lines.append("SALES (exits):")
    if sales:
        for cls, d in sorted(sales.items()):
            lines.append(f"  - {name(cls)}: {d['qty']} units -- {_fmt_money(d['value'])} {currency}")
    else:
        lines.append("  (none)")
    lines.append(f"  Total sale value: {_fmt_money(total_sale)} {currency}")
    lines.append("")

    lines.append(f"Gross profit/loss this period: {_fmt_money(profit)} {currency}")
    lines.append("")

    if internal:
        lines.append("INTERNAL MOVEMENT (no financial value):")
        for cls, qty in sorted(internal.items()):
            lines.append(f"  - {name(cls)}: {qty} units")
        lines.append("")

    lines.append("CURRENT INVENTORY:")
    if inventory:
        for row in inventory:
            lines.append(f"  - {name(row['product_class'])}: {row['quantity']} units")
    else:
        lines.append("  (no data)")
    lines.append("")

    if anomalies:
        lines.append("AUDIT WARNINGS:")
        for a in anomalies:
            lines.append(f"  - {a}")
    else:
        lines.append("No audit anomalies found in this period.")

    return "\n".join(lines)


def get_live_summary(limit: int = 30) -> dict:
    """Used by the dashboard: today's purchases/sales lists + totals + current inventory."""
    prices = load_prices()["products"]
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    txs = db.transactions_between(today_start.isoformat(timespec="microseconds"),
                                   datetime.now().isoformat(timespec="microseconds"))

    def label(cls):
        return prices.get(cls, {}).get("display_name_en", cls)

    purchases = [t for t in txs if t["tx_type"] == "purchase"]
    sales = [t for t in txs if t["tx_type"] == "sale"]

    total_purchase_value = sum(t["value"] for t in purchases)
    total_sale_value = sum(t["value"] for t in sales)

    def fmt(t):
        return {
            "time": t["created_at"][11:19],
            "product": label(t["product_class"]),
            "qty": t["quantity"],
            "value": t["value"],
            "is_anomaly": bool(t["is_anomaly"]),
        }

    inventory = db.all_inventory()
    inventory_out = [{"product": label(r["product_class"]), "quantity": r["quantity"]} for r in inventory]

    return {
        "purchases": [fmt(t) for t in purchases[-limit:][::-1]],
        "sales": [fmt(t) for t in sales[-limit:][::-1]],
        "totals": {
            "purchase_value": total_purchase_value,
            "sale_value": total_sale_value,
            "profit": total_sale_value - total_purchase_value,
            "currency": load_prices().get("currency", "IRR"),
        },
        "inventory": inventory_out,
    }


def generate_hourly_report() -> str:
    """Saves the Persian report (DB + used for telegram/webhook) and returns the
    console-language version (per settings.json) for printing/return to caller."""
    end = datetime.now()
    start = end - timedelta(hours=1)
    from .accounting import load_settings
    lang = load_settings().get("console_report_language", "en")

    text_fa = build_report_text("گزارش ساعتی", start, end)
    db.save_report("hourly", start.isoformat(timespec="microseconds"),
                    end.isoformat(timespec="microseconds"), datetime.now().isoformat(timespec="microseconds"),
                    text_fa)

    if lang == "en":
        return build_report_text_en("Hourly Report", start, end)
    return text_fa


def generate_daily_report() -> str:
    end = datetime.now()
    start = end.replace(hour=0, minute=0, second=0, microsecond=0)
    from .accounting import load_settings
    lang = load_settings().get("console_report_language", "en")

    text_fa = build_report_text("گزارش سراسری پایان روز", start, end)

    os.makedirs(REPORTS_DIR, exist_ok=True)
    file_name = f"daily_report_{end.strftime('%Y-%m-%d')}.txt"
    file_path = os.path.join(REPORTS_DIR, file_name)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(text_fa)

    db.save_report("daily", start.isoformat(timespec="microseconds"),
                    end.isoformat(timespec="microseconds"), datetime.now().isoformat(timespec="microseconds"),
                    text_fa, file_path=file_path)

    if lang == "en":
        return build_report_text_en("End-of-Day Report", start, end)
    return text_fa
