"""
Run this once after Neo4j is up to create all constraints/indexes:

    cd backend
    source .venv/bin/activate
    python scripts/init_schema.py

Safe to re-run any time (every statement is IF NOT EXISTS) — running it
again after Stage 3+ adds more indexes just adds the new ones.
"""

import sys
from pathlib import Path

# Allow `python scripts/init_schema.py` to find the `app` package without
# needing PYTHONPATH set manually.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.neo4j_client import run_query, verify_connectivity  # noqa: E402
from app.db.schema import apply_schema, get_schema_info  # noqa: E402


def main():
    ok, message = verify_connectivity()
    if not ok:
        print(f"Cannot reach Neo4j: {message}")
        print("Check that `docker compose up -d` is running and backend/.env matches docker-compose.yml.")
        sys.exit(1)

    print("Connected to Neo4j. Applying schema...")
    applied = apply_schema(run_query)
    print(f"Applied {len(applied)} constraint/index statements:")
    for statement in applied:
        print(f"  - {statement.splitlines()[0]}")

    print("\nVerifying against Neo4j...")
    info = get_schema_info(run_query)
    print(f"Neo4j now reports {len(info['constraints'])} constraints and {len(info['indexes'])} indexes.")


if __name__ == "__main__":
    main()
