"""
Stage 4 extraction from unstructured text ParsedDocuments.

This first implementation deliberately uses deterministic patterns rather
than an external LLM. The output remains provenance-aware and can later
be consumed by entity resolution and relationship extraction.
"""

import re

from app.models.schemas import EntityType, ExtractedEntity, ParsedDocument


PHONE_PATTERN = re.compile(r"\b\d{10}\b")

ACCOUNT_PATTERN = re.compile(
    r"\b(?:A/C\s*(?:No\.?|Number)?\s*)?(\d{9,18})\b",
    re.IGNORECASE,
)

VEHICLE_PATTERN = re.compile(
    r"\b[A-Z]{2}\d{1,2}[A-Z]{1,3}\d{1,4}\b",
    re.IGNORECASE,
)

IFSC_PATTERN = re.compile(r"\b[A-Z]{4}0[A-Z0-9]{6}\b")

RUPEE_PATTERN = re.compile(
    r"(?:Rs\.?|INR)\s*[\d,]+(?:\.\d+)?",
    re.IGNORECASE,
)

KNOWN_LOCATION_PATTERN = re.compile(
    r"\b("
    r"Koregaon Park|"
    r"Wakad|"
    r"Baner|"
    r"Pune|"
    r"Shivaji Nagar"
    r")\b",
    re.IGNORECASE,
)

PERSON_PATTERNS = [
    re.compile(r"\bName:\s*([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)+)", re.IGNORECASE),
    re.compile(
        r"\b(?:named|one)\s+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)+)",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:caller identified himself as|man matching .*?description)\s+"
        r"(?:\"([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)+)\")",
        re.IGNORECASE,
    ),
]


def _add_entity(
    entities: list[ExtractedEntity],
    *,
    entity_type: EntityType,
    value: str,
    document: ParsedDocument,
    evidence: str,
    confidence: float,
    normalized_value: str | None = None,
    timestamp: str | None = None,
) -> None:
    value = value.strip()

    if not value:
        return

    entities.append(
        ExtractedEntity(
            entity_type=entity_type,
            value=value,
            normalized_value=(
                normalized_value
                if normalized_value is not None
                else value.casefold()
            ),
            case_id=document.case_id,
            source_id=document.source_id,
            evidence=evidence,
            timestamp=timestamp,
            confidence=confidence,
        )
    )


def _context(text: str, start: int, end: int, window: int = 100) -> str:
    left = max(0, start - window)
    right = min(len(text), end + window)
    return text[left:right].replace("\n", " ").strip()


def extract_text_entities(document: ParsedDocument) -> list[ExtractedEntity]:
    """
    Extract entities from a TEXT ParsedDocument.
    """

    if document.format.value != "text":
        raise ValueError("extract_text_entities requires a text document.")

    text = document.text or ""
    entities: list[ExtractedEntity] = []

    # -------------------------
    # PHONE NUMBERS
    # -------------------------
    for match in PHONE_PATTERN.finditer(text):
        value = match.group(0)

        _add_entity(
            entities,
            entity_type=EntityType.PHONE,
            value=value,
            document=document,
            evidence=_context(text, match.start(), match.end()),
            confidence=1.0,
            normalized_value=value,
        )

    # -------------------------
    # ACCOUNT NUMBERS
    # -------------------------
    seen_accounts: set[str] = set()

    for match in ACCOUNT_PATTERN.finditer(text):
        value = match.group(1)

        if value in seen_accounts:
            continue

        seen_accounts.add(value)

        _add_entity(
            entities,
            entity_type=EntityType.ACCOUNT,
            value=value,
            document=document,
            evidence=_context(text, match.start(), match.end()),
            confidence=0.98,
            normalized_value=value,
        )

    # -------------------------
    # VEHICLE REGISTRATION
    # -------------------------
    for match in VEHICLE_PATTERN.finditer(text):
        value = match.group(0).upper()

        _add_entity(
            entities,
            entity_type=EntityType.VEHICLE,
            value=value,
            document=document,
            evidence=_context(text, match.start(), match.end()),
            confidence=1.0,
            normalized_value=value,
        )

    # -------------------------
    # IFSC / BANK ORGANIZATION
    # -------------------------
    for match in IFSC_PATTERN.finditer(text):
        value = match.group(0).upper()

        _add_entity(
            entities,
            entity_type=EntityType.ORGANIZATION,
            value=value,
            document=document,
            evidence=_context(text, match.start(), match.end()),
            confidence=0.90,
            normalized_value=value,
        )

    # -------------------------
    # LOCATIONS
    # -------------------------
    seen_locations: set[str] = set()

    for match in KNOWN_LOCATION_PATTERN.finditer(text):
        value = match.group(0)

        normalized = value.casefold()

        if normalized in seen_locations:
            continue

        seen_locations.add(normalized)

        _add_entity(
            entities,
            entity_type=EntityType.LOCATION,
            value=value,
            document=document,
            evidence=_context(text, match.start(), match.end()),
            confidence=0.95,
            normalized_value=normalized,
        )

    # -------------------------
    # PEOPLE
    # -------------------------
    seen_people: set[str] = set()

    for pattern in PERSON_PATTERNS:
        for match in pattern.finditer(text):
            value = match.group(1).strip()
            normalized = value.casefold()

            if normalized in seen_people:
                continue

            seen_people.add(normalized)

            _add_entity(
                entities,
                entity_type=EntityType.PERSON,
                value=value,
                document=document,
                evidence=_context(text, match.start(), match.end()),
                confidence=0.88,
                normalized_value=normalized,
            )

    return entities