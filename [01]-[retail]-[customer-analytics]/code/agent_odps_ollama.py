"""
Customer Analytics Agent — ODPS edition, Ollama (qwen2.5).

Building Block 8: ODPS (Open Data Product Standard). Upgrades the
table-level ODCS contract (contracts/customer_metrics.yaml) to
product-level governance — the agent now understands not just the
schema, but who owns this product, what use cases it's approved for, and
what SLA it's held to.

The agent extracts context from the product definition:
  - Product description and domain
  - Owner and team
  - Use cases (what questions is this product built to answer?)
  - Output port table definition and column descriptions
  - SLA properties (freshness, availability, retention)
  - Data quality checks
  - Usage terms

Requires:
  - Ollama running:  ollama serve && ollama pull qwen2.5
  - Bootstrap done:  python bootstrap.py

Usage:
    python agent_odps_ollama.py
    python agent_odps_ollama.py > trace.jsonl
"""

import json
from datetime import datetime
import duckdb
import yaml
import structlog
from openai import OpenAI

structlog.configure(
    processors=[structlog.processors.JSONRenderer()],
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)
logger = structlog.get_logger()

DB_FILE      = "customer_analytics.duckdb"
PRODUCT_FILE = "products/customer_analytics_odps.yaml"
MODEL        = "qwen2.5"
QUESTION     = (
    "Which customers are high-value and at risk of churn? Is this data "
    "product approved for VIP retention targeting, who owns it, and how "
    "fresh is the data?"
)

# --- Load ODPS product definition and extract context ---
with open(PRODUCT_FILE) as f:
    product_def = yaml.safe_load(f)

product   = product_def["product"]
owner     = product["owner"]
slas      = product.get("slaProperties", [])
terms     = product.get("terms", {})
use_cases = product.get("useCases", [])
quality   = product.get("dataQuality", [])

# Output port — where the data lives
output_port = product["outputPorts"][0]
table_def   = output_port["tables"][0]
columns     = table_def["columns"]

# Build product-level context summary
sla_summary = "; ".join(
    f"{s['dimension']}: {s['value']} ({s['description']})" for s in slas
)
use_case_summary = "; ".join(use_cases)
quality_summary = "; ".join(
    f"{q['dimension']}: {', '.join(q['checks'][:2])}" for q in quality
)

product_context = (
    f"Data product: '{product['name']}' v{product['version']} "
    f"[domain: {product['domain']}, status: {product['status']}]. "
    f"Owner: {owner['name']} <{owner['email']}>. "
    f"Use cases: {use_case_summary}. "
    f"SLAs: {sla_summary}. "
    f"Quality: {quality_summary}. "
    f"Usage: {terms.get('usage', '').strip()}"
)

column_descriptions = "\n".join(
    f"  - {col['name']} ({col['type']}): {col['description'].strip()}" for col in columns
)
table_description = table_def["description"].strip()

logger.msg(
    "agent.start", question=QUESTION, product=PRODUCT_FILE,
    odps_version=product_def["openDataProductSpecification"],
    product_status=product["status"], product_domain=product["domain"],
    product_owner=owner["email"], model=MODEL,
    timestamp=datetime.utcnow().isoformat() + "Z",
)

client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")

tools = [
    {
        "type": "function",
        "function": {
            "name": "query_customer_analytics",
            "description": (
                f"Query the customer_metrics table from the '{product['name']}' data product. "
                f"{table_description} "
                f"Product context: {product_context} "
                f"Columns:\n{column_descriptions}"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": (
                            "A SQL SELECT query against the customer_metrics table. "
                            "For high-value at-risk customers use: "
                            "WHERE customer_ltv > 5000 AND churn_risk_score > 50. "
                            "Always ORDER BY for readability."
                        ),
                    }
                },
                "required": ["sql"],
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

# --- Tool execution: query DuckDB ---
tool_call = msg.tool_calls[0]
args = json.loads(tool_call.function.arguments)
sql = args.get("sql") or next(iter(args.values()))
logger.msg("tool.call", sql=sql, timestamp=datetime.utcnow().isoformat() + "Z")

db = duckdb.connect(DB_FILE, read_only=True)
cursor = db.execute(sql)
cols = [d[0] for d in cursor.description]
rows = cursor.fetchall()
db.close()

data = [dict(zip(cols, row)) for row in rows]
logger.msg("tool.result", rows=len(data), data=data, timestamp=datetime.utcnow().isoformat() + "Z")

# --- Turn 2: agent synthesises the answer ---
final = client.chat.completions.create(
    model=MODEL,
    tools=tools,
    messages=[
        {"role": "user", "content": QUESTION},
        msg,
        {"role": "tool", "tool_call_id": tool_call.id, "content": json.dumps(data, default=str)},
        {"role": "user", "content": "Using the tool result above, answer the question in plain English. Do not call any tools."},
    ],
)
answer = final.choices[0].message.content

# Guard: model made another tool call instead of answering
if not answer and final.choices[0].message.tool_calls:
    answer = "(Model issued a second tool call instead of answering. Raw tool args: " \
             + json.dumps([json.loads(tc.function.arguments) for tc in final.choices[0].message.tool_calls]) + ")"

# Guard: model returned nothing
if not answer:
    answer = "(No answer generated — check model tool_calls loop or increase context)"

logger.msg("agent.answer", timestamp=datetime.utcnow().isoformat() + "Z")

print("\n" + "=" * 60)
print(answer)
print("=" * 60)
