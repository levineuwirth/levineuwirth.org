#!/usr/bin/env python3
"""Post-build sweep: stamp the site-wide build time into every footer.

Why this exists
---------------
build/Contexts.hs binds $build-time$ to getCurrentTime at item-compile
time, but Hakyll caches outputs. Pages whose dependencies have not
changed are not recompiled, so the previously-rendered timestamp stays
on disk and the footer drifts per page. We want one site-wide
"last built at" stamp, so this script walks _site/**/*.html after
Hakyll runs and rewrites the contents of every wrapped element.

Format must match build/Contexts.hs:buildTimeField exactly so a fresh
build (where Hakyll renders the timestamp itself) and the sweep agree.
"""
from __future__ import annotations

import os
import re
import sys
from datetime import datetime, timezone


def ordinal_suffix(day: int) -> str:
    if 11 <= day <= 13:
        return "th"
    return {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")


def format_now() -> str:
    now = datetime.now(timezone.utc)
    return (
        f"{now.strftime('%A, %B')} "
        f"{now.day}{ordinal_suffix(now.day)}, "
        f"{now.strftime('%Y %H:%M:%S')}"
    )


PATTERN = re.compile(
    rb'(<span class="footer-build-time" data-build-time>)[^<]*(</span>)'
)


def stamp_file(path: str, replacement_bytes: bytes) -> bool:
    with open(path, "rb") as f:
        data = f.read()
    new_data, count = PATTERN.subn(
        lambda m: m.group(1) + replacement_bytes + m.group(2),
        data,
    )
    if count and new_data != data:
        # Write to a sibling temp file and os.replace so an interrupt
        # mid-write never leaves a truncated deployed HTML file.
        tmp = path + ".stamp-tmp"
        try:
            with open(tmp, "wb") as f:
                f.write(new_data)
            os.replace(tmp, path)
        except BaseException:
            try:
                os.unlink(tmp)
            except FileNotFoundError:
                pass
            raise
        return True
    return False


def main(root: str) -> int:
    if not os.path.isdir(root):
        print(f"stamp-build-time: {root} not found", file=sys.stderr)
        return 1
    timestamp = format_now().encode("utf-8")
    rewritten = 0
    scanned = 0
    for dirpath, _, files in os.walk(root):
        for name in files:
            if not name.endswith(".html"):
                continue
            scanned += 1
            if stamp_file(os.path.join(dirpath, name), timestamp):
                rewritten += 1
    print(f"stamp-build-time: rewrote {rewritten}/{scanned} HTML files")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "_site"))
