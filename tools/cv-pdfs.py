#!/usr/bin/env python3
"""cv-pdfs.py — what /cv.pdf and /resume.pdf were built from (audit C02).

The website's CV and résumé PDFs are built by hand (`make pdfs`, which
needs xelatex), from the same YAML under yaml-source/data that the Vita page
reads at every build. Nothing noticed when the two parted: on 2026-10-01
/cv.pdf was a month old and missing a publication the Vita page listed.

    tools/cv-pdfs.py write    # after `make pdfs`: record the inputs' digests
    tools/cv-pdfs.py check    # name each PDF whose inputs have changed since

The record, yaml-source/pdfs.sha256, holds one digest per PDF over its
inputs: build.py, layouts.yml, every data/*.yml, every template, and the
PDF's own variant file. check-site reads it too, as a warning. Checking
needs no LaTeX.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "yaml-source"
RECORD = SOURCE / "pdfs.sha256"
PDFS = {"cv": "static/cv.pdf", "resume": "static/resume.pdf"}


def inputs(variant: str, source: Path = SOURCE) -> list[Path]:
    files = [source / "build.py", source / "layouts.yml",
             source / "variants" / f"{variant}.yml"]
    files += sorted((source / "data").glob("*.yml"))
    files += sorted(p for p in (source / "templates").rglob("*") if p.is_file())
    return files


def digest(variant: str, source: Path = SOURCE) -> str:
    h = hashlib.sha256()
    for path in inputs(variant, source):
        h.update(path.relative_to(source).as_posix().encode() + b"\0")
        h.update(path.read_bytes() + b"\0")
    return h.hexdigest()


def recorded(record: Path = RECORD) -> dict[str, str]:
    if not record.is_file():
        return {}
    out = {}
    for line in record.read_text().splitlines():
        parts = line.split()
        if len(parts) == 2:
            out[parts[1]] = parts[0]
    return out


def stale(source: Path = SOURCE, record: Path = RECORD) -> list[str]:
    """One message per PDF whose inputs differ from what it was built from."""
    have = recorded(record)
    out = []
    for variant, pdf in PDFS.items():
        if variant not in have:
            out.append(f"{pdf}: no record of what it was built from — run `make pdfs`")
        elif have[variant] != digest(variant, source):
            out.append(f"{pdf}: built from older CV data than yaml-source/ holds — run `make pdfs`")
    return out


def write(source: Path = SOURCE, record: Path = RECORD) -> None:
    record.write_text("".join(f"{digest(v, source)}  {v}\n" for v in PDFS))


def main(argv: list[str]) -> int:
    if argv[1:] == ["write"]:
        write()
        print(f"cv-pdfs: recorded {', '.join(PDFS.values())} as built from yaml-source/ now")
        return 0
    if argv[1:] == ["check"]:
        problems = stale()
        for p in problems:
            print(f"cv-pdfs: {p}")
        return 1 if problems else 0
    print(__doc__.split("\n\n")[1], file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
