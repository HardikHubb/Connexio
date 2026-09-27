# SIH26189 — Criminal Network Analysis System

An evidence-backed criminal network analysis system that transforms fragmented investigation records into a connected knowledge graph.

The system ingests realistic synthetic investigation records such as FIRs, Call Detail Records (CDRs), transaction records, and vehicle records. These records are processed through a real backend pipeline to extract entities, identify relationships, resolve repeated entities, construct a Neo4j knowledge graph, and expose the resulting network through a FastAPI API and React interface.

> **Important:** The prototype uses realistic synthetic investigation data. It does not use or claim access to confidential government or police data.

## What This Project Demonstrates

```text
Investigation Records
        |
        v
   File Ingestion
        |
        v
      Parsing
        |
        v
 Entity Extraction
        |
        v
Relationship Extraction
        |
        v
 Entity Resolution
        |
        v
      Neo4j
   Graph Database
        |
   Cypher Queries
        |
        v
      FastAPI
        |
        v
 React Frontend
        |
        v
Interactive Network
```

The graph displayed in the frontend is retrieved from Neo4j through the backend. It is not a hardcoded frontend graph.

## Current MVP

The repository contains a working end-to-end vertical slice.

1. Investigation files are ingested.
2. Files are parsed into structured documents.
3. Entities are extracted from tabular and free-text records.
4. Relationships are extracted from the structured information.
5. Repeated entity mentions are resolved using deterministic normalized matching.
6. Entities and relationships are written to Neo4j.
7. FastAPI retrieves graph data from Neo4j.
8. React renders the retrieved investigation network.
9. Entities can be selected and their stored properties and source references inspected.

### Current Case 101 verification

The working seed investigation currently demonstrates:

- **4** parsed source documents
- **58** extracted entity mentions
- **27** canonical entities
- **27** entities written to Neo4j
- **26** extracted relationships written to the graph
- **27** entities returned by the graph network API
- **24** graph edges returned by the network API

These are current implementation/test values, not performance claims.

## Implemented

### Data ingestion

- [x] Case creation
- [x] File ingestion through FastAPI
- [x] Raw file storage
- [x] Parsed document storage
- [x] FIR/text parsing
- [x] CSV/tabular parsing
- [x] Source registration
- [x] Document listing and retrieval

Supported source types:

- FIR
- CDR
- TRANSACTION
- VEHICLE
- LOCATION
- REPORT

### Entity extraction

Current entity types:

- PERSON
- PHONE
- ACCOUNT
- VEHICLE
- LOCATION
- ORGANIZATION

Extracted entities preserve information such as entity type, original value, normalized value, case ID, source ID, evidence, timestamp when available, and confidence.

### Relationship extraction

Current relationship types include:

- CALLED
- TRANSFERRED_TO
- OWNS
- USES
- SEEN_AT
- LOCATED_AT
- VISITED
- IDENTIFIED_AS
- MENTIONED_IN

Relationships retain provenance such as source record, case, evidence, timestamp when available, and confidence.

### Entity resolution

The MVP performs conservative deterministic entity resolution using normalized values.

Canonical entities maintain:

- canonical ID
- entity type
- canonical value
- normalized value
- aliases
- source IDs
- mention count

The current stage does not perform unrestricted fuzzy matching or make identity claims beyond the implemented matching rules.

## Neo4j Is a Real Graph Database

Neo4j is not mocked by the frontend.

The project runs Neo4j using Docker Compose:

```text
React
  |
  v
FastAPI
  |
  v
Neo4j
```

The backend uses the Neo4j Bolt driver to communicate with the running database.

The project applies Neo4j constraints and indexes, including node uniqueness constraints, property indexes, relationship indexes, and a Person full-text index.

### Start Neo4j

```bash
docker compose up -d
```

Neo4j Browser:

```text
http://localhost:7474
```

Development credentials:

```text
Username: neo4j
Password: testpassword123
```

Bolt:

```text
bolt://localhost:7687
```

> These credentials are development-only.

## FastAPI Backend

The backend provides the application API and connects the frontend to the graph database.

Responsibilities include:

- case management
- file ingestion
- document parsing
- entity extraction
- relationship extraction
- entity resolution
- graph construction
- graph retrieval
- entity detail retrieval
- Neo4j connectivity and schema verification

API:

```text
http://localhost:8000
```

Swagger:

```text
http://localhost:8000/docs
```

Health check:

```text
http://localhost:8000/api/health
```

The health endpoint checks actual Neo4j connectivity rather than returning a hardcoded success response.

## React Frontend

The frontend provides the investigator-facing interface:

- investigation overview
- data ingestion interface
- investigation network visualization
- interactive graph exploration
- entity selection
- entity details
- source references

The graph is populated from:

```text
FastAPI -> Neo4j
```

rather than frontend-only mock graph data.

## Project Structure

```text
SIH26189/
|
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── cases.py
│   │   │   ├── graph.py
│   │   │   ├── health.py
│   │   │   └── schema.py
│   │   ├── db/
│   │   │   ├── neo4j_client.py
│   │   │   └── schema.py
│   │   ├── models/
│   │   │   └── schemas.py
│   │   └── services/
│   │       ├── case_service.py
│   │       ├── ingestion_service.py
│   │       ├── extraction/
│   │       ├── resolution/
│   │       ├── relationship/
│   │       ├── graph/
│   │       └── parsers/
│   ├── scripts/
│   ├── seed_data/
│   ├── storage/
│   └── requirements.txt
|
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
|
├── docker-compose.yml
├── .env.example
└── README.md
```

`backend/storage/` is runtime-generated storage for uploaded and parsed case data and should not contain sensitive production data.

## Prerequisites

Install:

- Docker
- Python 3.11+
- Node.js 18+

Verify:

```bash
docker --version
python --version
node --version
npm --version
```

## Local Setup

### 1. Start Neo4j

From the project root:

```bash
docker compose up -d
```

Check:

```bash
docker ps
```

Open Neo4j Browser:

```text
http://localhost:7474
```

### 2. Start the Backend

```bash
cd backend
```

Create a virtual environment.

Windows:

```powershell
python -m venv .venv
.venv\Scripts\activate
```

Linux/macOS:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create `.env` from `.env.example`.

Windows:

```powershell
copy .env.example .env
```

Linux/macOS:

```bash
cp .env.example .env
```

Start FastAPI:

```bash
uvicorn app.main:app --reload --port 8000
```

### 3. Apply the Neo4j Schema

With the backend environment active:

```bash
cd backend
python scripts/init_schema.py
```

Verify:

```text
http://localhost:8000/api/schema
```

You can also inspect Neo4j directly:

```cypher
SHOW CONSTRAINTS;
```

```cypher
SHOW INDEXES;
```

### 4. Load the Seed Investigation

The project includes synthetic Case 101.

```bash
cd backend
python scripts/ingest_seed_data.py
```

Verify:

```text
http://localhost:8000/api/cases
```

and:

```text
http://localhost:8000/api/cases/101/documents
```

Runtime files are stored under:

```text
backend/storage/101/
```

### 5. Start the Frontend

Open another terminal:

```bash
cd frontend
npm install
```

Create `.env` from `.env.example`.

Then:

```bash
npm run dev
```

Open:

```text
http://localhost:5173
```

## Verifying the Complete Pipeline

```text
Seed Investigation
       |
       v
Real File Ingestion
       |
       v
Real Parsing
       |
       v
Entity Extraction
       |
       v
Relationship Extraction
       |
       v
Entity Resolution
       |
       v
Neo4j Write
       |
       v
FastAPI Graph API
       |
       v
React Network
```

The frontend is therefore the visualization layer of an implemented backend pipeline, not the source of the graph data.

## Useful API Endpoints

### Health

```text
GET /api/health
```

### Cases

```text
GET /api/cases
POST /api/cases
GET /api/cases/{case_id}
```

### Documents

```text
GET /api/cases/{case_id}/documents
GET /api/cases/{case_id}/documents/{source_id}
POST /api/cases/{case_id}/ingest
```

### Graph

```text
GET /api/cases/{case_id}/network
GET /api/entities/{entity_id}
```

### Schema

```text
GET /api/schema
```

## Inspecting the Graph Directly

Open:

```text
http://localhost:7474
```

Example:

```cypher
MATCH (n)
RETURN n
LIMIT 100;
```

Inspect relationships for Case 101:

```cypher
MATCH ()-[r]->()
WHERE r.case_id = "101"
RETURN type(r) AS type, count(r) AS count
ORDER BY type;
```

This verifies the underlying graph independently of the React visualization.

## Current MVP Scope

The MVP focuses on proving:

```text
ONE INVESTIGATION
      |
      v
REAL INGESTION
      |
      v
REAL EXTRACTION
      |
      v
REAL ENTITY RESOLUTION
      |
      v
REAL NEO4J GRAPH
      |
      v
REAL GRAPH API
      |
      v
REAL FRONTEND VISUALIZATION
```

The project intentionally prioritizes a working end-to-end system over a large number of incomplete features.

## Not Yet Implemented / Future Work

- [ ] Large historical case repository
- [ ] Full cross-case intelligence
- [ ] Hidden bridge detection
- [ ] Advanced graph centrality/community analysis
- [ ] Natural-language investigation queries / GraphRAG
- [ ] Advanced evidence exploration
- [ ] Timeline analytics
- [ ] Production authentication / RBAC
- [ ] Production cloud deployment
- [ ] Integration with authorized government data systems

These are future extensions and are not claimed as completed MVP functionality.

## Data and Privacy

This project uses synthetic investigation data.

It does not claim access to:

- CCTNS
- ICJS
- police CDR systems
- bank databases
- confidential FIR repositories
- restricted government investigation systems

The architecture is designed so that authorized data sources could potentially be integrated in a future production environment.

No real criminal or personally sensitive investigation records should be used for development or demonstration.

## Design Principle

The system is designed as an investigative decision-support tool.

It is intended to surface:

- observed relationships
- potential connections
- source evidence
- network structure
- investigative leads

It does not determine guilt or replace human investigation and decision-making.

## Development Stages

The system was developed incrementally:

```text
Stage 0  -> Project / infrastructure skeleton
Stage 1  -> Synthetic seed dataset
Stage 2  -> Neo4j schema
Stage 3  -> Data ingestion and parsing
Stage 4  -> Entity extraction
Stage 5  -> Relationship extraction
Stage 6  -> Entity resolution
Stage 7  -> Graph construction
Stage 8  -> Graph read APIs
Stage 9  -> Frontend investigation interface
Stage 10 -> Network visualization
Stage 11 -> Entity details and source references
```

The current repository represents the completed working portion of this vertical slice.

## Technology Stack

### Frontend

- React
- Vite
- JavaScript
- React Force Graph

### Backend

- Python
- FastAPI
- Pydantic

### Graph Database

- Neo4j

### Infrastructure

- Docker
- Docker Compose

### Processing

- Deterministic parsing
- Rule-based entity extraction
- Deterministic relationship extraction
- Normalized entity resolution

## Project Status

**Working MVP / End-to-end vertical slice**

The core system has been verified from source ingestion through graph construction and graph visualization.

The current focus is on presentation, documentation, deployment, and demonstrating the implemented pipeline clearly rather than adding large amounts of unfinished functionality.

## Disclaimer

This is an academic/hackathon prototype developed to demonstrate a criminal-network analysis concept using synthetic data.

It is not a production law-enforcement system and should not be used to make real-world enforcement decisions.
