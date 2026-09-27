"""
Stage 7 - Graph Write

Writes Stage 6 resolved entities and Stage 5 extracted relationships
into Neo4j.

Responsibilities:
- create/merge canonical entity nodes
- create/merge the case node
- preserve aliases and provenance
- write relationship evidence
- safely avoid duplicate nodes/relationships
"""

from app.db.neo4j_client import run_query
from app.models.schemas import (
    EntityType,
    EntityResolutionResult,
    RelationshipExtractionResult,
    RelationshipType,
)


# ---------------------------------------------------------------------------
# Node helpers
# ---------------------------------------------------------------------------

def _node_label(entity_type: EntityType) -> str:
    """Map application entity types to Neo4j labels."""

    mapping = {
        EntityType.PERSON: "Person",
        EntityType.PHONE: "Phone",
        EntityType.ACCOUNT: "Account",
        EntityType.VEHICLE: "Vehicle",
        EntityType.LOCATION: "Location",
        EntityType.ORGANIZATION: "Organization",
    }

    return mapping[entity_type]


def _merge_entity_node(
    resolved_entity,
) -> None:
    """
    Merge one canonical entity into Neo4j.

    canonical_id is stored on every entity so relationships can
    reliably find their endpoints regardless of node type.
    """

    label = _node_label(resolved_entity.entity_type)

    query = f"""
    MERGE (n:{label} {{canonical_id: $canonical_id}})
    SET
        n.id = CASE
            WHEN $entity_type IN ['PERSON', 'LOCATION']
            THEN $canonical_id
            ELSE coalesce(n.id, n.id)
        END,
        n.name = CASE
            WHEN $entity_type IN ['PERSON', 'LOCATION', 'ORGANIZATION']
            THEN $canonical_value
            ELSE coalesce(n.name, n.name)
        END,
        n.number = CASE
            WHEN $entity_type = 'PHONE'
            THEN $canonical_value
            ELSE coalesce(n.number, n.number)
        END,
        n.account_number = CASE
            WHEN $entity_type = 'ACCOUNT'
            THEN $canonical_value
            ELSE coalesce(n.account_number, n.account_number)
        END,
        n.registration_number = CASE
            WHEN $entity_type = 'VEHICLE'
            THEN $canonical_value
            ELSE coalesce(n.registration_number, n.registration_number)
        END,
        n.normalized_value = $normalized_value,
        n.aliases = $aliases,
        n.source_ids = $source_ids,
        n.mention_count = $mention_count,
        n.case_id = $case_id
    """

    run_query(
        query,
        {
            "canonical_id": resolved_entity.canonical_id,
            "entity_type": resolved_entity.entity_type.value,
            "canonical_value": resolved_entity.canonical_value,
            "normalized_value": resolved_entity.normalized_value,
            "aliases": resolved_entity.aliases,
            "source_ids": resolved_entity.source_ids,
            "mention_count": resolved_entity.mention_count,
            "case_id": resolved_entity.case_id,
        },
    )


# ---------------------------------------------------------------------------
# Case node
# ---------------------------------------------------------------------------

def _merge_case(case_id: str) -> None:
    """Create the case node if it does not already exist."""

    query = """
    MERGE (c:Case {case_id: $case_id})
    ON CREATE SET
        c.status = "PROCESSING"
    RETURN c.case_id AS case_id
    """

    run_query(query, {"case_id": case_id})


# ---------------------------------------------------------------------------
# Relationship endpoint resolution
# ---------------------------------------------------------------------------

def _canonical_id_for_relationship(
    relationship,
    side: str,
    resolution: EntityResolutionResult,
) -> str:
    """
    Resolve a Stage 5 relationship endpoint to the Stage 6 canonical ID.

    Uses the Stage 6 mapping first, then falls back to generating the same
    deterministic canonical ID used by the resolver.
    """

    if side == "from":
        entity_type = relationship.from_entity_type
        normalized_value = relationship.from_normalized_value
    else:
        entity_type = relationship.to_entity_type
        normalized_value = relationship.to_normalized_value

    mapping_key = f"{entity_type.value}:{normalized_value}"

    canonical_id = resolution.entity_mappings.get(mapping_key)

    if canonical_id:
        return canonical_id

    # Defensive fallback.
    from app.services.extraction.entity_resolver import (
        make_canonical_id,
        normalize_entity_value,
    )

    normalized = normalize_entity_value(
        entity_type,
        normalized_value,
    )

    mapping_key = f"{entity_type.value}:{normalized}"

    canonical_id = resolution.entity_mappings.get(mapping_key)

    if canonical_id:
        return canonical_id

    return make_canonical_id(
        entity_type,
        normalized,
    )


# ---------------------------------------------------------------------------
# Relationship writer
# ---------------------------------------------------------------------------

def _write_relationship(
    relationship,
    resolution: EntityResolutionResult,
) -> None:
    """
    Write one relationship between canonical entity nodes.

    Relationship types are taken only from the controlled enum, so
    interpolating the type into Cypher is safe here.
    """

    relationship_type = relationship.relationship_type.value

    allowed_types = {item.value for item in RelationshipType}

    if relationship_type not in allowed_types:
        raise ValueError(
            f"Unsupported relationship type: {relationship_type}"
        )

    from_id = _canonical_id_for_relationship(
        relationship,
        "from",
        resolution,
    )

    to_id = _canonical_id_for_relationship(
        relationship,
        "to",
        resolution,
    )

    query = f"""
    MATCH (source {{canonical_id: $from_id}})
    MATCH (target {{canonical_id: $to_id}})

    MERGE (source)-[r:{relationship_type} {{
        case_id: $case_id,
        source_id: $source_id,
        evidence_snippet: $evidence_snippet
    }}]->(target)

    SET
        r.source_type = $source_type,
        r.timestamp = $timestamp,
        r.confidence = $confidence
    """

    run_query(
        query,
        {
            "from_id": from_id,
            "to_id": to_id,
            "case_id": relationship.case_id,
            "source_id": relationship.source_id,
            "source_type": relationship_source_type(relationship),
            "timestamp": relationship.timestamp or "",
            "confidence": relationship.confidence,
            "evidence_snippet": relationship.evidence,
        },
    )


def relationship_source_type(relationship) -> str:
    """
    Relationship provenance source type.

    Stage 5 relationships do not carry a separate source_type field,
    so the value is derived from the source ID prefix where possible.
    """

    source_id = relationship.source_id or ""

    for source_type in (
        "FIR",
        "CDR",
        "TRANSACTION",
        "VEHICLE",
        "LOCATION",
        "REPORT",
    ):
        if source_id.startswith(source_type):
            return source_type

    return relationship.relationship_type.value


# ---------------------------------------------------------------------------
# Public Stage 7 API
# ---------------------------------------------------------------------------

def write_case_graph(
    resolution: EntityResolutionResult,
    relationship_result: RelationshipExtractionResult,
) -> dict:
    """
    Write one complete case graph into Neo4j.

    Inputs:
        resolution:
            Stage 6 canonical entities.

        relationship_result:
            Stage 5 extracted relationships.

    Returns:
        Summary of what was written.
    """

    if resolution.case_id != relationship_result.case_id:
        raise ValueError(
            "Stage 6 resolution and Stage 5 relationships "
            "belong to different cases."
        )

    case_id = resolution.case_id

    # ---------------------------------------------------------------
    # Case
    # ---------------------------------------------------------------

    _merge_case(case_id)

    # ---------------------------------------------------------------
    # Canonical entities
    # ---------------------------------------------------------------

    for entity in resolution.entities:
        _merge_entity_node(entity)

    # ---------------------------------------------------------------
    # Relationships
    # ---------------------------------------------------------------

    relationship_count = 0

    for relationship in relationship_result.relationships:

        if relationship.case_id != case_id:
            raise ValueError(
                f"Relationship belongs to case "
                f"{relationship.case_id}, expected {case_id}."
            )

        _write_relationship(
            relationship,
            resolution,
        )

        relationship_count += 1

    return {
        "case_id": case_id,
        "entity_count": len(resolution.entities),
        "relationship_count": relationship_count,
        "message": "Case graph written successfully.",
    }