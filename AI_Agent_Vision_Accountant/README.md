# Factory Accountant Agent

An agent that receives the JSON output of a computer-vision factory product
counter (`akhal_position_base/main.py`), acts as an accountant (prices are
pre-configured), performs inventory auditing, converts entries/exits into
purchases/sales, and sends hourly + end-of-day reports to the factory manager.

It also ships with a small web dashboard (all-English UI) with a **Start
Vision** / **Stop Vision** button and a live purchases/sales/inventory view.

## How it works

The vision counter app (`main.py`) posts a batch to
`http://<IP>:6008/receive_data/` every time a batch of detections finishes
(i.e. no new object has been seen for a while). A batch payload looks like:

```json
{
  "akhal_3": { "...per-track details..." },
  "forklift_1": { "..." },
  "total_entered":  {"forklift": 1, "akhal": 4},
  "total_exit":     {"forklift": 1, "akhal": 2},
  "total_internal": {"forklift": 0, "akhal": 1},
  "total": 4
}
```

Important: `main.py` resets its own counters immediately after sending each
batch. That means every JSON payload received is the **delta** (increase) for
that batch, not a cumulative total since the start of the day. This agent
accumulates those deltas itself so it can build accurate hourly/daily reports.

## Business-rule assumption ⚠️

By default:
- **Entry at the detection line = purchase** (goods/raw material entering the warehouse)
- **Exit at the detection line = sale** (goods leaving the warehouse to a customer)
- **Internal movement = no financial effect**, logged for reporting only

If your factory's real logic is reversed (e.g. the detection line is where a
manufactured product enters the warehouse, not a purchase from outside),
change `business_rules` in `config/settings.json`, or edit `process_payload()`
in `app/accounting.py` with your exact logic.
**Confirm this with your operations team before relying on the financial
numbers.**

## Prices

`config/prices.json` holds the purchase/sale price for each detected product
class. The classes match the ones the vision model can detect
(`forklift, sulfate, pack, fructose, paper-roll, akhal, sude, akd`). The
shipped file has **placeholder numbers** — replace them with your real prices
before using this in production.

```json
"akhal": {
  "display_name": "آخال",
  "display_name_en": "Akhal",
  "unit": "Bale",
  "purchase_unit_price": 120,
  "sale_unit_price": 0,
  "is_valued": true
}
```

`forklift` is not a product, so it has `is_valued: false` and is excluded
from financial calculations — but its entry/exit/internal counts are still
tracked as an operational metric.

## Requirements

- Python 3.10+ (any recent version works; avoid brand-new releases like 3.14
  if you hit missing prebuilt wheels for some dependency)
- The vision counter app (`akhal_position_base`) already set up and working
  with its own Python environment (opencv, torch, ultralytics, etc.)

## Getting the code from GitHub

```bash
git clone https://github.com/masoudshahrian/Agentic-App.git
cd <your-repo>/factory_accountant
```

(Adjust the path if you put this project inside a different folder structure
in your repository.)

## Installation

```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
```

## Configuration (do this before running)

1. **Prices** — edit `config/prices.json` and put in your real purchase/sale
   prices for each product.
2. **Business rules** — confirm `entry_means` / `exit_means` in
   `config/settings.json` match your factory's real logic.
3. **Vision app paths** (needed for the dashboard's Start/Stop button) — edit
   `vision_app` in `config/settings.json`:
   ```json
   "vision_app": {
     "python_executable": "C:\\path\\to\\akhal_position_base\\venv\\Scripts\\python.exe",
     "script_path": "C:\\path\\to\\akhal_position_base\\main.py",
     "working_directory": "C:\\path\\to\\akhal_position_base"
   }
   ```
   `python_executable` must be the vision app's **own** Python/venv (the one
   with opencv/torch installed), not this agent's venv — they are separate
   environments.
4. **Notifications** (optional) — set `notifier.channel` in
   `config/settings.json` to `telegram` and fill in `bot_token` / `chat_id`
   if you want hourly/daily reports delivered automatically. Default is
   `console` (prints to the terminal).

## Running

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 6008
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:6008
INFO:     Application startup complete.
```

Keep this terminal open — the agent must stay running for the scheduled
hourly/daily reports to fire.

### Point the vision app at this agent

In the vision app's `main.py`, find the line that posts data and make sure it
targets this agent's address:

```python
requests.post("http://127.0.0.1:6008/receive_data/", json=GLOBAL_OUTPUT)
```

Use `127.0.0.1` if both apps run on the same machine, or this machine's LAN
IP if they run on different machines on the same network.

### Open the dashboard

Go to `http://127.0.0.1:6008/` in your browser. Click **Start Vision** to
launch the vision counter script (opens in its own console window), and
watch the **Purchases**, **Sales**, and **Current Inventory** tables update
live as objects cross the detection line. Click **Stop Vision** to stop it.

## Quick test without a camera

```bash
python scripts/simulate_send.py
```

This posts a few sample batches (matching the real vision app's JSON shape)
so you can verify the pipeline end-to-end.

Then check:
```bash
curl http://127.0.0.1:6008/inventory
curl http://127.0.0.1:6008/reports/hourly/run
```

## Scheduled reports

- **Hourly report**: on the hour, every hour (configurable via
  `settings.json` → `hourly_report`)
- **End-of-day report**: 23:59 by default (configurable via `settings.json`
  → `daily_report`), also saved to `reports/daily_report_<date>.txt`

Both run via APScheduler in the background — the server process must stay
alive (consider running it with `systemd`, `pm2`, `nssm`, or Docker in
production instead of a plain terminal).

## Automatic auditing

Whenever a sale (exit) is recorded for more units than are currently in
stock, the agent flags it as an anomaly and includes it in the report — a
likely sign of a camera miscount, or a mismatch between real-world entries
and what was actually detected.

## Project structure

```
factory_accountant/
├── app/
│   ├── main.py           # FastAPI server, dashboard route, and the ingest endpoint
│   ├── accounting.py     # Converts entries/exits into purchases/sales + auditing
│   ├── database.py       # SQLite storage layer
│   ├── reporting.py      # Builds hourly/daily report text (Persian + English)
│   ├── notifier.py       # Sends reports via console/Telegram/webhook
│   ├── scheduler.py      # Schedules the automatic hourly/daily reports
│   ├── vision_control.py # Starts/stops the vision counter subprocess
│   └── static/
│       └── dashboard.html
├── config/
│   ├── prices.json       # Purchase/sale price per product (replace with real values)
│   └── settings.json     # Server, schedule, notification, vision-app paths
├── scripts/
│   └── simulate_send.py  # Sends sample payloads for testing
├── data/                 # SQLite database (created automatically)
└── reports/              # Saved daily report .txt files
```

## Note on report language

The saved daily report file and Telegram/webhook messages are generated in
**Persian**, since they are meant for a Persian-speaking factory manager. The
plain console/cmd output uses **English** by default (`console_report_language`
in `settings.json`), since Windows `cmd` often can't render Persian glyphs
correctly. Change `console_report_language` to `"fa"` if your terminal
supports UTF-8/RTL properly (e.g. Windows Terminal with `chcp 65001`).

## Suggested next steps

1. Enter your real prices in `prices.json`.
2. Confirm the entry=purchase / exit=sale mapping with your operations team.
3. Set up the Telegram channel so the manager receives reports automatically.
4. Run the agent as a persistent service (not just from an interactive
   terminal) on the machine that will host it long-term.
