"""
Stage 0 entrypoint. This file should stay small as the app grows —
each later stage adds its own router under app/api/ and gets included
here, rather than everything being piled into this one file.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api import cases, health, schema
from app.api import graph

app = FastAPI(
    title="SIH26189 — Criminal Network Analysis API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(schema.router, prefix="/api", tags=["schema"])
app.include_router(cases.router, prefix="/api", tags=["cases"])
app.include_router(graph.router, prefix="/api", tags=["graph"])


@app.get("/")
def root():
    return {"service": "sih26189-backend", "status": "running"}
