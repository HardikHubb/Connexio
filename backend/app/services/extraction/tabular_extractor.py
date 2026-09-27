"""
Stage 4 extraction from structured/tabular ParsedDocuments.

The extractor uses the source type and known column names to identify
entities. It does not read raw files and does not write to Neo4j.
"""

import re
from typing import Optional

from app.models.schemas import (
    EntityType,
    ExtractedEntity,
    ParsedDocument,
    SourceType,
)


PHONE_PATTERN = re.compile(r"^\d{10}$")
ACCOUNT_PATTERN = re.compile(r"^\d{9,18}$")
VEHICLE_PATTERN = re.compile(
    r"^[A-Z]{2}\d{1,2}[A-Z]{1,3}\d{1,4}$",
    re.IGNORECASE,
)


def _normalize_phone(value: str) -> str:
    digits = re.sub(r"\D", "", value)
    return digits


def _normalize_account(value: str) -> str:
    return re.sub(r"\D", "", value)


def _normalize_vehicle(value: str) -> str:
    return re.sub(r"[\s-]", "", value).upper()


def _add_entity(
    entities: list[ExtractedEntity],
    *,
    entity_type: EntityType,
    value: str,
    case_id: str,
    source_id: str,
    evidence: str,
    timestamp: Optional[str] = None,
    confidence: float = 1.0,
    normalized_value: Optional[str] = None,
) -> None:
    value = str(value).strip()

    if not value:
        return

    if normalized_value is None:
        normalized_value = value

    entities.append(
        ExtractedEntity(
            entity_type=entity_type,
            value=value,
            normalized_value=normalized_value,
            case_id=case_id,
            source_id=source_id,
            evidence=evidence,
            timestamp=timestamp,
            confidence=confidence,
        )
    )


def _extract_cdr(document: ParsedDocument) -> list[ExtractedEntity]:
    entities: list[ExtractedEntity] = []

    for row in document.rows or []:
        timestamp = row.get("timestamp")

        caller = row.get("caller_number", "").strip()
        if caller and PHONE_PATTERN.match(_normalize_phone(caller)):
            _add_entity(
                entities,
                entity_type=EntityType.PHONE,
                value=caller,
                normalized_value=_normalize_phone(caller),
                case_id=document.case_id,
                source_id=document.source_id,
                evidence=f"CDR call {row.get('call_id', '')}: caller_number={caller}",
                timestamp=timestamp,
            )

        receiver = row.get("receiver_number", "").strip()
        if receiver and PHONE_PATTERN.match(_normalize_phone(receiver)):
            _add_entity(
                entities,
                entity_type=EntityType.PHONE,
                value=receiver,
                normalized_value=_normalize_phone(receiver),
                case_id=document.case_id,
                source_id=document.source_id,
                evidence=f"CDR call {row.get('call_id', '')}: receiver_number={receiver}",
                timestamp=timestamp,
            )

        location = row.get("tower_location", "").strip()
        if location:
            _add_entity(
                entities,
                entity_type=EntityType.LOCATION,
                value=location,
                normalized_value=location.lower(),
                case_id=document.case_id,
                source_id=document.source_id,
                evidence=f"CDR call {row.get('call_id', '')}: tower_location={location}",
                timestamp=timestamp,
            )

    return entities


def _extract_transactions(document: ParsedDocument) -> list[ExtractedEntity]:
    entities: list[ExtractedEntity] = []

    for row in document.rows or []:
        timestamp = row.get("timestamp")
        transaction_id = row.get("transaction_id", "")

        from_account = row.get("from_account", "").strip()
        if from_account and ACCOUNT_PATTERN.match(_normalize_account(from_account)):
            _add_entity(
                entities,
                entity_type=EntityType.ACCOUNT,
                value=from_account,
                normalized_value=_normalize_account(from_account),
                case_id=document.case_id,
                source_id=document.source_id,
                evidence=(
                    f"Transaction {transaction_id}: "
                    f"from_account={from_account}"
                ),
                timestamp=timestamp,
            )

        to_account = row.get("to_account", "").strip()
        if to_account and ACCOUNT_PATTERN.match(_normalize_account(to_account)):
            _add_entity(
                entities,
                entity_type=EntityType.ACCOUNT,
                value=to_account,
                normalized_value=_normalize_account(to_account),
                case_id=document.case_id,
                source_id=document.source_id,
                evidence=(
                    f"Transaction {transaction_id}: "
                    f"to_account={to_account}"
                ),
                timestamp=timestamp,
            )

    return entities


def _extract_vehicles(document: ParsedDocument) -> list[ExtractedEntity]:
    entities: list[ExtractedEntity] = []

    for row in document.rows or []:
        timestamp = row.get("seen_timestamp")
        record_id = row.get("record_id", "")

        registration = row.get("registration_number", "").strip()

        if registration and VEHICLE_PATTERN.match(
            _normalize_vehicle(registration)
        ):
            _add_entity(
                entities,
                entity_type=EntityType.VEHICLE,
                value=registration,
                normalized_value=_normalize_vehicle(registration),
                case_id=document.case_id,
                source_id=document.source_id,
                evidence=(
                    f"Vehicle record {record_id}: "
                    f"registration_number={registration}"
                ),
                timestamp=timestamp,
            )

        owner_name = row.get("owner_name", "").strip()
        if owner_name:
            _add_entity(
                entities,
                entity_type=EntityType.PERSON,
                value=owner_name,
                normalized_value=owner_name.casefold(),
                case_id=document.case_id,
                source_id=document.source_id,
                evidence=(
                    f"Vehicle record {record_id}: "
                    f"owner_name={owner_name}"
                ),
                timestamp=timestamp,
            )

        owner_phone = row.get("owner_phone", "").strip()
        if owner_phone and PHONE_PATTERN.match(_normalize_phone(owner_phone)):
            _add_entity(
                entities,
                entity_type=EntityType.PHONE,
                value=owner_phone,
                normalized_value=_normalize_phone(owner_phone),
                case_id=document.case_id,
                source_id=document.source_id,
                evidence=(
                    f"Vehicle record {record_id}: "
                    f"owner_phone={owner_phone}"
                ),
                timestamp=timestamp,
            )

        location = row.get("seen_location", "").strip()
        if location:
            _add_entity(
                entities,
                entity_type=EntityType.LOCATION,
                value=location,
                normalized_value=location.casefold(),
                case_id=document.case_id,
                source_id=document.source_id,
                evidence=(
                    f"Vehicle record {record_id}: "
                    f"seen_location={location}"
                ),
                timestamp=timestamp,
            )

    return entities


def _extract_locations(document: ParsedDocument) -> list[ExtractedEntity]:
    entities: list[ExtractedEntity] = []

    for row in document.rows or []:
        location = (
            row.get("location")
            or row.get("tower_location")
            or row.get("seen_location")
            or ""
        ).strip()

        if location:
            _add_entity(
                entities,
                entity_type=EntityType.LOCATION,
                value=location,
                normalized_value=location.casefold(),
                case_id=document.case_id,
                source_id=document.source_id,
                evidence=f"Location record: {location}",
                timestamp=row.get("timestamp") or row.get("seen_timestamp"),
            )

    return entities


def extract_tabular_entities(
    document: ParsedDocument,
) -> list[ExtractedEntity]:
    """
    Dispatch tabular extraction according to the document source type.
    """

    if document.format.value != "tabular":
        raise ValueError("extract_tabular_entities requires a tabular document.")

    if document.source_type == SourceType.CDR:
        return _extract_cdr(document)

    if document.source_type == SourceType.TRANSACTION:
        return _extract_transactions(document)

    if document.source_type == SourceType.VEHICLE:
        return _extract_vehicles(document)

    if document.source_type == SourceType.LOCATION:
        return _extract_locations(document)

    return []