"""
Parses structured tabular files (CDR, transactions, vehicle records).

Uses Python's built-in csv module rather than pandas on purpose — these
files are small, and it avoids pulling in a heavy dependency for
something a stdlib module already does cleanly. Every row becomes a
plain dict of column_name -> value (all strings; type coercion, e.g.
amount to float, timestamp to datetime, happens downstream in Stage 4
where the extraction logic knows what each column actually means).
"""

import csv
from pathlib import Path


class UnsupportedFileFormatError(Exception):
    pass


def parse_csv_file(file_path: Path) -> list[dict[str, str]]:
    suffix = file_path.suffix.lower()

    if suffix != ".csv":
        raise UnsupportedFileFormatError(
            f"Don't know how to parse a tabular document with extension '{suffix}'. "
            "Only .csv is supported in this stage."
        )

    with file_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = [row for row in reader]

    if not rows:
        raise ValueError(f"{file_path.name} parsed to zero rows — is the file empty?")

    return rows
