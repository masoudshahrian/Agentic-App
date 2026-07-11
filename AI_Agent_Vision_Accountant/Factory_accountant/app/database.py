"""
Database layer - everything is stored in a single SQLite file to keep
installation and maintenance simple.
"""
import sqlite3
import json
import os
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "accounting.db")
DB_PATH = os.path.abspath(DB_PATH)


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS raw_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                received_at TEXT NOT NULL,
                payload TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER,
                created_at TEXT NOT NULL,
                product_class TEXT NOT NULL,
                tx_type TEXT NOT NULL,      -- purchase | sale | internal
                quantity INTEGER NOT NULL,
                unit_price REAL NOT NULL,
                value REAL NOT NULL,
                is_anomaly INTEGER NOT NULL DEFAULT 0,
                anomaly_note TEXT,
                FOREIGN KEY(event_id) REFERENCES raw_events(id)
            );

            CREATE TABLE IF NOT EXISTS inventory (
                product_class TEXT PRIMARY KEY,
                quantity INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT
            );

            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_type TEXT NOT NULL,   -- hourly | daily
                period_start TEXT NOT NULL,
                period_end TEXT NOT NULL,
                created_at TEXT NOT NULL,
                content TEXT NOT NULL,
                file_path TEXT
            );
            """
        )


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def insert_raw_event(payload: dict, received_at: str) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO raw_events (received_at, payload) VALUES (?, ?)",
            (received_at, json.dumps(payload, ensure_ascii=False)),
        )
        return cur.lastrowid


def insert_transaction(event_id, created_at, product_class, tx_type, quantity,
                        unit_price, value, is_anomaly=False, anomaly_note=None):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO transactions
               (event_id, created_at, product_class, tx_type, quantity, unit_price,
                value, is_anomaly, anomaly_note)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (event_id, created_at, product_class, tx_type, quantity, unit_price,
             value, int(is_anomaly), anomaly_note),
        )


def get_inventory(product_class: str) -> int:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT quantity FROM inventory WHERE product_class = ?", (product_class,)
        ).fetchone()
        return row["quantity"] if row else 0


def adjust_inventory(product_class: str, delta: int, updated_at: str):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT quantity FROM inventory WHERE product_class = ?", (product_class,)
        ).fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO inventory (product_class, quantity, updated_at) VALUES (?, ?, ?)",
                (product_class, max(delta, 0), updated_at),
            )
        else:
            new_qty = row["quantity"] + delta
            conn.execute(
                "UPDATE inventory SET quantity = ?, updated_at = ? WHERE product_class = ?",
                (new_qty, updated_at, product_class),
            )


def all_inventory():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM inventory ORDER BY product_class").fetchall()
        return [dict(r) for r in rows]


def transactions_between(start_iso: str, end_iso: str):
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT * FROM transactions
               WHERE created_at >= ? AND created_at <= ?
               ORDER BY created_at""",
            (start_iso, end_iso),
        ).fetchall()
        return [dict(r) for r in rows]


def save_report(report_type, period_start, period_end, created_at, content, file_path=None):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO reports (report_type, period_start, period_end, created_at, content, file_path)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (report_type, period_start, period_end, created_at, content, file_path),
        )


def latest_report(report_type: str):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM reports WHERE report_type = ? ORDER BY id DESC LIMIT 1",
            (report_type,),
        ).fetchone()
        return dict(row) if row else None
