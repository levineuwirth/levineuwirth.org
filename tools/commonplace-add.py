#!/usr/bin/env python3
"""Add a passage to the commonplace book (data/commonplace.yaml).

  tools/commonplace-add.py                      ask for everything
  tools/commonplace-add.py --clipboard          the passage from the clipboard
  tools/commonplace-add.py -a "Fyodor Dostoevsky" -s "Notes from Underground" \\
      -t "the will, reason" < passage.txt       the passage from standard input

The passage and its attribution are required; the source, a link for it,
themes and a commentary are not. The entry is appended as WRITING.md's
"Commonplace book" sets it out, dated today unless --date says otherwise,
after the file's own entries, whose bytes are left as they are. A passage
already in the book is refused. The new book is written beside the old,
read back, and only then put in its place, under a lock that another add
waits for, so an interruption or a second add at once loses nothing.

`make build` puts it on /commonplace.html. --dry-run prints the entry and
writes nothing.
"""

from __future__ import annotations

import argparse
import contextlib
import datetime
import fcntl
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOK = ROOT / "data" / "commonplace.yaml"


def normalized(text: str) -> str:
    """A passage as compared for duplicates: case, spacing and punctuation
    do not make it another passage. Apostrophes and full stops are dropped,
    so that a word keeps together ("Don't" is "Dont", "U.S." is "US"); other
    punctuation (commas, dashes, quotation marks) is a space between words;
    symbols (x < y, a + b) are kept, for they are what the passage says."""
    kept = []
    for ch in text.casefold():
        if ch in "'\u2018\u2019\u02bc\u00b4`.":
            continue
        kept.append(" " if unicodedata.category(ch).startswith("P") else ch)
    return " ".join("".join(kept).split())


def passage(text: str) -> str:
    """The passage as the book keeps it: its lines as given, less trailing
    spaces, and less the lines that are then blank at either end."""
    lines = [line.rstrip() for line in text.splitlines()]
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


def quoted(value: str) -> str:
    """A string in YAML's double quotes (JSON's quoting is YAML's), so that
    nothing in it is read as another type or as syntax."""
    return json.dumps(value, ensure_ascii=False)


def entry(text: str, attribution: str, source: str = "", source_url: str = "",
          tags: list[str] | None = None, commentary: str = "", date: str = "") -> str:
    """The entry as the book's YAML, in WRITING.md's order of fields. The
    passage is a literal block with its indentation stated (|2-), so a
    passage whose lines begin indented keeps that indentation."""
    lines = ["- text: |2-"]
    lines += ["    " + line if line else "" for line in passage(text).split("\n")]
    lines.append(f"  attribution: {quoted(attribution)}")
    if source:
        lines.append(f"  source: {quoted(source)}")
    if source_url:
        lines.append(f"  source-url: {quoted(source_url)}")
    if tags:
        lines.append("  tags: [" + ", ".join(quoted(t) for t in tags) + "]")
    if commentary:
        lines.append(f"  commentary: {quoted(commentary.strip())}")
    if date:
        lines.append(f"  date-added: {date}")
    return "\n".join(lines) + "\n"


def expected(text: str, attribution: str, source: str = "", source_url: str = "",
             tags: list[str] | None = None, commentary: str = "", date: str = "") -> dict:
    """The entry as it must read back."""
    out = {"text": passage(text), "attribution": attribution}
    if source:
        out["source"] = source
    if source_url:
        out["source-url"] = source_url
    if tags:
        out["tags"] = list(tags)
    if commentary:
        out["commentary"] = commentary.strip()
    if date:
        out["date-added"] = datetime.date.fromisoformat(date)
    return out


def themes(value: str) -> list[str]:
    """Comma-separated themes, as lowercase words."""
    return [t.strip().lower() for t in value.split(",") if t.strip()]


def parse(data: bytes, where: object) -> list:
    import yaml   # the site's .venv has it
    loaded = yaml.safe_load(data.decode("utf-8-sig")) if data.strip() else []
    if loaded is None:
        return []
    if not isinstance(loaded, list):
        raise SystemExit(f"{where}: not a list of entries")
    return loaded


def load(path: Path) -> list:
    return parse(path.read_bytes() if path.exists() else b"", path)


@contextlib.contextmanager
def locked(directory: Path):
    """The book's directory, locked against another add for as long as
    this one reads, writes and replaces the book."""
    fd = os.open(directory, os.O_RDONLY)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def add(path: Path, block: str, text: str, want: dict) -> None:
    """Append `block` to the book at `path`. Under a lock, from the first
    read to the replacement: a passage already in the book is refused; the
    new book is the old one's bytes unchanged, then the entry, in the old
    one's line endings, written to a temporary file of its own beside it,
    read back (every old entry as it was, and this one exactly), and only
    then put in the book's place. Nothing is written to the book until it
    is right, and nothing else is touched."""
    with locked(path.parent):
        before = path.read_bytes() if path.exists() else b""
        existing = parse(before, path)
        if any(normalized(str(e.get("text", ""))) == normalized(text) for e in existing if isinstance(e, dict)):
            raise SystemExit("commonplace-add: that passage is already in the book")
        newline = b"\r\n" if b"\r\n" in before else b"\n"
        prefix = before
        if prefix and not prefix.endswith(b"\n"):
            prefix += newline
        if prefix.strip():
            prefix += newline
        data = prefix + block.encode("utf-8").replace(b"\n", newline)
        fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
        try:
            with os.fdopen(fd, "wb") as out:
                out.write(data)
                out.flush()
                os.fsync(out.fileno())
            if path.exists():
                shutil.copymode(path, tmp)
            try:
                after = parse(Path(tmp).read_bytes(), tmp)
            except Exception:
                after = None
            if not after or after[:-1] != existing or after[-1:] != [want]:
                raise SystemExit("commonplace-add: not added, the entry did not read back as written; "
                                 "the book is as it was")
            os.replace(tmp, path)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise


def clipboard() -> str:
    for cmd in (["wl-paste", "--no-newline"], ["xclip", "-selection", "clipboard", "-o"], ["pbpaste"]):
        if shutil.which(cmd[0]):
            return subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    raise SystemExit("commonplace-add: no clipboard tool (wl-paste, xclip or pbpaste)")


def ask(prompt: str, required: bool = False) -> str:
    while True:
        value = input(prompt).strip()
        if value or not required:
            return value


def ask_passage() -> str:
    print("The passage, as many lines as it has; a line with only a full stop ends it:")
    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip() == ".":
            break
        lines.append(line)
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("-a", "--attribution", help="who wrote it")
    parser.add_argument("-s", "--source", default=None, help="the work it is from")
    parser.add_argument("-u", "--source-url", default=None, help="a link for the source")
    parser.add_argument("-t", "--tags", default=None, help="themes, comma-separated")
    parser.add_argument("-c", "--commentary", default=None, help="a remark of your own")
    parser.add_argument("--date", default=datetime.date.today().isoformat(), help="date added (default today)")
    parser.add_argument("--clipboard", action="store_true", help="take the passage from the clipboard")
    parser.add_argument("--dry-run", action="store_true", help="print the entry; write nothing")
    parser.add_argument("--book", type=Path, default=BOOK, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    # fromisoformat also takes 20261126 and 2026-W48-4; the book takes the
    # date as written, and reads only YYYY-MM-DD back as a date.
    try:
        valid = datetime.date.fromisoformat(args.date).isoformat() == args.date
    except ValueError:
        valid = False
    if not valid:
        parser.error(f"--date: not a date of the calendar, as YYYY-MM-DD: {args.date}")
    if args.attribution is not None and not args.attribution.strip():
        parser.error("--attribution: empty")

    interactive = sys.stdin.isatty()
    if args.clipboard:
        text = clipboard()
    elif not interactive:
        text = sys.stdin.read()
    else:
        text = ask_passage()
    if not passage(text):
        raise SystemExit("commonplace-add: no passage")
    if args.clipboard and interactive:
        print(text.strip(), "\n")

    attribution = (args.attribution or "").strip() or (ask("Attribution: ", required=True) if interactive else "")
    if not attribution:
        raise SystemExit("commonplace-add: --attribution is required")
    source = (args.source if args.source is not None else (ask("Source (optional): ") if interactive else "")).strip()
    source_url = (args.source_url if args.source_url is not None else (ask("Link for it (optional): ") if interactive and source else "")).strip()
    if args.tags is None and interactive:
        known = sorted({t for e in load(args.book) if isinstance(e, dict) for t in (e.get("tags") or [])})
        hint = f" (in use: {', '.join(known)})" if known else ""
        tags = themes(ask(f"Themes, comma-separated (optional){hint}: "))
    else:
        tags = themes(args.tags or "")
    commentary = (args.commentary if args.commentary is not None else (ask("Commentary (optional): ") if interactive else "")).strip()

    block = entry(text, attribution, source, source_url, tags, commentary, args.date)
    if args.dry_run:
        print(block, end="")
        return 0
    add(args.book, block, text, expected(text, attribution, source, source_url, tags, commentary, args.date))
    print(f"commonplace-add: added to {args.book.relative_to(ROOT) if args.book.is_relative_to(ROOT) else args.book}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
