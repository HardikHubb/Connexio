"""
Stage 6 - Entity Resolution

Resolves Stage 4 extracted entities into canonical entities.

This stage is intentionally conservative.

It:
- normalizes values
- groups exact normalized matches
- preserves aliases
- preserves source provenance
- generates stable canonical IDs

It does NOT:
- write to Neo4j
- perform fuzzy person matching
- infer identity
- merge different people based only on similar names
"""

import re
import hashlib

from app.models.schemas import (
    EntityType,
    ExtractedEntity,
    EntityResolutionResult,
    ResolvedEntity,
)


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

def normalize_phone(value: str) -> str:
    """
    Normalize Indian-style phone numbers.

    Examples:
        9876543210
        +91 9876543210
        +91-9876543210
        98765 43210

    All become:
        9876543210
    """

    digits = re.sub(r"\D", "", value)

    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]

    return digits


def normalize_account(value: str) -> str:
    """
    Account numbers are represented by digits only.
    """

    return re.sub(r"\D", "", value)


def normalize_vehicle(value: str) -> str:
    """
    Normalize vehicle registration numbers.

    Examples:

        MH12 AB 1234
        MH-12-AB-1234
        mh12ab1234

    become:

        MH12AB1234
    """

    return re.sub(r"[^A-Z0-9]", "", value.upper())


def normalize_text(value: str) -> str:
    """
    Generic text normalization.

    Converts:
        '  Ravi   Kumar  '

    to:
        'ravi kumar'
    """

    value = value.strip().lower()

    value = re.sub(r"\s+", " ", value)

    return value


def normalize_entity_value(
    entity_type: EntityType,
    value: str,
) -> str:

    if entity_type == EntityType.PHONE:
        return normalize_phone(value)

    if entity_type == EntityType.ACCOUNT:
        return normalize_account(value)

    if entity_type == EntityType.VEHICLE:
        return normalize_vehicle(value)

    return normalize_text(value)


# ---------------------------------------------------------------------------
# Canonical value
# ---------------------------------------------------------------------------

def canonical_value(
    entity_type: EntityType,
    values: list[str],
) -> str:
    """
    Select the canonical display value.

    For most entities we use the first observed representation.
    The normalized value is separately stored for matching.
    """

    if not values:
        return ""

    return values[0].strip()


# ---------------------------------------------------------------------------
# Canonical ID
# ---------------------------------------------------------------------------

def make_canonical_id(
    entity_type: EntityType,
    normalized_value: str,
) -> str:
    """
    Generate a deterministic canonical ID.

    Example:

        PERSON + ravi kumar

    becomes something similar to:

        PERSON:5f7c2c...

    The hash prevents problematic characters from appearing
    in identifiers while keeping the ID deterministic.
    """

    identity_string = (
        f"{entity_type.value}:{normalized_value}"
    )

    digest = hashlib.sha1(
        identity_string.encode("utf-8")
    ).hexdigest()[:16]

    return f"{entity_type.value}:{digest}"


# ---------------------------------------------------------------------------
# Resolution key
# ---------------------------------------------------------------------------

def resolution_key(
    entity: ExtractedEntity,
) -> tuple[str, str]:

    normalized = normalize_entity_value(
        entity.entity_type,
        entity.normalized_value or entity.value,
    )

    return (
        entity.entity_type.value,
        normalized,
    )


# ---------------------------------------------------------------------------
# Main resolver
# ---------------------------------------------------------------------------

def resolve_entities(
    case_id: str,
    entities: list[ExtractedEntity],
) -> EntityResolutionResult:
    """
    Resolve all extracted entities belonging to one case.

    Matching rule:

        Same entity type
        +
        Same normalized value
        =
        Same canonical entity

    This is deliberately conservative.
    """

    if not entities:
        return EntityResolutionResult(
            case_id=case_id,
            entities=[],
            entity_mappings={},
        )

    groups: dict[
        tuple[str, str],
        list[ExtractedEntity],
    ] = {}

    # ---------------------------------------------------------------
    # Group exact normalized matches
    # ---------------------------------------------------------------

    for entity in entities:

        if entity.case_id != case_id:
            raise ValueError(
                f"Entity {entity.value!r} belongs to "
                f"case {entity.case_id}, expected {case_id}."
            )

        key = resolution_key(entity)

        groups.setdefault(key, []).append(entity)

    # ---------------------------------------------------------------
    # Build canonical entities
    # ---------------------------------------------------------------

    resolved_entities: list[ResolvedEntity] = []

    entity_mappings: dict[str, str] = {}

    for (entity_type_value, normalized), mentions in groups.items():

        entity_type = EntityType(entity_type_value)

        values = []
        aliases = []
        source_ids = []

        for mention in mentions:

            if mention.value not in values:
                values.append(mention.value)

            if mention.value not in aliases:
                aliases.append(mention.value)

            if mention.source_id not in source_ids:
                source_ids.append(mention.source_id)

        canonical = canonical_value(
            entity_type,
            values,
        )

        canonical_id = make_canonical_id(
            entity_type,
            normalized,
        )

        resolved = ResolvedEntity(
            canonical_id=canonical_id,

            entity_type=entity_type,

            canonical_value=canonical,

            normalized_value=normalized,

            case_id=case_id,

            aliases=aliases,

            source_ids=source_ids,

            mention_count=len(mentions),
        )

        resolved_entities.append(resolved)

        # -----------------------------------------------------------
        # Map every extracted mention to the canonical ID
        # -----------------------------------------------------------

        for mention in mentions:

            mention_key = (
                f"{mention.entity_type.value}:"
                f"{mention.normalized_value}"
            )

            entity_mappings[mention_key] = canonical_id

    return EntityResolutionResult(
        case_id=case_id,

        entities=resolved_entities,

        entity_mappings=entity_mappings,
    )