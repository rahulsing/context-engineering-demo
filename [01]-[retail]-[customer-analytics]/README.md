# Context Engineering — Retail Customer Analytics Demo

A complete, working demonstration of Context Engineering with **all 9 building blocks**. An AI agent reads structured context (data contract, ontology, metrics, knowledge graph, semantic layer, data product, MCP) and automatically generates correct SQL — or, once the semantic layer exists, no SQL at all — to answer business questions about customer lifetime value, churn risk, and retention strategy.

```
code/
├── bootstrap.py                             — Seed DuckDB (12 sample customers)
├── agent.py                                 — Anthropic Claude agent
├── agent_ollama.py                          — Local Ollama agent (qwen2.5)
├── agent_with_ontology.py                   — Domain-aware agent (with ontology)
├── agent_slayer_ollama.py                   — Semantic Layer agent (SLayer REST)
├── agent_odps_ollama.py                     — Data Product agent (ODPS)
├── setup_slayer.py                          — Register datasource into SLayer (REST)
├── setup_mcp.py                             — Register datasource into SLayer (MCP)
├── contracts/customer_metrics.yaml          — Data Contract (Layer 3)
├── contracts/retention_policy.md            — Retention policy prose (Layer 6)
├── ontology/customer_segments.ttl           — Ontology (Layer 4)
├── metrics/metrics.yaml                     — MetricFlow Metrics (Layer 5)
├── products/customer_analytics_odps.yaml    — ODPS Data Product (Layer 8)
└── graph/
    ├── ingest_to_graph.py                   — Policy-driven Neo4j ingestion (Layer 6)
    └── agent_graph_ollama.py                — Knowledge Graph agent (Layer 6)

config/
└── claude_desktop_retail.json               — MCP config for Claude Desktop (Layer 9)
```

---

## The 9 Building Blocks — All Included

| Layer | Building Block | What It Is | File(s) |
|---|---|---|---|
| **1** | **LLM** | Reasoning engine (Claude or Qwen2.5) | `agent.py`, `agent_ollama.py` |
| **2** | **Agent** | Decision-maker (2-turn loop: plan → execute → synthesize) | `agent.py`, `agent_ollama.py` |
| **3** | **Data Contract** | Schema + business meaning (ODCS YAML) | `contracts/customer_metrics.yaml` |
| **4** | **Ontology** | Domain knowledge + business rules (OWL/SKOS) | `ontology/customer_segments.ttl` |
| **5** | **MetricFlow** | Governed metrics catalog with formulas | `metrics/metrics.yaml` |
| **6** | **Knowledge Graph** | Policy-driven Neo4j graph (Customer → Segment → RetentionAction) | `contracts/retention_policy.md`, `graph/ingest_to_graph.py`, `graph/agent_graph_ollama.py` |
| **7** | **Semantic Layer** | SLayer REST — agent never writes SQL | `setup_slayer.py`, `agent_slayer_ollama.py` |
| **8** | **ODPS** | Product-level governance (ports, use cases, SLAs) | `products/customer_analytics_odps.yaml`, `agent_odps_ollama.py` |
| **9** | **MCP** | Claude Desktop auto-discovers tools, zero Python agent | `setup_mcp.py`, `config/claude_desktop_retail.json` |

---

## Quick Start

### Setup (One-Time)
```bash
# Install Ollama and pull model
ollama pull qwen2.5

# Install Python dependencies
cd code/
pip install duckdb structlog pyyaml openai rdflib neo4j requests

# Create database
python bootstrap.py
```

### Run Agents

**Option 1: Basic Agent**
```bash
python agent_ollama.py
```

**Option 2: Domain-Aware Agent (with Ontology)**
```bash
python agent_with_ontology.py
```

**Option 3: Full Comparison (5 Agents, Scoring)**
```bash
python run_comparison.py
```

**Option 4: Knowledge Graph (Neo4j)**
```bash
docker run -d --name neo4j-retail -p 7475:7474 -p 7688:7687 -e NEO4J_AUTH=neo4j/password neo4j:5
python graph/ingest_to_graph.py
python graph/agent_graph_ollama.py
```

**Option 5: Semantic Layer (SLayer REST)**
```bash
uvx --from 'motley-slayer[all]' slayer serve --demo   # in a separate terminal
python setup_slayer.py
python agent_slayer_ollama.py
```

**Option 6: ODPS Data Product**
```bash
python agent_odps_ollama.py
```

**Option 7: MCP (Claude Desktop)**
```bash
uvx --from 'motley-slayer[all]' slayer serve   # registration only
python setup_mcp.py
# Stop the REST server, add ../config/claude_desktop_retail.json to Claude Desktop, restart
```

---

## The Retail Use Case

A retail company needs to answer critical questions daily:
- *"What is our customer lifetime value? Who are our high-value customers?"*
- *"Which customers are at churn risk? Who needs a retention offer?"*
- *"Should we send a special offer this week?"*

**Without Context Engineering:** Manual SQL, error-prone, slow, not auditable.  
**With Context Engineering:** Data contract + agent → fast, correct, auditable, consistent.

---

## How It Works (The 2-Turn Agent Loop)

```
User Question: "What is our customer LTV and churn risk?"
       ↓
Turn 1 — PLANNING (LLM decides what to query)
   Agent reads: Data Contract (schema + meaning) + Ontology (business rules)
   Agent thinks: "I need customer_ltv and churn_risk_score columns"
   Agent writes: SELECT customer_ltv, churn_risk_score FROM customer_metrics
   Agent executes: DuckDB returns data
       ↓
Turn 2 — SYNTHESIS (LLM explains the answer)
   Agent reads: Data + Ontology rules
   Agent thinks: "This customer LTV is $2847, below our $3000 target"
   Agent says: "Our LTV is $2847 (below $3000 target). Churn risk: 72/100 (monitor)."
   structlog logs: Full JSON trace of every step
       ↓
Result + Audit Trail (every decision logged)
```

---

## Building Block 1: LLM (Reasoning Engine)

**What it is:** The AI model that reads context and reasons about data.

**In this demo:**
- ✅ Qwen2.5 via local Ollama (fully on-premise, no API key)

**How it improves:**
- Better models → better reasoning from same context
- LLM doesn't need to understand SQL, just business concepts

---

## Building Block 2: Agent (Decision-Maker)

**What it is:** Autonomous loop that orchestrates LLM reasoning and tool execution.

**In this demo:**
- ✅ Two-turn structure:
  - **Turn 1:** LLM plans ("What data do I need?")
  - **Turn 2:** LLM synthesizes ("What does this mean for the business?")
- ✅ Tool integration: Executes SQL queries
- ✅ Structured logging: JSON trace of all decisions

**How it improves:**
- Separating planning from synthesis gives cleaner decision records
- Tool calls are auditable and traceable
- Latency tracked per turn

---

## Building Block 3: Data Contract (Schema + Description)

**What it is:** Structured documentation of what data means, in language LLMs understand.

**File:** `contracts/customer_metrics.yaml` (ODCS format)

**Contains:**
```yaml
models:
  - name: customer_metrics
    description: "Daily customer health snapshot..."
    
    columns:
      - name: customer_ltv
        type: decimal
        description: >
          Customer lifetime value in USD.
          Tiers: High-value (>$5000), Standard ($1000-$5000), Low-value (<$1000)
      
      - name: churn_risk_score
        type: decimal
        description: >
          Churn risk as 0-100 score (100 = highest risk).
          Thresholds:
          - Score > 85: CRITICAL → retention offer within 24 hours
          - Score 70-85: HIGH → monitor closely
          - Score < 50: LOW → stable customer

servicelevels:
  freshness: "Updated daily at 02:00 UTC"
  availability: "99.5% uptime"
  retention: "2 years of historical data"

quality:
  checks:
    - row_count > 0
    - no duplicates
    - no null LTV values
    - churn_risk_score between 0-100
```

**How it improves:**
- Agent understands: Schema + business meaning + governance
- No hardcoded prompts needed
- Contract is version-controlled, auditable

---

## Building Block 4: Ontology (Domain Knowledge)

**What it is:** Formal machine-readable representation of business concepts and rules.

**File:** `ontology/customer_segments.ttl` (OWL/SKOS format)

**Contains:**
```turtle
# Class Hierarchy
retail:HighValueCustomer
  rdfs:subClassOf retail:ActiveCustomer ;
  skos:definition "LTV > $5000, requiring VIP treatment"@en ;
  retail:retention_strategy "dedicated_support, exclusive_offers"@en .

# Business Rules
retail:CriticalChurn
  skos:definition "Churn risk score > 85 — IMMEDIATE ACTION"@en ;
  retail:requires_action "retention_offer_24h"@en ;
  retail:escalation_to "retention_specialist"@en .

# Key Insights
# IF ltv > 5000 AND churn_risk_score > 70 THEN action = VIPRetention
# IF churn_risk_score > 85 THEN action = RetentionOffer24h (within 24h)
```

**New Agent:** `agent_with_ontology.py`
- Loads and reasons with ontology
- Answers domain questions WITHOUT querying database
- Understands business rules and workflows

**Example:**
```
Question: "What does being at-risk mean?"
Ontology: "AtRiskCustomer with churn_risk_score > 70 → monitor + prepare retention offer"
Answer: Returns business definition from domain knowledge, not from data
```

**How it improves:**
- Agent becomes domain-aware, not just schema-aware
- Can answer conceptual questions without hitting database
- Business logic is explicit and auditable

---

## Building Block 5: MetricFlow (Governed Metrics)

**What it is:** Named, versioned business metrics with formulas enforced by the system.

**File:** `metrics/metrics.yaml` (MetricFlow format)

**Includes 9 metrics:**
1. `customer_ltv` — Formula: AOV × frequency × lifespan
2. `churn_risk_score` — Formula: (days_since × 10) + (return_rate × 5) − (repeat_rate × 3)
3. `repeat_purchase_rate` — % of repeat customers
4. `high_value_customer_count` — COUNT(LTV > $5000)
5. `at_risk_customer_count` — COUNT(churn > 70)
6. `average_order_value` — Mean transaction value
7. `purchase_frequency_12m` — Purchases per year
8. `retention_rate` — **Derived metric** (depends on others)
9. `dormant_customer_count` — COUNT(days_since_purchase > 365)

**Example metric:**
```yaml
- name: customer_ltv
  type: simple
  label: "Customer Lifetime Value (USD)"
  formula: "average_order_value * purchase_frequency_12m * lifespan_months"
  owner: "analytics@retailcompany.com"
  
  sla:
    freshness: "daily at 02:00 UTC"
    accuracy: "99.5%"
  
  governance:
    - rule: "value must be >= 0"
    - rule: "null values not allowed"
  
  benchmark:
    target: 3000
    high_performer: "> 3500"
```

**Agent behavior:**
- Would call: `query_metric("customer_ltv", "churn_risk_score")`
- MetricFlow enforces formula (no manual SQL)
- Every consumer gets same number, computed the same way

**How it improves:**
- One source of truth for every metric
- Formula enforcement prevents errors
- Metrics are version-controlled
- Every consumer gets consistent answers

---

## Building Block 6: Knowledge Graph (Neo4j)

**What it is:** A real ingestion pipeline that turns flat rows plus a prose policy document into a traversable graph — not a pre-loaded graph.

**Files:** `contracts/retention_policy.md`, `graph/ingest_to_graph.py`, `graph/agent_graph_ollama.py`

**Contains:**
- `graph/ingest_to_graph.py` reads `customer_metrics` from the existing `customer_analytics.duckdb` and the retention policy markdown, then writes `Customer`, `Segment`, and `RetentionAction` nodes into Neo4j.
- The three retention rules (`VIPRetention`, `RetentionOffer24h`, `WinBackCampaign`) — the same ones defined in `ontology/customer_segments.ttl` — are **parsed out of the policy's prose table at runtime**, then applied by running each rule's SQL condition against DuckDB. There is no hardcoded `if customer_ltv > 5000` anywhere in the ingestion code.
- `graph/agent_graph_ollama.py` calls one tool, `trace_customer`, which runs a Cypher traversal (`Customer -[:BELONGS_TO]-> Segment`, `Customer -[:TRIGGERS]-> RetentionAction`) instead of a hand-written join per question.

**Example:**
```
Question: "Which retention action, if any, applies to CUST_00009, and why?"
Graph:    (Customer CUST_00009)-[:TRIGGERS]->(RetentionAction RetentionOffer24h)
Answer:   "CUST_00009 has a churn risk score above 85, which triggers
           RetentionOffer24h: send a personalized discount offer within 24 hours."
```

**How it improves:**
- Edit `contracts/retention_policy.md`'s wording, rerun `ingest_to_graph.py`, and the graph changes — no code edits.
- An empty `actions` list is a real answer ("no rule currently applies"), not missing data.
- Relationships (`Customer` → `Segment` → `RetentionAction`) become directly traversable instead of re-derived per query.

---

## Building Block 7: Semantic Layer (SLayer)

**What it is:** A REST API that abstracts SQL away — the agent asks for measures and dimensions by name, SLayer compiles the SQL.

**Files:** `setup_slayer.py`, `agent_slayer_ollama.py`

**Contains:**
- `setup_slayer.py` registers `customer_analytics.duckdb`'s `customer_metrics` table as a datasource in a running SLayer server and ingests it as a model.
- `agent_slayer_ollama.py` discovers the model's columns at startup, then calls `query_customer_segments(measures, dimensions, filters, order, limit)` — e.g. `measures: ["customer_ltv:avg", "churn_risk_score:avg"], dimensions: ["segment"]` — and logs the SQL SLayer compiled.

**Example:**
```
Without SLayer: agent writes  SELECT AVG(customer_ltv) FROM customer_metrics WHERE segment = 'high-value'
With SLayer:    agent asks    {"measures": ["customer_ltv:avg"], "dimensions": ["segment"]}
                SLayer compiles and returns the SQL — never hand-written by the agent.
```

**How it improves:**
- The agent never writes raw SQL — only names measures and dimensions.
- The compiled SQL is still visible (logged as `slayer.sql`) for audit.
- The same semantic model could be swapped to MCP transport with zero change to what "customer_ltv" means (see Building Block 9).

---

## Building Block 8: ODPS (Data Product Standard)

**What it is:** Steps up from table-level governance (ODCS, Building Block 3) to product-level governance — ports, use cases, pricing.

**File:** `products/customer_analytics_odps.yaml`, `agent_odps_ollama.py`

**Contains:**
```yaml
openDataProductSpecification: 2.0.0
product:
  name: Customer Analytics
  productID: urn:dataproduct:retail:customer-analytics:v1
  owner: {name: Retail Analytics Team, email: analytics@retailcompany.com}
  useCases:
    - VIP retention targeting for high-value at-risk customers
    - Churn risk segmentation for proactive retention outreach
  outputPorts:
    - path: customer_analytics.duckdb
      tables: [{name: customer_metrics, columns: [...11 columns...]}]
  slaProperties:
    - {dimension: freshness, value: P1D}
```

**Example:**
```
Question: "Is this data product approved for VIP retention targeting?"
ODPS says: useCases includes "VIP retention targeting for high-value at-risk customers"
Agent:    "Yes — this product is approved for VIP retention targeting.
           Owned by Retail Analytics Team, refreshed daily at 02:00 UTC."
```

**How it improves:**
- Agent understands what problem the product solves and who it's approved for, not just its schema.
- Same underlying `customer_metrics` table and columns as the ODCS contract — this is a governance upgrade, not a new dataset.

---

## Building Block 9: MCP (Model Context Protocol)

**What it is:** The transport layer for tool discovery — Claude Desktop auto-discovers the semantic layer with zero Python agent code.

**Files:** `setup_mcp.py`, `config/claude_desktop_retail.json`

**Contains:**
- `setup_mcp.py` registers the same `customer_analytics` datasource into SLayer's shared storage (`~/.local/share/slayer`) so the MCP server can read it without the REST server running afterward.
- `config/claude_desktop_retail.json` points Claude Desktop at `uvx --from 'motley-slayer[all]' slayer mcp` (no `--demo` flag, so it loads the registered retail datasource, not the built-in Jaffle Shop demo).

**How it improves:**
- No Python agent script for this layer at all — Claude Desktop calls the semantic layer's tools directly.
- Same business definitions as Building Block 7 (SLayer REST) — only the transport changes.

---

## Sample Data (12 Customers)

```
Segment      Count  LTV Range        Churn Score  Action
─────────────────────────────────────────────────────────
High-Value     3    $6,000-$8,700    15-22        VIP tier
Standard       4    $1,800-$4,100    48-72        Monitor
At-Risk        3    $600-$1,200      82-89        Retention offer
Dormant        2    $89-$125         98-99        Win-back campaign
```

Data spans 3 regions (US, EU, APAC) with realistic customer behaviors.

---

## Installation

### Step 1: Install Ollama
```bash
# macOS
brew install ollama

# Linux/Windows: visit ollama.com/download
```

### Step 2: Start Ollama (keep running)
```bash
ollama serve
```

### Step 3: Pull Model (in another terminal)
```bash
ollama pull qwen2.5
```

### Step 4: Install Python Dependencies
```bash
cd code/
pip install duckdb structlog pyyaml openai rdflib numpy pandas neo4j requests
```

---

## Usage

### Step 1 — Seed Database (Run Once)
```bash
python bootstrap.py
```
Creates `customer_analytics.duckdb` with 12 sample customers.

### Step 2A — Run with Anthropic
```bash
python agent.py
```

### Step 2B — Run with Ollama
```bash
python agent_ollama.py
```

### Step 2C — Run with Ontology (Domain-Aware)
```bash
python agent_with_ontology.py
```

### Step 2D — Run with Knowledge Graph (Neo4j)
```bash
docker run -d --name neo4j-retail -p 7475:7474 -p 7688:7687 -e NEO4J_AUTH=neo4j/password neo4j:5
python graph/ingest_to_graph.py
python graph/agent_graph_ollama.py
```

### Step 2E — Run with Semantic Layer (SLayer)
```bash
uvx --from 'motley-slayer[all]' slayer serve --demo   # separate terminal
python setup_slayer.py
python agent_slayer_ollama.py
```

### Step 2F — Run with ODPS (Data Product)
```bash
python agent_odps_ollama.py
```

### Step 2G — Run with MCP (Claude Desktop)
```bash
uvx --from 'motley-slayer[all]' slayer serve   # registration only
python setup_mcp.py
# Stop the server, add ../config/claude_desktop_retail.json to Claude Desktop, restart
```

### Step 3: Run Comparison (5 Context Layers, Scoring)
```bash
python run_comparison.py
```

Shows how answer quality improves with richer context (1/5 → 5/5 score):
- **Agent 1:** Schema only
- **Agent 2:** + YAML contract
- **Agent 3:** + ODCS governance
- **Agent 4:** + OWL/SKOS ontology
- **Agent 5:** + MetricFlow metrics

**This demonstrates the YouTube video!**

### Step 3 — Capture Trace (Optional)
```bash
python agent_ollama.py > trace.jsonl

# Query the trace:
grep "tool.call" trace.jsonl | python3 -m json.tool  # See SQL generated
grep "latency_ms" trace.jsonl                          # See performance
grep "lineage_source" trace.jsonl                      # See data lineage
```

---

## Sample Output

```
Agent reads contract → Writes SQL → Queries data → Answers question

Example:

============================================================
AGENT OUTPUT:
Based on the data, we have:

High-Value Customers (avg LTV: $7,395):
- 3 customers with very low churn risk (18.33/100)
- Recommendation: VIP tier, special offers, dedicated support

Standard Customers (avg LTV: $2,643):
- 4 customers with medium churn risk (60.75/100)
- Recommendation: Monitor closely, personalized retention campaigns

At-Risk Customers (avg LTV: $914):
- 3 customers with high churn risk (85.67/100)
- Recommendation: Immediate retention offers (24 hours), discounts

Dormant Customers (avg LTV: $108):
- 2 customers with critical churn risk (98.5/100)
- Recommendation: Win-back campaign
============================================================
```

---

## How Each Layer Improves Answer Quality

### Layer 1-2: Schema Only
```
Agent sees: column names
Agent knows: "These are numbers"
Score: 1/5
```

### Layer 3: + Data Contract
```
Agent sees: Columns + descriptions + tiers
Agent knows: "LTV > $5000 = high-value, churn > 85 = critical"
Score: 2-3/5
```

### Layer 4: + Ontology
```
Agent sees: Concepts, hierarchies, business rules
Agent knows: "HighValueCustomer needs VIP treatment, churn triggers retention offer"
Score: 4/5
```

### Layer 5: + MetricFlow
```
Agent sees: Governed metrics, formulas, quality rules
Agent knows: "customer_ltv is certified, updated daily, formula enforced"
Score: 5/5
```

---

## Switching Models

Edit `agent_ollama.py` or `agent_with_ontology.py`:
```python
MODEL = "qwen2.5"        # Recommended (tested)
MODEL = "llama2"         # Alternative
MODEL = "mistral"        # Lightweight
MODEL = "command-r"      # Good for retrieval tasks
```

Then pull the model:
```bash
ollama pull llama2
```

---

## Stack

| Layer | Component | Technology |
|---|---|---|
| **Database** | Data storage | DuckDB (in-process, no server) |
| **Data Contract** | Schema + business docs | YAML (ODCS format) |
| **Ontology** | Domain knowledge | TTL (OWL/SKOS, W3C standard) |
| **Metrics** | Metric governance | YAML (MetricFlow format) |
| **Knowledge Graph** | Policy-driven graph | Neo4j (Cypher) |
| **Semantic Layer** | SQL-free querying | SLayer (REST) |
| **Data Product** | Product-level governance | YAML (ODPS 2.0) |
| **MCP** | Tool discovery/transport | Claude Desktop + `slayer mcp` |
| **Agent** | LLM reasoning | Qwen2.5 via Ollama (local, on-premise) |
| **Observability** | Audit trail | structlog (JSON) |

---

## Files Overview

```
code/
├── bootstrap.py
│   └─ Creates customer_analytics.duckdb
│   └─ Populates 12 sample customers
│   └─ Run once: python bootstrap.py

├── agent.py
│   └─ Anthropic Claude agent (2-turn loop)
│   └─ Reads contract at startup
│   └─ Generates SQL and answers questions

├── agent_ollama.py
│   └─ Local Ollama agent (same logic, different LLM)
│   └─ No API key needed, fully on-premise
│   └─ Requires: ollama serve running

├── agent_with_ontology.py
│   └─ Domain-aware agent (loads ontology)
│   └─ Answers business questions from domain knowledge
│   └─ No DB queries for conceptual questions

├── contracts/customer_metrics.yaml
│   └─ ODCS data contract
│   └─ Documents: schema, columns, SLAs, quality, business rules
│   └─ Read by agents at startup

├── ontology/customer_segments.ttl
│   └─ OWL/SKOS ontology
│   └─ Defines: customer segments, churn thresholds, retention rules
│   └─ Read by agent_with_ontology.py

└── metrics/metrics.yaml
    └─ MetricFlow metric catalog
    └─ Defines: 9 metrics with formulas, owners, SLAs
    └─ Read by run_comparison.py

├── contracts/retention_policy.md
│   └─ Prose retention-trigger policy (3 rules)
│   └─ Parsed at runtime by graph/ingest_to_graph.py

├── graph/ingest_to_graph.py
│   └─ Reads customer_metrics + retention_policy.md
│   └─ Writes Customer/Segment/RetentionAction into Neo4j

├── graph/agent_graph_ollama.py
│   └─ Knowledge graph agent (trace_customer tool)
│   └─ Requires: Neo4j container running

├── setup_slayer.py
│   └─ Registers customer_analytics datasource into SLayer (REST)

├── agent_slayer_ollama.py
│   └─ Semantic layer agent — never writes raw SQL

├── products/customer_analytics_odps.yaml
│   └─ ODPS 2.0 product definition (ports, use cases, SLAs)

├── agent_odps_ollama.py
│   └─ Product-governance-aware agent

├── setup_mcp.py
│   └─ Registers datasource into SLayer's shared storage for MCP

└── ../config/claude_desktop_retail.json
    └─ MCP config for Claude Desktop — no Python agent needed
```

---

## Building Blocks 6-9 (Knowledge Graph, SLayer, ODPS, MCP)

These four layers are now implemented above as Building Blocks 6-9 — see
those sections for what each one is, the exact files, and worked examples.
`ADVANCED_LAYERS.md` in this folder is kept as the original design
rationale for why each layer was added.

---

## Debugging

### Enable Ollama Logging
```bash
OLLAMA_DEBUG=1 ollama serve

# In another terminal, follow the logs
tail -f ~/.ollama/logs/server.log
```

### View Agent Trace
```bash
python agent_ollama.py > trace.jsonl

# See SQL generated
grep "tool.call" trace.jsonl | python3 -m json.tool

# See latency breakdown
grep "latency_ms" trace.jsonl

# See data lineage
grep "lineage_source" trace.jsonl
```

### Modify Questions
Edit `agent.py` or `agent_ollama.py`:
```python
QUESTION = "What is our customer LTV and churn risk this month?"
QUESTION = "Show me all high-value customers"
QUESTION = "Which customers need retention offers?"
```

---

## What This Demonstrates

✅ **Layer 1: LLM** — Reasoning engine (Claude or Qwen2.5)  
✅ **Layer 2: Agent** — Autonomous decision-maker (2-turn loop)  
✅ **Layer 3: Data Contract** — Schema + business context (ODCS YAML)  
✅ **Layer 4: Ontology** — Domain knowledge + business rules (OWL/SKOS)  
✅ **Layer 5: MetricFlow** — Governed metrics catalog (MetricFlow YAML)  
✅ **Layer 6: Knowledge Graph** — Policy-driven Neo4j graph (Customer → Segment → RetentionAction)  
✅ **Layer 7: Semantic Layer** — SLayer REST, agent never writes SQL  
✅ **Layer 8: ODPS** — Product-level governance (ports, use cases, SLAs)  
✅ **Layer 9: MCP** — Claude Desktop auto-discovers tools, zero Python agent  

**Together they show:** Better context = better LLM reasoning = measurably better answers.

---

## Why Context Engineering Matters

**Without Context Engineering:**
- Agent writes SQL by hand (error-prone)
- Multiple teams define metrics differently (inconsistent)
- No audit trail (non-compliant)
- Scaling is slow and risky

**With Context Engineering:**
- Contract + ontology + metrics guide the agent
- One source of truth (consistent)
- Every decision is auditable
- Scaling is safe and repeatable

---

## Next Steps

1. ✅ Run `bootstrap.py` to seed the database
2. ✅ Run `agent.py` or `agent_ollama.py` to see it work
3. ✅ Modify QUESTION and run again
4. ✅ Try `agent_with_ontology.py` for domain-aware reasoning
5. ✅ Capture traces to understand agent decisions
6. ✅ Knowledge Graph, SLayer, ODPS, and MCP added — see Building Blocks 6-9

---

## License

MIT — See LICENSE file for details.

---

## Questions?

- See README.md sections above for detailed explanations
- Run agents with `> trace.jsonl` to see full execution logs
- Check `contracts/`, `ontology/`, `metrics/` for context definitions
- Reference main project README for full Context Engineering series
