# -*- coding: utf-8 -*-
"""
Simulates several output batches from the vision counter app, for testing
the accountant agent.
Run: python scripts/simulate_send.py
"""
import requests
import time

URL = "http://127.0.0.1:6008/receive_data/"

BATCHES = [
    {"total_entered": {"forklift": 1, "akhal": 4}, "total_exit": {"forklift": 0, "akhal": 0}, "total_internal": {"forklift": 0, "akhal": 0}, "total": 4},
    {"total_entered": {"forklift": 0, "sulfate": 2}, "total_exit": {"forklift": 1, "akhal": 2}, "total_internal": {"forklift": 0, "akhal": 1}, "total": 2},
    {"total_entered": {"forklift": 1, "paper-roll": 6}, "total_exit": {"forklift": 0, "sulfate": 1}, "total_internal": {}, "total": 6},
    # This batch intentionally exits more akhal than is in stock, to test the audit warning
    {"total_entered": {}, "total_exit": {"akhal": 50}, "total_internal": {}, "total": 0},
]

for i, batch in enumerate(BATCHES, 1):
    r = requests.post(URL, json=batch)
    print(f"batch {i} -> status={r.status_code} response={r.json()}")
    time.sleep(0.5)
