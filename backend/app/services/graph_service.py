"""
Stage 7 - Neo4j Graph Writer

Takes Stage 6 resolved entities and Stage 5 extracted relationships
and writes them into the existing Neo4j database.

Responsibilities:
- create/update canonical entity nodes
- create Case node
- create provenance-preserving relationships
- remain idempotent when the same data is written again

This module does NOT:
- perform entity extraction
- perform entity resolution
- perform cross-case analysis
- calculate graph analytics
"""

from app.db.neo4j_client import run_query
from app.models.schemas import (
    EntityType,
    EntityResolutionResult,
    ExtractedRelationship,
    RelationshipExtractionResult,
    ResolvedEntity,
)


# ---------------------------------------------------------------------------
# Entity type -> Neo4j label
# ---------------------------------------------------------------------------

ENTITY_LABELS = {
    EntityType.PERSON: "Person",
    EntityType.PHONE: "Phone",
    EntityType.ACCOUNT: "Account",
    EntityType.VEHICLE: "Vehicle",
    EntityType.LOCATION: "Location",
    EntityType.ORGANIZATION: "Organization",
}


# ---------------------------------------------------------------------------
# Entity type -> Neo4j identity property
#
# These match the Stage 2 Neo4j schema.
# ---------------------------------------------------------------------------

ENTITY_ID_PROPERTIES = {
    EntityType.PERSON: "id",
    EntityType.PHONE: "number",
    EntityType.ACCOUNT: "account_number",
    EntityType.VEHICLE: "registration_number",
    EntityType.LOCATION: "id",
    EntityType.ORGANIZATION: "name",
}


# ---------------------------------------------------------------------------
# Relationship type whitelist
#
# Relationship types cannot safely be passed as ordinary Cypher parameters,
# so only values from our controlled enum are allowed here.
# ---------------------------------------------------------------------------

ALLOWED_RELATIONSHIP_TYPES = {
    "CALLED",
    "TRANSFERRED_TO",
    "OWNS",
    "USES",
    "SEEN_AT",
    "LOCATED_AT",
    "VISITED",
    "IDENTIFIED_AS",
    "MENTIONED_IN",
}


# ---------------------------------------------------------------------------
# Node identity value
# ---------------------------------------------------------------------------

def _node_identity_value(entity: ResolvedEntity) -> str:
    """
    Return the value used by the Stage 2 Neo4j uniqueness constraint.
    """

    if entity.entity_type in (
        EntityType.PERSON,
        EntityType.LOCATION,
    ):
        return entity.canonical_id

    if entity.entity_type == EntityType.PHONE:
        return entity.normalized_value

    if entity.entity_type == EntityType.ACCOUNT:
        return entity.normalized_value

    if entity.entity_type == EntityType.VEHICLE:
        return entity.normalized_value

    if entity.entity_type == EntityType.ORGANIZATION:
        return entity.canonical_value

    raise ValueError(
        f"Unsupported entity type: {entity.entity_type}"
    )


# ---------------------------------------------------------------------------
# Node properties
# ---------------------------------------------------------------------------

def _node_properties(entity: ResolvedEntity) -> dict:
    """
    Properties stored on every graph node.

    We intentionally keep:
    - canonical identity
    - normalized value
    - original aliases
    - source provenance
    - case information
    """

    properties = {
        "canonical_id": entity.canonical_id,
        "canonical_value": entity.canonical_value,
        "normalized_value": entity.normalized_value,
        "case_id": entity.case_id,
        "aliases": entity.aliases,
        "source_ids": entity.source_ids,
        "mention_count": entity.mention_count,
    }

    if entity.entity_type == EntityType.PERSON:
        properties["id"] = entity.canonical_id
        properties["name"] = entity.canonical_value

    elif entity.entity_type == EntityType.PHONE:
        properties["number"] = entity.normalized_value

    elif entity.entity_type == EntityType.ACCOUNT:
        properties["account_number"] = entity.normalized_value

    elif entity.entity_type == EntityType.VEHICLE:
        properties["registration_number"] = entity.normalized_value

    elif entity.entity_type == EntityType.LOCATION:
        properties["id"] = entity.canonical_id
        properties["name"] = entity.canonical_value

    elif entity.entity_type == EntityType.ORGANIZATION:
        properties["name"] = entity.canonical_value

    return properties


# ---------------------------------------------------------------------------
# Create/update Case node
# ---------------------------------------------------------------------------

def _write_case(case_id: str) -> None:

    run_query(
        """
        MERGE (c:Case {case_id: $case_id})
        ON CREATE SET
            c.created_by = 'stage7',
            c.status = 'active'
        SET
            c.updated_by = 'stage7'
        """,
        {
            "case_id": case_id,
        },
    )


# ---------------------------------------------------------------------------
# Write one resolved entity
# ---------------------------------------------------------------------------

def _write_entity(
    entity: ResolvedEntity,
) -> None:

    label = ENTITY_LABELS.get(entity.entity_type)

    if not label:
        raise ValueError(
            f"Unsupported entity type: {entity.entity_type}"
        )

    identity_property = ENTITY_ID_PROPERTIES[
        entity.entity_type
    ]

    identity_value = _node_identity_value(entity)

    properties = _node_properties(entity)

    query = f"""
        MERGE (n:{label} {{{identity_property}: $identity_value}})

        SET
            n.canonical_id = $canonical_id,
            n.canonical_value = $canonical_value,
            n.normalized_value = $normalized_value,
            n.case_id = $case_id,
            n.aliases = $aliases,
            n.source_ids = $source_ids,
            n.mention_count = $mention_count
    """

    # Person / Location / Organization have additional display properties.
    if entity.entity_type == EntityType.PERSON:
        query += "\nSET n.id = $id, n.name = $name"

    elif entity.entity_type == EntityType.LOCATION:
        query += "\nSET n.id = $id, n.name = $name"

    elif entity.entity_type == EntityType.ORGANIZATION:
        query += "\nSET n.name = $name"

    elif entity.entity_type == EntityType.PHONE:
        query += "\nSET n.number = $number"

    elif entity.entity_type == EntityType.ACCOUNT:
        query += "\nSET n.account_number = $account_number"

    elif entity.entity_type == EntityType.VEHICLE:
        query += "\nSET n.registration_number = $registration_number"

    parameters = {
        "identity_value": identity_value,
        "canonical_id": properties["canonical_id"],
        "canonical_value": properties["canonical_value"],
        "normalized_value": properties["normalized_value"],
        "case_id": properties["case_id"],
        "aliases": properties["aliases"],
        "source_ids": properties["source_ids"],
        "mention_count": properties["mention_count"],
    }

    if entity.entity_type in (
        EntityType.PERSON,
        EntityType.LOCATION,
    ):
        parameters["id"] = entity.canonical_id
        parameters["name"] = entity.canonical_value

    elif entity.entity_type == EntityType.ORGANIZATION:
        parameters["name"] = entity.canonical_value

    elif entity.entity_type == EntityType.PHONE:
        parameters["number"] = entity.normalized_value

    elif entity.entity_type == EntityType.ACCOUNT:
        parameters["account_number"] = entity.normalized_value

    elif entity.entity_type == EntityType.VEHICLE:
        parameters["registration_number"] = entity.normalized_value

    run_query(query, parameters)


# ---------------------------------------------------------------------------
# Resolve a Stage 5 relationship endpoint to canonical ID
# ---------------------------------------------------------------------------

def _mapping_key(
    entity_type: EntityType,
    normalized_value: str,
) -> str:

    return (
        f"{entity_type.value}:"
        f"{normalized_value}"
    )


def _canonical_id_for_endpoint(
    entity_type: EntityType,
    normalized_value: str,
    resolution_result: EntityResolutionResult,
) -> str:

    key = _mapping_key(
        entity_type,
        normalized_value,
    )

    canonical_id = resolution_result.entity_mappings.get(key)

    if not canonical_id:
        raise ValueError(
            "Could not resolve relationship endpoint: "
            f"{key}"
        )

    return canonical_id


# ---------------------------------------------------------------------------
# Relationship node matching
# ---------------------------------------------------------------------------

def _match_clause(
    variable: str,
    entity_type: EntityType,
) -> str:

    label = ENTITY_LABELS.get(entity_type)

    if not label:
        raise ValueError(
            f"Unsupported entity type: {entity_type}"
        )

    if entity_type in (
        EntityType.PERSON,
        EntityType.LOCATION,
    ):
        return (
            f"MATCH ({variable}:{label} {{id: "
            f"${variable}_id}})"
        )

    if entity_type == EntityType.PHONE:
        return (
            f"MATCH ({variable}:{label} {{number: "
            f"${variable}_id}})"
        )

    if entity_type == EntityType.ACCOUNT:
        return (
            f"MATCH ({variable}:{label} {{account_number: "
            f"${variable}_id}})"
        )

    if entity_type == EntityType.VEHICLE:
        return (
            f"MATCH ({variable}:{label} {{registration_number: "
            f"${variable}_id}})"
        )

    if entity_type == EntityType.ORGANIZATION:
        return (
            f"MATCH ({variable}:{label} {{name: "
            f"${variable}_id}})"
        )

    raise ValueError(
        f"Unsupported entity type: {entity_type}"
    )


# ---------------------------------------------------------------------------
# Write one relationship
# ---------------------------------------------------------------------------

def _write_relationship(
    relationship: ExtractedRelationship,
    resolution_result: EntityResolutionResult,
) -> None:

    relationship_type = relationship.relationship_type.value

    if relationship_type not in ALLOWED_RELATIONSHIP_TYPES:
        raise ValueError(
            f"Relationship type {relationship_type!r} "
            "is not allowed."
        )

    from_id = _canonical_id_for_endpoint(
        relationship.from_entity_type,
        relationship.from_normalized_value,
        resolution_result,
    )

    to_id = _canonical_id_for_endpoint(
        relationship.to_entity_type,
        relationship.to_normalized_value,
        resolution_result,
    )

    from_match = _match_clause(
        "source",
        relationship.from_entity_type,
    )

    to_match = _match_clause(
        "target",
        relationship.to_entity_type,
    )

    query = f"""
        {from_match}
        {to_match}

        MERGE (
            source
        )-[r:{relationship_type} {{
            source_id: $source_id,
            timestamp: $timestamp,
            evidence_snippet: $evidence_snippet
        }}]->(
            target
        )

        SET
            r.source_type = $source_type,
            r.confidence = $confidence
    """

    parameters = {
        "source_id": relationship.source_id,
        "timestamp": relationship.timestamp or "",
        "evidence_snippet": relationship.evidence,
        "source_type": relationship.source_type.value,
        "confidence": relationship.confidence,
        "source_id": from_id,
        "target_id": to_id,
    }

    run_query(query, parameters)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def write_case_graph(
    case_id: str,
    resolution_result: EntityResolutionResult,
    relationship_results: list[RelationshipExtractionResult],
) -> dict:
    """
    Write one complete resolved case into Neo4j.

    The operation is intentionally idempotent:
    running it again with the same inputs should reuse existing nodes
    and relationships rather than blindly creating duplicates.
    """

    if resolution_result.case_id != case_id:
        raise ValueError(
            "Resolution result belongs to a different case."
        )

    _write_case(case_id)

    # ---------------------------------------------------------------
    # Nodes
    # ---------------------------------------------------------------

    for entity in resolution_result.entities:
        _write_entity(entity)

    # ---------------------------------------------------------------
    # Relationships
    # ---------------------------------------------------------------

    relationship_count = 0

    for result in relationship_results:

        if result.case_id != case_id:
            raise ValueError(
                "Relationship result belongs to a different case."
            )

        for relationship in result.relationships:

            _write_relationship(
                relationship,
                resolution_result,
            )

            relationship_count += 1

    return {
        "case_id": case_id,
        "entities_written": len(
            resolution_result.entities
        ),
        "relationships_written": relationship_count,
    }


# ---------------------------------------------------------------------------
# Graph inspection helpers
# ---------------------------------------------------------------------------

def get_case_graph(case_id: str) -> list[dict]:
    """
    Return nodes and relationships belonging to a case.

    Used for Stage 7 verification and later by the graph API.
    """

    return run_query(
        """
        MATCH (n)
        WHERE n.case_id = $case_id

        OPTIONAL MATCH (n)-[r]->(m)

        RETURN
            n.canonical_id AS source_id,
            labels(n) AS source_labels,
            n.canonical_value AS source_value,
            type(r) AS relationship_type,
            r.source_id AS relationship_source_id,
            r.source_type AS relationship_source_type,
            r.timestamp AS relationship_timestamp,
            r.confidence AS relationship_confidence,
            r.evidence_snippet AS evidence,
            m.canonical_id AS target_id,
            labels(m) AS target_labels,
            m.canonical_value AS target_value

        ORDER BY source_id
        """,
        {
            "case_id": case_id,
        },
    )


def count_case_graph(case_id: str) -> dict:
    """
    Return basic graph counts for a case.
    """

    rows = run_query(
        """
        MATCH (n)
        WHERE n.case_id = $case_id

        WITH count(DISTINCT n) AS node_count

        OPTIONAL MATCH (a)-[r]->(b)
        WHERE a.case_id = $case_id
           OR b.case_id = $case_id

        RETURN
            node_count,
            count(DISTINCT r) AS relationship_count
        """,
        {
            "case_id": case_id,
        },
    )

    if not rows:
        return {
            "node_count": 0,
            "relationship_count": 0,
        }

    return {
        "node_count": rows[0]["node_count"],
        "relationship_count": rows[0]["relationship_count"],
    }