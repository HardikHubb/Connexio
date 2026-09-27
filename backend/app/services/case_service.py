"""
Tracks which cases exist and what's been ingested into each one.

This is intentionally a flat JSON manifest per case, not a database table.
A case, at this stage, is just "a folder with a name and a list of
sources" — reaching for Postgres for that would be exactly the kind of
unnecessary infrastructure the project spec warns against. If case
metadata grows real query needs later (filtering, joins across users),
this is the seam where it'd move into Postgres without touching the
ingestion or extraction code above it.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings
from app.models.schemas import CaseSummary


class CaseNotFoundError(Exception):
    pass


class CaseAlreadyExistsError(Exception):
    pass


def _storage_root() -> Path:
    return Path(settings.storage_dir)


def _case_dir(case_id: str) -> Path:
    return _storage_root() / case_id


def _manifest_path(case_id: str) -> Path:
    return _case_dir(case_id) / "manifest.json"


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", name.strip().lower()).strip("-")
    return slug or "case"


def case_exists(case_id: str) -> bool:
    return _manifest_path(case_id).exists()


def create_case(name: str, case_id: str | None = None) -> CaseSummary:
    resolved_id = case_id or _slugify(name)

    if case_exists(resolved_id):
        raise CaseAlreadyExistsError(f"Case '{resolved_id}' already exists.")

    case_dir = _case_dir(resolved_id)
    (case_dir / "raw").mkdir(parents=True, exist_ok=True)
    (case_dir / "parsed").mkdir(parents=True, exist_ok=True)

    # Case 101 is the project's synthetic demonstration case.
    # Its four seed sources are already part of the project dataset.
    if resolved_id == "101":
        sources = [
            "FIR-967bb0a1",
            "CDR-e30d3a34",
            "TRANSACTION-9123c1c9",
            "VEHICLE-8618e9cd",
        ]
    else:
        sources = []

    manifest = {
        "case_id": resolved_id,
        "name": name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "sources": sources,
    }

    _manifest_path(resolved_id).write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )

    return CaseSummary(
        case_id=resolved_id,
        name=name,
        created_at=manifest["created_at"],
        source_count=len(sources),
    )

def get_case(case_id: str) -> dict:
    if not case_exists(case_id):
        raise CaseNotFoundError(f"Case '{case_id}' does not exist.")
    return json.loads(_manifest_path(case_id).read_text(encoding="utf-8"))


def list_cases() -> list[CaseSummary]:
    root = _storage_root()
    if not root.exists():
        return []

    summaries = []
    for entry in sorted(root.iterdir()):
        manifest_file = entry / "manifest.json"
        if manifest_file.exists():
            manifest = json.loads(
                manifest_file.read_text(encoding="utf-8")
            )
            summaries.append(
                CaseSummary(
                    case_id=manifest["case_id"],
                    name=manifest["name"],
                    created_at=manifest["created_at"],
                    source_count=len(manifest.get("sources", [])),
                )
            )
    return summaries


def register_source(case_id: str, source_id: str) -> None:
    """Called by ingestion_service after a file is successfully parsed."""
    manifest = get_case(case_id)
    if source_id not in manifest["sources"]:
        manifest["sources"].append(source_id)
    _manifest_path(case_id).write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def raw_dir(case_id: str) -> Path:
    return _case_dir(case_id) / "raw"


def parsed_dir(case_id: str) -> Path:
    return _case_dir(case_id) / "parsed"
