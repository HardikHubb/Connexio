# SIH26189 — Criminal Network Analysis System

Stage 0: project skeleton. This proves the full chain — React frontend →
FastAPI backend → Neo4j — is wired together correctly. No pipeline logic
yet (that starts at Stage 3).

## Prerequisites

- Docker (for Neo4j)
- Python 3.11+
- Node.js 18+

## 1. Start Neo4j

```bash
docker compose up -d
```

Neo4j Browser: http://localhost:7474 (login: `neo4j` / `testpassword123`)
Bolt endpoint: `bolt://localhost:7687`

## 2. Start the backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

API root: http://localhost:8000
Health check: http://localhost:8000/api/health — this actually pings Neo4j,
it isn't a hardcoded "ok".

## 3. Start the frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Open http://localhost:5173 — you should see two badges, "Backend API" and
"Neo4j", both turn green once everything above is running. If Neo4j shows
red, check that `docker compose up -d` succeeded and the password in
`backend/.env` matches `docker-compose.yml`.

## 4. Apply the graph schema (Stage 2)

With the backend venv active:

```bash
cd backend
python scripts/init_schema.py
```

This creates all node uniqueness constraints, property indexes, and the
Person full-text index in Neo4j. It's idempotent — safe to re-run after
later stages add more indexes.

Verify it worked either from the script's own output, or by hitting
http://localhost:8000/api/schema — it should report 8 constraints and
several indexes. You can also open Neo4j Browser (http://localhost:7474)
and run `SHOW CONSTRAINTS` / `SHOW INDEXES` directly.

## Project layout

```
backend/
  app/
    main.py          # FastAPI app entrypoint — stays small, each stage adds a router
    config.py         # all env-driven settings in one place
    db/neo4j_client.py # shared Neo4j driver + run_query() helper — every later stage uses this
    db/schema.py        # constraints/indexes as executable Cypher — the graph's contract
    api/health.py        # real connectivity check endpoint
    api/schema.py         # verifies the schema is actually applied
    models/schemas.py         # ParsedDocument contract — Stage 4 is built against this, nothing else
    services/case_service.py   # case registry (JSON manifest, no DB needed yet)
    services/ingestion_service.py # orchestrates: save raw file -> parse -> store JSON -> register
    services/parsers/           # text_parser.py (FIR/Report), csv_parser.py (CDR/Transaction/Vehicle)
    api/cases.py                 # /api/cases and /api/cases/{id}/ingest routes
  scripts/init_schema.py   # run once to apply the schema (Stage 2)
  scripts/ingest_seed_data.py # loads Stage 1's seed files through the real pipeline (Stage 3)
  seed_data/case_101/       # Stage 1 — one hand-built fraud case (FIR/CDR/transactions/vehicle)
  storage/                   # created at runtime — raw uploads + parsed JSON per case (gitignored)
frontend/
  src/
    App.jsx            # Stage 0 connectivity screen — replaced by real UI from Stage 9 on
    api/client.js       # shared fetch wrapper — later stages add functions here
```

## What's NOT here yet (by design)

No ingestion, extraction, resolution, graph-write, or analytics code —
those are Stages 3–8. No product UI (landing, upload, graph, evidence
panel) — those are Stages 9–11. This stage is deliberately just plumbing,
so every stage after it can build on a foundation that's already proven
to work, rather than debugging infrastructure and pipeline logic at the
same time.

## 5. Load the seed data (Stage 3)

With the backend venv active:

```bash
cd backend
python scripts/ingest_seed_data.py
```

This creates Case 101 ("Operation Nexus") and ingests all four seed files
through the real parsing pipeline — no upload UI needed yet (that's
Stage 9). You should see 4 lines of `OK` output.

Verify:
- http://localhost:8000/api/cases — should list Case 101
- http://localhost:8000/api/cases/101/documents — should list 4 parsed
  documents, with real extracted text/rows, not placeholders
- `backend/storage/101/` — the raw files and their parsed JSON now live
  on disk here

Uploading through the API directly is also possible (e.g. via the
`/docs` Swagger UI at http://localhost:8000/docs): `POST /api/cases` to
create a case, then `POST /api/cases/{case_id}/ingest` with a file and a
`source_type` (FIR / CDR / TRANSACTION / VEHICLE / LOCATION / REPORT).

## Next stage

Stage 4 — entity extraction (NER): reads the ParsedDocument JSON this
stage produces and pulls out People, Phones, Accounts, Vehicles, and
Locations from both the tabular rows and the FIR free text.
