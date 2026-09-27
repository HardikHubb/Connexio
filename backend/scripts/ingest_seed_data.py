"""
Loads Case 101's seed files (Stage 1) through the real ingestion pipeline
(Stage 3) — creates the case if needed, then ingests each file with the
correct source_type. This exists so we can test/verify Stage 3 without
waiting for Stage 9's upload UI.

Run from backend/, with the venv active:

    python scripts/ingest_seed_data.py

Safe to re-run: it skips creating the case if it already exists, but note
it WILL re-ingest files (creating new source_ids) if run twice — this is
fine for now since Stage 3 doesn't dedupe by filename, only Stage 6/7's
entity resolution cares about duplicate content, not duplicate uploads.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.models.schemas import SourceType  # noqa: E402
from app.services import case_service  # noqa: E402
from app.services.ingestion_service import IngestionError, ingest_bytes  # noqa: E402

CASE_ID = "101"
CASE_NAME = "Operation Nexus"

SEED_DIR = Path(__file__).resolve().parent.parent / "seed_data" / "case_101"

FILES_TO_INGEST = [
    ("fir_101.txt", SourceType.FIR),
    ("cdr_101.csv", SourceType.CDR),
    ("transactions_101.csv", SourceType.TRANSACTION),
    ("vehicle_101.csv", SourceType.VEHICLE),
]


def main():
    if not case_service.case_exists(CASE_ID):
        case_service.create_case(name=CASE_NAME, case_id=CASE_ID)
        print(f"Created case '{CASE_ID}' ({CASE_NAME}).")
    else:
        print(f"Case '{CASE_ID}' already exists, reusing it.")

    for filename, source_type in FILES_TO_INGEST:
        file_path = SEED_DIR / filename
        if not file_path.exists():
            print(f"  SKIP {filename}: not found at {file_path}")
            continue

        try:
            result = ingest_bytes(CASE_ID, source_type, filename, file_path.read_bytes())
            detail = f"{result.row_count} rows" if result.row_count else "text document"
            print(f"  OK   {filename} -> {result.source_id} ({detail})")
        except IngestionError as exc:
            print(f"  FAIL {filename}: {exc}")

    print("\nDone. Verify with:")
    print(f"  GET http://localhost:8000/api/cases/{CASE_ID}/documents")


if __name__ == "__main__":
    main()
