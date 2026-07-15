"""
CE Knowledge Graph Demo — Retail Customer Analytics (Neo4j / Ollama qwen2.5)

Building Block 6: Knowledge Graph. graph/ingest_to_graph.py builds a real
graph from customer_metrics rows plus a prose retention policy — this
agent calls one tool, trace_customer, which runs a Cypher traversal
instead of an ad-hoc join written per question.

An empty `actions` list in the tool result means no retention rule
currently applies to that customer — it does not mean the data is
missing.

Requires:
  - Neo4j running:  docker run -d --name neo4j-retail -p 7475:7474 -p 7688:7687 -e NEO4J_AUTH=neo4j/password neo4j:5
  - Ingest done:    python graph/ingest_to_graph.py
  - Ollama running: ollama serve && ollama pull qwen2.5

Usage:
    python graph/agent_graph_ollama.py
    python graph/agent_graph_ollama.py "Which retention action applies to CUST_00009?"
"""

import sys
import json
from datetime import datetime
import structlog
from openai import OpenAI
from neo4j import GraphDatabase

structlog.configure(
    processors=[structlog.processors.JSONRenderer()],
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)
logger = structlog.get_logger()

MODEL      = "qwen2.5"
NEO4J_URI  = "bolt://localhost:7688"
NEO4J_AUTH = ("neo4j", "password")

DEFAULT_QUESTION = "Which retention action, if any, applies to CUST_00009, and why?"

TRACE_CYPHER = """
MATCH (c:Customer {customer_id: $customer_id})-[:BELONGS_TO]->(seg:Segment)
OPTIONAL MATCH (c)-[:TRIGGERS]->(a:RetentionAction)
RETURN c.customer_id AS customer_id, c.region AS region,
       c.customer_ltv AS customer_ltv, c.churn_risk_score AS churn_risk_score,
       c.days_since_last_purchase AS days_since_last_purchase,
       seg.name AS segment,
       collect(CASE WHEN a IS NOT NULL THEN
         {rule: a.name, action: a.action, timeline: a.timeline, channel: a.channel}
       END) AS actions
"""


def build_tool() -> dict:
    return {
        "type": "function",
        "function": {
            "name": "trace_customer",
            "description": (
                "Traverse the retail retention knowledge graph for one customer: "
                "walks Customer -> Segment and Customer -> RetentionAction, where "
                "RetentionAction edges only exist if a policy rule from "
                "contracts/retention_policy.md actually matched this customer. "
                "An empty actions list means no retention rule currently applies "
                "to this customer, not that data is missing."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {
                        "type": "string",
                        "description": "The customer ID to trace, e.g. 'CUST_00009'.",
                    }
                },
                "required": ["customer_id"],
            },
        },
    }


def trace_customer(customer_id: str, driver: GraphDatabase.driver) -> str:
    logger.msg("tool.call", tool="trace_customer", customer_id=customer_id,
               timestamp=datetime.utcnow().isoformat() + "Z")

    with driver.session() as session:
        rows = session.run(TRACE_CYPHER, customer_id=customer_id).data()

    if not rows:
        result = json.dumps({"error": f"No customer found with id {customer_id}"})
    else:
        row = rows[0]
        row["actions"] = [a for a in row["actions"] if a is not None]
        result = json.dumps(row, default=str)

    logger.msg("tool.result", result=result[:300], timestamp=datetime.utcnow().isoformat() + "Z")
    return result


def ask(question: str, tool: dict, client: OpenAI, driver: GraphDatabase.driver) -> None:
    logger.msg("agent.start", question=question, model=MODEL, timestamp=datetime.utcnow().isoformat() + "Z")

    messages = [
        {
            "role": "system",
            "content": (
                "You are a retail retention assistant. Use the trace_customer tool "
                "to look up what the knowledge graph actually knows about a customer "
                "before answering. Do not assume a retention action applies unless "
                "the tool result's actions list is non-empty."
            ),
        },
        {"role": "user", "content": question},
    ]

    response = client.chat.completions.create(
        model=MODEL, messages=messages, tools=[tool], tool_choice="auto",
    )
    msg = response.choices[0].message
    logger.msg("agent.turn1", stop_reason=response.choices[0].finish_reason,
               timestamp=datetime.utcnow().isoformat() + "Z")

    if not msg.tool_calls:
        print("\n" + "=" * 60)
        print(msg.content)
        print("=" * 60)
        return

    tool_call = msg.tool_calls[0]
    args = json.loads(tool_call.function.arguments)
    customer_id = args.get("customer_id", "")
    result = trace_customer(customer_id, driver)

    messages += [
        {"role": "assistant", "content": None, "tool_calls": [tool_call]},
        {"role": "tool", "content": result, "tool_call_id": tool_call.id},
        {
            "role": "user",
            "content": (
                "Using the graph trace above, answer the question in plain English. "
                "If the actions list is empty, say clearly that no retention action "
                "is currently triggered for this customer. Do not call any tools."
            ),
        },
    ]

    final = client.chat.completions.create(
        model=MODEL, messages=messages, tools=[tool], tool_choice="none",
    )
    answer = final.choices[0].message.content

    if not answer and final.choices[0].message.tool_calls:
        answer = "(Model issued a second tool call instead of answering — try a simpler question.)"
    if not answer:
        answer = "(No answer generated.)"

    logger.msg("agent.answer", timestamp=datetime.utcnow().isoformat() + "Z")

    print("\n" + "=" * 60)
    print(answer)
    print("=" * 60)
    print("\nGraph trace (Cypher result):")
    print(result)


def main() -> None:
    question = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else DEFAULT_QUESTION

    driver = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)
    try:
        driver.verify_connectivity()
    except Exception as e:
        print(f"ERROR: cannot reach Neo4j at {NEO4J_URI} — is the container running?")
        print(f"  {e}")
        sys.exit(1)

    tool = build_tool()
    client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")

    ask(question, tool, client, driver)
    driver.close()


if __name__ == "__main__":
    main()
