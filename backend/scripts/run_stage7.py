"""
Stage 7 test runner.

Runs the complete extraction -> resolution -> Neo4j write pipeline
for an existing case.

Usage:
    python scripts/run_stage7.py 101
"""

import sys

from app.services.ingestion_service import list_parsed_documents
from app.services.extraction.entity_extractor import extract_entities
from app.services.extraction.relationship_extractor import extract_relationships
from app.services.extraction.entity_resolver import resolve_entities
from app.services.graph.write_service import write_case_graph


def run(case_id: str) -> None:
    print("=" * 60)
    print(f"STAGE 7 GRAPH WRITE - CASE {case_id}")
    print("=" * 60)

    # ---------------------------------------------------------------
    # Stage 3 - Load parsed documents
    # ---------------------------------------------------------------

    documents = list_parsed_documents(case_id)

    print(f"\n[Stage 3] Parsed documents: {len(documents)}")

    if not documents:
        print("ERROR: No parsed documents found for this case.")
        return

    # ---------------------------------------------------------------
    # Stage 4 + Stage 5
    # ---------------------------------------------------------------

    all_entities = []
    all_relationships = []

    for document in documents:

        print(
            f"\nProcessing:"
            f"\n  source_id   = {document.source_id}"
            f"\n  source_type = {document.source_type.value}"
            f"\n  file        = {document.original_filename}"
        )

        # Stage 4
        entity_result = extract_entities(document)

        print(
            f"  Stage 4 entities       = "
            f"{len(entity_result.entities)}"
        )

        all_entities.extend(entity_result.entities)

        # Stage 5
        relationship_result = extract_relationships(
            document,
            entity_result,
        )

        print(
            f"  Stage 5 relationships  = "
            f"{len(relationship_result.relationships)}"
        )

        all_relationships.extend(
            relationship_result.relationships
        )

    # ---------------------------------------------------------------
    # Stage 6 - Resolve entities across the ENTIRE CASE
    # ---------------------------------------------------------------

    print("\n" + "-" * 60)
    print("[Stage 6] Resolving entities across entire case...")

    resolution = resolve_entities(
        case_id,
        all_entities,
    )

    print(
        f"  Extracted entity mentions = {len(all_entities)}"
    )

    print(
        f"  Canonical entities         = "
        f"{len(resolution.entities)}"
    )

    print(
        f"  Entity mappings            = "
        f"{len(resolution.entity_mappings)}"
    )

    # ---------------------------------------------------------------
    # Stage 7 - Write graph
    # ---------------------------------------------------------------

    print("\n" + "-" * 60)
    print("[Stage 7] Writing graph to Neo4j...")

    relationship_result_for_case = type(
        "RelationshipResult",
        (),
        {
            "case_id": case_id,
            "relationships": all_relationships,
        },
    )()

    result = write_case_graph(
        resolution,
        relationship_result_for_case,
    )

    print("\n" + "=" * 60)
    print("STAGE 7 COMPLETE")
    print("=" * 60)

    print(f"Case ID             : {result['case_id']}")
    print(f"Entities written    : {result['entity_count']}")
    print(f"Relationships written: {result['relationship_count']}")
    print(f"Message             : {result['message']}")


if __name__ == "__main__":

    if len(sys.argv) != 2:
        print("Usage: python scripts/run_stage7.py <case_id>")
        sys.exit(1)

    run(sys.argv[1])