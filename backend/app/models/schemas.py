"""
Shared data shapes used across stages. ParsedDocument in particular is the
contract point: Stage 3 (this stage) is the only thing allowed to produce
it, and Stage 4 (entity extraction) is written to consume it and nothing
else — it never touches a raw file or knows a file format exists. That
separation is what lets us swap in the team's real dataset later without
changing a line of extraction code.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class SourceType(str, Enum):
    FIR = "FIR"
    CDR = "CDR"
    TRANSACTION = "TRANSACTION"
    VEHICLE = "VEHICLE"
    LOCATION = "LOCATION"
    REPORT = "REPORT"


class DocumentFormat(str, Enum):
    TEXT = "text"        # unstructured prose — goes to NER (Stage 4)
    TABULAR = "tabular"  # structured rows — goes to rule-based extraction (Stage 4)


class ParsedDocument(BaseModel):
    """
    The normalized output of Stage 3, for exactly one uploaded file.

    - `text` is populated for TEXT format documents (e.g. an FIR narrative).
    - `rows` is populated for TABULAR format documents (e.g. a CDR CSV),
      as a list of plain dicts keyed by column name — no assumptions
      baked in yet about which columns matter, that's Stage 4's job.
    """

    source_id: str
    case_id: str
    source_type: SourceType
    original_filename: str
    format: DocumentFormat

    text: Optional[str] = None
    rows: Optional[list[dict[str, str]]] = None
    row_count: Optional[int] = None

    raw_file_path: str = Field(
        description="Path (relative to storage_dir) to the original uploaded file — "
        "this is what the evidence panel (Stage 11) opens."
    )
    ingested_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class IngestResponse(BaseModel):
    source_id: str
    case_id: str
    source_type: SourceType
    format: DocumentFormat
    row_count: Optional[int] = None
    message: str


class CaseCreateRequest(BaseModel):
    name: str
    case_id: Optional[str] = Field(
        default=None,
        description="If omitted, a case_id is generated from the name.",
    )


class CaseSummary(BaseModel):
    case_id: str
    name: str
    created_at: str
    source_count: int

class EntityType(str, Enum):
    PERSON = "PERSON"
    PHONE = "PHONE"
    ACCOUNT = "ACCOUNT"
    VEHICLE = "VEHICLE"
    LOCATION = "LOCATION"
    ORGANIZATION = "ORGANIZATION"


class ExtractedEntity(BaseModel):
    """
    A single entity extracted from a ParsedDocument.

    Stage 4 produces these objects. Later stages can resolve duplicate
    entities, create graph nodes, and attach relationships without
    needing to understand the original file format.
    """

    entity_type: EntityType
    value: str
    normalized_value: str

    case_id: str
    source_id: str

    evidence: str
    timestamp: Optional[str] = None

    confidence: float = Field(ge=0.0, le=1.0)


class EntityExtractionResult(BaseModel):
    """
    Complete Stage 4 output for one ParsedDocument.
    """

    case_id: str
    source_id: str
    source_type: SourceType
    entities: list[ExtractedEntity]

class EntityExtractionResult(BaseModel):
    case_id: str
    source_id: str
    source_type: SourceType
    entities: list[ExtractedEntity]


class RelationshipType(str, Enum):
    CALLED = "CALLED"
    TRANSFERRED_TO = "TRANSFERRED_TO"
    OWNS = "OWNS"
    USES = "USES"
    SEEN_AT = "SEEN_AT"
    LOCATED_AT = "LOCATED_AT"
    VISITED = "VISITED"
    IDENTIFIED_AS = "IDENTIFIED_AS"
    MENTIONED_IN = "MENTIONED_IN"


class ExtractedRelationship(BaseModel):
    from_entity_type: EntityType
    from_value: str
    from_normalized_value: str

    relationship_type: RelationshipType

    to_entity_type: EntityType
    to_value: str
    to_normalized_value: str

    case_id: str
    source_id: str

    evidence: str
    timestamp: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)


class RelationshipExtractionResult(BaseModel):
    case_id: str
    source_id: str
    source_type: SourceType
    relationships: list[ExtractedRelationship]

class ResolvedEntity(BaseModel):
    canonical_id: str

    entity_type: EntityType
    canonical_value: str
    normalized_value: str

    case_id: str

    aliases: list[str] = Field(default_factory=list)

    source_ids: list[str] = Field(default_factory=list)

    mention_count: int = 1


class EntityResolutionResult(BaseModel):
    case_id: str

    entities: list[ResolvedEntity]

    entity_mappings: dict[str, str] = Field(default_factory=dict)