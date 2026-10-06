#!/usr/bin/env python3
"""What the last finished build was built from: a manifest of its inputs.

`make build` removes data/build-inputs.json when it starts and, as its last
step, records every file under the build inputs it is given (the Makefile's
$(DIRTY_PATHS) and content/) with its size and modification time. A build
that stops partway therefore leaves no manifest. `check` compares the tree
with it and lists the files changed, added or removed since; the browser
tests (tests/_browser.py) refuse to run against a _site whose inputs have
moved on.

Size and mtime, not a hash: content/ is a gigabyte of photographs, and a
file rewritten with the same bytes costs only a rebuild.

    python3 tools/build-inputs.py record build templates static ...
    python3 tools/build-inputs.py check     # exit 1, with a list, if stale
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "build-inputs.json"

# Under the inputs, but not what _site is built from.
EXCLUDE = (
    "data/build-inputs.json",      # this manifest
    "data/build-inputs.json.tmp",  # its write in progress, left by one interrupted
    "data/.compress-cache",        # compress-assets.sh's cache of compressed outputs
    "data/.site-build.lock",       # truncated by tools/with-lock.sh on every locked target
    "data/sign-manifest.txt",      # written by `make sign`, after the build
    "nginx",                       # served configuration; the browser tests read it as it is
    "tools/browser",               # the browser harness
)
# Bytecode that Python writes beside a tool whenever something imports it.
SKIP_DIRS = {"__pycache__"}


def excluded(rel: str) -> bool:
    return any(rel == e or rel.startswith(e + "/") for e in EXCLUDE)


def snapshot(paths: list[str]) -> dict[str, list[int]]:
    """Each file under `paths` (relative to the repository), as
    path -> [size, mtime_ns]."""
    files: dict[str, list[int]] = {}

    def add(path: Path) -> None:
        rel = path.relative_to(ROOT).as_posix()
        if not excluded(rel):
            st = path.stat()
            files[rel] = [st.st_size, st.st_mtime_ns]

    for name in paths:
        top = ROOT / name
        if top.is_file():
            add(top)
            continue
        for directory, dirs, names in os.walk(top):
            here = Path(directory)
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS
                       and not excluded((here / d).relative_to(ROOT).as_posix())]
            for n in names:
                if (here / n).is_file():
                    add(here / n)
    return files


def record(paths: list[str]) -> None:
    MANIFEST.parent.mkdir(exist_ok=True)
    tmp = MANIFEST.with_suffix(".json.tmp")
    tmp.write_text(json.dumps({"paths": paths, "files": snapshot(paths)}), encoding="utf-8")
    tmp.replace(MANIFEST)


def stale() -> list[str]:
    """What differs from the manifest, one "changed|added|removed <path>"
    per file; a single line saying so when there is no manifest."""
    if not MANIFEST.is_file():
        return [f"no {MANIFEST.relative_to(ROOT)}: run `make build` (one that stops partway leaves none)"]
    built = json.loads(MANIFEST.read_text(encoding="utf-8"))
    now = snapshot(built["paths"])
    then = built["files"]
    return ([f"changed {p}" for p in sorted(now.keys() & then.keys()) if now[p] != then[p]]
            + [f"added {p}" for p in sorted(now.keys() - then.keys())]
            + [f"removed {p}" for p in sorted(then.keys() - now.keys())])


def main(argv: list[str]) -> int:
    if len(argv) >= 2 and argv[0] == "record":
        record(argv[1:])
        return 0
    if argv == ["check"]:
        differ = stale()
        for line in differ[:50]:
            print(line)
        if len(differ) > 50:
            print(f"... and {len(differ) - 50} more")
        return 1 if differ else 0
    print("usage: build-inputs.py record PATH... | check", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
