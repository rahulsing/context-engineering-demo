# Advanced Layers — Knowledge Graph, Semantic Layer, ODPS, MCP

> **Status update (2026-07-14):** all four layers described in this document
> have since been implemented as Building Blocks 6-9 in `README.md`. This
> document is kept as the original design rationale for *why* each layer
> was added and what it demonstrates — for the actual files and how to run
> them, see `README.md`'s Building Block 6-9 sections.

## What This Covers

1. **Knowledge Graph** — Entity relationships
2. **Semantic Layer (SLayer)** — REST API layer
3. **ODPS** — Open Data Product Standard
4. **MCP** — Model Context Protocol

These are **Layers 6-9** of Context Engineering. This document explains what each is and how it extends the demo.

---

## Current Demo Coverage

The retail demo includes:

✅ **Layers 1-9** (Complete):
- Layer 1: LLM (Claude + Ollama)
- Layer 2: Agent (Two-turn loop)
- Layer 3: Data Contract (ODCS YAML)
- Layer 4: Ontology (OWL/SKOS TTL)
- Layer 5: Metrics (MetricFlow YAML)
- Layer 6: Knowledge Graph (Neo4j) — `contracts/retention_policy.md`, `graph/ingest_to_graph.py`, `graph/agent_graph_ollama.py`
- Layer 7: Semantic Layer (SLayer REST) — `setup_slayer.py`, `agent_slayer_ollama.py`
- Layer 8: ODPS — `products/customer_analytics_odps.yaml`, `agent_odps_ollama.py`
- Layer 9: MCP — `setup_mcp.py`, `config/claude_desktop_retail.json`

---

## Layer 5.5: Knowledge Graph

### What It Is

A graph database representing **entities and relationships** between them.

**Example for retail:**
```
Customer_123
  ├─ belongs_to → Segment (HighValue)
  ├─ has_churn_risk → 75/100
  ├─ last_purchase → Order_789
  └─ made_purchases → [Order_1, Order_2, ..., Order_789]

Segment (HighValue)
  ├─ has_members → [Customer_1, Customer_123, ...]
  └─ triggers_action → RetentionAction (VIPRetention)

RetentionAction (VIPRetention)
  ├─ applies_to → Segment (HighValue)
  ├─ threshold → "churn_risk > 50"
  └─ sends_offer → "dedicated_account_manager"
```

### Implementation (Not in Current Demo)

Would require:
- **Database**: Neo4j, AWS Neptune, or in-memory graph
- **Format**: Property Graph or RDF triples
- **Agent enhancement**: Graph query capability (Cypher or SPARQL)

### Example Query

```cypher
MATCH (c:Customer)-[:has_churn_risk]->(score)
  WHERE score > 85
MATCH (c)-[:belongs_to]->(seg:Segment)
MATCH (seg)-[:triggers_action]->(action:RetentionAction)
RETURN c.id, c.ltv, action.name, action.timeline
```

### How It Improves Context

Agent can traverse relationships:
- "Show me all high-value customers and their retention actions"
- "Which segments have the highest at-risk rate?"
- "Map customer → order → product → category"

### Status in Demo
- ✅ **Implemented.** The three trigger rules already modeled in
  `ontology/customer_segments.ttl` are now also encoded as prose in
  `contracts/retention_policy.md`, parsed at runtime (never hardcoded),
  and applied by `graph/ingest_to_graph.py` when it writes
  `Customer`/`Segment`/`RetentionAction` nodes into Neo4j.
- Query it with `graph/agent_graph_ollama.py` (tool: `trace_customer`).

---

## Layer 6: Semantic Layer (REST API)

### What It Is

A REST API that abstracts SQL away. Agent queries business concepts, SLayer compiles SQL.

**Example requests:**
```bash
# Agent asks for business concept
GET /models/customer_metrics/explore

# Agent queries by dimensions/metrics
POST /query
{
  "metrics": ["customer_ltv", "churn_risk_score"],
  "dimensions": ["segment", "region"],
  "filters": [{"segment": "high_value"}]
}

# SLayer returns compiled query + results
{
  "sql_compiled": "SELECT segment, region, AVG(customer_ltv), AVG(churn_risk_score) FROM ... GROUP BY ...",
  "results": [...]
}
```

### Implementation (Not in Current Demo)

Would require:
- **Framework**: SLayer (open-source), dbt Semantic Layer, Cube, etc.
- **Server**: Python FastAPI or similar
- **Agent enhancement**: HTTP client for REST queries

### Example Server Code

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/models/customer_metrics/explore")
def explore():
    return {
        "metrics": ["customer_ltv", "churn_risk_score", "repeat_purchase_rate"],
        "dimensions": ["segment", "region", "customer_id"]
    }

@app.post("/query")
def query(request):
    # Build SQL from business request
    sql = compile_to_sql(request)
    # Execute
    results = duckdb.query(sql)
    return {
        "sql_compiled": sql,
        "results": results
    }
```

### How It Improves Context

- Agent never writes raw SQL
- Queries by business metric names
- SLayer enforces consistency
- Observable compiled SQL for audit

### Comparison: Direct SQL vs. SLayer

**Without SLayer (Current Demo):**
```python
# Agent generates SQL
SELECT customer_ltv, churn_risk_score FROM customer_metrics
WHERE customer_ltv > 5000

# Risk: Agent might write incorrect SQL
```

**With SLayer:**
```python
# Agent requests concept
POST /query {metrics: ["customer_ltv"], filters: {segment: "high_value"}}

# SLayer generates SQL (guaranteed correct)
SELECT AVG(customer_ltv) FROM customer_metrics WHERE segment = 'high_value'
```

### Status in Demo
- ✅ **Implemented**, using the actual SLayer project (not a hand-rolled
  FastAPI server): `setup_slayer.py` registers the `customer_analytics`
  datasource and `agent_slayer_ollama.py` queries it via `POST /query`,
  logging the compiled SQL.
- Reference: See main project Examples 2-7 for SLayer usage

---

## Layer 7: ODPS (Open Data Product Standard)

### What It Is

A **formal standard** for describing data products (not just tables).

**Difference from ODCS:**
- **ODCS** (current demo): Describes a **table** with schema, quality, SLA
- **ODPS**: Describes a **product** with ports, use cases, pricing, governance

### ODPS Structure

```yaml
dataProductSpecification: "2.0"
info:
  name: "Customer Analytics Product"
  owner: "analytics@retailcompany.com"
  
inputPorts:
  - name: "raw_events"
    source: "events_database"
    cadence: "real-time"
    
outputPorts:
  - name: "customer_metrics"
    table: "customer_metrics"
    columns: [customer_ltv, churn_risk_score, ...]
    api: "REST"
    
useCases:
  - name: "retention_targeting"
    description: "Identify at-risk customers for retention offers"
    stakeholders: ["Marketing", "Retention Team"]
    kpis: ["customers_retained", "offer_redemption_rate"]
    
  - name: "customer_segmentation"
    description: "Segment customers by LTV and churn risk"
    stakeholders: ["Analytics", "Product"]
    
sla:
  availability: "99.5%"
  freshness: "daily at 02:00 UTC"
  support: "1 business day response"
  
terms:
  pricing: "per API call"
  usage: "internal marketing and analytics only"
```

### Implementation (Not in Current Demo)

Would require:
- Expanding `contracts/customer_metrics_odps.yaml`
- Adding "ports", "use cases", "product metadata"

### How It Improves Context

Agent understands:
- What problem the product solves
- Who the intended users are
- What SLAs are guaranteed
- What use cases are supported

**Example agent reasoning:**
```
Question: "Can I use this for direct customer targeting?"
ODPS says: use_case = "retention_targeting" (specific targeting OK)
Agent: "Yes, this product supports retention targeting. SLA: daily refresh, 1-day support."
```

### Status in Demo
- ✅ **Implemented**: `products/customer_analytics_odps.yaml` upgrades
  the ODCS contract to ODPS 2.0, adding `inputPorts`, `outputPorts`,
  `useCases`, `slaProperties`, `dataQuality`, and `pricing` — reusing the
  same 11 `customer_metrics` columns, not a new dataset.
- Queried by `agent_odps_ollama.py`, which answers both data and
  product-governance questions (owner, freshness, approved use cases).

---

## Layer 8: MCP (Model Context Protocol)

### What It Is

An **open standard** for agents to discover and query tools, data models, and resources.

**MCP = the transport layer** (not the context itself).

### How MCP Works

Instead of agent calling Python functions directly:

**Without MCP (Current Demo):**
```python
# Agent calls Python function
result = query_customer_metrics(sql="SELECT ...")
```

**With MCP (Better):**
```
Agent asks MCP server: "What tools do you have?"
MCP server responds: "Tools available: query_customer_metrics, get_metrics_catalog, ..."

Agent: "I want to query_customer_metrics"
MCP server: "Here's the tool schema: {input_schema: ...}"

Agent: "Call query_customer_metrics with SQL = ..."
MCP server: Executes and returns result
```

### MCP Benefits

1. **Tool Discovery**: Agent learns what's available at runtime
2. **Transport Independence**: Same tools work over stdio, HTTP, WebSocket
3. **Claude Desktop Support**: Claude Desktop app auto-discovers MCP servers
4. **Versioning**: MCP server can evolve independently

### Example MCP Server (Claude Desktop Integration)

```json
{
  "mcpServers": {
    "retail_analytics": {
      "command": "python",
      "args": ["/path/to/mcp_server.py"],
      "env": {
        "DATABASE_URL": "duckdb://customer_analytics.duckdb"
      }
    }
  }
}
```

### Implementation (Not in Current Demo)

Would require:
- `server/mcp_server.py` — MCP server implementation
- Updates to both agents to use MCP instead of direct function calls
- Configuration for Claude Desktop to discover the server

### Example MCP Server Code

```python
from mcp.server import Server
from mcp.types import Tool, TextContent

server = Server("retail_analytics")

@server.tool()
def query_customer_metrics(sql: str) -> str:
    """Execute SQL against customer analytics database."""
    result = duckdb.query(sql)
    return json.dumps(result.to_pylist())

@server.tool()
def get_metrics_catalog() -> str:
    """List all available metrics."""
    # Load from metrics/metrics.yaml
    metrics = load_metrics()
    return json.dumps([m['name'] for m in metrics])

server.run()
```

### Why MCP Matters for YouTube Content

**Example from transcript — using MCP:**

**Without MCP (Agent calls Python functions):**
```
Agent: "I need customer_ltv"
Function call: query_customer_metrics("SELECT customer_ltv...")
```

**With MCP (Agent uses Claude Desktop + MCP server):**
```
Claude Desktop user: "What's our customer LTV?"
Claude Desktop: Auto-discovers MCP server
Claude Desktop: Sees tools: query_customer_metrics, get_metrics_catalog
Claude Desktop: Calls query_customer_metrics
Result: Same answer, but NO Python code, NO CLI
```

### Status in Demo
- ✅ **Implemented**, using SLayer's own MCP server (`slayer mcp`) rather
  than a hand-rolled one: `setup_mcp.py` registers the datasource into
  SLayer's shared storage, and `config/claude_desktop_retail.json` points
  Claude Desktop at it.
- No agent script for this layer — Claude Desktop is the agent.

---

## Progression: Full Stack Comparison

| Layer | What | Implementation | File(s) |
|-------|------|---|---|
| **1** | LLM | Claude, Ollama | `agent.py`, `agent_ollama.py` |
| **2** | Agent | Two-turn loop | `agent.py`, `agent_ollama.py` |
| **3** | Data Contract | ODCS YAML | ✅ `contracts/customer_metrics.yaml` |
| **4** | Ontology | OWL/SKOS | ✅ `ontology/customer_segments.ttl` |
| **5** | Metrics | MetricFlow YAML | ✅ `metrics/metrics.yaml` |
| **6** | Knowledge Graph | Neo4j, policy-driven | ✅ `graph/ingest_to_graph.py`, `graph/agent_graph_ollama.py` |
| **7** | Semantic Layer | SLayer REST API | ✅ `setup_slayer.py`, `agent_slayer_ollama.py` |
| **8** | ODPS | Product definition | ✅ `products/customer_analytics_odps.yaml`, `agent_odps_ollama.py` |
| **9** | MCP | Tool discovery | ✅ `setup_mcp.py`, `config/claude_desktop_retail.json` |

---

## How These Were Added

### Knowledge Graph
```bash
docker run -d --name neo4j-retail -p 7475:7474 -p 7688:7687 -e NEO4J_AUTH=neo4j/password neo4j:5
python graph/ingest_to_graph.py     # reads customer_metrics + contracts/retention_policy.md
python graph/agent_graph_ollama.py  # tool: trace_customer
```
The three retention rules are parsed out of `contracts/retention_policy.md`'s
prose table at runtime and applied as SQL conditions against DuckDB — there
is no hardcoded threshold anywhere in `graph/ingest_to_graph.py`.

### Semantic Layer (SLayer)
```bash
uvx --from 'motley-slayer[all]' slayer serve --demo   # separate terminal
python setup_slayer.py       # registers customer_analytics datasource
python agent_slayer_ollama.py
```

### ODPS
`products/customer_analytics_odps.yaml` upgrades the existing ODCS
contract to product-level governance (same 11 columns, plus `useCases`,
`inputPorts`, `outputPorts`, `slaProperties`, `dataQuality`, `pricing`).
Queried by `agent_odps_ollama.py`.

### MCP
```bash
uvx --from 'motley-slayer[all]' slayer serve   # registration only
python setup_mcp.py
# Add config/claude_desktop_retail.json to Claude Desktop, restart
```
No Python agent for this layer — Claude Desktop auto-discovers the tools.

---

## Why These Matter for Your YouTube Video

### Current Demo (5 Building Blocks)
- Covers the YouTube transcript completely ✅
- Shows progression from 1/5 → 5/5 scores ✅
- Demonstrates all core concepts ✅

### With Knowledge Graph
- Shows how to model complex relationships
- Enables graph queries (traverse customer → order → product)

### With Semantic Layer
- Shows transport independence (REST API instead of Python)
- Demonstrates how multiple clients can use same semantic model

### With ODPS
- Shows scaling from table governance → product governance
- Demonstrates who can use the product and for what purpose

### With MCP
- Shows zero-code integration with Claude Desktop
- Demonstrates serverless/CLI-free operation
- Makes it accessible to non-technical users

---

## Recommendation for YouTube Video

**For the initial video (transcript you created):**
- ✅ Use Layers 1-5 (current demo) — complete and working, matches the
  existing `YOUTUBE_TRANSCRIPT.md` script.

**For Part 2 videos:**
- ✅ Knowledge Graph — now implemented, adds relationship modeling
- ✅ ODPS — now implemented, shows scaling to products
- ✅ MCP — now implemented, shows Claude Desktop integration

---

## Summary

| Feature | Included | Why |
|---------|----------|-----|
| **5 Building Blocks** | ✅ Yes | Core to YouTube video |
| **Knowledge Graph** | ✅ Yes | Policy-driven Neo4j ingestion, see Building Block 6 |
| **Semantic Layer** | ✅ Yes | SLayer REST, see Building Block 7 |
| **ODPS** | ✅ Yes | Product-level governance, see Building Block 8 |
| **MCP** | ✅ Yes | Claude Desktop integration, see Building Block 9 |

---

## Next Steps

1. **Run current demo** (Layers 1-5) — it's complete ✅
2. **Record YouTube video** — use the transcript with this demo ✅
3. **Part 2 layers** — Knowledge Graph, SLayer, ODPS, and MCP are all
   implemented; see `README.md`'s Building Block 6-9 sections for how to
   run each one.

The demo now covers **all 9 Context Engineering building blocks**.
