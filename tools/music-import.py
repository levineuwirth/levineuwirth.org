#!/usr/bin/env python3
"""music-import.py — bring a MuseScore score onto the site, and keep it there.

Score pages are derived artifacts, like the photography delivery JPEGs:
git carries each composition's index.md and a small score-source.yaml
manifest, and the pages themselves are regenerated from the engraver's
source and deployed through _site/. (See the note in .gitignore.)

    tools/music-import.py import <score.mscz> <slug> [--pdf]
    tools/music-import.py refresh [<slug> ...] [--force]
    tools/music-import.py check

import   Exports one SVG per page into content/music/<slug>/scores/,
         optionally a PDF, and writes score-source.yaml. For a new piece
         it also scaffolds index.md — title, year, duration, category and
         the movements (numeral, tempo, reader page, duration), all read
         from the score. An existing index.md is never touched; the
         computed movements are compared against it instead.
refresh  Re-exports pieces from their manifests (all of them by default):
         the fresh-clone path, and the re-engrave path.
check    Reports every composition whose score is missing or stale.

Why refresh refuses to change the page count without --force: unlike a
photo resize, a re-export is not reproducible. A newer MuseScore can
reflow the layout (the 3.6 → 4.x Violin Sonata moved whole systems), and
a reflow moves every movement's `page:` in index.md with it — a silent
wrong jump in the reader. The manifest records the page count and the
MuseScore version so that change is caught and named.

Source paths are stored relative to MUSIC_SCORES_DIR (default
~/Documents/Scores) so the manifest does not publish a home directory.

Requires MuseScore 4's `mscore` on PATH; runs headless.
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
MUSIC = ROOT / "content" / "music"
SCORES_DIR = Path(os.environ.get("MUSIC_SCORES_DIR", "~/Documents/Scores")).expanduser()
MANIFEST = "score-source.yaml"
PAGES = "scores"

# MuseScore writes note values into tempo text as SMuFL symbols, either as
# <sym> elements or as private-use characters. The frontmatter gets the
# readable Unicode forms; the page's Tempo Notes font draws both.
SMUFL = {
    "metNoteDoubleWhole": "𝅜", "metNoteWhole": "𝅝", "metNoteHalfUp": "𝅗𝅥",
    "metNoteQuarterUp": "♩", "metNote8thUp": "♪", "metNote16thUp": "𝅘𝅥𝅯",
    "metAugmentationDot": ".",
}
SMUFL_PUA = {
    "": "𝅜", "": "𝅝", "": "𝅗𝅥", "": "♩",
    "": "♪", "": "𝅘𝅥𝅯", "": ".",
}

# MuseScore instrument ids that are voices, not instruments.
VOICES = {"voice", "soprano", "mezzo-soprano", "alto", "contralto", "countertenor",
          "tenor", "baritone", "bass", "boy-soprano", "women", "men", "choir"}

# A printed subtitle that reads as a dedication. "for" is left out on
# purpose: "for string quartet" is a scoring, not a person.
DEDICATION = re.compile(r"^(to|für|pour|à|per|dedicated|in memoriam|in memory)\b", re.I)

ROMAN = re.compile(r"^\s*([IVXLC]+)\b\.?\s*(?:[-–—:]\s*)?(.*)$", re.S)


def die(msg: str) -> None:
    sys.exit(f"music-import: {msg}")


def warn(msg: str) -> None:
    print(f"music-import: {msg}", file=sys.stderr)


# ---------------------------------------------------------------------------
# MuseScore
# ---------------------------------------------------------------------------

def mscore(*args: str, timeout: int = 600) -> subprocess.CompletedProcess:
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    try:
        return subprocess.run(["mscore", *args], capture_output=True, text=True,
                              timeout=timeout, env=env, check=False)
    except FileNotFoundError:
        die("`mscore` (MuseScore 4) is not on PATH")


def mscore_version() -> str:
    out = mscore("--version").stdout.strip().splitlines()
    # "MuseScore4 4.7.5" → "MuseScore 4.7.5"
    ver = out[-1].split()[-1] if out else "unknown"
    return f"MuseScore {ver}"


def export_one(source: Path, target: Path) -> None:
    """One MuseScore export, checked on both counts: the exit status, and a
    non-empty file where it was asked for. Either alone can be fooled —
    an existing file satisfies a presence check after a failed export."""
    r = mscore("-o", str(target), str(source))
    made = target if target.suffix != ".svg" else \
        target.with_name(f"{target.stem}-1{target.suffix}")
    if r.returncode != 0 or not made.exists() or made.stat().st_size == 0:
        die(f"MuseScore could not export {target.suffix} from {source} "
            f"(exit {r.returncode}):\n{r.stderr[-2000:]}")


def export(source: Path, outdir: Path, pdf_name: str | None) -> dict:
    """Export everything a piece needs into outdir, a scratch directory.
    Nothing published is touched until all of it has succeeded."""
    export_one(source, outdir / "page.svg")
    pages = sorted(outdir.glob("page-*.svg"),
                   key=lambda p: int(p.stem.rsplit("-", 1)[1]))
    export_one(source, outdir / "score.mpos")
    pdf = None
    if pdf_name:
        pdf = outdir / pdf_name
        export_one(source, pdf)
    return {"pages": pages, "mpos": outdir / "score.mpos", "pdf": pdf}


def score_meta(source: Path) -> dict:
    import json
    r = mscore("--score-meta", str(source))
    try:
        m = json.loads(r.stdout)
    except ValueError:
        die(f"could not read metadata from {source}")
    return m.get("metadata", m)


# ---------------------------------------------------------------------------
# Structure: movements from section breaks, pages and times from .mpos
# ---------------------------------------------------------------------------

def read_mscx(source: Path) -> ET.Element:
    with zipfile.ZipFile(source) as z:
        name = next(n for n in z.namelist() if n.endswith(".mscx"))
        return ET.fromstring(z.read(name))


def text_of(el: ET.Element | None) -> str:
    """Flatten a MuseScore <text>, turning SMuFL note symbols into Unicode."""
    if el is None:
        return ""
    out = []
    def walk(e: ET.Element) -> None:
        if e.tag == "sym":
            out.append(SMUFL.get((e.text or "").strip(), ""))
        else:
            out.append(e.text or "")
            for c in e:
                walk(c)
        if e is not el:
            out.append(e.tail or "")
    walk(el)
    s = "".join(out)
    for pua, uni in SMUFL_PUA.items():
        s = s.replace(pua, uni)
    return re.sub(r"\s+", " ", s).strip()


def movements(root: ET.Element, mpos: Path, total_seconds: float) -> list[dict]:
    """One entry per section of the score: its opening measure's tempo
    text, reader page, and duration."""
    staff = root.find("Score/Staff")
    starts, tempos, idx = [0], {}, 0
    for el in staff:
        breaks = [b.findtext("subtype") for b in el.iter("LayoutBreak")]
        if el.tag != "Measure":
            # A section break can sit on the frame between movements.
            if "section" in breaks:
                starts.append(idx)
            continue
        for t in el.iter("Tempo"):
            tempos.setdefault(idx, text_of(t.find("text")))
        if "section" in breaks:
            starts.append(idx + 1)
        idx += 1
    starts = sorted({s for s in starts if s < idx})

    x = mpos.read_text()
    page = {int(a): int(b) for a, b in
            re.findall(r'<element id="(\d+)"[^>]*page="(\d+)"', x)}
    first = {}
    for a, b in re.findall(r'<event elid="(\d+)" position="(\d+)"', x):
        first.setdefault(int(a), int(b) / 1000)

    out = []
    for i, s in enumerate(starts):
        t0 = first.get(s, 0.0)
        t1 = first.get(starts[i + 1], total_seconds) if i + 1 < len(starts) else total_seconds
        numeral, tempo = "", tempos.get(s, "")
        m = ROMAN.match(tempo)
        if m:
            numeral, tempo = m.group(1) + ".", m.group(2).strip()
        out.append({"numeral": numeral, "tempo": tempo,
                    "page": page.get(s, 0) + 1, "seconds": max(t1 - t0, 0)})
    return out


def roman(n: int) -> str:
    out = ""
    for value, sym in ((10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")):
        while n >= value:
            out, n = out + sym, n - value
    return out


def stale_properties(root: ET.Element, meta: dict) -> list[str]:
    """Project properties that disagree with the printed title page.

    MuseScore copies File → Project properties along with Save As, so a
    score begun from another project carries that project's work title —
    and the work title is what a PDF export writes as the document title,
    shown in every viewer's title bar. Nothing on the page reads these;
    a downloaded PDF does."""
    props = {t.get("name"): (t.text or "").strip() for t in root.iter("metaTag")}
    frames = meta.get("textFramesData", {})
    printed_title = " ".join(frames.get("titles") or [])
    printed_sub = " ".join(frames.get("subtitles") or [])
    out = []
    if props.get("workTitle") and props["workTitle"] != printed_title:
        out.append(f"work title is {props['workTitle']!r}, the score is titled "
                   f"{printed_title!r} — a PDF export takes the work title")
    if props.get("subtitle") and props["subtitle"] != printed_sub:
        out.append(f"subtitle is {props['subtitle']!r}, the score prints "
                   f"{printed_sub or 'none'!r}")
    if props.get("composer") in ("Composer / arranger", "Composer"):
        out.append(f"composer is the placeholder {props['composer']!r}")
    return out


def minutes(seconds: float) -> str:
    """Durations as a programme gives them: to the half minute, or in
    seconds under a minute. Typed with straight quotes; the site sets
    them as primes."""
    if seconds < 60:
        return f'{round(seconds)}"'
    half = round(seconds / 30) / 2
    whole = int(half)
    return f"{whole}½'" if half - whole else f"{whole}'"


# ---------------------------------------------------------------------------
# Manifest and frontmatter
# ---------------------------------------------------------------------------

def source_key(source: Path) -> str:
    try:
        return str(source.resolve().relative_to(SCORES_DIR.resolve()))
    except ValueError:
        home = Path.home()
        s = source.resolve()
        return "~/" + str(s.relative_to(home)) if s.is_relative_to(home) else str(s)


def source_path(key: str) -> Path:
    p = Path(key).expanduser()
    return p if p.is_absolute() else SCORES_DIR / p


def read_manifest(slug: str) -> dict | None:
    f = MUSIC / slug / MANIFEST
    return yaml.safe_load(f.read_text()) if f.exists() else None


def write_manifest(slug: str, data: dict) -> None:
    head = ("# Written by tools/music-import.py. The score pages in scores/ are\n"
            "# not versioned; this records how to regenerate them:\n"
            f"#   tools/music-import.py refresh {slug}\n")
    body = yaml.safe_dump(data, sort_keys=False, allow_unicode=True)
    (MUSIC / slug / MANIFEST).write_text(head + body)


def frontmatter(slug: str) -> dict | None:
    f = MUSIC / slug / "index.md"
    if not f.exists():
        return None
    parts = f.read_text().split("---", 2)
    return yaml.safe_load(parts[1]) if len(parts) >= 3 else {}


def scaffold(slug: str, meta: dict, mvts: list[dict], pdf: bool, created: str) -> None:
    title = (meta.get("textFramesData", {}).get("titles") or [meta.get("title")])[0] or slug
    composer = " ".join(meta.get("textFramesData", {}).get("composers") or [meta.get("composer", "")])
    # "L. Neuwirth (2025)" or "(2022-2023)" on the title page — possibly
    # followed by an opus line — else the file's creation date. A range
    # gives the finishing year and a `composed:` span.
    span = re.search(r"\((\d{4})(?:\s*[-–]\s*(\d{2,4}))?", composer)
    year, composed = None, None
    if span:
        start, end = span.group(1), span.group(2)
        if end:
            end = start[:4 - len(end)] + end          # "2023-24" → 2024
        year = end or start
        if end and end != start:
            composed = f"{start} – {end}"
    elif re.match(r"\d{4}", created):
        year = created[:4]
    opus = (re.findall(r"\bop\.\s*(\d+[a-z]?(?:\s*(?:no\.|/)\s*\d+)?)", composer, re.I) or [None])[0]
    subtitle = " ".join(meta.get("textFramesData", {}).get("subtitles") or []).strip()
    parts = [p["name"] for p in meta.get("parts", [])]
    voices = sum(1 for p in meta.get("parts", []) if p.get("instrumentId") in VOICES)
    category = ("orchestral" if len(parts) > 12 else
                "choral" if voices >= 3 else
                "vocal" if voices else
                "solo" if len(parts) == 1 else "chamber")
    forces = ("orchestra" if category == "orchestral" else
              " and ".join(re.sub(r"\s+\d+$", "", p).lower() for p in parts))
    fm = {"title": title}
    # `date` is the page's publication date — the feed, the New page and
    # the footer's version history all read it — so a new page is dated
    # today. When the work was finished goes in `completed:`, by hand.
    fm["date"] = dt.date.today()
    if year:
        fm["year"] = int(year)
    if composed:
        fm["composed"] = composed
    if opus:
        fm["opus"] = opus
    if subtitle and DEDICATION.match(subtitle):
        fm["dedication"] = subtitle
    fm |= {"tags": ["music"], "instrumentation": forces,
           "duration": f"ca. {max(round(meta.get('duration', 0) / 60), 1)}'",
           "category": category, "score-dir": f"{PAGES}/"}
    if pdf:
        fm["pdf"] = f"{PAGES}/{slug}.pdf"
    if len(mvts) > 1:
        fm["movements"] = [
            {"name": m["numeral"] or f"{roman(i + 1)}.", **({"tempo": m["tempo"]} if m["tempo"] else {}),
             "page": m["page"], "duration": minutes(m["seconds"])}
            for i, m in enumerate(mvts)]
    text = "---\n" + yaml.safe_dump(fm, sort_keys=False, allow_unicode=True) + "---\n"
    (MUSIC / slug / "index.md").write_text(text)
    print(f"  scaffolded index.md — check the date, forces, and movement names,\n"
          f"  and add `scoring:` by hand: divisi does not show in the part list.")
    if subtitle and "dedication" not in fm:
        print(f"  the title page's subtitle {subtitle!r} was not used — place it by hand")
    if str(meta.get("hasLyrics")).lower() == "true" and not meta.get("poet"):
        print(f"  the score sets a text but credits no poet — add `text:` for the author")


def compare_movements(slug: str, mvts: list[dict]) -> None:
    """Check index.md's movements against the sections of this export.

    Counts are compared before anything else, and a score that has
    collapsed to a single section is a count mismatch like any other:
    five declared movements against one section means the reader's
    movement buttons all point into a score that no longer has them."""
    fm = frontmatter(slug) or {}
    declared = fm.get("movements") or []
    sections = len(mvts) if len(mvts) > 1 else 0   # one section = no movements
    if len(declared) != sections:
        have = f"{sections} sections" if sections else "a single section"
        warn(f"{slug}: index.md lists {len(declared)} movement(s), this export "
             f"has {have} — update `movements:`")
    if not declared or not sections:
        return
    for d, m in zip(declared, mvts):
        if d.get("page") != m["page"]:
            warn(f"{slug}: movement {d.get('name')!r} is at page {m['page']} "
                 f"in this export, index.md says {d.get('page')} — update `page:`")


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def install(slug: str, source: Path, pdf: bool, force: bool, new: bool) -> None:
    if not source.exists():
        die(f"no such score: {source}")
    dest = MUSIC / slug / PAGES
    old = read_manifest(slug)
    meta = score_meta(source)
    with tempfile.TemporaryDirectory(prefix="music-import-") as tmp:
        tmpdir = Path(tmp)
        got = export(source, tmpdir, f"{slug}.pdf" if pdf else None)
        n = len(got["pages"])
        version = mscore_version()
        if old and old.get("pages") != n and not force:
            die(f"{slug}: this export has {n} pages, the manifest records "
                f"{old.get('pages')} ({old.get('engraver')} → {version}). Every "
                f"movement `page:` may have moved. Re-run with --force, then fix index.md.")
        if old and old.get("engraver") != version:
            warn(f"{slug}: engraver changed, {old.get('engraver')} → {version}; "
                 f"page count unchanged, but look the pages over")
        root = read_mscx(source)
        mvts = movements(root, got["mpos"], float(meta.get("duration", 0)))
        created = next((t.text or "" for t in root.iter("metaTag")
                        if t.get("name") == "creationDate"), "")
        for problem in stale_properties(root, meta):
            warn(f"{slug}: {source.name} project properties: {problem} "
                 f"(fix in MuseScore: File → Project properties)")

        # Every export has succeeded; only now replace the published files.
        dest.mkdir(parents=True, exist_ok=True)
        for f in dest.glob("page-*.svg"):
            f.unlink()
        for f in got["pages"]:
            shutil.move(str(f), dest / f.name)
        if got["pdf"]:
            shutil.move(str(got["pdf"]), dest / got["pdf"].name)

    write_manifest(slug, {
        "source": source_key(source),
        "engraver": version,
        "pages": n,
        "pdf": pdf,
        "exported": dt.datetime.now().isoformat(timespec="seconds"),
    })
    print(f"{slug}: {n} pages from {source.name} ({version})")
    for m in mvts if len(mvts) > 1 else []:
        print(f"  {m['numeral'] or '·':5} page {m['page']:>4}  {minutes(m['seconds']):>5}  {m['tempo']}")
    if new and not (MUSIC / slug / "index.md").exists():
        scaffold(slug, meta, mvts, pdf, created)
    else:
        compare_movements(slug, mvts)


def cmd_import(a: argparse.Namespace) -> None:
    if not re.fullmatch(r"[a-z0-9-]+", a.slug):
        die(f"invalid slug {a.slug!r} (lowercase a-z, 0-9, hyphens)")
    install(a.slug, Path(a.score).expanduser(), a.pdf, a.force, new=True)


def pieces() -> list[str]:
    return sorted(p.parent.name for p in MUSIC.glob(f"*/{MANIFEST}"))


def cmd_refresh(a: argparse.Namespace) -> None:
    for slug in a.slugs or pieces():
        m = read_manifest(slug)
        if not m:
            warn(f"{slug}: no {MANIFEST}; import it first")
            continue
        install(slug, source_path(m["source"]), bool(m.get("pdf")), a.force, new=False)


def cmd_check(_: argparse.Namespace) -> None:
    problems = 0
    for index in sorted(MUSIC.glob("*/index.md")):
        slug = index.parent.name
        fm = frontmatter(slug) or {}
        if not fm.get("score-dir"):
            continue
        m = read_manifest(slug)
        have = len(list((MUSIC / slug / PAGES).glob("page-*.svg")))
        if not m:
            print(f"{slug}: declares a score but has no {MANIFEST}")
            problems += 1
        elif have != m.get("pages"):
            print(f"{slug}: {have} pages on disk, manifest records {m.get('pages')} "
                  f"— tools/music-import.py refresh {slug}")
            problems += 1
        elif not source_path(m["source"]).exists():
            print(f"{slug}: source {m['source']} is missing (pages present)")
        elif source_path(m["source"]).stat().st_mtime > \
                dt.datetime.fromisoformat(str(m["exported"])).timestamp():
            print(f"{slug}: {m['source']} changed since the {m['exported']} export")
    if problems:
        sys.exit(1)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("import", help="export a score and scaffold its page")
    p.add_argument("score"); p.add_argument("slug")
    p.add_argument("--pdf", action="store_true", help="also export a downloadable PDF")
    p.add_argument("--force", action="store_true", help="accept a changed page count")
    p.set_defaults(fn=cmd_import)
    p = sub.add_parser("refresh", help="re-export pieces from their manifests")
    p.add_argument("slugs", nargs="*")
    p.add_argument("--force", action="store_true", help="accept a changed page count")
    p.set_defaults(fn=cmd_refresh)
    p = sub.add_parser("check", help="report missing or stale score pages")
    p.set_defaults(fn=cmd_check)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
