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
import json
import os
import re
import signal
import subprocess
import sys
import time
import unittest
import urllib.error
import urllib.request
from collections import Counter, defaultdict
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


def harness_constant(script: str, name: str):
    """A literal a tools/browser script assigns to `name` at top level (a
    route list, its widths), read without running the script: lib makes
    its output directories on import, and the others launch browsers."""
    for node in ast.parse((HARNESS / script).read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == name
                                                for t in node.targets):
            return ast.literal_eval(node.value)
    raise AssertionError(f"tools/browser/{script} defines no {name}")


def harness_routes() -> dict[str, str]:
    """tools/browser/lib.py's ROUTES, name -> path."""
    return dict(harness_constant("lib.py", "ROUTES"))


def assert_complete(case: unittest.TestCase, report: dict, expected, what: str) -> None:
    """A harness report holds a record for each key in `expected` and for
    nothing else. Tests check the records there are, so a page the script
    skipped, or a report it left empty, would otherwise pass unchecked."""
    expected = set(expected)
    case.assertTrue(expected, f"{what}: no records expected")
    missing, extra = sorted(expected - set(report)), sorted(set(report) - expected)
    if missing or extra:
        case.fail(f"{what}: {len(missing)} record(s) missing {missing[:12]}, "
                  f"{len(extra)} unexpected {extra[:12]}")


def page_styles(path: str = "/essays/proof-broker/") -> str:
    """The <link rel="stylesheet"> tags of a built page, as root-relative
    URLs, for a fixture page to look as that page does."""
    from urllib.parse import urljoin
    html = (SITE / path.lstrip("/") / "index.html").read_text(encoding="utf-8")
    links = re.findall(r'<link rel="stylesheet" href="([^"]+)"( media="[^"]+")?>', html)
    if not links:
        raise AssertionError(f"no stylesheets on {path}")
    return "\n".join(f'<link rel="stylesheet" href="{urljoin(path, href)}"{media}>'
                     for href, media in links)


def require_playwright() -> None:
    try:
        import playwright.sync_api  # noqa: F401
    except ImportError as e:
        raise AssertionError("Playwright is not installed: run `uv sync`") from e


def enforcing_csp() -> str:
    """The policy nginx/security-headers.conf enforces (before its
    promotion on 2026-10-09, a commented candidate; either is read)."""
    text = (ROOT / "nginx" / "security-headers.conf").read_text(encoding="utf-8")
    found = re.findall(r'^(?:#\s+)?add_header Content-Security-Policy "([^"]+)" always;$',
                       text, re.M)
    if len(found) != 1:
        raise AssertionError(f"expected one enforcing Content-Security-Policy line in "
                             f"nginx/security-headers.conf, found {len(found)}")
    return found[0]


@contextmanager
def site_server(workdir: Path, csp: str | None = None,
                fixtures: Path | None = None, compress: bool = False) -> Iterator[str]:
    """tools/browser/serve.py over _site on a free port, with `csp`
    enforcing (no policy at all when None), `fixtures`, if given, served
    under /__fixture/, and the .br/.gz sidecars served when `compress`, as
    nginx does; yields its base URL. CSP reports go to
    workdir/csp-reports.jsonl."""
    args = [sys.executable, str(HARNESS / "serve.py"), "--root", str(SITE), "--port", "0",
            "--csp", csp or "", "--mode", "enforce" if csp else "none",
            "--log", str(workdir / "csp-reports.jsonl")]
    if fixtures:
        args += ["--fixtures", str(fixtures)]
    if compress:
        args += ["--compress"]
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


def fake_answer(body, ctype: str = "application/json", status: int = 200) -> dict:
    """A route.fulfill() answer. It carries the CORS header the real APIs
    send, but the browser does not check CORS on a fulfilled route."""
    if not isinstance(body, (str, bytes)):
        body = json.dumps(body)
    return {"status": status, "body": body,
            "headers": {"content-type": ctype, "access-control-allow-origin": "*"}}


class FakeNetwork:
    """Requests a test answers itself, in place of the network or serve.py.

    `routes` maps a name to a pattern searched in the full URL; the first
    that matches answers from `answers[name]`: a route.fulfill() dict, a
    callable taking the route, or None to abort. A request leaving
    serve.py that no route matches is aborted and kept in `unexpected`,
    which a test should end with empty. Same-origin requests are routed
    only where `local` (a pattern for the path after the origin's "/")
    matches; the rest reach serve.py. `hits` and `requests` count and keep
    what each route answered."""

    def __init__(self, context, base: str, routes: dict, answers: dict, local: str | None = None):
        self.routes = routes
        self.answers = dict(answers)
        self.hits: Counter = Counter()
        self.requests = defaultdict(list)
        self.unexpected: list[str] = []
        origin = re.escape(base)
        context.route(re.compile(rf"^(?!{origin}/)"), self.handle)
        if local:
            context.route(re.compile(rf"^{origin}/(?:{local})"), self.handle)

    def handle(self, route) -> None:
        url = route.request.url
        for name, pattern in self.routes.items():
            if re.search(pattern, url):
                self.hits[name] += 1
                self.requests[name].append(route.request)
                reply = self.answers.get(name)
                if reply is None:
                    route.abort()
                elif callable(reply):
                    reply(route)
                else:
                    route.fulfill(**reply)
                return
        self.unexpected.append(url)
        route.abort()


BASELINE = ROOT / "tests" / "browser-baseline"
UPDATE_BASELINE = os.environ.get("UPDATE_BROWSER_BASELINE") == "1"


def stop_process(proc: subprocess.Popen) -> None:
    """A harness script still running, with its Playwright driver: SIGTERM
    to its process group lets the driver close the browsers it launched
    (they run in groups of their own); SIGKILL if it does not go."""
    if proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.wait()
    except ProcessLookupError:
        pass


def run_harness(case, base: str, out: Path, jobs: list[list[str]], *,
                offline: bool = True, seconds: int = 1800) -> None:
    """Run tools/browser scripts (each an argument list: script, then its
    arguments) at once against `base`, writing to `out`, offline unless
    told otherwise; each is stopped at class cleanup if still running.
    Raises with the stderr of any that fail, or of all if time runs out."""
    env = dict(os.environ, BROWSER_OUT=str(out), BROWSER_PORT=base.rsplit(":", 1)[1])
    if offline:
        env["BROWSER_OFFLINE"] = "1"
    running = []
    for job in jobs:
        proc = subprocess.Popen([sys.executable, *job], cwd=HARNESS, env=env, text=True,
                                start_new_session=True, stdout=subprocess.DEVNULL,
                                stderr=subprocess.PIPE)
        case.addClassCleanup(stop_process, proc)
        running.append((" ".join(job[:2]), proc))
    deadline = time.monotonic() + seconds
    failed = []
    for name, proc in running:
        try:
            _, err = proc.communicate(timeout=max(0.1, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            failed.append(f"{name}: still running after {seconds} s")
            continue
        if proc.returncode:
            failed.append(f"{name} exited {proc.returncode}:\n{err[-2000:]}")
    if failed:
        raise AssertionError("\n\n".join(failed))


def baseline(name: str, current):
    """The recorded tests/browser-baseline/<name>.json; with
    UPDATE_BROWSER_BASELINE=1, `current` is recorded there first."""
    path = BASELINE / f"{name}.json"
    if UPDATE_BASELINE:
        BASELINE.mkdir(exist_ok=True)
        path.write_text(json.dumps(current, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    if not path.is_file():
        raise AssertionError(f"no {path.relative_to(ROOT)}: record one with UPDATE_BROWSER_BASELINE=1")
    return json.loads(path.read_text(encoding="utf-8"))


def require_axe() -> Path:
    """tools/browser/axe.min.js, as tools/browser/axe-version records it."""
    import hashlib
    axe = HARNESS / "axe.min.js"
    lines = [l.split() for l in (HARNESS / "axe-version").read_text(encoding="utf-8").splitlines()
             if l.strip() and not l.lstrip().startswith("#")]
    want = lines[0][1]
    if not axe.is_file() or hashlib.sha256(axe.read_bytes()).hexdigest() != want:
        raise AssertionError("tools/browser/axe.min.js is missing or not the recorded axe-core "
                             f"{lines[0][0]}: run `make test-browser` (tools/browser/fetch_axe.py)")
    return axe
