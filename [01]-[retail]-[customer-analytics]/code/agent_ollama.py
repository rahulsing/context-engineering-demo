#!/usr/bin/env python3
"""
Context Engineering Agent — Retail Customer Analytics
Uses local Ollama for on-premises LLM inference.

Prerequisites:
- Ollama installed and running (ollama serve)
- Model pulled: ollama pull qwen2.5
- Run bootstrap.py first

Usage:
    python agent_ollama.py
    python agent_ollama.py > trace.jsonl

Change model at top of file if needed:
    MODEL = "qwen2.5"      (recommended, tested)
    MODEL = "llama2"       (alternative)
    MODEL = "mistral"      (lightweight)
"""

import json
import os
from datetime import datetime
import duckdb
import yaml
import structlog
from openai import OpenAI

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)

logger = structlog.get_logger()

# Model configuration
MODEL = "qwen2.5"

def load_contract(contract_path: str) -> dict:
    """Load data contract from YAML file."""
    with open(contract_path, "r") as f:
        return yaml.safe_load(f)

def build_tool_description(contract: dict) -> str:
    """Build LLM tool description from data contract."""
    info = contract.get("info", {})
    models = contract.get("models", [])

    description = f"""
You have access to a customer analytics database.

DATABASE: {info.get('title', 'Customer Metrics')}
VERSION: {info.get('version', '1.0')}
OWNER: {info.get('owner', 'analytics@retailcompany.com')}
STATUS: {info.get('status', 'active')}

DESCRIPTION:
{info.get('description', '')}

SERVICE LEVELS:
- Freshness: Updated daily at 02:00 UTC
- Availability: 99.5% uptime
- Retention: 2 years of historical data

USAGE TERMS:
- Internal marketing and analytics use only
- GDPR/CCPA regulations apply
- Churn scores are predictive estimates

AVAILABLE DATA:
"""

    for model in models:
        description += f"\nTable: {model['name']}\n"
        description += f"  {model.get('description', '')}\n"
        description += "  Columns:\n"
        for col in model.get("columns", []):
            description += f"    - {col['name']}: {col.get('description', '')} (type: {col['type']})\n"

    return description

def query_customer_metrics(sql: str) -> dict:
    """Execute SQL query against customer_metrics table."""
    try:
        conn = duckdb.connect("customer_analytics.duckdb")
        result = conn.execute(sql).fetch_arrow_table()
        conn.close()

        data = result.to_pylist()
        return {
            "success": True,
            "rows": len(data),
            "data": data
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def run_agent():
    """Main agent loop (Turn 1: Plan, Turn 2: Answer)."""

    # Load contract
    contract = load_contract("contracts/customer_metrics.yaml")
    tool_description = build_tool_description(contract)

    # Initialize Ollama client
    client = OpenAI(
        base_url="http://localhost:11434/v1",
        api_key="ollama"
    )

    # User question
    QUESTION = (
        "What is our current customer LTV and churn risk this month? "
        "Who are our at-risk customers? "
        "How many high-value customers do we have? "
        "Should we trigger retention offers for anyone?"
    )

    logger.msg(
        "agent.start",
        question=QUESTION,
        contract="customer_metrics",
        model=MODEL,
        timestamp=datetime.utcnow().isoformat() + "Z"
    )

    # System prompt
    system_prompt = f"""You are a retail analytics agent. You answer questions about customer health, retention risk, and business metrics.

{tool_description}

You have access to a SQL query tool. When a user asks a question:
1. Write SQL to fetch the relevant data
2. Call the query_customer_metrics tool
3. Analyze the results
4. Provide a business-focused answer

Always be specific about numbers, segments, and actionable recommendations."""

    # Turn 1: Planning (LLM decides what to query)
    messages = [
        {
            "role": "user",
            "content": QUESTION
        }
    ]

    # Define tools
    tools = [
        {
            "type": "function",
            "function": {
                "name": "query_customer_metrics",
                "description": "Execute SQL queries against the customer_metrics table",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "sql": {
                            "type": "string",
                            "description": "SQL query to execute (SELECT only)"
                        }
                    },
                    "required": ["sql"]
                }
            }
        }
    ]

    # Call Ollama for Turn 1
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

    # Process tool calls from Turn 1
    tool_results = []
    if response.choices[0].message.tool_calls:
        for tool_call in response.choices[0].message.tool_calls:
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments)
            sql = tool_args.get("sql", "")

            logger.msg(
                "tool.call",
                tool=tool_name,
                sql=sql,
                timestamp=datetime.utcnow().isoformat() + "Z"
            )

            # Execute query
            result = query_customer_metrics(sql)

            logger.msg(
                "tool.result",
                rows=result.get("rows", 0),
                data=result.get("data", []),
                timestamp=datetime.utcnow().isoformat() + "Z"
            )

            tool_results.append({
                "type": "tool_result",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result)
            })

        # Turn 2: Synthesis (LLM generates answer from results)
        messages.append({"role": "assistant", "content": response.choices[0].message.content})

        if response.choices[0].message.tool_calls:
            messages.append({
                "role": "assistant",
                "tool_calls": response.choices[0].message.tool_calls
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
            timestamp=datetime.utcnow().isoformat() + "Z"
        )

    # Extract final answer
    final_answer = response.choices[0].message.content

    logger.msg(
        "agent.answer",
        latency_ms=turn2_latency,
        lineage_source=["bootstrap.py", "contracts/customer_metrics.yaml"],
        timestamp=datetime.utcnow().isoformat() + "Z"
    )

    # Print answer
    print()
    print("=" * 60)
    print(final_answer)
    print("=" * 60)

if __name__ == "__main__":
    run_agent()
