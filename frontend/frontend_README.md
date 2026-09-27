# SIH26189 Frontend

The frontend is the investigator-facing interface for the SIH26189 Criminal Network Analysis System.

It is built with React and Vite and consumes the FastAPI backend to display investigation data and the graph stored in Neo4j.

> The frontend does not contain the source of truth for the investigation graph. Network data is retrieved from the backend API, which reads from Neo4j.

---

## Frontend Architecture

```text
                    React Frontend
                          |
              -------------------------
              |           |           |
           Overview     Add Data    Network
                                      |
                                      v
                              FastAPI Backend
                                      |
                                      v
                                    Neo4j
```

The frontend is responsible for presentation and interaction.

The backend is responsible for processing, graph construction, and graph retrieval.

---

# Current Frontend MVP

The current interface includes:

- [x] Investigation overview
- [x] Case context
- [x] Add Data interface
- [x] File upload interaction
- [x] Investigation network page
- [x] Interactive graph visualization
- [x] Entity selection
- [x] Entity detail panel
- [x] Entity properties
- [x] Source references
- [x] Graph fit/reset interaction
- [x] Backend API integration
- [x] Neo4j-backed graph visualization

The graph is not generated from a hardcoded frontend dataset.

The frontend requests:

```text
GET /api/cases/{case_id}/network
```

and renders the response returned by the backend.

---

# Frontend Data Flow

```text
User
 |
 v
React UI
 |
 v
API Client
 |
 v
FastAPI
 |
 v
Neo4j
 |
 v
Graph JSON
 |
 v
React Force Graph
 |
 v
Interactive Investigation Network
```

For entity details:

```text
User clicks node
       |
       v
GET /api/entities/{entity_id}
       |
       v
FastAPI
       |
       v
Neo4j
       |
       v
Entity properties
       |
       v
Detail panel
```

---

# Technology Stack

### Core

- React
- Vite
- JavaScript

### Graph Visualization

- `react-force-graph-2d`

### API Communication

- Browser Fetch API
- Shared API client

---

# Project Structure

```text
frontend/
│
├── .env.example
├── index.html
├── package.json
├── vite.config.js
│
└── src/
    ├── App.jsx
    ├── main.jsx
    │
    ├── api/
    │   └── client.js
    │
    ├── components/
    │   ├── Sidebar.jsx
    │   └── AddData.jsx
    │
    └── pages/
        ├── Overview.jsx
        └── Network.jsx
```

---

# API Client

The shared API layer is:

```text
src/api/client.js
```

It provides frontend functions for:

- listing cases
- retrieving a case
- retrieving a case network
- retrieving entity details
- uploading case files

The API base URL is controlled through:

```text
VITE_API_BASE_URL
```

If it is not specified, the current development default is:

```text
http://127.0.0.1:8000
```

---

# Local Setup

## Prerequisites

- Node.js 18+
- npm
- Running SIH26189 FastAPI backend

From the frontend directory:

```bash
npm install
```

Create the environment file.

Windows:

```powershell
copy .env.example .env
```

Linux/macOS:

```bash
cp .env.example .env
```

For local development, the API should point to:

```text
http://127.0.0.1:8000
```

---

# Run the Frontend

```bash
npm run dev
```

Open:

```text
http://localhost:5173
```

The backend should be running separately:

```text
http://localhost:8000
```

Neo4j should also be running through Docker:

```bash
docker compose up -d
```

---

# Build for Production

Create a production build:

```bash
npm run build
```

Vite outputs the production files into:

```text
dist/
```

Preview the production build locally:

```bash
npm run preview
```

---

# Graph Visualization

The investigation network uses:

```text
react-force-graph-2d
```

The graph receives nodes and relationships from the backend.

Each graph node is derived from backend properties such as:

- canonical ID
- entity type
- number
- account number
- vehicle registration
- name
- normalized value
- aliases
- source IDs
- mention count

Relationships are derived from the backend graph response.

The graph supports:

- pan
- zoom
- node selection
- relationship direction indicators
- automatic graph fitting
- entity detail inspection

---

# Entity Details

Clicking an entity requests its details from the backend.

The detail panel can display:

- entity type
- canonical ID
- entity value
- case
- mention count
- aliases
- source IDs

This information comes from the backend response rather than being independently hardcoded into the graph UI.

---

# Current Case

The current development/demo dataset includes:

```text
Case 101
```

The case is backed by the synthetic investigation data processed by the backend.

The current graph returned by the backend contains approximately:

```text
27 entities
24 returned graph edges
```

These values describe the current development dataset and are not performance metrics.

---

# Frontend and Backend Must Both Be Running

The frontend alone does not contain the complete application.

For the local MVP:

```text
Docker
  |
  +--> Neo4j
         |
         v
      FastAPI
         |
         v
      React
```

Start Neo4j:

```bash
docker compose up -d
```

Start FastAPI:

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

Start React:

```bash
cd frontend
npm run dev
```

Then open:

```text
http://localhost:5173
```

---

# Deployment Note

GitHub Pages can host the built React frontend because it is a static Vite application.

However, GitHub Pages does not host the FastAPI backend or Neo4j database.

Therefore a public deployment requires:

```text
GitHub Pages
      |
      v
React Frontend
      |
      v
Public FastAPI Backend
      |
      v
Hosted Neo4j
```

For local development, all three layers can run on the developer machine.

Do not put backend secrets or Neo4j credentials into the frontend environment.

---

# Frontend Responsibilities

The frontend intentionally focuses on:

- presenting investigation context
- accepting user interaction
- uploading data through the API
- visualizing the graph
- allowing entity exploration
- displaying source references

It does not perform the core graph construction itself.

The actual pipeline remains in the backend:

```text
Ingestion
   |
Parsing
   |
Entity Extraction
   |
Relationship Extraction
   |
Entity Resolution
   |
Neo4j
```

---

# Current Frontend MVP vs Future Work

Implemented:

- [x] React/Vite application
- [x] Backend API integration
- [x] Case overview
- [x] Add Data interface
- [x] Network visualization
- [x] Real Neo4j-backed graph display
- [x] Entity selection
- [x] Entity details
- [x] Source references
- [x] Responsive graph sizing
- [x] Graph fit controls

Future UI work:

- [ ] Cross-case investigation page
- [ ] Advanced evidence drawer
- [ ] Timeline interface
- [ ] Cross-case connection visualization
- [ ] Natural-language investigation interface
- [ ] Advanced graph filtering
- [ ] Production authentication
- [ ] Production deployment

---

# Design Principle

The frontend is intended to be:

- simple
- dark/analytical
- professional
- investigator-oriented
- visually clear
- explainable
- demo-friendly

The interface should communicate investigation information without exposing unnecessary internal implementation details.

The frontend should present relationships and investigative leads as information to support human investigation, not as determinations of guilt.

---

# Frontend Status

**Working MVP interface**

The frontend currently provides a functional visualization layer over the implemented backend and Neo4j graph pipeline.

The important distinction is:

```text
Frontend
    = visualization + interaction

Backend
    = processing + API

Neo4j
    = graph persistence
```

The frontend therefore does not claim to implement the criminal-network analysis pipeline by itself.
