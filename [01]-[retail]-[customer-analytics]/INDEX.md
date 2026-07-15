# Project Index — Context Engineering Retail Demo

## 📁 Complete Project Structure

```
[ce]-[retail]-[customer-analytics]-[2026-05]/
│
├── 📄 INDEX.md                           ← This file (project overview)
├── 📄 README.md                          ← Main documentation (start here)
├── 📄 ADVANCED_LAYERS.md                 ← Design rationale for Layers 6-9
├── 📄 YOUTUBE_TRANSCRIPT.md              ← 21-min video script (all 5 blocks)
├── 📄 TRANSCRIPT_CHANGES_SUMMARY.md      ← Banking → Retail conversion notes
│
├── 🗂️ code/
│   ├── bootstrap.py                      ← Seed DuckDB with sample data
│   ├── agent.py                          ← Anthropic Claude agent
│   ├── agent_ollama.py                   ← Local Ollama agent
│   ├── agent_with_ontology.py            ← Domain-aware agent
│   ├── agent_slayer_ollama.py            ← Semantic Layer agent (SLayer REST)
│   ├── agent_odps_ollama.py              ← Data Product agent (ODPS)
│   ├── setup_slayer.py                   ← Register datasource into SLayer (REST)
│   ├── setup_mcp.py                      ← Register datasource into SLayer (MCP)
│   ├── run_comparison.py                 ← 5-layer scoring comparison
│   │
│   ├── 🗂️ contracts/
│   │   ├── customer_metrics.yaml         ← Data Contract (ODCS format)
│   │   └── retention_policy.md           ← Retention trigger rules (prose)
│   │
│   ├── 🗂️ ontology/
│   │   └── customer_segments.ttl         ← OWL/SKOS Ontology
│   │
│   ├── 🗂️ metrics/
│   │   └── metrics.yaml                  ← MetricFlow Metrics Catalog
│   │
│   ├── 🗂️ products/
│   │   └── customer_analytics_odps.yaml  ← ODPS 2.0 Data Product
│   │
│   └── 🗂️ graph/
│       ├── ingest_to_graph.py            ← Policy-driven Neo4j ingestion
│       └── agent_graph_ollama.py         ← Knowledge Graph agent
│
├── 🗂️ config/
│   └── claude_desktop_retail.json        ← MCP config for Claude Desktop
│
└── 📄 [Other supporting files]
```

---

## 📖 Where to Start

### For YouTube Video Production
👉 **Start here:** `YOUTUBE_TRANSCRIPT.md`
- 21-minute complete script
- All 5 building blocks explained
- Retail example (Customer LTV, churn risk)
- Ready to record from

### For Running the Demo
👉 **Start here:** `README.md`
- Quick start (3 options: Anthropic, Ollama, with Ontology)
- Installation instructions
- How to run each agent
- Sample output
- Debugging tips

### For Understanding Context Engineering
👉 **Architecture overview:** `README.md` (Building Blocks section)
- What each of the 5 blocks does
- How they stack to improve reasoning
- Score progression: 1/5 → 5/5

---

## 🚀 Quick Commands

### Setup (One-Time)
```bash
cd code/
pip install duckdb structlog pyyaml openai rdflib anthropic
python bootstrap.py
```

### Run Demo (Pick One)
```bash
# Option A: Anthropic Cloud
export ANTHROPIC_API_KEY=sk-ant-YOUR_KEY
python agent.py

# Option B: Local Ollama (no API key)
ollama pull qwen2.5
python agent_ollama.py

# Option C: Domain-Aware (with ontology)
python agent_with_ontology.py
```

### Capture Trace
```bash
python agent_ollama.py > trace.jsonl
grep "tool.call" trace.jsonl | python3 -m json.tool
```

### Knowledge Graph (Neo4j)
```bash
docker run -d --name neo4j-retail -p 7475:7474 -p 7688:7687 -e NEO4J_AUTH=neo4j/password neo4j:5
python graph/ingest_to_graph.py
python graph/agent_graph_ollama.py
```

### Semantic Layer (SLayer REST) + MCP
```bash
uvx --from 'motley-slayer[all]' slayer serve --demo   # separate terminal
python setup_slayer.py && python agent_slayer_ollama.py

# For MCP (Claude Desktop) instead:
python setup_mcp.py
# then add config/claude_desktop_retail.json to Claude Desktop
```

---

## 📊 The 9 Building Blocks (What's Included)

| Layer | Building Block | File(s) | Status |
|---|---|---|---|
| **1** | LLM | `agent.py`, `agent_ollama.py` | ✅ Working |
| **2** | Agent | `agent.py`, `agent_ollama.py` | ✅ Working |
| **3** | Data Contract | `contracts/customer_metrics.yaml` | ✅ Working |
| **4** | Ontology | `ontology/customer_segments.ttl` | ✅ Working |
| **5** | MetricFlow | `metrics/metrics.yaml` | ✅ Working |
| **6** | Knowledge Graph | `contracts/retention_policy.md`, `graph/ingest_to_graph.py`, `graph/agent_graph_ollama.py` | ✅ Working |
| **7** | Semantic Layer (SLayer) | `setup_slayer.py`, `agent_slayer_ollama.py` | ✅ Working |
| **8** | ODPS | `products/customer_analytics_odps.yaml`, `agent_odps_ollama.py` | ✅ Working |
| **9** | MCP | `setup_mcp.py`, `config/claude_desktop_retail.json` | ✅ Working |

---

## 📋 File Descriptions

### Documentation Files

| File | Purpose | Length |
|------|---------|--------|
| `README.md` | Main documentation (consolidated) | ~17KB |
| `YOUTUBE_TRANSCRIPT.md` | Video script (21 min, all 5 blocks) | ~28KB |
| `TRANSCRIPT_CHANGES_SUMMARY.md` | Banking→Retail conversion notes | ~7KB |
| `INDEX.md` | This file (project overview) | ~4KB |

### Code Files

| File | Purpose | Lines |
|------|---------|-------|
| `code/bootstrap.py` | Create DuckDB, seed 12 customers | ~150 |
| `code/agent.py` | Anthropic Claude agent (2-turn loop) | ~200 |
| `code/agent_ollama.py` | Ollama agent (same logic) | ~200 |
| `code/agent_with_ontology.py` | Domain-aware agent | ~250 |
| `code/graph/ingest_to_graph.py` | Policy-driven Neo4j ingestion | ~200 |
| `code/graph/agent_graph_ollama.py` | Knowledge Graph agent | ~180 |
| `code/setup_slayer.py` | Register datasource into SLayer (REST) | ~70 |
| `code/agent_slayer_ollama.py` | Semantic Layer agent | ~140 |
| `code/agent_odps_ollama.py` | Data Product (ODPS) agent | ~150 |
| `code/setup_mcp.py` | Register datasource into SLayer (MCP) | ~80 |

### Context Files

| File | Type | Purpose | Content |
|------|------|---------|---------|
| `contracts/customer_metrics.yaml` | YAML | Data Contract (ODCS) | Schema, SLA, quality, business rules |
| `ontology/customer_segments.ttl` | TTL | OWL/SKOS Ontology | Customer segments, churn rules, retention actions |
| `metrics/metrics.yaml` | YAML | MetricFlow Catalog | 9 metrics with formulas, owners, SLAs |
| `contracts/retention_policy.md` | Markdown | Retention policy prose | 3 retention trigger rules, parsed at runtime |
| `products/customer_analytics_odps.yaml` | YAML | ODPS 2.0 Data Product | Ports, use cases, SLAs, pricing, terms |
| `config/claude_desktop_retail.json` | JSON | MCP config | Claude Desktop → SLayer MCP server |

---

## 💾 Sample Data

**Database:** `code/customer_analytics.duckdb` (created by `bootstrap.py`)

**Customers (12 total):**
- 3 High-Value (LTV $6K-$8.7K, churn 15-22)
- 4 Standard (LTV $1.8K-$4.1K, churn 48-72)
- 3 At-Risk (LTV $600-$1.2K, churn 82-89)
- 2 Dormant (LTV $89-$125, churn 98-99)

**Regions:** US, EU, APAC

---

## 🎯 Project Stats

| Metric | Count |
|--------|-------|
| **Documentation Files** | 4 |
| **Code Files** | 10 |
| **Context Files** | 6 |
| **Building Blocks** | 9 |
| **Sample Customers** | 12 |
| **Metrics Defined** | 9 |
| **Retention Trigger Rules** | 3 |
| **Total Lines of Code** | ~1750 |
| **Total Documentation** | ~56KB |

---

## ✅ Verification Checklist

- ✅ All 9 building blocks implemented
- ✅ 3 working agents (Claude, Ollama, with Ontology)
- ✅ Sample data with realistic customers
- ✅ Full documentation (README + video script)
- ✅ YAML contracts and OWL ontologies
- ✅ MetricFlow metric definitions
- ✅ Structured logging (JSON audit trail)
- ✅ Knowledge Graph — policy-driven Neo4j ingestion + agent
- ✅ Semantic Layer — SLayer REST setup + agent
- ✅ ODPS — product-level governance definition + agent
- ✅ MCP — Claude Desktop config, zero Python agent
- ✅ Ready for YouTube video production

---

## 🎬 For YouTube Video

### Script
📄 `YOUTUBE_TRANSCRIPT.md` (21 minutes)
- Intro & Problem (2 min)
- What is Context Engineering (2 min)
- 5 Building Blocks explained (9 min)
- How they work together + scoring (6 min)
- Real-world examples (2 min)

### Demo
Use `code/agent_ollama.py` to show:
1. Agent reading contract at startup
2. Agent generating SQL from business question
3. SQL executing against DuckDB
4. Agent explaining results
5. JSON trace logged to file

### Visual Assets Needed
- Screenshots of YAML contract
- Diagram of 2-turn agent loop
- Scoring table (1/5 → 5/5)
- Architecture diagram
- Sample output terminal screenshot

---

## 🔧 Technical Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| **Database** | DuckDB | Latest |
| **LLM (Cloud)** | Claude Opus 4.8 | Latest |
| **LLM (Local)** | Qwen2.5 | Latest |
| **Data Contract** | YAML (ODCS format) | 0.9.3 |
| **Ontology** | TTL (OWL/SKOS) | W3C Standard |
| **Metrics** | YAML (MetricFlow) | Apache 2.0 |
| **Logging** | structlog | Latest |
| **Language** | Python | 3.10+ |

---

## 📚 How the Project Demonstrates Context Engineering

```
Question: "What is our customer LTV and churn risk?"

WITHOUT Context Engineering:
  ❌ Agent has no idea what LTV means
  ❌ Must write SQL from scratch (error-prone)
  ❌ No audit trail
  ❌ Not consistent across teams

WITH Context Engineering (this demo):
  ✅ Agent reads Data Contract (schema + meaning)
  ✅ Agent reads Ontology (business rules)
  ✅ Agent reads MetricFlow (metric definitions)
  ✅ Agent generates correct SQL
  ✅ Full JSON trace logged
  ✅ Consistent, auditable, repeatable
  ✅ Score: 5/5 (all criteria met)
```

---

## 🎯 Next Steps

1. **Read** `README.md` for full understanding
2. **Run** `python bootstrap.py` to create database
3. **Execute** one of the agents (`agent.py`, `agent_ollama.py`, or `agent_with_ontology.py`)
4. **Review** `YOUTUBE_TRANSCRIPT.md` for video script
5. **Record** YouTube video using transcript + live demo

---

## 📞 File Relationships

```
YOUTUBE_TRANSCRIPT.md
  ↓ (describes)
  The 9 Building Blocks
  ↓ (implemented by)
  README.md
  ↓ (references)
  code/agent.py, agent_ollama.py, agent_with_ontology.py,
  code/agent_slayer_ollama.py, code/agent_odps_ollama.py,
  code/graph/agent_graph_ollama.py
  ↓ (reads at startup)
  contracts/customer_metrics.yaml
  contracts/retention_policy.md
  ontology/customer_segments.ttl
  metrics/metrics.yaml
  products/customer_analytics_odps.yaml
  ↓ (queries)
  code/customer_analytics.duckdb  ←  code/bootstrap.py
  ↓ (also feeds, via setup scripts)
  SLayer datasource (setup_slayer.py, setup_mcp.py)
  Neo4j graph (graph/ingest_to_graph.py)
```

---

## 💡 Key Insights

1. **Same LLM + Same Data + Different Context = Different Quality**
   - With Schema only: 1/5 score
   - With Contract: 2/5 score
   - With Ontology: 4/5 score
   - With Full Stack: 5/5 score

2. **Context Engineering is Measurable**
   - Not abstract, has concrete impact
   - Scoring table proves progression
   - Audit trail shows every decision

3. **Layers Build on Each Other**
   - LLM + Agent = basic automation
   - + Contract = schema awareness
   - + Ontology = domain awareness
   - + Metrics = governance awareness

---

## 📝 License

MIT — See LICENSE file in parent directory.

---

**Last Updated:** 2026-07-14  
**Project Status:** ✅ Complete (9 Building Blocks) and Ready for YouTube Production
