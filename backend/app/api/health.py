from fastapi import APIRouter

from app.db.neo4j_client import verify_connectivity

router = APIRouter()


@router.get("/health")
def health():
    """
    Real check, not a stub: actually pings Neo4j over the Bolt driver.
    The frontend skeleton calls this on load to prove the whole chain
    (React -> FastAPI -> Neo4j) is wired correctly before any pipeline
    code exists.
    """
    neo4j_ok, neo4j_message = verify_connectivity()
    return {
        "api": "ok",
        "neo4j": "ok" if neo4j_ok else "unreachable",
        "neo4j_detail": neo4j_message,
    }
