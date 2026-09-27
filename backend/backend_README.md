# SIH26189 Backend

The backend is the processing and graph layer of the SIH26189 Criminal Network Analysis System.

It provides the real pipeline that takes investigation records, parses them, extracts entities and relationships, resolves repeated entity mentions, writes the resulting graph to Neo4j, and exposes the graph through FastAPI APIs.

> **Data note:** The prototype uses realistic synthetic investigation data. It does not use or claim access to confidential police or government data.

---

## Backend Architecture

```text
Investigation Files
        |
        v
   Ingestion Service
        |
        v
      Parsers
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
   Graph Write Service
        |
        v
      Neo4j
        |
        v
   Graph Read APIs
        |
        v
     Frontend
```

The backend is therefore responsible for the actual data-processing and graph operations. The React frontend consumes the APIs exposed here.

---

## Current Pipeline

### 1. Ingestion

Investigation files are received through the FastAPI ingestion endpoint.

The ingestion layer:

- validates the case
- saves the raw source file
- determines the document format
- parses the document
- stores the parsed representation
- registers the source against the case

Supported source types currently include:

- `FIR`
- `CDR`
- `TRANSACTION`
- `VEHICLE`
- `LOCATION`
- `REPORT`

---

### 2. Parsing

The parsing layer converts source files into a common `ParsedDocument` representation.

Current parsers include:

```text
services/parsers/
├── text_parser.py
└── csv_parser.py
```

Text-based records such as FIRs and reports are represented as parsed text.

Tabular sources such as CDR, transaction, and vehicle records are represented as structured rows.

---

### 3. Entity Extraction

The extraction stage converts parsed documents into structured entities.

Current entity types:

```text
PERSON
PHONE
ACCOUNT
VEHICLE
LOCATION
ORGANIZATION
```

Each extracted entity can preserve:

- entity type
- original value
- normalized value
- case ID
- source ID
- evidence
- timestamp when available
- confidence

The implementation currently uses deterministic/rule-based extraction appropriate for the synthetic MVP dataset.

---

### 4. Relationship Extraction

Relationships are generated from the parsed document and extracted entities.

Current relationship types include:

```text
CALLED
TRANSFERRED_TO
OWNS
USES
SEEN_AT
LOCATED_AT
VISITED
IDENTIFIED_AS
MENTIONED_IN
```

Relationships preserve provenance information such as:

- case ID
- source ID
- evidence
- timestamp when available
- confidence

The relationship stage does not write to Neo4j directly. Graph persistence is handled separately by the graph service.

---

### 5. Entity Resolution

The current resolver performs conservative deterministic matching using normalized entity values.

For example, repeated mentions of the same normalized phone number can resolve to the same canonical entity.

Canonical entities maintain:

- canonical ID
- entity type
- canonical value
- normalized value
- aliases
- source IDs
- mention count

The current implementation does not perform unrestricted fuzzy matching or cross-case identity inference.

---

### 6. Graph Construction

The graph write service converts the resolved entities and extracted relationships into Neo4j nodes and relationships.

The graph contains entity labels such as:

```text
Person
Phone
Account
Vehicle
Location
Organization
```

Case information is also represented in the graph.

Neo4j is the actual persistence layer. The frontend does not contain a substitute/mock copy of the graph.

---

# Neo4j

Neo4j runs locally through Docker Compose.

From the project root:

```bash
docker compose up -d
```

Default development endpoints:

```text
Neo4j Browser
http://localhost:7474

Bolt
bolt://localhost:7687
```

Development credentials:

```text
Username: neo4j
Password: testpassword123
```

> These credentials are for local development only.

---

## Neo4j Schema

The backend contains the graph schema in:

```text
app/db/schema.py
```

The schema includes:

- node uniqueness constraints
- property indexes
- relationship indexes
- Person full-text index

Apply the schema with:

```bash
cd backend
python scripts/init_schema.py
```

The operation is idempotent and can safely be run again.

Verify:

```text
http://localhost:8000/api/schema
```

Or directly in Neo4j Browser:

```cypher
SHOW CONSTRAINTS;
```

```cypher
SHOW INDEXES;
```

---

# FastAPI

The backend is built with FastAPI.

Start it from the backend directory:

```bash
uvicorn app.main:app --reload --port 8000
```

API:

```text
http://localhost:8000
```

Swagger documentation:

```text
http://localhost:8000/docs
```

---

## API Endpoints

### Health

```http
GET /api/health
```

Checks backend and Neo4j connectivity.

The Neo4j status is based on an actual connectivity check rather than a hardcoded response.

### Cases

```http
GET /api/cases
POST /api/cases
GET /api/cases/{case_id}
```

### Ingestion

```http
POST /api/cases/{case_id}/ingest
```

Accepts a source type and uploaded file.

### Documents

```http
GET /api/cases/{case_id}/documents
GET /api/cases/{case_id}/documents/{source_id}
```

### Graph

```http
GET /api/cases/{case_id}/network
GET /api/entities/{entity_id}
```

### Schema

```http
GET /api/schema
```

---

# Backend Project Structure

```text
backend/
│
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── cases.py
│   │   ├── graph.py
│   │   ├── health.py
│   │   └── schema.py
│   │
│   ├── db/
│   │   ├── __init__.py
│   │   ├── neo4j_client.py
│   │   └── schema.py
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py
│   │
│   └── services/
│       ├── __init__.py
│       ├── case_service.py
│       ├── ingestion_service.py
│       │
│       ├── parsers/
│       │   ├── __init__.py
│       │   ├── csv_parser.py
│       │   └── text_parser.py
│       │
│       ├── extraction/
│       │   ├── ...
│       │
│       ├── relationship/
│       │   ├── ...
│       │
│       ├── resolution/
│       │   ├── ...
│       │
│       └── graph/
│           ├── ...
│
├── scripts/
│   ├── init_schema.py
│   └── run_stage7.py
│
├── seed_data/
│   └── case_101/
│
├── storage/
│   └── 101/
│
├── requirements.txt
└── README.md
```

`storage/` is runtime-generated and contains raw uploads and parsed case data.

---

# Local Setup

## Prerequisites

- Python 3.11+
- Docker
- Docker Compose
- Neo4j through the supplied Docker configuration

Create the environment:

```bash
python -m venv .venv
```

Windows:

```powershell
.venv\Scripts\activate
```

Linux/macOS:

```bash
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

Make sure the Neo4j credentials match the Docker configuration.

---

# Load the Seed Investigation

The current MVP uses synthetic Case 101 to verify the pipeline.

From the backend directory:

```bash
python scripts/ingest_seed_data.py
```

The data is processed through the real ingestion/parsing path.

Verify:

```text
GET /api/cases
```

and:

```text
GET /api/cases/101/documents
```

---

# Stage 7 — Graph Write Verification

The graph-writing stage can be executed with:

```bash
python -m scripts.run_stage7 101
```

A successful run currently produces approximately:

```text
Parsed documents: 4
Extracted mentions: 58
Canonical entities: 27
Entities written: 27
Relationships written: 26
```

These values correspond to the current synthetic Case 101 dataset.

---

# Inspecting Neo4j Directly

The graph can be inspected independently of the frontend.

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

Inspect Case 101 relationships:

```cypher
MATCH ()-[r]->()
WHERE r.case_id = "101"
RETURN type(r) AS type, count(r) AS count
ORDER BY type;
```

This is useful when debugging or verifying that graph data was actually written to Neo4j.

---

# Backend Responsibilities

The backend intentionally keeps the following concerns separate:

```text
API Layer
   |
   v
Service Layer
   |
   +--> Ingestion
   +--> Parsing
   +--> Extraction
   +--> Relationship Extraction
   +--> Resolution
   +--> Graph
   |
   v
Neo4j
```

This allows each processing stage to be tested independently before data is persisted to the graph.

---

# Current Backend MVP

Implemented:

- [x] FastAPI application
- [x] Neo4j connectivity
- [x] Docker-based Neo4j
- [x] Neo4j schema
- [x] Case management
- [x] File ingestion
- [x] Text parsing
- [x] CSV parsing
- [x] Entity extraction
- [x] Relationship extraction
- [x] Deterministic entity resolution
- [x] Graph writing
- [x] Graph read APIs
- [x] Entity detail API
- [x] Seed investigation
- [x] Source/provenance preservation

Future work:

- [ ] Cross-case analysis
- [ ] Hidden bridge detection
- [ ] Advanced graph analytics
- [ ] Natural-language graph queries
- [ ] GraphRAG
- [ ] Production authentication/RBAC
- [ ] Production deployment
- [ ] Authorized external data integrations

---

# Data and Privacy

The current data is synthetic.

The backend does not connect to:

- CCTNS
- ICJS
- police CDR infrastructure
- banking systems
- confidential FIR repositories
- restricted government databases

The system is designed so that authorized data sources could potentially be integrated later.

Do not use real confidential investigation records in this development setup.

---

# Backend Status

**Working MVP backend / real graph-processing pipeline**

The backend currently demonstrates the core path:

```text
Synthetic Investigation Data
        |
        v
Real Ingestion
        |
        v
Real Parsing
        |
        v
Real Entity Extraction
        |
        v
Real Relationship Extraction
        |
        v
Real Entity Resolution
        |
        v
Real Neo4j Graph
        |
        v
FastAPI Graph API
```

The React frontend is only one consumer of these APIs; the underlying graph-processing pipeline can be inspected and verified independently through the backend and Neo4j.
