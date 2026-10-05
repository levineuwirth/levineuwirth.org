"""Small helpers the site's Python tools share. Standard library only.

A tool imports this, and the other shared modules beside it (front_matter,
photo_naming, shared_rules, unpublished), after putting its own directory on
the path, which works whether it runs as a script or a test loads it by path:

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import sitelib  # noqa: E402
"""

from __future__ import annotations

import os
import re
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def atomic_path(path: Path, *, durable: bool = True, mode: int | None = None) -> Iterator[Path]:
    """Yield a temporary sibling of `path` to write; when the block ends
    without an exception, one rename puts it in place, so an interrupted
    write never leaves a truncated file at `path`.

    The temporary is dot-prefixed (Hakyll and the site's copy rules skip
    it, so a build running alongside never publishes one), unique to the
    process (two runs cannot write into the same one), ends in `.tmp`
    (gitignored, and refused by the build and check-site), and is removed
    if the block fails. `durable` fsyncs the file before the rename and
    the directory after, so the rename survives a power loss; outputs
    regenerated on every run (sidecars, thumbnails, build stamps) turn it
    off for speed. `mode` sets the permissions before the rename.

    The block must not finish early without raising: a `return` inside it
    puts whatever was written in place.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        yield tmp
        if durable:
            _fsync(tmp, os.O_RDONLY)
        if mode is not None:
            os.chmod(tmp, mode)
        os.replace(tmp, path)
        if durable:
            _fsync(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    finally:
        tmp.unlink(missing_ok=True)


def _fsync(path: Path, flags: int) -> None:
    fd = os.open(path, flags)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def atomic_write_bytes(path: Path, data: bytes, *, durable: bool = True,
                       skip_if_unchanged: bool = False) -> bool:
    """Write `data` to `path` through 'atomic_path'. With
    `skip_if_unchanged`, identical bytes are left alone so the file keeps
    its mtime (Hakyll judges an input changed by it). True if written."""
    if skip_if_unchanged:
        try:
            if path.read_bytes() == data:
                return False
        except OSError:
            pass
    with atomic_path(path, durable=durable) as tmp:
        tmp.write_bytes(data)
    return True


def atomic_write_text(path: Path, text: str, **kwargs) -> bool:
    """'atomic_write_bytes' for UTF-8 text."""
    return atomic_write_bytes(path, text.encode("utf-8"), **kwargs)


def slugify(text: str) -> str:
    """Lowercase, drop what is neither a word character, space nor hyphen,
    and join the words with single hyphens: "Rilke's Elegies" →
    "rilkes-elegies"."""
    s = re.sub(r"[^\w\s-]", "", text.lower())
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"-+", "-", s)
    return s.strip("-")
