#!/usr/bin/env python3
"""
Context Engineering Agent — With Ontology (Layer 2)
Loads OWL/SKOS ontology to provide domain-aware reasoning.

This agent understands customer segments, churn thresholds, and retention rules
without querying the database — it answers from domain knowledge.

Usage:
    python agent_with_ontology.py
"""

import os
import sys
from datetime import datetime
import duckdb
import yaml
import structlog
from rdflib import Graph, RDFS, SKOS, Namespace
from openai import OpenAI

structlog.configure(
    processors=[structlog.processors.JSONRenderer()],
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)
logger = structlog.get_logger()

MODEL = "qwen2.5"

def load_ontology():
    """Load customer segments ontology from TTL file."""
    g = Graph()
    try:
        g.parse("ontology/customer_segments.ttl", format="turtle")
        print(f"✓ Loaded ontology: {len(g)} triples")
        return g
    except Exception as e:
        print(f"ERROR loading ontology: {e}")
        return None

def build_ontology_context(ontology_graph):
    """Extract key concepts from ontology for LLM."""
    context = """
# DOMAIN ONTOLOGY — Customer Segments & Churn Rules

## Customer Segments (Hierarchy)
- Customer (base class)
  ├─ ActiveCustomer (purchase in last 90 days)
  │  ├─ HighValueCustomer (LTV > $5000) → VIP treatment
  │  └─ StandardCustomer (LTV $1000-$5000) → Regular engagement
  ├─ AtRiskCustomer (churn_risk_score > 70) → Retention priority
  └─ DormantCustomer (no purchase 365+ days) → Win-back campaign

## Churn Risk Thresholds (Critical Business Rules)
- CRITICAL (> 85): Send retention offer within 24 hours + assign specialist
- HIGH (70-85): Monitor closely, prepare personalized offer
- MEDIUM (50-70): Watch for warning signs
- LOW (< 50): Stable, no action needed

## LTV Tiers
- High-Value (> $5000): Dedicated support, exclusive offers, early access
- Standard ($1000-$5000): Personalized offers, email campaigns
- Low-Value (< $1000): Promotional campaigns, acquisition focus

## Key Business Rules
1. IF ltv > 5000 AND churn_risk_score > 70 THEN priority = VIP_RETENTION
2. IF churn_risk_score > 85 THEN action = retention_offer_24h
3. IF days_since_purchase > 365 AND churn_risk_score > 90 THEN action = win_back_campaign

## Retention Actions
- RetentionOffer24h: Send personalized offer within 24 hours (trigger: churn > 85)
- WinBackCampaign: Re-engagement for dormant customers (365+ days)
- VIPRetention: Premium program for high-value customers (LTV > 5000)
"""
    return context

def load_contract(contract_path):
    """Load data contract."""
    with open(contract_path, "r") as f:
        return yaml.safe_load(f)

def build_tool_description(contract):
    """Build tool description from contract."""
    info = contract.get("info", {})
    models = contract.get("models", [])

    description = f"""
DATABASE: {info.get('title', 'Customer Metrics')}

DESCRIPTION:
{info.get('description', '')}

AVAILABLE TABLE:
"""
    for model in models:
        description += f"\nTable: {model['name']}\n"
        description += "  Columns:\n"
        for col in model.get("columns", []):
            description += f"    - {col['name']}: {col.get('description', '')} (type: {col['type']})\n"

    return description

def query_customer_metrics(sql):
    """Execute SQL query."""
    try:
        conn = duckdb.connect("customer_analytics.duckdb")
        result = conn.execute(sql).fetch_arrow_table()
        conn.close()
        return {
            "success": True,
            "rows": len(result),
            "data": result.to_pylist()
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def run_agent_with_ontology():
    """Agent loop with ontology context."""

    # Load ontology (domain knowledge)
    ontology = load_ontology()
    if not ontology:
        print("ERROR: Could not load ontology")
        sys.exit(1)

    ontology_context = build_ontology_context(ontology)

    # Load contract
    contract = load_contract("contracts/customer_metrics.yaml")
    tool_description = build_tool_description(contract)

    # Initialize client
    client = OpenAI(
        base_url="http://localhost:11434/v1",
        api_key="ollama"
    )

    # Question with ontology
    QUESTION = (
        "Based on our customer segments and churn rules, "
        "what actions should we take? "
        "Which customers are critical? "
        "What does being at-risk mean in our business? "
        "Show me the breakdown by churn threshold."
    )

    logger.msg(
        "agent.start",
        question=QUESTION,
        with_ontology=True,
        model=MODEL,
        timestamp=datetime.utcnow().isoformat() + "Z"
    )

    # Enhanced system prompt
    system_prompt = f"""You are a retail analytics expert with deep domain knowledge.

{ontology_context}

{tool_description}

You have SQL query tools available, but you also understand the business logic.

When answering questions:
1. First explain what the domain concepts mean
2. Then query data if needed to show examples
3. Provide actionable recommendations based on domain rules

Be specific about churn thresholds, retention actions, and customer segments."""

    messages = [{
        "role": "user",
        "content": QUESTION
    }]

    tools = [
        {
            "type": "function",
            "function": {
                "name": "query_customer_metrics",
                "description": "Execute SQL to fetch customer data",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "sql": {
                            "type": "string",
                            "description": "SQL SELECT query"
                        }
                    },
                    "required": ["sql"]
                }
            }
        }
    ]

    # Turn 1: Planning
    import time
    start_time = time.time()

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=tools,
        tool_choice="auto",
        temperature=0.7,
    )

    turn1_latency = int((time.time() - start_time) * 1000)

    logger.msg(
        "agent.turn1",
        stop_reason=response.choices[0].finish_reason,
        latency_ms=turn1_latency,
        timestamp=datetime.utcnow().isoformat() + "Z"
    )

    # Process tool calls
    if response.choices[0].message.tool_calls:
        for tool_call in response.choices[0].message.tool_calls:
            import json
            tool_args = json.loads(tool_call.function.arguments)
            sql = tool_args.get("sql", "")

            logger.msg(
                "tool.call",
                tool=tool_call.function.name,
                sql=sql,
                timestamp=datetime.utcnow().isoformat() + "Z"
            )

            result = query_customer_metrics(sql)

            logger.msg(
                "tool.result",
                rows=result.get("rows", 0),
                data=result.get("data", []),
                timestamp=datetime.utcnow().isoformat() + "Z"
            )

        # Turn 2: Synthesis
        messages.append({"role": "assistant", "content": response.choices[0].message.content})

        if response.choices[0].message.tool_calls:
            messages.append({
                "role": "assistant",
                "tool_calls": response.choices[0].message.tool_calls
            })

        import json
        tool_results = []
        for tool_call in response.choices[0].message.tool_calls:
            tool_args = json.loads(tool_call.function.arguments)
            sql = tool_args.get("sql", "")
            result = query_customer_metrics(sql)
            tool_results.append({
                "type": "tool_result",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result)
            })

        messages.append({
            "role": "user",
            "content": tool_results
        })

        start_time = time.time()

        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.7,
        )

        turn2_latency = int((time.time() - start_time) * 1000)

        logger.msg(
            "agent.turn2",
            stop_reason=response.choices[0].finish_reason,
            latency_ms=turn2_latency,
            with_ontology=True,
            timestamp=datetime.utcnow().isoformat() + "Z"
        )

    final_answer = response.choices[0].message.content

    logger.msg(
        "agent.answer",
        latency_ms=turn2_latency,
        context_layers=["data_contract", "ontology"],
        timestamp=datetime.utcnow().isoformat() + "Z"
    )

    print()
    print("=" * 70)
    print("AGENT WITH ONTOLOGY — Domain-Aware Reasoning")
    print("=" * 70)
    print(final_answer)
    print("=" * 70)

if __name__ == "__main__":
    run_agent_with_ontology()
