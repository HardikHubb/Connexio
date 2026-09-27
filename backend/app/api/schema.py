from fastapi import APIRouter

from app.db.neo4j_client import run_query
from app.db.schema import get_schema_info

router = APIRouter()


@router.get("/schema")
def schema_status():
    """
    Returns the constraints/indexes Neo4j actually has right now — this
    calls SHOW CONSTRAINTS / SHOW INDEXES for real, so an empty result
    here genuinely means `python scripts/init_schema.py` hasn't been run
    yet, not a stubbed response.
    """
    info = get_schema_info(run_query)
    return {
        "constraint_count": len(info["constraints"]),
        "index_count": len(info["indexes"]),
        "constraints": info["constraints"],
        "indexes": info["indexes"],
    }
