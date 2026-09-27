"""
Parses unstructured text files (FIR narratives, free-text reports).

Deliberately minimal right now: this handles .txt directly, which is all
the Stage 1 seed data needs. A real FIR often arrives as a scanned or
digital PDF — when that's actually needed, this is where a PDF-to-text
step (e.g. pypdf) gets added, as an explicit extension of this function,
not a silent assumption baked in now.
"""

from pathlib import Path


class UnsupportedFileFormatError(Exception):
    pass


def parse_text_file(file_path: Path) -> str:
    suffix = file_path.suffix.lower()

    if suffix == ".txt":
        return file_path.read_text(encoding="utf-8")

    if suffix == ".pdf":
        raise UnsupportedFileFormatError(
            "PDF parsing isn't implemented yet — only .txt is supported for "
            "FIR/Report uploads in this stage. Convert to .txt, or ask to "
            "add PDF support (pypdf) as a follow-up."
        )

    raise UnsupportedFileFormatError(
        f"Don't know how to parse a text document with extension '{suffix}'."
    )
