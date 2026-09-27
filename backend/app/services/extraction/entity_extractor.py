"""
Public Stage 4 entity extraction entry point.

This module accepts ParsedDocument objects and dispatches them to the
appropriate extraction strategy.
"""

from app.models.schemas import (
    EntityExtractionResult,
    ParsedDocument,
)

from app.services.extraction.tabular_extractor import extract_tabular_entities
from app.services.extraction.text_extractor import extract_text_entities


def extract_entities(document: ParsedDocument) -> EntityExtractionResult:
    """
    Extract entities from one ParsedDocument.

    Stage 4 knows only about ParsedDocument. It does not read files,
    access Neo4j, or depend on the frontend.
    """

    if document.format.value == "text":
        entities = extract_text_entities(document)

    elif document.format.value == "tabular":
        entities = extract_tabular_entities(document)

    else:
        raise ValueError(
            f"Unsupported document format: {document.format}"
        )

    return EntityExtractionResult(
        case_id=document.case_id,
        source_id=document.source_id,
        source_type=document.source_type,
        entities=entities,
    )