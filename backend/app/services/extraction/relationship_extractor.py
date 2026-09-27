"""
Stage 5 - Relationship Extraction

Converts Stage 3 ParsedDocument data + Stage 4 extracted entities
into deterministic, provenance-preserving relationships.

This stage does NOT:
- write to Neo4j
- merge entities
- perform fuzzy matching
- create cross-case relationships
- infer guilt or criminal involvement

Those responsibilities belong to later stages.
"""

import re
from typing import Optional

from app.models.schemas import (
    EntityType,
    ExtractedEntity,
    ExtractedRelationship,
    EntityExtractionResult,
    ParsedDocument,
    RelationshipExtractionResult,
    RelationshipType,
    SourceType,
)


# ---------------------------------------------------------------------------
# Normalization helpers
# ---------------------------------------------------------------------------

def _normalize_text(value: str) -> str:
    return " ".join(value.strip().lower().split())


def _normalize_phone(value: str) -> str:
    return re.sub(r"\D", "", value)


def _normalize_account(value: str) -> str:
    return re.sub(r"\D", "", value)


def _normalize_vehicle(value: str) -> str:
    return re.sub(r"[\s-]", "", value.upper())


def _normalize_entity(entity_type: EntityType, value: str) -> str:
    if entity_type == EntityType.PHONE:
        return _normalize_phone(value)

    if entity_type == EntityType.ACCOUNT:
        return _normalize_account(value)

    if entity_type == EntityType.VEHICLE:
        return _normalize_vehicle(value)

    return _normalize_text(value)


# ---------------------------------------------------------------------------
# Entity lookup
# ---------------------------------------------------------------------------

def _find_entity(
    entities: list[ExtractedEntity],
    entity_type: EntityType,
    value: str,
) -> Optional[ExtractedEntity]:
    """
    Find an already extracted Stage 4 entity.

    Stage 5 deliberately does not create new entities.
    """

    normalized = _normalize_entity(entity_type, value)

    for entity in entities:
        if entity.entity_type != entity_type:
            continue

        entity_normalized = _normalize_entity(
            entity.entity_type,
            entity.normalized_value,
        )

        if entity_normalized == normalized:
            return entity

    return None


# ---------------------------------------------------------------------------
# Relationship builder
# ---------------------------------------------------------------------------

def _build_relationship(
    *,
    from_entity: ExtractedEntity,
    relationship_type: RelationshipType,
    to_entity: ExtractedEntity,
    case_id: str,
    source_id: str,
    evidence: str,
    timestamp: Optional[str] = None,
    confidence: float = 1.0,
) -> ExtractedRelationship:

    return ExtractedRelationship(
        from_entity_type=from_entity.entity_type,
        from_value=from_entity.value,
        from_normalized_value=from_entity.normalized_value,

        relationship_type=relationship_type,

        to_entity_type=to_entity.entity_type,
        to_value=to_entity.value,
        to_normalized_value=to_entity.normalized_value,

        case_id=case_id,
        source_id=source_id,

        evidence=evidence,
        timestamp=timestamp,
        confidence=confidence,
    )


# ---------------------------------------------------------------------------
# Duplicate protection
# ---------------------------------------------------------------------------

def _relationship_key(
    relationship: ExtractedRelationship,
) -> tuple:
    return (
        relationship.from_entity_type.value,
        relationship.from_normalized_value,
        relationship.relationship_type.value,
        relationship.to_entity_type.value,
        relationship.to_normalized_value,
        relationship.source_id,
        relationship.evidence,
        relationship.timestamp,
    )


def _deduplicate(
    relationships: list[ExtractedRelationship],
) -> list[ExtractedRelationship]:

    seen = set()
    result = []

    for relationship in relationships:
        key = _relationship_key(relationship)

        if key in seen:
            continue

        seen.add(key)
        result.append(relationship)

    return result


# ---------------------------------------------------------------------------
# Tabular relationships
# ---------------------------------------------------------------------------

def _extract_cdr_relationships(
    document: ParsedDocument,
    entities: list[ExtractedEntity],
) -> list[ExtractedRelationship]:

    relationships = []

    if not document.rows:
        return relationships

    for row in document.rows:

        caller = row.get("caller_number", "").strip()
        receiver = row.get("receiver_number", "").strip()
        tower = row.get("tower_location", "").strip()
        timestamp = row.get("timestamp")

        if caller and receiver:
            caller_entity = _find_entity(
                entities,
                EntityType.PHONE,
                caller,
            )

            receiver_entity = _find_entity(
                entities,
                EntityType.PHONE,
                receiver,
            )

            if caller_entity and receiver_entity:
                evidence = (
                    f"CDR record {row.get('call_id', 'unknown')}: "
                    f"{caller} called {receiver}"
                )

                relationships.append(
                    _build_relationship(
                        from_entity=caller_entity,
                        relationship_type=RelationshipType.CALLED,
                        to_entity=receiver_entity,
                        case_id=document.case_id,
                        source_id=document.source_id,
                        evidence=evidence,
                        timestamp=timestamp,
                        confidence=1.0,
                    )
                )

        if caller and tower:
            caller_entity = _find_entity(
                entities,
                EntityType.PHONE,
                caller,
            )

            location_entity = _find_entity(
                entities,
                EntityType.LOCATION,
                tower,
            )

            if caller_entity and location_entity:
                evidence = (
                    f"CDR record {row.get('call_id', 'unknown')}: "
                    f"tower location recorded as {tower}"
                )

                relationships.append(
                    _build_relationship(
                        from_entity=caller_entity,
                        relationship_type=RelationshipType.LOCATED_AT,
                        to_entity=location_entity,
                        case_id=document.case_id,
                        source_id=document.source_id,
                        evidence=evidence,
                        timestamp=timestamp,
                        confidence=0.85,
                    )
                )

    return relationships


def _extract_transaction_relationships(
    document: ParsedDocument,
    entities: list[ExtractedEntity],
) -> list[ExtractedRelationship]:

    relationships = []

    if not document.rows:
        return relationships

    for row in document.rows:

        from_account = row.get("from_account", "").strip()
        to_account = row.get("to_account", "").strip()
        timestamp = row.get("timestamp")

        if not from_account or not to_account:
            continue

        from_entity = _find_entity(
            entities,
            EntityType.ACCOUNT,
            from_account,
        )

        to_entity = _find_entity(
            entities,
            EntityType.ACCOUNT,
            to_account,
        )

        if not from_entity or not to_entity:
            continue

        amount = row.get("amount_inr", "").strip()
        transaction_id = row.get("transaction_id", "unknown")

        evidence = (
            f"Transaction {transaction_id}: "
            f"account {from_account} transferred "
            f"{amount} INR to account {to_account}"
        )

        relationships.append(
            _build_relationship(
                from_entity=from_entity,
                relationship_type=RelationshipType.TRANSFERRED_TO,
                to_entity=to_entity,
                case_id=document.case_id,
                source_id=document.source_id,
                evidence=evidence,
                timestamp=timestamp,
                confidence=1.0,
            )
        )

    return relationships


def _extract_vehicle_relationships(
    document: ParsedDocument,
    entities: list[ExtractedEntity],
) -> list[ExtractedRelationship]:

    relationships = []

    if not document.rows:
        return relationships

    for row in document.rows:

        registration = row.get("registration_number", "").strip()
        owner_name = row.get("owner_name", "").strip()
        owner_phone = row.get("owner_phone", "").strip()
        location = row.get("seen_location", "").strip()
        timestamp = row.get("seen_timestamp")

        vehicle_entity = _find_entity(
            entities,
            EntityType.VEHICLE,
            registration,
        )

        person_entity = _find_entity(
            entities,
            EntityType.PERSON,
            owner_name,
        )

        phone_entity = _find_entity(
            entities,
            EntityType.PHONE,
            owner_phone,
        )

        location_entity = _find_entity(
            entities,
            EntityType.LOCATION,
            location,
        )

        # PERSON -> OWNS -> VEHICLE
        if person_entity and vehicle_entity:

            evidence = (
                f"Vehicle record: {owner_name} is listed as "
                f"owner of vehicle {registration}"
            )

            relationships.append(
                _build_relationship(
                    from_entity=person_entity,
                    relationship_type=RelationshipType.OWNS,
                    to_entity=vehicle_entity,
                    case_id=document.case_id,
                    source_id=document.source_id,
                    evidence=evidence,
                    timestamp=timestamp,
                    confidence=1.0,
                )
            )

        # PERSON -> USES -> PHONE
        if person_entity and phone_entity:

            evidence = (
                f"Vehicle record: owner {owner_name} is associated "
                f"with phone number {owner_phone}"
            )

            relationships.append(
                _build_relationship(
                    from_entity=person_entity,
                    relationship_type=RelationshipType.USES,
                    to_entity=phone_entity,
                    case_id=document.case_id,
                    source_id=document.source_id,
                    evidence=evidence,
                    timestamp=timestamp,
                    confidence=0.95,
                )
            )

        # VEHICLE -> SEEN_AT -> LOCATION
        if vehicle_entity and location_entity:

            evidence = (
                f"Vehicle record: vehicle {registration} "
                f"was seen at {location}"
            )

            relationships.append(
                _build_relationship(
                    from_entity=vehicle_entity,
                    relationship_type=RelationshipType.SEEN_AT,
                    to_entity=location_entity,
                    case_id=document.case_id,
                    source_id=document.source_id,
                    evidence=evidence,
                    timestamp=timestamp,
                    confidence=1.0,
                )
            )

    return relationships


# ---------------------------------------------------------------------------
# FIR / text relationships
# ---------------------------------------------------------------------------

def _extract_fir_relationships(
    document: ParsedDocument,
    entities: list[ExtractedEntity],
) -> list[ExtractedRelationship]:

    relationships = []

    if not document.text:
        return relationships

    text = document.text

    def add_relationship(
        from_type: EntityType,
        from_value: str,
        relation: RelationshipType,
        to_type: EntityType,
        to_value: str,
        evidence: str,
        confidence: float = 1.0,
    ):
        from_entity = _find_entity(
            entities,
            from_type,
            from_value,
        )

        to_entity = _find_entity(
            entities,
            to_type,
            to_value,
        )

        if from_entity and to_entity:
            relationships.append(
                _build_relationship(
                    from_entity=from_entity,
                    relationship_type=relation,
                    to_entity=to_entity,
                    case_id=document.case_id,
                    source_id=document.source_id,
                    evidence=evidence,
                    confidence=confidence,
                )
            )

    # ------------------------------------------------------------------
    # Complainant -> phone
    # ------------------------------------------------------------------

    complainant_match = re.search(
        r"Complainant:\s*([A-Za-z .]+).*?"
        r"Phone:\s*(\d{10})",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    if complainant_match:

        person = complainant_match.group(1).strip()
        phone = complainant_match.group(2).strip()

        add_relationship(
            EntityType.PERSON,
            person,
            RelationshipType.USES,
            EntityType.PHONE,
            phone,
            f"FIR complainant details list phone number {phone} "
            f"for {person}",
            confidence=1.0,
        )

    # ------------------------------------------------------------------
    # Ravi Kumar -> account
    # "this account belongs to an individual named Ravi Kumar"
    # ------------------------------------------------------------------

    ravi_account_match = re.search(
        r"account\s+(\d{9,18})\s+belongs\s+to\s+an?\s+"
        r"(?:individual|person)\s+named\s+([A-Za-z ]+)",
        text,
        flags=re.IGNORECASE,
    )

    if ravi_account_match:

        account = ravi_account_match.group(1).strip()
        person = ravi_account_match.group(2).strip()

        add_relationship(
            EntityType.PERSON,
            person,
            RelationshipType.OWNS,
            EntityType.ACCOUNT,
            account,
            f"FIR states that account {account} belongs to {person}",
            confidence=1.0,
        )

    # ------------------------------------------------------------------
    # "account held by one Suresh Yadav"
    # ------------------------------------------------------------------

    held_account_match = re.search(
        r"account\s+(\d{9,18})\s+held\s+by\s+one\s+"
        r"([A-Za-z ]+)",
        text,
        flags=re.IGNORECASE,
    )

    if held_account_match:

        account = held_account_match.group(1).strip()
        person = held_account_match.group(2).strip()

        add_relationship(
            EntityType.PERSON,
            person,
            RelationshipType.OWNS,
            EntityType.ACCOUNT,
            account,
            f"FIR states that account {account} is held by {person}",
            confidence=1.0,
        )

    # ------------------------------------------------------------------
    # Caller identified as Ravi Kumar
    #
    # IMPORTANT:
    # We deliberately use IDENTIFIED_AS rather than OWNS/USES.
    # This preserves the distinction between an identity claim and
    # a verified identity.
    # ------------------------------------------------------------------

    caller_match = re.search(
        r"caller\s+(\d{10})\s+identified\s+"
        r"(?:himself|herself)\s+as\s+([A-Za-z ]+)",
        text,
        flags=re.IGNORECASE,
    )

    if caller_match:

        phone = caller_match.group(1).strip()
        person = caller_match.group(2).strip()

        add_relationship(
            EntityType.PHONE,
            phone,
            RelationshipType.IDENTIFIED_AS,
            EntityType.PERSON,
            person,
            f"FIR states that caller {phone} identified "
            f"themselves as {person}",
            confidence=0.80,
        )

    # ------------------------------------------------------------------
    # Person -> visited location
    #
    # Only create this when the text explicitly says the person
    # visited/went to the location.
    # ------------------------------------------------------------------

    visit_patterns = [
        r"([A-Za-z ]+)\s+visited\s+([A-Za-z0-9 .,'-]+)",
        r"([A-Za-z ]+)\s+went\s+to\s+([A-Za-z0-9 .,'-]+)",
    ]

    for pattern in visit_patterns:

        for match in re.finditer(
            pattern,
            text,
            flags=re.IGNORECASE,
        ):

            person = match.group(1).strip()
            location = match.group(2).strip()

            # Prevent the regex from consuming a huge sentence.
            if len(person) > 50 or len(location) > 80:
                continue

            person_entity = _find_entity(
                entities,
                EntityType.PERSON,
                person,
            )

            location_entity = _find_entity(
                entities,
                EntityType.LOCATION,
                location,
            )

            if person_entity and location_entity:

                relationships.append(
                    _build_relationship(
                        from_entity=person_entity,
                        relationship_type=RelationshipType.VISITED,
                        to_entity=location_entity,
                        case_id=document.case_id,
                        source_id=document.source_id,
                        evidence=match.group(0).strip(),
                        confidence=0.90,
                    )
                )

    # ------------------------------------------------------------------
    # Explicit mention of another person
    #
    # We DO NOT turn "may also be involved" into an INVOLVED_IN edge.
    # MENTIONED_IN is intentionally neutral.
    # ------------------------------------------------------------------

    mentioned_match = re.search(
        r"(?:colleague(?:'s)? statement|statement).*?"
        r"([A-Z][a-z]+ [A-Z][a-z]+).*?"
        r"(?:may also be involved|mentioned)",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    if mentioned_match:

        person = mentioned_match.group(1).strip()

        person_entity = _find_entity(
            entities,
            EntityType.PERSON,
            person,
        )

        if person_entity:

            relationships.append(
                _build_relationship(
                    from_entity=person_entity,
                    relationship_type=RelationshipType.MENTIONED_IN,
                    to_entity=person_entity,
                    case_id=document.case_id,
                    source_id=document.source_id,
                    evidence=mentioned_match.group(0).strip(),
                    confidence=0.60,
                )
            )

    return relationships


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_relationships(
    document: ParsedDocument,
    entity_result: EntityExtractionResult,
) -> RelationshipExtractionResult:
    """
    Main Stage 5 entry point.

    Parameters
    ----------
    document:
        Stage 3 ParsedDocument.

    entity_result:
        Stage 4 EntityExtractionResult for the same document.

    Returns
    -------
    RelationshipExtractionResult
    """

    if document.case_id != entity_result.case_id:
        raise ValueError(
            "Document and entity result belong to different cases."
        )

    if document.source_id != entity_result.source_id:
        raise ValueError(
            "Document and entity result belong to different sources."
        )

    relationships = []

    if document.format.value == "tabular":

        if document.source_type == SourceType.CDR:
            relationships.extend(
                _extract_cdr_relationships(
                    document,
                    entity_result.entities,
                )
            )

        elif document.source_type == SourceType.TRANSACTION:
            relationships.extend(
                _extract_transaction_relationships(
                    document,
                    entity_result.entities,
                )
            )

        elif document.source_type == SourceType.VEHICLE:
            relationships.extend(
                _extract_vehicle_relationships(
                    document,
                    entity_result.entities,
                )
            )

        elif document.source_type == SourceType.LOCATION:
            # No relationship extraction for generic LOCATION
            # documents yet.
            pass

    elif document.format.value == "text":

        if document.source_type in (
            SourceType.FIR,
            SourceType.REPORT,
        ):
            relationships.extend(
                _extract_fir_relationships(
                    document,
                    entity_result.entities,
                )
            )

    relationships = _deduplicate(relationships)

    return RelationshipExtractionResult(
        case_id=document.case_id,
        source_id=document.source_id,
        source_type=document.source_type,
        relationships=relationships,
    )