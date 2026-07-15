"""
Ingest — read customer_metrics from the existing customer_analytics.duckdb,
apply the retention trigger rules extracted from the policy markdown, and
write the connected graph into Neo4j.

bootstrap.py leaves customers as flat rows in one table. This script is the
actual "context building" step: it decides which retention actions each
customer triggers, based ONLY on what ../contracts/retention_policy.md
says. There is no hardcoded `if customer_ltv > 5000 and churn_risk_score >
50` anywhere in this file — each rule's condition is a SQL expression
parsed out of the policy document at runtime and evaluated by DuckDB
itself. Change the policy's wording, rerun this script, and the graph
changes without touching this file's logic.

Run order:
    python bootstrap.py               (from code/, once)
    python graph/ingest_to_graph.py
    python graph/agent_graph_ollama.py

Usage:
    python graph/ingest_to_graph.py
"""

import os
import re
import sys
import duckdb
from neo4j import GraphDatabase

DB_FILE     = "../customer_analytics.duckdb"
POLICY_FILE = "../contracts/retention_policy.md"
NEO4J_URI   = "bolt://localhost:7688"
NEO4J_AUTH  = ("neo4j", "password")

DECIMAL_COLUMNS = (
    "customer_ltv", "repeat_purchase_rate", "average_order_value",
    "purchase_frequency_12m", "return_rate",
)


# ── 1. Parse the policy markdown -- no hand-written rule in this file ──
def parse_policy(md_text: str) -> list:
    """
    Extract every retention trigger rule from the '## Retention trigger
    rules' table. Each row's Condition cell is a SQL boolean expression
    over customer_metrics columns -- it is applied later via DuckDB, never
    via a Python eval() and never via a hardcoded threshold in this file.
    """
    section_match = re.search(r"## Retention trigger rules\n(.*?)\n## ", md_text, re.DOTALL)
    if not section_match:
        raise ValueError(f"Could not find '## Retention trigger rules' section in {POLICY_FILE}.")
    section = section_match.group(1)

    row_pattern = re.compile(
        r"^\|\s*`([^`]+)`\s*\|\s*`([^`]+)`\s*\|\s*`([^`]+)`\s*\|\s*`([^`]+)`\s*\|\s*`([^`]+)`\s*\|\s*$",
        re.MULTILINE,
    )
    rules = [
        {
            "rule": m.group(1), "condition": m.group(2), "action": m.group(3),
            "timeline": m.group(4), "channel": m.group(5),
        }
        for m in row_pattern.finditer(section)
    ]
    if not rules:
        raise ValueError(f"No retention trigger rules could be parsed from {POLICY_FILE} — check the table formatting.")
    return rules


# ── 2. Read raw rows from DuckDB ─────────────────────────────────────
def load_customers(db_path: str) -> list:
    db = duckdb.connect(db_path, read_only=True)
    cursor = db.execute("SELECT * FROM customer_metrics")
    columns = [d[0] for d in cursor.description]
    rows = cursor.fetchall()
    db.close()

    customers = []
    for row in rows:
        record = dict(zip(columns, row))
        # DuckDB DECIMAL columns come back as decimal.Decimal, which the
        # Neo4j driver cannot serialize -- coerce to float/str up front.
        for col in DECIMAL_COLUMNS:
            record[col] = float(record[col])
        record["updated_date"] = str(record["updated_date"])
        customers.append(record)
    return customers


def match_rule(db_path: str, condition: str) -> list:
    """Evaluate one policy rule's SQL condition via DuckDB -- never Python eval()."""
    db = duckdb.connect(db_path, read_only=True)
    try:
        matches = [r[0] for r in db.execute(f"SELECT customer_id FROM customer_metrics WHERE {condition}").fetchall()]
    finally:
        db.close()
    return matches


# ── 3. Write nodes, segment edges, and policy-driven TRIGGERS edges ──
CLEAR_CYPHER = """
MATCH (n) WHERE n:Customer OR n:Segment OR n:RetentionAction
DETACH DELETE n
"""
SEED_CUSTOMER = """
MERGE (c:Customer {customer_id: $customer_id})
SET c.region = $region,
    c.customer_ltv = $customer_ltv,
    c.churn_risk_score = $churn_risk_score,
    c.repeat_purchase_rate = $repeat_purchase_rate,
    c.average_order_value = $average_order_value,
    c.purchase_frequency_12m = $purchase_frequency_12m,
    c.days_since_last_purchase = $days_since_last_purchase,
    c.return_rate = $return_rate,
    c.updated_date = $updated_date
"""
SEED_SEGMENT = "MERGE (seg:Segment {name: $segment})"
LINK_BELONGS_TO = """
MATCH (c:Customer {customer_id: $customer_id})
MATCH (seg:Segment {name: $segment})
MERGE (c)-[:BELONGS_TO]->(seg)
"""
SEED_RETENTION_ACTION = """
MERGE (a:RetentionAction {name: $rule})
SET a.condition = $condition, a.action = $action, a.timeline = $timeline, a.channel = $channel
"""
TRIGGER_ACTION = """
MATCH (c:Customer {customer_id: $customer_id})
MATCH (a:RetentionAction {name: $rule})
MERGE (c)-[:TRIGGERS]->(a)
"""
COUNT_NODES = """
MATCH (n) WHERE n:Customer OR n:Segment OR n:RetentionAction
RETURN labels(n) AS labels, count(*) AS n ORDER BY labels
"""


def ingest(customers: list, rules: list, db_path: str, driver: GraphDatabase.driver) -> tuple:
    rule_matches = {}

    with driver.session() as session:
        session.run(CLEAR_CYPHER)

        for customer in customers:
            session.run(SEED_CUSTOMER, **{k: v for k, v in customer.items() if k != "segment"})
            session.run(SEED_SEGMENT, segment=customer["segment"])
            session.run(LINK_BELONGS_TO, customer_id=customer["customer_id"], segment=customer["segment"])

        for rule in rules:
            session.run(
                SEED_RETENTION_ACTION, rule=rule["rule"], condition=rule["condition"],
                action=rule["action"], timeline=rule["timeline"], channel=rule["channel"],
            )
            # The only place a rule is evaluated -- parsed straight out of
            # the policy document, applied as SQL, not a hardcoded `if`.
            matches = match_rule(db_path, rule["condition"])
            rule_matches[rule["rule"]] = matches
            for customer_id in matches:
                session.run(TRIGGER_ACTION, customer_id=customer_id, rule=rule["rule"])

        node_counts = session.run(COUNT_NODES).data()

    return rule_matches, node_counts


def main() -> None:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.normpath(os.path.join(script_dir, DB_FILE))
    policy_path = os.path.normpath(os.path.join(script_dir, POLICY_FILE))

    if not os.path.exists(db_path):
        print(f"ERROR: {db_path} not found — run bootstrap.py first (from code/).")
        sys.exit(1)
    if not os.path.exists(policy_path):
        print(f"ERROR: policy not found at {policy_path}")
        sys.exit(1)

    with open(policy_path) as f:
        rules = parse_policy(f.read())

    print(f"Parsed policy: {POLICY_FILE}")
    for rule in rules:
        print(f"  {rule['rule']}: {rule['condition']} -> {rule['timeline']}")
    print()

    customers = load_customers(db_path)

    driver = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)
    try:
        driver.verify_connectivity()
    except Exception as e:
        print(f"ERROR: cannot reach Neo4j at {NEO4J_URI} — is the container running?")
        print(f"  {e}")
        sys.exit(1)

    rule_matches, node_counts = ingest(customers, rules, db_path, driver)
    driver.close()

    print("Retention rules applied:")
    for rule_name, matches in rule_matches.items():
        print(f"  {rule_name}: {len(matches)} customers -> {matches}")
    print()
    print("Graph nodes:")
    for row in node_counts:
        print(f"  {row['labels'][0]:<16} -> {row['n']}")
    print()
    print("View it: http://localhost:7475  (neo4j / password)")
    print("  MATCH (n) RETURN n")


if __name__ == "__main__":
    main()
