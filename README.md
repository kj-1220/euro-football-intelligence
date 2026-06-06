# Euro Football Intelligence Platform

An AI-driven sports analytics platform using European football as its prototype. Built to demonstrate a general-purpose intelligence layer for analytics — one that builds dashboards, enables custom dashboard composition, and provides a conversational AI analyst for freeform questions.

**This is a platform first. Football is the proof of concept.**

---

## What This Is

Most sports analytics tools are either static dashboards or prediction engines. This platform is neither. It is an intelligent analytics layer that:

- Renders pre-built dashboards across leagues, clubs, players, and competitions
- Lets users compose custom dashboards from a certified metric and widget library
- Provides an AI analyst that answers freeform questions in natural language
- Reasons over structured metrics AND unstructured context simultaneously
- Connects knowledge across entities — clubs, players, managers, competitions — via a graph

The AI does not compute metrics or hallucinate statistics. Every number it states is pulled from a certified semantic layer definition via tool use. It reasons over outputs; it never produces them.

---

## Prototype Scope

**Leagues:** Premier League, La Liga, Bundesliga, Serie A, Ligue 1

**History:** Metric data from 2021-22 onward (post-COVID, consistent tactical context). Historical results and narrative context with no hard floor.

**Special module:** World Cup 2026

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        DATA SOURCES                             │
│  football-data.org · StatsBomb Open · OpenFootball · FBref      │
│  Understat · Transfermarkt · ClubElo · API-Football (WC2026)    │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│              BRONZE LAYER  (schema: euro_raw)                   │
│  Append-only. Source-native. 34 tables across 8 sources.        │
│  Three data tiers: historical record, contextual, metric.       │
└───────────────────────────────┬─────────────────────────────────┘
                                │  dbt run
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│         SILVER LAYER  (schemas: euro_stg, euro_int)             │
│  Staging views · Intermediate feature tables                    │
│  Entity resolution · Rolling windows · Derived ratios           │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│          GOLD LAYER  (schemas: euro_mart, euro_semantic)         │
│  Mart tables · Certified semantic layer metric definitions       │
└──────────────────┬─────────────────────┬────────────────────────┘
                   │                     │
                   ▼                     ▼
┌──────────────────────────┐  ┌──────────────────────────────────┐
│    KNOWLEDGE GRAPH       │  │      RAG CORPUS (euro_rag)       │
│    Neo4j                 │  │      pgvector · PostgreSQL        │
│                          │  │                                  │
│  Clubs · Players         │  │  Match narratives                │
│  Managers · Matches      │  │  Club identity docs              │
│  Seasons · Competitions  │  │  Manager profiles                │
│                          │  │  Tactical breakdowns             │
│  Synced nightly from     │  │  Competition context             │
│  mart tables             │  │                                  │
└──────────┬───────────────┘  └──────────────────┬───────────────┘
           └─────────────────┬────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│               PLATFORM INTELLIGENCE LAYER                       │
│  Claude tool use · Semantic layer contract                      │
│  Dashboard · Analysis · Chat reasoning modes                    │
└─────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FASTAPI BACKEND                            │
└─────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND                                 │
│                    (specification pending)                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Architecture

### Three-Tier Data Model

**Tier A — Historical Record (no floor)**
Results, standings, competition winners. Facts, not metrics. Powers knowledge graph history and RAG corpus. Answers questions like "who won Champions League 20 years ago."

**Tier B — Contextual / Narrative (no floor)**
Manager tenures, transfer history, tactical evolution, squad valuations. Powers the knowledge graph edges and RAG corpus narrative documents. Pep Guardiola's full career arc lives here.

**Tier C — Metric Pipeline (2021-22 floor)**
xG, PPDA, progressive passes, pressing metrics, all advanced stats. Post-COVID, consistent tactical context. Powers dashboards, semantic layer, and all quantitative reasoning.

### The Semantic Layer is the Contract
Every metric Claude can reference is defined in `euro_semantic` with a formula, grain, valid dimensions, and human-readable description. Claude never computes or infers numbers. It calls `get_metric()` and reasons over the result.

### Semantic Layer vs RAG Corpus
**Semantic layer** answers "how much" — PPDA is 8.3, xG differential is +0.4.
**RAG corpus** answers "what does it mean and why" — Arsenal's pressing philosophy under Arteta, how their press triggers have evolved, why their PPDA in the Champions League differs from domestic form.

Tactics split across both: pressing metrics (numbers) live in the semantic layer; tactical identity narratives live in RAG.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Database | PostgreSQL 15 |
| Vector search | pgvector (same Postgres instance) |
| Knowledge graph | Neo4j |
| Transformation | dbt (postgres adapter) |
| Embedding | text-embedding-3-small (OpenAI) |
| Backend | FastAPI |
| LLM | Claude (Anthropic) via tool use |
| Deployment | Railway (API) · Vercel (frontend) |

---

## Data Sources

| Source | Type | Covers |
|---|---|---|
| football-data.org | REST API (free) | Fixtures, results, standings, lineups, events |
| StatsBomb Open Data | GitHub JSON | Event-level data, tactical depth |
| OpenFootball | GitHub CSV/JSON | Deep historical results |
| FBref | Scraper | xG, PPDA, all advanced metrics |
| Understat | Scraper | xG per match and player, 2014-present |
| Transfermarkt | Scraper | Transfers, valuations, manager history |
| ClubElo | REST endpoint | Historical Elo ratings |
| API-Football | REST API | World Cup 2026 coverage |

---

## Key Design Principles

**Claude never computes metrics.** Every number it states is returned by `get_metric()` from the certified semantic layer. If a metric isn't defined there, it doesn't exist as far as Claude is concerned.

**The knowledge graph is context, not data.** Neo4j stores relationships and entity properties. Mart tables store numbers. The graph answers "who is connected to what" so the AI assembles the right context before calling metric tools.

**Dashboard configs are data.** A saved dashboard is a JSON config stored in the database. The AI builds configs; the frontend renders them. The AI never writes UI code.

**Bronze is immutable.** Raw tables are append-only. All transformation happens in Silver and above.

**Sport agnosticism via schemas.** Each sport gets its own schema namespace. The platform API, composition engine, and AI reasoning layer operate on entity types and metric definitions — not sport-specific hardcoding.

---

## Build Phases

| Phase | Scope | Status |
|---|---|---|
| 1 | Bronze layer — ingestion scripts, all 34 tables populated | 🔲 |
| 2 | Silver layer — dbt staging views + intermediate tables | 🔲 |
| 3 | Gold layer — mart tables + semantic layer definitions | 🔲 |
| 4 | Knowledge graph — Neo4j schema, entity sync, traversal | 🔲 |
| 5 | RAG corpus — document generation, embedding, pgvector | 🔲 |
| 6 | Intelligence layer — Claude tool suite, reasoning modes | 🔲 |
| 7 | FastAPI backend — all endpoints, contracts | 🔲 |
| 8 | Frontend — specification pending | 🔲 |
| 9 | World Cup 2026 module | 🔲 |
| 10 | Integration testing + deployment | 🔲 |

---

## Local Setup

**Prerequisites:** Docker Desktop, Python 3.11+, Node 18+, dbt-postgres, Neo4j Desktop

```bash
# Clone
git clone https://github.com/<your-username>/euro-football-intelligence.git
cd euro-football-intelligence

# Start PostgreSQL
docker start euro-pg

# Start Neo4j
# Open Neo4j Desktop and start your local instance

# Python dependencies
pip install -r requirements.txt

# Environment variables
cp .env.example .env
# Add: ANTHROPIC_API_KEY, FBREF_DELAY_SECONDS, TRANSFERMARKT_DELAY_SECONDS
# Add: NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
# Add: POSTGRES connection string

# Run dbt
cd euro_analytics
dbt debug
dbt run
```

---

## Repository Structure

```
euro-football-intelligence/
├── euro_raw/                  # Bronze ingestion scripts (one per source)
│   ├── fbref/
│   ├── football_data_org/
│   ├── openfootball/
│   ├── understat/
│   ├── transfermarkt/
│   └── clubelo/
├── euro_analytics/            # dbt project
│   ├── models/
│   │   ├── staging/           # euro_stg views
│   │   ├── intermediate/      # euro_int tables
│   │   ├── mart/              # euro_mart tables
│   │   └── semantic/          # euro_semantic definitions
│   └── dbt_project.yml
├── knowledge_graph/           # Neo4j schema + sync jobs
├── rag/                       # Document generation + embedding
├── api/                       # FastAPI backend
├── docs/                      # Architecture decisions, specs
│   ├── BRONZE_SPEC.md         # Locked Bronze schema specification
│   ├── SEMANTIC_LAYER.md      # Metric definitions (forthcoming)
│   └── GRAPH_SCHEMA.md        # Neo4j schema (forthcoming)
├── scripts/                   # ETL utilities, cron jobs
├── .env.example
├── requirements.txt
└── README.md
```

---

## Documentation

- [`docs/BRONZE_SPEC.md`](docs/BRONZE_SPEC.md) — Locked Bronze schema specification (all 34 tables)
- `docs/SEMANTIC_LAYER.md` — Certified metric definitions (forthcoming)
- `docs/GRAPH_SCHEMA.md` — Neo4j knowledge graph schema (forthcoming)
