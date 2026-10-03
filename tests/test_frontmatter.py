#!/usr/bin/env python3
"""Front-matter values the build would silently drop or misrender.

The epistemic footer reads a dozen front-matter fields, and almost every one
fails soft. build/Marks.hs maps an unknown scope, novelty, practicality or
result-shape to Nothing, so a typo makes that row vanish; Contexts.dotsField
clamps an importance of 7 to five dots and drops a 0; a confidence of "85%"
leaves the trust score blank; an unknown peer-status is a line on stderr; a
history entry without a date disappears from the version history. And
`status` takes any string at all, which is how "Working system", a value the
colophon never defined, shipped on the Proof Broker essay until 2026-10-01.

None of these fail a build, so this suite reads the front matter of every
page under content/ (drafts excepted: they never ship) and fails instead.

Each vocabulary is read from where the site defines it rather than copied
here: status from the colophon, which is the published contract; the
orientation fields from build/Marks.hs; peer-status from build/Contexts.hs.

Run with: ``make test`` (or ``python3 -m unittest tests.test_frontmatter``).
"""

from __future__ import annotations

import datetime
import re
import unittest
from functools import lru_cache
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - `make validate` requires .venv
    yaml = None

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTENT = REPO_ROOT / "content"
MARKS_HS = REPO_ROOT / "build" / "Marks.hs"
CONTEXTS_HS = REPO_ROOT / "build" / "Contexts.hs"
COLOPHON = CONTENT / "colophon.md"

# Hakyll's own delimiters: a leading `---` line, closed by `---` or `...`.
FRONT_MATTER_RE = re.compile(r"\A---[ \t]*\n(.*?)\n(?:---|\.\.\.)[ \t]*(?:\n|\Z)", re.S)
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# The fields that only render inside the epistemic footer, which appears
# only when `status` is set (colophon, "Epistemic profile").
FOOTER_ONLY = (
    "confidence", "importance", "evidence", "scope", "novelty",
    "practicality", "result-shape", "confidence-history",
)

# Contexts.isProvedConfidence / Marks.isProvedConfidenceM.
PROVED = ("proved", "proven")


# ---------------------------------------------------------------------------
# Vocabularies, read from their definitions
# ---------------------------------------------------------------------------


def haskell_string_list(path: Path, name: str) -> list[str]:
    """The string literals of a top-level or where-bound `name = [...]`."""
    text = path.read_text(encoding="utf-8")
    m = re.search(rf"^\s*{re.escape(name)}\s*=\s*\[(.*?)\]", text, re.M | re.S)
    if not m:
        raise AssertionError(f"{path.name}: no `{name} = [...]` definition")
    return re.findall(r'"([^"]*)"', m.group(1))


def colophon_statuses() -> list[str]:
    """The italicised values in the colophon's **Status** definition."""
    text = COLOPHON.read_text(encoding="utf-8")
    m = re.search(r"^- \*\*Status\*\*[^:\n]*:\s*([^\n]*?\*)\.", text, re.M)
    if not m:
        raise AssertionError("colophon.md: no **Status** vocabulary line")
    return re.findall(r"\*([^*]+)\*", m.group(1))


VOCABULARIES = {
    "scope": lambda: haskell_string_list(MARKS_HS, "scopeValues"),
    "novelty": lambda: haskell_string_list(MARKS_HS, "noveltyValues"),
    "practicality": lambda: haskell_string_list(MARKS_HS, "practicalityValues"),
    "result-shape": lambda: haskell_string_list(MARKS_HS, "resultShapeValues"),
    "peer-status": lambda: haskell_string_list(CONTEXTS_HS, "knownPeerStatuses"),
}


# ---------------------------------------------------------------------------
# The corpus
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def published_front_matter() -> tuple[list[tuple[str, dict]], list[str]]:
    """(page, front matter) for every published Markdown page, plus any
    front matter that does not parse."""
    pages: list[tuple[str, dict]] = []
    unparsable: list[str] = []
    for path in sorted(CONTENT.rglob("*.md")):
        rel = path.relative_to(REPO_ROOT).as_posix()
        if "drafts" in path.relative_to(CONTENT).parts:
            continue
        m = FRONT_MATTER_RE.match(path.read_text(encoding="utf-8"))
        if not m:
            continue
        try:
            meta = yaml.safe_load(m.group(1))
        except yaml.YAMLError as exc:
            unparsable.append(f"{rel}: {exc}".splitlines()[0])
            continue
        if isinstance(meta, dict):
            pages.append((rel, meta))
    return pages, unparsable


def as_int(value) -> int | None:
    """An integer the way Hakyll's lookupString + readMaybe sees one."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and re.fullmatch(r"\s*-?\d+\s*", value):
        return int(value)
    return None


def is_iso_date(value) -> bool:
    if isinstance(value, datetime.date):
        return True
    return isinstance(value, str) and bool(ISO_DATE_RE.match(value.strip()))


@unittest.skipIf(yaml is None, "PyYAML not installed — run `uv sync`")
class FrontMatterTests(unittest.TestCase):
    """Every published page's front matter speaks the site's vocabulary."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.pages, cls.unparsable = published_front_matter()

    def assertNoViolations(self, violations: list[str], what: str) -> None:
        self.assertEqual(
            violations, [],
            f"{len(violations)} page(s) with {what}:\n  " + "\n  ".join(violations),
        )

    def values(self, key: str):
        for rel, meta in self.pages:
            if key in meta and meta[key] is not None:
                yield rel, meta[key]

    # -- the readers themselves -------------------------------------------

    def test_corpus_and_vocabularies_are_found(self) -> None:
        # A parser that silently finds nothing would pass every test below.
        self.assertGreater(len(self.pages), 100)
        self.assertIn("Working model", colophon_statuses())
        self.assertIn("Durable", colophon_statuses())
        for field, load in VOCABULARIES.items():
            with self.subTest(field=field):
                self.assertGreaterEqual(len(load()), 3, field)

    def test_front_matter_parses(self) -> None:
        self.assertNoViolations(self.unparsable, "front matter that is not YAML")

    # -- epistemic fields -------------------------------------------------

    def test_status_is_in_the_colophon_vocabulary(self) -> None:
        # Exact spelling: the footer prints the value verbatim.
        allowed = colophon_statuses()
        bad = [f"{rel}: status {v!r} (colophon: {', '.join(allowed)})"
               for rel, v in self.values("status") if v not in allowed]
        self.assertNoViolations(bad, "an undefined status")

    def test_confidence_is_a_percentage_or_proved(self) -> None:
        bad = []
        for rel, v in self.values("confidence"):
            n = as_int(v)
            if n is None and not (isinstance(v, str) and v.strip().lower() in PROVED):
                bad.append(f"{rel}: confidence {v!r}")
            elif n is not None and not 0 <= n <= 100:
                bad.append(f"{rel}: confidence {v!r} outside 0–100")
        self.assertNoViolations(bad, "an unreadable confidence")

    def test_confidence_history_is_percentages_and_not_beside_proved(self) -> None:
        bad = []
        for rel, v in self.values("confidence-history"):
            if not isinstance(v, list) or not all(
                (n := as_int(x)) is not None and 0 <= n <= 100 for x in v
            ):
                bad.append(f"{rel}: confidence-history {v!r}")
        for rel, meta in self.pages:
            conf = meta.get("confidence")
            if (isinstance(conf, str) and conf.strip().lower() in PROVED
                    and meta.get("confidence-history") is not None):
                # Contexts.confidenceTrendField ignores the history with a
                # warning nobody reads.
                bad.append(f"{rel}: confidence-history beside confidence: {conf}")
        self.assertNoViolations(bad, "a confidence history the trend cannot use")

    def test_importance_and_evidence_are_on_the_five_point_scale(self) -> None:
        bad = []
        for key in ("importance", "evidence"):
            for rel, v in self.values(key):
                n = as_int(v)
                if n is None or not 1 <= n <= 5:
                    bad.append(f"{rel}: {key} {v!r}")
        self.assertNoViolations(bad, "a dot value off the 1–5 scale")

    def test_orientation_fields_use_the_build_vocabulary(self) -> None:
        bad = []
        for key, load in VOCABULARIES.items():
            allowed = load()
            for rel, v in self.values(key):
                # Marks.validate trims and lowercases before matching.
                if not isinstance(v, str) or v.strip().lower() not in allowed:
                    bad.append(f"{rel}: {key} {v!r} (one of: {', '.join(allowed)})")
        self.assertNoViolations(bad, "a value the build drops")

    def test_footer_fields_have_a_status_to_render_in(self) -> None:
        bad = []
        for rel, meta in self.pages:
            if meta.get("status") is None:
                orphans = [k for k in FOOTER_ONLY if meta.get(k) is not None]
                if orphans:
                    bad.append(f"{rel}: {', '.join(orphans)} without a status")
        self.assertNoViolations(bad, "epistemic fields that never render")

    # -- version history --------------------------------------------------

    def test_history_entries_carry_iso_dates(self) -> None:
        # Stability.parseFmHistory drops an entry without a date.
        bad = []
        for rel, v in self.values("history"):
            if not isinstance(v, list):
                bad.append(f"{rel}: history is a {type(v).__name__}, not a list")
                continue
            for entry in v:
                if not isinstance(entry, dict) or not is_iso_date(entry.get("date")):
                    bad.append(f"{rel}: history entry {entry!r}")
                elif entry.get("note") is not None and not isinstance(entry["note"], str):
                    bad.append(f"{rel}: history note {entry['note']!r} is not text")
        self.assertNoViolations(bad, "history entries the build drops")

    def test_revised_is_a_date_or_dated_entries(self) -> None:
        # Contexts.getRevisions accepts a bare date or a list of
        # {date, note}; anything else is dropped without a word.
        bad = []
        for rel, v in self.values("revised"):
            if is_iso_date(v):
                continue
            if not isinstance(v, list):
                bad.append(f"{rel}: revised {v!r}")
                continue
            for entry in v:
                if not isinstance(entry, dict) or not is_iso_date(entry.get("date")):
                    bad.append(f"{rel}: revised entry {entry!r}")
        self.assertNoViolations(bad, "revisions the build drops")

    def test_draft_flags_are_ones_the_build_reads(self) -> None:
        # build/Drafts.hs withholds any page whose `draft:` is true (YAML
        # true, or "true"/"yes"/"on"/"1") and publishes it otherwise. A value it
        # does not read as either — `draft: maybe`, `draft: [x]` — would
        # publish the page while looking like it holds it back (audit C06).
        truthy, falsy = {"true", "yes", "on", "1"}, {"false", "no", "off", "0"}
        bad = []
        for rel, value in self.values("draft"):
            if isinstance(value, bool):
                continue
            if isinstance(value, int) and value in (0, 1):
                continue
            if isinstance(value, str) and "".join(value.split()).lower() in truthy | falsy:
                continue
            bad.append(f"{rel}: draft: {value!r} is neither true nor false to the build")
        self.assertNoViolations(bad, "a draft flag the build cannot read")

if __name__ == "__main__":
    unittest.main()
