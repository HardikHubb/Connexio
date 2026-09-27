"""
Stage 8 - Graph Read Service

Reads graph data from Neo4j for the API layer.

The Neo4j client returns plain dictionaries from run_query(),
so this service converts the returned values into JSON-safe
node and relationship representations.
"""

from app.db.neo4j_client import run_query


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _serialize_node(node):
    """
    Convert a Neo4j node or dictionary into a JSON-safe dictionary.

    run_query() normally returns record.data(), so values may already
    be dictionaries depending on how the query/result was produced.
    """

    if node is None:
        return None

    # Neo4j Node object
    if hasattr(node, "labels") and hasattr(node, "items"):
        return {
            "labels": sorted(list(node.labels)),
            "properties": dict(node),
        }

    # Dictionary returned by the query
    if isinstance(node, dict):
        # If the query already produced the expected structure.
        if "labels" in node and "properties" in node:
            return {
                "labels": list(node.get("labels", [])),
                "properties": dict(node.get("properties", {})),
            }

        # Otherwise treat the dictionary itself as properties.
        return {
            "labels": [],
            "properties": node,
        }

    return {
        "labels": [],
        "properties": {},
    }


def _serialize_relationship(
    relationship_type,
    relationship,
):
    if relationship is None:
        return None

    if hasattr(relationship, "items"):
        properties = dict(relationship)
    elif isinstance(relationship, dict):
        properties = relationship
    else:
        properties = {}

    return {
        "type": relationship_type,
        "properties": properties,
    }


# ---------------------------------------------------------------------------
# Case network
# ---------------------------------------------------------------------------

def get_case_network(case_id: str) -> dict:
    """
    Return all entity nodes belonging to a case and all relationships
    belonging to that case.

    The Case node itself is intentionally excluded from the investigator
    network because it is metadata about the investigation, not an
    investigative entity.
    """

    # ---------------------------------------------------------------
    # Get every entity belonging to the case
    # ---------------------------------------------------------------

    node_query = """
    MATCH (node)
    WHERE node.case_id = $case_id
      AND NOT node:Case

    RETURN
        labels(node) AS labels,
        properties(node) AS properties
    """

    node_records = run_query(
        node_query,
        {
            "case_id": case_id,
        },
    )

    nodes = []
    node_ids = set()

    for record in node_records:

        properties = record.get("properties", {})
        labels = record.get("labels", [])

        node_id = (
            properties.get("canonical_id")
            or properties.get("id")
            or properties.get("number")
            or properties.get("account_number")
            or properties.get("registration_number")
            or properties.get("name")
        )

        if node_id is None:
            continue

        node_id = str(node_id)

        if node_id in node_ids:
            continue

        nodes.append(
            {
                "id": node_id,
                "labels": labels,
                "properties": properties,
            }
        )

        node_ids.add(node_id)

    # ---------------------------------------------------------------
    # Get relationships belonging to the case
    # ---------------------------------------------------------------

    relationship_query = """
    MATCH (source)-[r]->(target)
    WHERE r.case_id = $case_id

    RETURN
        properties(source) AS source_properties,
        properties(target) AS target_properties,
        type(r) AS relationship_type,
        properties(r) AS relationship
    ORDER BY relationship_type
    """

    relationship_records = run_query(
        relationship_query,
        {
            "case_id": case_id,
        },
    )

    edges = []

    for record in relationship_records:

        source_properties = record.get(
            "source_properties",
            {},
        )

        target_properties = record.get(
            "target_properties",
            {},
        )

        source_id = (
            source_properties.get("canonical_id")
            or source_properties.get("id")
            or source_properties.get("number")
            or source_properties.get("account_number")
            or source_properties.get("registration_number")
            or source_properties.get("name")
        )

        target_id = (
            target_properties.get("canonical_id")
            or target_properties.get("id")
            or target_properties.get("number")
            or target_properties.get("account_number")
            or target_properties.get("registration_number")
            or target_properties.get("name")
        )

        if source_id is None or target_id is None:
            continue

        edges.append(
            {
                "source": str(source_id),
                "target": str(target_id),
                "type": record.get("relationship_type"),
                "properties": record.get(
                    "relationship",
                    {},
                ),
            }
        )

    return {
        "case_id": case_id,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "nodes": nodes,
        "edges": edges,
    }


# ---------------------------------------------------------------------------
# Entity details
# ---------------------------------------------------------------------------

def get_entity(entity_id: str):
    node_rows = run_query(
        """
        MATCH (entity)
        WHERE entity.canonical_id = $entity_id
        RETURN
            labels(entity) AS labels,
            properties(entity) AS properties
        """,
        {"entity_id": entity_id},
    )

    if not node_rows:
        return None

    node_row = node_rows[0]
    properties = node_row["properties"]

    outgoing_rows = run_query(
        """
        MATCH (entity)-[r]->(target)
        WHERE entity.canonical_id = $entity_id
        RETURN
            properties(target) AS target_properties,
            type(r) AS relationship_type,
            properties(r) AS relationship
        ORDER BY relationship_type
        """,
        {"entity_id": entity_id},
    )

    incoming_rows = run_query(
        """
        MATCH (source)-[r]->(entity)
        WHERE entity.canonical_id = $entity_id
        RETURN
            properties(source) AS source_properties,
            type(r) AS relationship_type,
            properties(r) AS relationship
        ORDER BY relationship_type
        """,
        {"entity_id": entity_id},
    )

    def entity_id_from_properties(props: dict) -> str:
        return (
            props.get("canonical_id")
            or props.get("id")
            or props.get("number")
            or props.get("account_number")
            or props.get("registration_number")
            or props.get("name")
        )

    outgoing_relationships = [
        {
            "target": row["target_properties"],
            "target_id": entity_id_from_properties(row["target_properties"]),
            "type": row["relationship_type"],
            "properties": row["relationship"],
        }
        for row in outgoing_rows
    ]

    incoming_relationships = [
        {
            "source": row["source_properties"],
            "source_id": entity_id_from_properties(row["source_properties"]),
            "type": row["relationship_type"],
            "properties": row["relationship"],
        }
        for row in incoming_rows
    ]

    return {
        "id": entity_id,
        "labels": node_row["labels"],
        "properties": properties,
        "outgoing_relationships": outgoing_relationships,
        "incoming_relationships": incoming_relationships,
    }