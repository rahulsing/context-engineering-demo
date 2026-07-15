"""
Customer Analytics Agent — SLayer edition, Ollama (qwen2.5).

Building Block 7: Semantic Layer. Instead of the agent writing raw SQL
(agent_ollama.py) or reading a hand-parsed contract, this agent queries a
live SLayer semantic layer over REST. SLayer compiles the SQL — the agent
only ever asks for measures and dimensions by name, and the compiled SQL
is logged for audit (see the slayer.sql event in the trace).

Requires:
  - SLayer running:  uvx --from 'motley-slayer[all]' slayer serve --demo
  - Setup complete:  python setup_slayer.py
  - Ollama running:  ollama serve && ollama pull qwen2.5

Usage:
    python agent_slayer_ollama.py
    python agent_slayer_ollama.py > trace.jsonl
"""

import json
from datetime import datetime
import requests
import structlog
from openai import OpenAI

structlog.configure(
    processors=[structlog.processors.JSONRenderer()],
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)
logger = structlog.get_logger()

SLAYER_BASE = "http://127.0.0.1:5143"
MODEL_NAME  = "customer_metrics"
DS_NAME     = "customer_analytics"
MODEL       = "qwen2.5"
QUESTION    = (
    "What is the average customer LTV and churn risk score by segment, "
    "and which segment has the highest average churn risk?"
)

# --- Discover model metadata ---
model = requests.get(
    f"{SLAYER_BASE}/models/{MODEL_NAME}",
    params={"data_source": DS_NAME},
).json()

direct_columns = [
    c["name"] for c in model["columns"]
    if not c.get("hidden") and not c.get("primary_key")
]

logger.msg(
    "agent.start", question=QUESTION, slayer_model=MODEL_NAME, data_source=DS_NAME,
    model=MODEL, columns=direct_columns, timestamp=datetime.utcnow().isoformat() + "Z",
)

client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")

tools = [
    {
        "type": "function",
        "function": {
            "name": "query_customer_segments",
            "description": (
                f"Query the '{MODEL_NAME}' customer analytics model via SLayer. "
                f"Available columns: {direct_columns}. "
                "Use formula measures — 'customer_ltv:avg', 'churn_risk_score:avg', "
                "'repeat_purchase_rate:avg', 'customer_id:count'. "
                "Group by dimensions — 'segment', 'region'. "
                "Filters use SQL syntax: \"segment = 'at-risk'\"."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "measures": {
                        "type": "array", "items": {"type": "string"},
                        "description": "Formula measures, e.g. ['customer_ltv:avg', 'churn_risk_score:avg']",
                    },
                    "dimensions": {
                        "type": "array", "items": {"type": "string"},
                        "description": "Columns to group by, e.g. ['segment']",
                    },
                    "filters": {
                        "type": "array", "items": {"type": "string"},
                        "description": "SQL-style filters, e.g. [\"region = 'US'\"]",
                    },
                    "order": {
                        "type": "array", "items": {"type": "object"},
                        "description": "Sort, e.g. [{\"column\": \"segment\", \"direction\": \"asc\"}]",
                    },
                    "limit": {"type": "integer", "description": "Max rows to return"},
                },
                "required": ["measures"],
            },
        },
    }
]

# --- Turn 1: agent decides what to query ---
response = client.chat.completions.create(
    model=MODEL, tools=tools, messages=[{"role": "user", "content": QUESTION}],
)
msg = response.choices[0].message
logger.msg("agent.turn1", stop_reason=response.choices[0].finish_reason,
           timestamp=datetime.utcnow().isoformat() + "Z")

if not msg.tool_calls:
    print("\n" + "=" * 60)
    print(msg.content)
    print("=" * 60)
    exit(0)

# --- Tool execution: POST to SLayer REST API ---
tool_call = msg.tool_calls[0]
params = json.loads(tool_call.function.arguments)
logger.msg("tool.call", tool="query_customer_segments", params=params,
           timestamp=datetime.utcnow().isoformat() + "Z")

params["measures"]   = [{"formula": m} if isinstance(m, str) else m for m in params.get("measures", [])]
params["dimensions"] = [{"name": d}    if isinstance(d, str) else d for d in params.get("dimensions", [])]

# Remove 'order' if no dimensions — SLayer can't order without dimensions
if not params.get("dimensions"):
    params.pop("order", None)
# Remove empty filters — SLayer rejects an empty filter array
if not params.get("filters"):
    params.pop("filters", None)

query_payload = {"source_model": MODEL_NAME, **params}
slayer_resp = requests.post(f"{SLAYER_BASE}/query", json=query_payload)

if not slayer_resp.ok:
    logger.msg("slayer.error", status=slayer_resp.status_code, body=slayer_resp.text,
               timestamp=datetime.utcnow().isoformat() + "Z")
slayer_resp.raise_for_status()

result = slayer_resp.json()
data = result.get("data", [])
sql = result.get("sql")

logger.msg("tool.result", rows=len(data), data=data, timestamp=datetime.utcnow().isoformat() + "Z")
logger.msg("slayer.sql", sql=sql, timestamp=datetime.utcnow().isoformat() + "Z")

# --- Turn 2: agent synthesises the answer ---
final = client.chat.completions.create(
    model=MODEL,
    tools=tools,
    messages=[
        {"role": "user", "content": QUESTION},
        msg,
        {"role": "tool", "tool_call_id": tool_call.id, "content": json.dumps(data)},
    ],
)
answer = final.choices[0].message.content
logger.msg("agent.answer", timestamp=datetime.utcnow().isoformat() + "Z")

print("\n" + "=" * 60)
print(answer)
print("=" * 60)
