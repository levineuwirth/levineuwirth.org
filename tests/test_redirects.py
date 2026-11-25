#!/usr/bin/env python3
"""The 301s in nginx/levineuwirth.conf lead to pages, and hide none.

nginx answers a redirect before it looks for a file, so a redirect whose
target the site no longer builds sends readers to the 404 page, and a tag
redirect whose source the site builds again (a tag brought back) hides that
page. Neither shows in the build or the gate; `make deploy` does not install
nginx. This suite reads the file's redirects and compares them with the
pages a production build makes (`site list-routes`).

The tag addresses retired in the reclassification of November 2026 (apocrypha,
Passus/Site tags and portals) are listed here, so that a redirect deleted by
mistake fails too.

Run with: ``make test`` (or ``python3 -m unittest tests.test_redirects``).
"""

from __future__ import annotations

import re
import subprocess
import unittest
from functools import lru_cache

from tests._helpers import SITE_ROOT, requires_cabal, script_env, site_binary

CONF = SITE_ROOT / "nginx" / "levineuwirth.conf"

# Each takes /old, /old/ and /old/index.html.
RETIRED_TAGS = (
    "nonfiction", "nonfiction/philosophy", "miscellany",
    "research/mathematics", "research/graph-theory", "research/machine-learning",
    "research/informal", "research/cryptography", "research/hpc", "research/compilers",
    "research/systems", "hpc", "mtg", "tech/rust", "tech/asm", "systems", "tech/C",
    "llm", "projects", "releases", "political", "tft", "speculative", "open", "tech/python",
)

REDIRECT = re.compile(r"location\s+(=|~)\s+(\S+)\s*\{\s*return\s+301\s+(\S+?);\s*\}")


def redirects() -> list[tuple[str, str, str]]:
    """(kind, source, target) for each `location = | ~ … { return 301 … }`,
    in file order: `=` an exact path, `~` a regular expression."""
    return REDIRECT.findall(CONF.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def built_paths() -> frozenset[str]:
    """Every URL path a production build serves a page or file at, as nginx
    finds it: the route itself, a directory's index at /dir/ and /dir, and a
    page at its name without .html (try_files $uri $uri/ $uri.html)."""
    done = subprocess.run([str(site_binary()), "list-routes"], cwd=SITE_ROOT,
                          env=script_env(SITE_ENV="production"),
                          capture_output=True, text=True, check=True)
    paths = set()
    for line in done.stdout.splitlines():
        route = "/" + line.split("\t", 1)[0]
        paths.add(route)
        if route.endswith("/index.html"):
            directory = route[: -len("index.html")]
            paths.update({directory, directory.rstrip("/") or "/"})
        elif route.endswith(".html"):
            paths.add(route[: -len(".html")])
    return frozenset(paths)


def redirected(path: str) -> str | None:
    """Where nginx sends `path`: an exact match first, else the first
    regular expression that matches, in file order."""
    found = redirects()
    for kind, source, target in found:
        if kind == "=" and source == path:
            return target
    for kind, source, target in found:
        if kind == "~" and re.search(source, path):
            return target
    return None


class RedirectFile(unittest.TestCase):
    def test_the_file_has_redirects(self):
        kinds = {kind for kind, _, _ in redirects()}
        self.assertEqual(kinds, {"=", "~"})

    def test_every_retired_tag_address_is_redirected(self):
        missing = [path for tag in RETIRED_TAGS
                   for path in (f"/{tag}", f"/{tag}/", f"/{tag}/index.html")
                   if redirected(path) is None]
        self.assertEqual(missing, [], "retired tag addresses nginx would 404")

    def test_a_tag_pattern_takes_nothing_beneath_the_tag(self):
        # /research/ itself, and a page under a retired tag's name, are not
        # the tag's page.
        for path in ("/research/", "/research/preprint/", "/nonfiction/philosophy/x.html",
                     "/tech/", "/tech/hpc/", "/systems-thinking/", "/projectsx/"):
            with self.subTest(path=path):
                self.assertIsNone(redirected(path))


@requires_cabal
class RedirectTargets(unittest.TestCase):
    def test_every_target_is_built(self):
        stray = sorted({target for _, _, target in redirects() if target not in built_paths()})
        self.assertEqual(stray, [], "redirect targets a production build does not make")

    def test_no_tag_redirect_hides_a_page(self):
        # An exact redirect may stand over a file on purpose (/papers/: one
        # address per PDF); a tag pattern over a page means the tag is back.
        hidden = sorted(path for path in built_paths()
                        for kind, source, _ in redirects()
                        if kind == "~" and re.search(source, path))
        self.assertEqual(hidden, [], "pages a tag redirect would hide; drop its line")


if __name__ == "__main__":
    unittest.main()
