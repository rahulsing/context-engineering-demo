"""
Register the customer_analytics datasource and auto-ingest the
customer_metrics model into the running SLayer instance.

Run once after bootstrap.py, before running agent_slayer_ollama.py.

Requires SLayer running at http://127.0.0.1:5143:
    uvx --from 'motley-slayer[all]' slayer serve --demo

Usage:
    python setup_slayer.py
"""

import os
import sys
import requests

SLAYER_BASE = "http://127.0.0.1:5143"
DS_NAME     = "customer_analytics"
DB_FILE     = "customer_analytics.duckdb"
TABLE       = "customer_metrics"

db_path = os.path.abspath(DB_FILE)

if not os.path.exists(db_path):
    print(f"ERROR: {db_path} not found — run bootstrap.py first.")
    sys.exit(1)

# --- Step 1: Register datasource ---
print(f"\n[1/3] Registering datasource '{DS_NAME}' -> {db_path}")

existing = [d["name"] for d in requests.get(f"{SLAYER_BASE}/datasources").json()]
if DS_NAME in existing:
    print("      Already registered — skipping.")
else:
    resp = requests.post(f"{SLAYER_BASE}/datasources", json={
        "name":     DS_NAME,
        "type":     "duckdb",
        "database": db_path,
    })
    if not resp.ok:
        print(f"ERROR: {resp.status_code} — {resp.text}")
        sys.exit(1)
    print(f"      Done: {resp.json()}")

# --- Step 2: Auto-ingest models ---
print(f"\n[2/3] Ingesting models from '{DS_NAME}' (table: {TABLE})")

resp = requests.post(f"{SLAYER_BASE}/ingest", json={
    "datasource":     DS_NAME,
    "include_tables": [TABLE],
})
if not resp.ok:
    print(f"ERROR: {resp.status_code} — {resp.text}")
    sys.exit(1)

ingested = resp.json()
print(f"      Done: {ingested}")

# --- Step 3: Verify model is visible ---
print(f"\n[3/3] Verifying model '{TABLE}' is available")

model = requests.get(f"{SLAYER_BASE}/models/{TABLE}", params={"data_source": DS_NAME}).json()
columns = [c["name"] for c in model.get("columns", [])]
print(f"      Columns : {columns}")
print(f"      Source  : {model.get('data_source')}")
print("\nReady. Run agent_slayer_ollama.py to ask questions.")
