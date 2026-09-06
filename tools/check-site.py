#!/usr/bin/env python3
"""check-site.py — post-build artifact gate for a finished ``_site/``.

Why this exists
---------------
``cabal run site -- build`` exits 0 on outcomes that must never reach the
VPS.  Three of them are confirmed defects rather than hypotheticals:

  * **S01** — the Hakyll provider is not Git's ignore policy, so a
    ``*.local.md`` note, a stray ``*.key``, or the local planning
    ``checklist.md`` can be published even though Git refuses to commit it.
  * **B03** — ``Filters.Viz`` and ``Filters.Score`` deliberately turn a
    rendering failure into page *content* (a ``viz-error`` div, a
    ``score-fragment--error`` figure), and ``Filters.FigureRefs`` renders an
    unresolved cross-reference as ``Figure ?``.  All three ship silently.
  * **B08** — a ``SITE_ENV=dev`` value inherited from the environment makes
    the build emit draft routes; deleting ``_site/drafts`` afterwards does
    not remove the links to it that other pages already grew.

This script inspects the *output*, not the exit status of the process that
made it.  It is stdlib-only and reads nothing outside the site directory, so
it can run against an isolated build, a release staging directory, or the
working ``_site``.

Usage
-----
    tools/check-site.py [SITE_DIR] [options]

    --allow-missing-404   downgrade a missing 404.html to a warning
                          (needed until the 404 route lands; see F12)
    --require-webp        make "JPEGs present but zero WebP" an error (P02)
    --warn-only           report everything but exit 0 — diagnostic use
                          only, never for a build that will be deployed
    --max-report N        cap the number of detail lines per check
    --quiet               print only the summary and any failures

Exit status is 1 when any error-level check fired, 0 otherwise.  Warnings
never fail the build; they are printed so a human notices the drift.
"""

from __future__ import annotations

import argparse
import fnmatch
import os
import re
import sys
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree

# ---------------------------------------------------------------------------
# What must never be published (S01)
# ---------------------------------------------------------------------------

# Matched against the file's basename, after stripping any transport sidecar
# suffix, so a compressed or signed copy of a private file is caught too.
PRIVATE_FILE_GLOBS = (
    "*.local.md",
    "*.local.html",
    "*.draft.*",
    "*.key",
    "*.pem",
    "*.p12",
    "*.pfx",
    ".env*",
    "*.env",
    "*~",
    "*.swp",
    "*.pyc",
    "*.tmp",
    "*.part",
    ".DS_Store",
    "credentials*",
    "checklist.md",
)

PRIVATE_DIR_NAMES = frozenset({"__pycache__"})

# compress-assets.sh and sign-site.sh write these alongside every artifact.
SIDECAR_SUFFIXES = (".gz", ".br", ".sig")

# ---------------------------------------------------------------------------
# Subtrees excluded from *page-content* checks
# ---------------------------------------------------------------------------
#
# These are not first-party pages, and scanning them produces only false
# positives:
#
#   source/    the published source mirror — HTML there is Hakyll *templates*
#              ($body$ placeholders, no resolvable image paths) and prose
#              files that legitimately contain the strings we grep for.
#   pdfjs/     Mozilla's vendored viewer.
#   pagefind/  generated search fragments.
#   archive/**/snapshot.html  monolith captures of third-party pages.
#
# The publication check (S01) deliberately does NOT skip these: the whole
# point of that check is that source/checklist.md is published.
CONTENT_SCAN_SKIP_PREFIXES = ("source/", "pdfjs/", "pagefind/")


def skip_for_content_scan(rel: str) -> bool:
    if rel.startswith(CONTENT_SCAN_SKIP_PREFIXES):
        return True
    if rel.startswith("archive/") and os.path.basename(rel) == "snapshot.html":
        return True
    return False


# ---------------------------------------------------------------------------
# Markers of a failed render that still exited 0 (B03)
# ---------------------------------------------------------------------------
#
# Exact strings from build/Filters/Viz.hs:errorBlock,
# build/Filters/Score.hs:errorBlock, and build/Filters/FigureRefs.hs:labelFor.
RENDER_FAILURE_MARKERS = (
    ('class="viz-error"', "figure/visualization script failed"),
    ("score-fragment--error", "score fragment missing or unreadable"),
    ("Figure ?</a>", "unresolved figure cross-reference"),
)

# B08 — a link into the draft tree, wherever it survived the drafts purge.
DRAFT_HREF_RE = re.compile(r"""(?:href|src)=["'](?:[^"']*/)?drafts/""")

IMG_TAG_RE = re.compile(r"<(img|source)\b([^>]*)>", re.IGNORECASE)
ATTR_SRC_RE = re.compile(r"""\bsrc\s*=\s*["']([^"']*)["']""", re.IGNORECASE)
ATTR_SRCSET_RE = re.compile(r"""\bsrcset\s*=\s*["']([^"']*)["']""", re.IGNORECASE)
ID_ATTR_RE = re.compile(r"""\bid\s*=\s*["']([^"']+)["']""")

# RFC 3339 date-time, which is the Atom `updated` contract.
RFC3339_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}[Tt]\d{2}:\d{2}:\d{2}(\.\d+)?([Zz]|[+-]\d{2}:\d{2})$"
)

ATOM_NS = "{http://www.w3.org/2005/Atom}"


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


class Report:
    """Accumulates per-check errors and warnings, then prints one summary."""

    def __init__(self, max_report: int, quiet: bool) -> None:
        self.max_report = max_report
        self.quiet = quiet
        self.errors: list[tuple[str, str]] = []
        self.warnings: list[tuple[str, str]] = []
        self.checks_run: list[str] = []

    def check(self, name: str) -> None:
        self.checks_run.append(name)

    def error(self, name: str, detail: str) -> None:
        self.errors.append((name, detail))

    def warn(self, name: str, detail: str) -> None:
        self.warnings.append((name, detail))

    def fail(self, name: str, detail: str, *, as_error: bool) -> None:
        (self.error if as_error else self.warn)(name, detail)

    def _emit(self, label: str, items: list[tuple[str, str]], stream) -> None:
        if not items:
            return
        print(f"\n{label} ({len(items)}):", file=stream)
        by_check: dict[str, list[str]] = {}
        for name, detail in items:
            by_check.setdefault(name, []).append(detail)
        for name, details in by_check.items():
            print(f"  [{name}] {len(details)}", file=stream)
            for detail in details[: self.max_report]:
                print(f"      {detail}", file=stream)
            if len(details) > self.max_report:
                print(
                    f"      … and {len(details) - self.max_report} more",
                    file=stream,
                )

    def summarise(self, site_dir: str) -> int:
        # Flush first: the summary may go to stderr while the header went to
        # stdout, and an unflushed stdout would print after it in a pipeline.
        sys.stdout.flush()
        stream = sys.stderr if self.errors else sys.stdout
        self._emit("ERRORS", self.errors, stream)
        self._emit("WARNINGS", self.warnings, stream)
        print(
            f"\ncheck-site: {len(self.checks_run)} checks over {site_dir} — "
            f"{len(self.errors)} error(s), {len(self.warnings)} warning(s)",
            file=stream,
        )
        if self.errors:
            print(
                "check-site: FAILED — this build must not be signed or deployed",
                file=sys.stderr,
            )
            return 1
        print("check-site: OK", file=stream)
        return 0


# ---------------------------------------------------------------------------
# Walking helpers
# ---------------------------------------------------------------------------


def strip_sidecar(name: str) -> str:
    while name.endswith(SIDECAR_SUFFIXES):
        name = name.rsplit(".", 1)[0]
    return name


def walk_files(site_dir: str):
    """Yield (abs_path, site_relative_path) for every regular file."""
    for dirpath, dirnames, filenames in os.walk(site_dir):
        dirnames.sort()
        for name in sorted(filenames):
            full = os.path.join(dirpath, name)
            yield full, os.path.relpath(full, site_dir)


def read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        return handle.read()


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------


def check_private_files(site_dir: str, report: Report) -> None:
    """S01 — nothing private, temporary, or credential-shaped may ship."""
    report.check("private-files")
    for dirpath, dirnames, filenames in os.walk(site_dir):
        for bad in sorted(set(dirnames) & PRIVATE_DIR_NAMES):
            rel = os.path.relpath(os.path.join(dirpath, bad), site_dir)
            report.error("private-files", f"{rel}/ (private directory)")
        dirnames[:] = sorted(d for d in dirnames if d not in PRIVATE_DIR_NAMES)
        for name in sorted(filenames):
            base = strip_sidecar(name)
            for glob in PRIVATE_FILE_GLOBS:
                if fnmatch.fnmatch(base, glob) or fnmatch.fnmatch(name, glob):
                    rel = os.path.relpath(os.path.join(dirpath, name), site_dir)
                    report.error("private-files", f"{rel} (matches {glob})")
                    break


def check_no_drafts_dir(site_dir: str, report: Report) -> None:
    """B08 — dev drafts must not be present in a production tree."""
    report.check("drafts-dir")
    drafts = os.path.join(site_dir, "drafts")
    if os.path.isdir(drafts):
        count = sum(len(files) for _, _, files in os.walk(drafts))
        report.error("drafts-dir", f"drafts/ exists ({count} files)")


def check_html_corpus(
    site_dir: str,
    html_files: list[tuple[str, str]],
    report: Report,
) -> None:
    """B03 render failures, B08 draft links, and duplicate ids, in one pass."""
    report.check("render-failures")
    report.check("draft-links")
    report.check("duplicate-ids")
    report.check("image-targets")

    for full, rel in html_files:
        text = read_text(full)

        for marker, description in RENDER_FAILURE_MARKERS:
            if marker in text:
                report.error("render-failures", f"{rel}: {description}")

        if DRAFT_HREF_RE.search(text):
            report.error("draft-links", f"{rel}: links into /drafts/")

        seen: dict[str, int] = {}
        for ident in ID_ATTR_RE.findall(text):
            seen[ident] = seen.get(ident, 0) + 1
        dupes = sorted(i for i, n in seen.items() if n > 1)
        if dupes:
            shown = ", ".join(dupes[:5])
            more = "" if len(dupes) <= 5 else f" (+{len(dupes) - 5} more)"
            report.warn("duplicate-ids", f"{rel}: {shown}{more}")

        for missing in missing_image_targets(site_dir, rel, text):
            report.error("image-targets", f"{rel}: missing {missing}")


def missing_image_targets(site_dir: str, rel: str, text: str) -> list[str]:
    """Local <img src>/srcset and <source srcset> targets absent from _site."""
    page_dir = os.path.dirname(rel)
    missing: list[str] = []
    seen: set[str] = set()

    for _tag, attrs in IMG_TAG_RE.findall(text):
        candidates: list[str] = []
        src = ATTR_SRC_RE.search(attrs)
        if src:
            candidates.append(src.group(1))
        srcset = ATTR_SRCSET_RE.search(attrs)
        if srcset:
            for entry in srcset.group(1).split(","):
                entry = entry.strip()
                if entry:
                    candidates.append(entry.split()[0])

        for raw in candidates:
            url = raw.strip()
            if not url or url in seen:
                continue
            seen.add(url)
            resolved = resolve_local(site_dir, page_dir, url)
            if resolved is None:
                continue
            if not os.path.exists(resolved):
                missing.append(url)
    return missing


def resolve_local(site_dir: str, page_dir: str, url: str) -> str | None:
    """Map a URL to a path under site_dir, or None when it is not local."""
    if url.startswith(("http://", "https://", "//", "data:", "mailto:", "#")):
        return None
    parts = urlsplit(url)
    if parts.scheme or parts.netloc:
        return None
    path = unquote(parts.path)
    if not path:
        return None
    if path.startswith("/"):
        target = os.path.join(site_dir, path.lstrip("/"))
    else:
        target = os.path.join(site_dir, page_dir, path)
    return os.path.normpath(target)


def check_feed(site_dir: str, rel: str, report: Report) -> None:
    """F10 — an advertised Atom feed must parse and carry an RFC 3339 date."""
    report.check(f"feed:{rel}")
    path = os.path.join(site_dir, rel)
    if not os.path.exists(path):
        report.error(f"feed:{rel}", "missing")
        return
    try:
        root = ElementTree.parse(path).getroot()
    except ElementTree.ParseError as exc:
        report.error(f"feed:{rel}", f"not well-formed XML: {exc}")
        return

    updates = root.findall(f"{ATOM_NS}updated") + root.findall(
        f".//{ATOM_NS}entry/{ATOM_NS}updated"
    )
    if not updates:
        report.error(f"feed:{rel}", "no <updated> element")
        return
    for element in updates:
        value = (element.text or "").strip()
        if not RFC3339_RE.match(value):
            report.error(f"feed:{rel}", f"<updated> is not RFC 3339: {value!r}")


def check_sitemap(site_dir: str, report: Report) -> None:
    report.check("sitemap")
    path = os.path.join(site_dir, "sitemap.xml")
    if not os.path.exists(path):
        report.error("sitemap", "sitemap.xml missing")
        return
    try:
        ElementTree.parse(path)
    except ElementTree.ParseError as exc:
        report.error("sitemap", f"sitemap.xml is not well-formed: {exc}")


def check_404(site_dir: str, report: Report, *, as_error: bool) -> None:
    """F12 — nginx advertises /404.html; the build must actually emit it."""
    report.check("404-page")
    path = os.path.join(site_dir, "404.html")
    if not os.path.exists(path):
        report.fail(
            "404-page",
            "404.html is missing (nginx's error_page target does not exist)",
            as_error=as_error,
        )
    elif os.path.getsize(path) == 0:
        report.fail("404-page", "404.html is empty", as_error=as_error)


def check_webp(site_dir: str, report: Report, *, as_error: bool) -> None:
    """P02 — the WebP pipeline silently no-ops when cwebp is absent."""
    report.check("webp")
    webp = jpeg = 0
    for _full, rel in walk_files(site_dir):
        lower = rel.lower()
        if lower.endswith(".webp"):
            webp += 1
        elif lower.endswith((".jpg", ".jpeg")):
            jpeg += 1
    if jpeg and not webp:
        report.fail(
            "webp",
            f"{jpeg} JPEG(s) and zero .webp companions — cwebp is probably "
            f"not installed (pacman -S libwebp-utils / apt install webp)",
            as_error=as_error,
        )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="check-site.py",
        description="Reject a finished _site that must not be deployed.",
    )
    parser.add_argument("site_dir", nargs="?", default="_site")
    parser.add_argument(
        "--allow-missing-404",
        action="store_true",
        help="downgrade a missing 404.html from an error to a warning",
    )
    parser.add_argument(
        "--require-webp",
        action="store_true",
        help="fail when JPEGs are present but no .webp companions are",
    )
    parser.add_argument(
        "--warn-only",
        action="store_true",
        help="report every finding but exit 0 (diagnostic use only)",
    )
    parser.add_argument("--max-report", type=int, default=15)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    site_dir = os.path.normpath(args.site_dir)
    if not os.path.isdir(site_dir):
        print(f"check-site: {site_dir} is not a directory", file=sys.stderr)
        return 2

    report = Report(max_report=args.max_report, quiet=args.quiet)

    html_files = [
        (full, rel)
        for full, rel in walk_files(site_dir)
        if rel.endswith(".html") and not skip_for_content_scan(rel)
    ]
    if not args.quiet:
        print(
            f"check-site: scanning {site_dir} "
            f"({len(html_files)} first-party HTML pages)"
        )

    check_private_files(site_dir, report)
    check_no_drafts_dir(site_dir, report)
    check_html_corpus(site_dir, html_files, report)
    check_feed(site_dir, "feed.xml", report)
    check_feed(site_dir, os.path.join("music", "feed.xml"), report)
    check_sitemap(site_dir, report)
    check_404(site_dir, report, as_error=not args.allow_missing_404)
    check_webp(site_dir, report, as_error=args.require_webp)

    status = report.summarise(site_dir)
    if status and args.warn_only:
        print(
            "\ncheck-site: --warn-only — exiting 0 DESPITE the errors above.\n"
            "            This site is not fit to deploy. Use this flag only to\n"
            "            see the whole picture while fixes are still landing.",
            file=sys.stderr,
        )
        return 0
    return status


if __name__ == "__main__":
    sys.exit(main())
