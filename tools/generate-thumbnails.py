#!/usr/bin/env python3
"""
generate-thumbnails.py — Responsive delivery variants for photography.

The problem (audit finding P01). Every photography surface — the card
grids, the contact sheet, the series lead, the map tooltips — pointed
at the full 2400px delivery JPEG. A contact sheet slot is ~220 CSS
pixels wide and a map tooltip is 224; the browser downloaded ~800 KB
to paint each of them, and a single index page cost 32–40 MB.

The fix is not a smaller delivery file (the lightbox and the detail
page genuinely want 2400px) but a ladder of siblings the template can
offer through `srcset`, letting the browser pick.

NAMING CONTRACT (the Hakyll context and the templates depend on it):

    content/photography/<series>/<name>.<ext>
      -> <name>.w480.<ext>
         <name>.w960.<ext>
         <name>.w1440.<ext>

  * Same directory, same extension, same colour profile.
  * A variant is emitted only when the source is STRICTLY wider than
    that width. A 1200px source yields w480 and w960, never w1440 —
    upscaling buys nothing and lies to the browser about what it got.
  * A variant is never itself a source. Files matching
    `\\.w(480|960|1440)\\.(jpe?g|png)$` are skipped on the walk, so
    reruns cannot produce `photo.w960.w480.jpg`.
  * JPEG: quality 82, progressive, optimize. PNG: optimize, alpha
    preserved.
  * No EXIF. The delivery sources are already stripped by
    tools/import-photo.sh (the metadata lives in the .exif.yaml
    sidecar); Pillow writes none unless asked, and we do not ask. An
    embedded ICC profile IS carried across, because dropping it would
    change how the variant renders next to its own source.

Determinism. Rerunning with unchanged sources rewrites nothing: a
variant that exists and is newer than its source is skipped. Every
write goes to a PID-unique temp name and is renamed into place, so an
interrupted run cannot leave a truncated variant that is newer than
its source and therefore skipped forever. (That is the exact trap
tools/convert-images.sh documents for .webp.)

Ordering in `make build`. This runs BEFORE tools/convert-images.sh, so
the variants get .webp companions of their own, and before
tools/extract-dimensions.py, which skips variants (their dimensions
are derivable from the source, and 1000+ sidecars of pure churn help
nobody).

Usage:
    tools/generate-thumbnails.py [ROOT] [--dry-run] [--force] [--prune]

    ROOT       directory to walk, or one image (default:
               content/photography)
    --dry-run  report what would change; write and delete nothing
    --force    rewrite variants even when they look current
    --prune    delete variants whose source is gone, or that the
               contract no longer permits (source no longer wider)

Exit status is 0 for a clean run and 0 when Pillow is absent — the
build continues, exactly as tools/convert-images.sh continues without
cwebp, and the missing srcset targets are then the artifact gate's
problem (tools/check-site.py). A genuine conversion failure exits 1.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ROOT = REPO_ROOT / "content" / "photography"

# The ladder. Fixed: build/ and templates/ hard-code these widths in the
# srcset they emit, so adding one is a two-repo-side change, not a
# one-line edit here.
WIDTHS: tuple[int, ...] = (480, 960, 1440)

SOURCE_EXTS = {".jpg", ".jpeg", ".png"}

# The variant marker, as an anchored suffix. Written out rather than
# f-string-built from WIDTHS so that a grep for `.w960.` finds it.
VARIANT_RE = re.compile(r"\.w(480|960|1440)\.(jpe?g|png)$", re.IGNORECASE)

JPEG_QUALITY = 82

# Sidecars and companions that belong to a variant and should follow it
# into the bin when it is pruned. All are gitignored derived files.
VARIANT_COMPANION_SUFFIXES = (
    ".webp",
    ".dims.yaml",
    ".exif.yaml",
    ".palette.yaml",
)


# ---------------------------------------------------------------------------
# Path arithmetic
# ---------------------------------------------------------------------------


def is_variant(path: Path) -> bool:
    """True for a file this script itself produced.

    Shared shape with tools/extract-dimensions.py, which skips the same
    set. Keep the two in step if the ladder ever changes.
    """
    return VARIANT_RE.search(path.name) is not None


def variant_path(source: Path, width: int) -> Path:
    """`photo.jpg`, 960 -> `photo.w960.jpg` (same directory)."""
    stem = source.name[: -len(source.suffix)]
    return source.with_name(f"{stem}.w{width}{source.suffix}")


def source_for_variant(variant: Path) -> Path:
    """`photo.w960.jpg` -> `photo.jpg` (the file it was derived from)."""
    match = VARIANT_RE.search(variant.name)
    if match is None:  # pragma: no cover — callers check is_variant first
        raise ValueError(f"not a variant: {variant}")
    head = variant.name[: match.start()]
    return variant.with_name(f"{head}.{match.group(2)}")


def _qualifies(path: Path) -> bool:
    return (
        path.is_file()
        and path.suffix.lower() in SOURCE_EXTS
        and not path.name.startswith(".")
        and not path.name.endswith(".tmp")
        and not is_variant(path)
    )


def iter_sources(root: Path):
    """Every delivery image under `root`, variants excluded.

    `root` may also be a single image: tools/import-photo.sh names the
    one file it just wrote, which keeps a bulk import linear instead of
    quadratic (the same convenience extract-exif.py offers).
    """
    if not root.exists():
        return
    if root.is_file():
        if _qualifies(root):
            yield root
        return
    for path in sorted(root.rglob("*")):
        if _qualifies(path):
            yield path


def iter_variants(root: Path):
    """Every file under `root` that this script's contract would own."""
    if not root.exists():
        return
    if root.is_file():
        # A named source: its own ladder, not the whole directory's.
        for width in WIDTHS:
            candidate = variant_path(root, width)
            if candidate.exists():
                yield candidate
        return
    for path in sorted(root.rglob("*")):
        if path.is_file() and is_variant(path):
            yield path


def _is_current(source: Path, variant: Path) -> bool:
    """Skip rule: the variant exists and is not older than its source."""
    if not variant.exists():
        return False
    return variant.stat().st_mtime >= source.stat().st_mtime


def _rel(path: Path) -> Path:
    """Repo-relative for readable output; absolute when outside the repo."""
    try:
        return path.relative_to(REPO_ROOT)
    except ValueError:
        return path


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def _save_kwargs(source: Path, image) -> dict:
    """Encoder settings per output format, plus the ICC profile if any."""
    kwargs: dict = {}

    # Carry the colour profile across unchanged. Sources are sRGB
    # (import-photo.sh converts, and exiftool's `--icc_profile:all`
    # exempts the profile from the EXIF strip), so this is usually an
    # sRGB profile and dropping it would leave the variant to be
    # rendered as untagged next to a tagged source.
    icc = image.info.get("icc_profile")
    if icc:
        kwargs["icc_profile"] = icc

    # `format` is explicit because the write goes to a `.tmp.<pid>` name
    # first, and Pillow otherwise infers the encoder from the extension —
    # which on `photo.w480.jpg.tmp.1234` is `.1234`, and fails.
    if source.suffix.lower() in {".jpg", ".jpeg"}:
        kwargs.update(
            format="JPEG",
            quality=JPEG_QUALITY,
            optimize=True,
            progressive=True,
            subsampling="4:2:0",
        )
    else:
        kwargs.update(format="PNG", optimize=True)
    return kwargs


def _prepare_for_format(source: Path, image):
    """Coerce the mode to something the target encoder accepts.

    JPEG cannot hold alpha or a palette; PNG keeps whatever it has, so
    an RGBA source stays RGBA and its transparency survives.
    """
    if source.suffix.lower() in {".jpg", ".jpeg"}:
        if image.mode not in ("RGB", "L"):
            return image.convert("RGB")
        return image
    # PNG. Palette images with transparency convert cleanly to RGBA;
    # everything else is already writable as-is.
    if image.mode == "P":
        return image.convert("RGBA" if "transparency" in image.info else "RGB")
    return image


def render_variant(source: Path, destination: Path, width: int) -> None:
    """Write one variant. Raises on failure; never leaves a partial file."""
    from PIL import Image

    with Image.open(source) as image:
        image.load()
        src_w, src_h = image.size
        # Round rather than truncate: a 2400x1800 source at 960 must be
        # 720, not 719, or the variant no longer matches the aspect
        # ratio the width/height attributes declare.
        height = max(1, round(src_h * width / src_w))

        prepared = _prepare_for_format(source, image)
        resized = prepared.resize(
            (width, height), Image.Resampling.LANCZOS
        )
        kwargs = _save_kwargs(source, image)

    tmp = destination.with_name(f"{destination.name}.tmp.{os.getpid()}")
    try:
        resized.save(tmp, **kwargs)
        # Match the 644 that import-photo.sh sets on the delivery file;
        # these are rsync'd to the VPS and served by nginx.
        os.chmod(tmp, 0o644)
        tmp.replace(destination)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    finally:
        resized.close()


# ---------------------------------------------------------------------------
# Passes
# ---------------------------------------------------------------------------


def generate(root: Path, *, dry_run: bool, force: bool, counters: dict) -> None:
    from PIL import Image

    for source in iter_sources(root):
        try:
            with Image.open(source) as probe:
                src_width = probe.size[0]
        except Exception as exc:  # noqa: BLE001 — one bad file, keep walking
            print(f"generate-thumbnails: {source}: {exc}", file=sys.stderr)
            counters["failed"] += 1
            continue

        for width in WIDTHS:
            # Strictly wider. An exactly-480px source gets no w480: the
            # variant would be a byte-for-byte-pointless copy and the
            # srcset would advertise two identical candidates.
            if src_width <= width:
                continue

            destination = variant_path(source, width)
            if not force and _is_current(source, destination):
                counters["skipped"] += 1
                continue

            rel = _rel(destination)
            if dry_run:
                print(f"  thumb  {rel}  (dry run)")
                counters["would_write"] += 1
                continue

            try:
                render_variant(source, destination, width)
            except Exception as exc:  # noqa: BLE001 — keep walking
                print(
                    f"generate-thumbnails: {destination}: {exc}",
                    file=sys.stderr,
                )
                counters["failed"] += 1
                continue

            print(f"  thumb  {rel}")
            counters["written"] += 1


def prune(root: Path, *, dry_run: bool, counters: dict) -> None:
    """Delete variants the contract no longer accounts for.

    Two cases, both real: the source was deleted or renamed (the common
    one), and the source was re-imported smaller so a wide variant is no
    longer permitted. A source that exists but cannot be read is left
    alone — an unreadable file is a reason to look, not to delete.
    """
    from PIL import Image

    for variant in iter_variants(root):
        source = source_for_variant(variant)
        reason = None

        if not source.exists():
            reason = "source gone"
        else:
            match = VARIANT_RE.search(variant.name)
            assert match is not None
            width = int(match.group(1))
            try:
                with Image.open(source) as probe:
                    src_width = probe.size[0]
            except Exception:  # noqa: BLE001 — unreadable source: leave it
                continue
            if src_width <= width:
                reason = f"source is {src_width}px, not wider than {width}px"

        if reason is None:
            continue

        rel = _rel(variant)
        if dry_run:
            print(f"  prune  {rel}  ({reason}, dry run)")
            counters["would_prune"] += 1
            continue

        variant.unlink()
        # The .webp companion and any sidecar written before the
        # extractors learned to skip variants are orphaned by this
        # deletion; take them too. All are gitignored derived files.
        for suffix in VARIANT_COMPANION_SUFFIXES:
            if suffix == ".webp":
                companion = variant.with_suffix(".webp")
            else:
                companion = variant.with_name(variant.name + suffix)
            if companion.exists():
                companion.unlink()
        print(f"  prune  {rel}  ({reason})")
        counters["pruned"] += 1


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


PILLOW_HINT = """
  ==============================================================
   NOTICE: Pillow not importable — NO responsive photo variants.
  ==============================================================

   Every photography card, contact-sheet frame and map tooltip
   will fall back to the full 2400px delivery JPEG (the srcset
   candidates are only emitted for files that exist), so the
   site stays correct — it just ships tens of megabytes per
   index page.

   Install it:

     uv sync                 # Pillow is already in pyproject.toml
     .venv/bin/pip install pillow

   Then re-run `make thumbnails` (or `make build`).
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate responsive .w480/.w960/.w1440 photo variants.",
    )
    parser.add_argument(
        "root",
        nargs="?",
        default=str(DEFAULT_ROOT),
        help="directory to walk, or a single image "
        "(default: content/photography)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="report what would change; write and delete nothing",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="rewrite variants even when they are newer than their source",
    )
    parser.add_argument(
        "--prune",
        action="store_true",
        help="delete variants whose source is gone or is no longer wider",
    )
    args = parser.parse_args(argv)

    try:
        import PIL  # noqa: F401
    except ImportError:
        print(PILLOW_HINT, file=sys.stderr)
        # Exit 0 on purpose: same contract as tools/convert-images.sh
        # without cwebp. A missing optional converter degrades the site;
        # it does not break the build.
        return 0

    root = Path(args.root)
    if not root.is_absolute():
        root = (Path.cwd() / root).resolve()

    if not root.exists():
        print(
            f"generate-thumbnails: {root} does not exist — nothing to do.",
            file=sys.stderr,
        )
        return 0

    counters = {
        "written": 0,
        "skipped": 0,
        "failed": 0,
        "would_write": 0,
        "pruned": 0,
        "would_prune": 0,
    }

    # Prune first: a re-imported source that shrank should lose its stale
    # wide variant before the generate pass decides what is current.
    if args.prune:
        prune(root, dry_run=args.dry_run, counters=counters)

    generate(root, dry_run=args.dry_run, force=args.force, counters=counters)

    summary = (
        f"generate-thumbnails: {counters['written']} written, "
        f"{counters['skipped']} current"
    )
    if counters["would_write"]:
        summary += f", {counters['would_write']} would be written"
    if counters["pruned"]:
        summary += f", {counters['pruned']} pruned"
    if counters["would_prune"]:
        summary += f", {counters['would_prune']} would be pruned"
    if counters["failed"]:
        summary += f", {counters['failed']} FAILED"
    print(summary)

    return 1 if counters["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
