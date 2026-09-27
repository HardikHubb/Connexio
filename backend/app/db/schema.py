"""
Stage 2: the graph schema, expressed as executable Cypher rather than a
diagram someone has to keep in sync by hand.

This is the contract every later stage writes against:
  - Stage 7 (graph write) relies on these uniqueness constraints to make
    MERGE safe (so re-ingesting the same phone/account/vehicle doesn't
    create duplicate nodes).
  - Stage 6 (entity resolution) relies on the full-text index on
    Person.name to do fuzzy candidate lookup instead of scanning every
    node.
  - Stage 13/14 (cross-case, temporal) rely on the relationship property
    indexes to keep those queries fast once the historical repository
    (Stage 12) is loaded.

Node identity convention used throughout the project:
  Person.id, Location.id, Event.id   -> app-generated UUID string
  Phone.number                       -> the phone number itself is the key
  Account.account_number             -> the account number itself is the key
  Vehicle.registration_number        -> the plate number itself is the key
  Organization.name                  -> the name itself is the key
  Case.case_id                       -> human-facing case identifier (e.g. "101")

Relationship provenance convention (set on every relationship, every stage):
  source_id, source_type, timestamp, confidence, evidence_snippet
"""

# --- Uniqueness constraints (also creates a backing index automatically) ---
CONSTRAINTS = [
    "CREATE CONSTRAINT person_id_unique IF NOT EXISTS "
    "FOR (p:Person) REQUIRE p.id IS UNIQUE",

    "CREATE CONSTRAINT phone_number_unique IF NOT EXISTS "
    "FOR (ph:Phone) REQUIRE ph.number IS UNIQUE",

    "CREATE CONSTRAINT account_number_unique IF NOT EXISTS "
    "FOR (a:Account) REQUIRE a.account_number IS UNIQUE",

    "CREATE CONSTRAINT vehicle_reg_unique IF NOT EXISTS "
    "FOR (v:Vehicle) REQUIRE v.registration_number IS UNIQUE",

    "CREATE CONSTRAINT location_id_unique IF NOT EXISTS "
    "FOR (l:Location) REQUIRE l.id IS UNIQUE",

    "CREATE CONSTRAINT organization_name_unique IF NOT EXISTS "
    "FOR (o:Organization) REQUIRE o.name IS UNIQUE",

    "CREATE CONSTRAINT case_id_unique IF NOT EXISTS "
    "FOR (c:Case) REQUIRE c.case_id IS UNIQUE",

    "CREATE CONSTRAINT event_id_unique IF NOT EXISTS "
    "FOR (e:Event) REQUIRE e.id IS UNIQUE",
]

# --- Property indexes for lookups the app will do constantly ---
INDEXES = [
    # Exact-ish lookup support (e.g. "find case by status")
    "CREATE INDEX case_status_idx IF NOT EXISTS "
    "FOR (c:Case) ON (c.status)",

    "CREATE INDEX location_name_idx IF NOT EXISTS "
    "FOR (l:Location) ON (l.name)",

    # Relationship property indexes — needed for Stage 14 temporal queries
    # and to keep cross-case lookups fast once many cases are loaded.
    "CREATE INDEX called_timestamp_idx IF NOT EXISTS "
    "FOR ()-[r:CALLED]-() ON (r.timestamp)",

    "CREATE INDEX transferred_timestamp_idx IF NOT EXISTS "
    "FOR ()-[r:TRANSFERRED_TO]-() ON (r.timestamp)",

    "CREATE INDEX seen_at_timestamp_idx IF NOT EXISTS "
    "FOR ()-[r:SEEN_AT]-() ON (r.timestamp)",

    "CREATE INDEX involved_in_case_idx IF NOT EXISTS "
    "FOR ()-[r:INVOLVED_IN]-() ON (r.confidence)",
]

# --- Full-text index for fuzzy name lookup (Stage 6 entity resolution) ---
FULLTEXT_INDEXES = [
    "CREATE FULLTEXT INDEX person_name_fts IF NOT EXISTS "
    "FOR (p:Person) ON EACH [p.name]",
]

ALL_SCHEMA_STATEMENTS = CONSTRAINTS + INDEXES + FULLTEXT_INDEXES


def apply_schema(run_query_fn) -> list[str]:
    """
    Applies every constraint/index statement. Idempotent — safe to run
    every time the app starts, not just once — because every statement
    uses IF NOT EXISTS.

    `run_query_fn` is injected (rather than imported directly) so this
    module has no hard dependency on how the driver is wired — makes it
    trivial to unit-test with a fake later if we want to.
    """
    applied = []
    for statement in ALL_SCHEMA_STATEMENTS:
        run_query_fn(statement)
        applied.append(statement)
    return applied


def get_schema_info(run_query_fn) -> dict:
    """Returns what Neo4j actually has registered right now, for verification."""
    constraints = run_query_fn("SHOW CONSTRAINTS")
    indexes = run_query_fn("SHOW INDEXES")
    return {"constraints": constraints, "indexes": indexes}
