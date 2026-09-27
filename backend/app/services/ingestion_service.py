"""
Stage 3 core logic. This is what a later "Add Data" frontend button
(Stage 9) actually calls into, via the /api/cases/{case_id}/ingest route.

Flow for one uploaded file:
  1. Save the raw bytes to storage/{case_id}/raw/{source_type}/{filename}
     — kept forever, this is what the evidence panel opens later.
  2. Route to a parser by file extension:
       .csv        -> csv_parser  (CDR, TRANSACTION, VEHICLE, LOCATION)
       .txt        -> text_parser (FIR, REPORT)
  3. Wrap the parser's output in a ParsedDocument (the Stage 4 contract).
  4. Persist the ParsedDocument as JSON next to the raw file, so Stage 4
     can be built and tested independently of the upload endpoint.
  5. Register the source_id against the case manifest.

Nothing here is hardcoded to the seed dataset's specific content — it
only assumes the *shapes* (CSV has columns, text files have prose),
which is exactly the assumption that will still hold for the team's
real synthetic dataset later.
"""

import json
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.models.schemas import DocumentFormat, IngestResponse, ParsedDocument, SourceType
from app.services import case_service
from app.services.parsers.csv_parser import UnsupportedFileFormatError as CsvUnsupported
from app.services.parsers.csv_parser import parse_csv_file
from app.services.parsers.text_parser import UnsupportedFileFormatError as TextUnsupported
from app.services.parsers.text_parser import parse_text_file

TABULAR_SOURCE_TYPES = {SourceType.CDR, SourceType.TRANSACTION, SourceType.VEHICLE, SourceType.LOCATION}
TEXT_SOURCE_TYPES = {SourceType.FIR, SourceType.REPORT}


class IngestionError(Exception):
    pass


def _generate_source_id(source_type: SourceType) -> str:
    return f"{source_type.value}-{uuid.uuid4().hex[:8]}"


def _save_raw_bytes(case_id: str, source_type: SourceType, filename: str, file_bytes: bytes) -> Path:
    dest_dir = case_service.raw_dir(case_id) / source_type.value
    dest_dir.mkdir(parents=True, exist_ok=True)

    dest_path = dest_dir / filename
    dest_path.write_bytes(file_bytes)

    return dest_path


def ingest_bytes(case_id: str, source_type: SourceType, filename: str, file_bytes: bytes) -> IngestResponse:
    """
    Core ingestion logic, independent of how the bytes arrived. The API
    route (real HTTP upload) and scripts/ingest_seed_data.py (loading
    local files with no frontend needed yet) both call this — there's
    exactly one code path that does parsing + storage + registration.
    """
    if not case_service.case_exists(case_id):
        raise IngestionError(f"Case '{case_id}' does not exist — create it before ingesting files.")

    raw_path = _save_raw_bytes(case_id, source_type, filename, file_bytes)
    source_id = _generate_source_id(source_type)

    try:
        if source_type in TABULAR_SOURCE_TYPES:
            rows = parse_csv_file(raw_path)
            doc = ParsedDocument(
                source_id=source_id,
                case_id=case_id,
                source_type=source_type,
                original_filename=filename,
                format=DocumentFormat.TABULAR,
                rows=rows,
                row_count=len(rows),
                raw_file_path=str(raw_path),
            )
        elif source_type in TEXT_SOURCE_TYPES:
            text = parse_text_file(raw_path)
            doc = ParsedDocument(
                source_id=source_id,
                case_id=case_id,
                source_type=source_type,
                original_filename=filename,
                format=DocumentFormat.TEXT,
                text=text,
                raw_file_path=str(raw_path),
            )
        else:
            raise IngestionError(f"Unhandled source_type '{source_type}'.")
    except (CsvUnsupported, TextUnsupported, ValueError) as exc:
        raise IngestionError(str(exc)) from exc

    parsed_path = case_service.parsed_dir(case_id) / f"{source_id}.json"
    parsed_path.write_text(doc.model_dump_json(indent=2), encoding="utf-8")

    case_service.register_source(case_id, source_id)

    return IngestResponse(
        source_id=source_id,
        case_id=case_id,
        source_type=source_type,
        format=doc.format,
        row_count=doc.row_count,
        message=f"Parsed and stored {filename} as {source_id}.",
    )


def ingest_file(case_id: str, source_type: SourceType, upload: UploadFile) -> IngestResponse:
    """Thin adapter for the FastAPI route — reads the upload and delegates to ingest_bytes."""
    return ingest_bytes(case_id, source_type, upload.filename, upload.file.read())


def get_parsed_document(case_id: str, source_id: str) -> ParsedDocument:
    parsed_path = case_service.parsed_dir(case_id) / f"{source_id}.json"
    if not parsed_path.exists():
        raise IngestionError(f"No parsed document '{source_id}' found for case '{case_id}'.")
    data = json.loads(parsed_path.read_text(encoding="utf-8"))
    return ParsedDocument(**data)


def list_parsed_documents(case_id: str) -> list[ParsedDocument]:
    manifest = case_service.get_case(case_id)
    return [get_parsed_document(case_id, source_id) for source_id in manifest["sources"]]
