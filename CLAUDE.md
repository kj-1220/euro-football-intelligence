# Euro Football Intelligence Platform

## Project overview
AI-driven sports analytics platform. European football is the prototype.
Goal: intelligent analytics layer with dashboard composition, AI analyst chat,
and a knowledge graph connecting clubs, players, managers, and competitions.

## My setup
- Mac, Docker Desktop running Postgres 15
- Neo4j Desktop running locally (bolt://localhost:7687)
- dbt project at ./euro_analytics (postgres adapter)
- Python 3.11+

## Architecture
- Bronze (euro_raw schema) — append-only, 34 tables, 8 sources
- Silver (euro_stg + euro_int schemas) — dbt transformations
- Gold (euro_mart + euro_semantic schemas) — mart tables + semantic layer
- Knowledge graph — Neo4j (entities + relationships)
- RAG corpus — pgvector in Postgres (euro_rag schema)
- Backend — FastAPI
- LLM — Claude via tool use

## Data tiers (locked)
- Tier A: Historical record, no floor (results, standings, trophies)
- Tier B: Contextual/narrative, no floor (managers, transfers, history)
- Tier C: Metric pipeline, 2021-22 floor (xG, PPDA, advanced stats)

## Bronze rules (locked — never revisit)
- Append-only, never UPDATE or DELETE
- No transformations in Bronze
- Entity resolution happens in Silver
- Source URLs mandatory on all scraped tables
- Tier C tables: no data before 2021-22 in metric pipeline

## Key design decisions (locked)
- Claude never computes metrics — reads from semantic layer via get_metric()
- Semantic layer is the contract between data and AI
- Dashboard configs are JSON stored in DB — AI builds configs, frontend renders
- Neo4j for knowledge graph (not Postgres edge tables)
- No live/real-time data — scheduled refresh aligned with match schedule
- Frontend spec pending — do not make frontend assumptions

## Current phase
Phase 1 — Bronze ingestion

## Source notes

### football-data.org
- `fdorg_matches`: COMPLETE. 5,256 rows, 3 seasons (2023-24, 2024-25, 2025-26), 5 leagues.
- `fdorg_standings`: REASSIGNED. Free tier only returns current season. Source from OpenFootball or FBref.
- `fdorg_competition_seasons`: REASSIGNED. Source from OpenFootball or FBref alongside standings.
- `fdorg_lineups`: REASSIGNED. Free tier returns no lineup data. Source from StatsBomb or FBref.
- `fdorg_events`: REASSIGNED. Free tier returns no event data. Source from StatsBomb or FBref.
- `fdorg_head_to_head`: SILVER-DERIVED. Computed from fdorg_matches in dbt. No Bronze ingestion.

### Source reassignment summary
- Lineups + events → StatsBomb Open Data (preferred, free) or FBref
- Standings + competition seasons → OpenFootball (preferred) or FBref
- Head to head → Silver layer (dbt), derived from fdorg_matches