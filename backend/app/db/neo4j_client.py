"""
Single shared Neo4j driver for the whole app.

Every later stage (schema, graph writes, read APIs, analytics, cross-case
queries) should go through `run_query()` or `get_driver()` here rather than
opening its own connection — this is the one real dependency the rest of
the pipeline is built on, so it's worth keeping in one place.
"""

import logging
from neo4j import GraphDatabase, Driver

from app.config import settings

logger = logging.getLogger("neo4j_client")

_driver: Driver | None = None


def get_driver() -> Driver:
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
    return _driver


def close_driver() -> None:
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None


def verify_connectivity() -> tuple[bool, str]:
    """Returns (ok, message). Used by /health and by startup logging."""
    try:
        driver = get_driver()
        driver.verify_connectivity()
        return True, "connected"
    except Exception as exc:  # noqa: BLE001 — we want to report any failure reason
        logger.warning("Neo4j connectivity check failed: %s", exc)
        return False, str(exc)


def run_query(cypher: str, parameters: dict | None = None) -> list[dict]:
    """
    Thin helper for later stages: runs a Cypher query against the
    configured database and returns a list of plain dicts (one per record).
    """
    driver = get_driver()
    with driver.session(database=settings.neo4j_database) as session:
        result = session.run(cypher, parameters or {})
        return [record.data() for record in result]
