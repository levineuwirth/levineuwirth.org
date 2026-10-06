"""What the browser tests (tests/test_browser_*.py) share: the opt-in gate,
the built site checked for staleness, the enforcing CSP read from nginx/,
and tools/browser/serve.py started on a free port.

They run only with RUN_BROWSER_TESTS=1 (`make test-browser`), against the
_site that `make build` left. Once asked for, nothing they need may be
missing: without Playwright, without _site, or with a _site whose inputs
have changed since it was built, they fail instead of skipping.
"""

from __future__ import annotations

import ast
import os
import re
import subprocess
import sys
import unittest
import urllib.error
import urllib.request
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from tests._helpers import load_tool

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "tools" / "browser"
SITE = ROOT / "_site"
BROWSERS = ("chromium", "firefox")

requires_browser = unittest.skipUnless(
    os.environ.get("RUN_BROWSER_TESTS") == "1",
    "browser tests: RUN_BROWSER_TESTS=1, or `make test-browser`")


def check_site() -> None:
    """_site is what the tree describes: `make build` finished, and no input
    has changed, been added or been removed since (tools/build-inputs.py)."""
    if not (SITE / "index.html").is_file():
        raise AssertionError("_site/ has no index.html: run `make build` first")
    differ = load_tool("build-inputs.py").stale()
    if differ:
        listed = "\n  ".join(differ[:10]) + (f"\n  ... and {len(differ) - 10} more"
                                             if len(differ) > 10 else "")
        raise AssertionError(f"_site does not match its inputs; run `make build` first:\n  {listed}")


def harness_routes() -> dict[str, str]:
    """tools/browser/lib.py's ROUTES, name -> path, read without importing
    lib, which makes its output directories."""
    for node in ast.parse((HARNESS / "lib.py").read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "ROUTES"
                                                for t in node.targets):
            return dict(ast.literal_eval(node.value))
    raise AssertionError("tools/browser/lib.py defines no ROUTES")


def require_playwright() -> None:
    try:
        import playwright.sync_api  # noqa: F401
    except ImportError as e:
        raise AssertionError("Playwright is not installed: run `uv sync`") from e


def enforcing_csp() -> str:
    """The policy nginx/security-headers.conf enforces, or, while it is
    still Report-Only, the commented candidate under "Promotion"."""
    text = (ROOT / "nginx" / "security-headers.conf").read_text(encoding="utf-8")
    found = re.findall(r'^(?:#\s+)?add_header Content-Security-Policy "([^"]+)" always;$',
                       text, re.M)
    if len(found) != 1:
        raise AssertionError(f"expected one enforcing Content-Security-Policy line in "
                             f"nginx/security-headers.conf, found {len(found)}")
    return found[0]


@contextmanager
def site_server(workdir: Path, csp: str | None = None) -> Iterator[str]:
    """tools/browser/serve.py over _site on a free port, with `csp`
    enforcing (no policy at all when None); yields its base URL. CSP
    reports go to workdir/csp-reports.jsonl."""
    args = [sys.executable, str(HARNESS / "serve.py"), "--root", str(SITE), "--port", "0",
            "--csp", csp or "", "--mode", "enforce" if csp else "none",
            "--log", str(workdir / "csp-reports.jsonl")]
    with open(workdir / "serve.stderr", "w") as stderr, \
         subprocess.Popen(args, stdout=subprocess.PIPE, stderr=stderr, text=True) as server:
        try:
            line = server.stdout.readline()
            port = re.search(r" on 127\.0\.0\.1:(\d+) ", line)
            if not port:
                raise AssertionError(f"serve.py did not start: {line!r}\n"
                                     f"{(workdir / 'serve.stderr').read_text()[-2000:]}")
            base = f"http://127.0.0.1:{port.group(1)}"
            # A server that is down leaves every page with nothing to report,
            # which reads as clean (tools/browser/README.md).
            try:
                with urllib.request.urlopen(base + "/", timeout=10) as home:
                    status = home.status
            except urllib.error.URLError as e:
                raise AssertionError(f"serve.py on {base} does not answer: {e}") from e
            if status != 200:
                raise AssertionError(f"serve.py answered / with {status}")
            yield base
        finally:
            server.terminate()
            server.wait(timeout=10)
