#!/usr/bin/env python3
"""
extract-palette.py — Build-time 5-color palette sidecar for photography.

Walks content/photography/**/*.{jpg,jpeg,png} and writes a
{photo}.palette.yaml sidecar alongside each image, containing five
hex colors derived from the photograph via colorthief's k-means-like
quantisation. The sidecar is consumed by photographyCtx in Hakyll
and rendered as the thin <div class="photo-palette"> strip beneath
each photo.

Frontmatter `palette:` always wins. Authors can override the auto
extraction for artistic reasons (e.g. exposing brand-aligned tones
that aren't statistically dominant in the pixels). The sidecar is
the fallback so authors don't need to write hex codes by hand.

Staleness check: skips an image whose sidecar mtime > image mtime.

Called by `make build` when .venv exists. Per-image failures are
logged and the rest of the walk continues; the build never fails on
a palette extraction error.
"""

from __future__ import annotations

import os
import io
import sys
from pathlib import Path
from typing import Any

import yaml
from PIL import Image
from colorthief import ColorThief

REPO_ROOT = Path(__file__).parent.parent
CONTENT_DIR = REPO_ROOT / "content" / "photography"
TOOL = "extract-palette"

IMAGE_EXTS = {".jpg", ".jpeg", ".png"}

# Number of swatches in the rendered strip. Five matches the design in
# PHOTOGRAPHY.md and the existing `photo-palette` CSS, which sets
# `display: flex; height: 0.75rem;` and divides the bar evenly. Bumping
# this requires a CSS revisit — the bar reads as a unified strip up to
# about 7 swatches; beyond that the bands become too narrow to perceive.
N_SWATCHES = 5

# colorthief's quality knob: lower = better palette but slower. The
# default of 10 is a reasonable trade-off; 1 is exhaustive.
QUALITY = 10


def _hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def _sidecar_path(image: Path) -> Path:
    return image.with_suffix(image.suffix + ".palette.yaml")


def _is_stale(image: Path, sidecar: Path) -> bool:
    if not sidecar.exists():
        return True
    return image.stat().st_mtime > sidecar.stat().st_mtime


def _atomic_write_yaml(path: Path, data: dict[str, Any]) -> None:
    # PID-unique temp (concurrent runs can't share it), removed on
    # failure. No fsync: sidecars are regenerated from the photo on the
    # next build, so a lost rename costs one re-extraction, not data.
    tmp = path.with_suffix(path.suffix + f".tmp.{os.getpid()}")
    try:
        with tmp.open("w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)
        tmp.replace(path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


# Longest edge, in pixels, that the palette is computed from.
#
# Clustering a 2400x1600 image to find five colours is almost entirely wasted
# work: the answer is a property of the distribution, and a faithful 1/8-scale
# sample has the same distribution. Pillow's draft() asks the JPEG decoder for
# a reduced-scale decode, which is a different and much cheaper operation than
# decoding fully and then resizing. Measured on a 2400px frame: 0.297 s before,
# 0.191 s after, with the dominant swatch moving from #465129 to #47512a — a
# difference no eye will find on a 40px strip.
PALETTE_SAMPLE_PX = 320


def _extract_palette(image: Path) -> list[str]:
    """Return up to N_SWATCHES hex colors, in colorthief's dominance order."""
    try:
        with Image.open(image) as im:
            im.draft("RGB", (PALETTE_SAMPLE_PX, PALETTE_SAMPLE_PX))
            sample = im.convert("RGB")
            buf = io.BytesIO()
            sample.save(buf, format="JPEG", quality=90)
        buf.seek(0)
        ct = ColorThief(buf)
        # quality=1 inspects every pixel of the sample. On an image this small
        # that is cheaper than the stride-sampling QUALITY exists to avoid, and
        # it removes sampling as a source of run-to-run variation.
        palette = ct.get_palette(color_count=N_SWATCHES, quality=1)
    except Exception:
        # Any decoder that will not co-operate with a reduced-scale read falls
        # back to the original path rather than losing its palette.
        ct = ColorThief(str(image))
        palette = ct.get_palette(color_count=N_SWATCHES, quality=QUALITY)
    # colorthief sometimes returns one fewer entry than requested for
    # very low-color images; just take what we got.
    return [_hex(rgb) for rgb in palette[:N_SWATCHES]]


def _candidates(argv: list[str]) -> list[Path]:
    """Images to consider: the ones named, or the whole section.

    `make build` calls this with no arguments and wants the full walk.
    import-photo.sh names the single file it just wrote, which keeps a bulk
    import linear instead of quadratic.
    """
    if argv:
        out = []
        for a in argv:
            p = Path(a)
            if not p.is_absolute():
                p = REPO_ROOT / p
            if p.exists():
                out.append(p)
            else:
                print(f"{TOOL}: no such file: {p}", file=sys.stderr)
        return out
    return sorted(CONTENT_DIR.rglob("*"))


def main() -> int:
    if not CONTENT_DIR.exists():
        print(
            f"extract-palette: {CONTENT_DIR} does not exist — skipping.",
            file=sys.stderr,
        )
        return 0

    written = 0
    skipped = 0
    failed = 0

    for image in _candidates(sys.argv[1:]):
        if image.suffix.lower() not in IMAGE_EXTS:
            continue
        if image.name.startswith(".") or image.name.endswith(".tmp"):
            continue

        sidecar = _sidecar_path(image)
        if not _is_stale(image, sidecar):
            skipped += 1
            continue

        try:
            palette = _extract_palette(image)
        except Exception as e:  # noqa: BLE001 — keep walking
            import traceback
            print(f"extract-palette: {image}: {e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            failed += 1
            continue

        _atomic_write_yaml(sidecar, {"palette": palette})
        written += 1

    print(
        f"extract-palette: {written} written, {skipped} skipped, {failed} failed",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
