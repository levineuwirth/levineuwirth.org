# Browser harness

Playwright scripts that drive Chromium and Firefox over the built site, from
the 2026-10-01 audit and later checks. They print a line per route and dump
JSON, and assert nothing themselves. The browser tests
(`tests/test_browser_*.py`, `make test-browser`) run `csp_run.py` and assert
on what it records (`tests/test_browser_csp.py`), and drive fixture pages of
their own through `serve.py --fixtures`: popups with every provider's answer
faked, dates, the slideshow, the Random link, the footer and three
robustness fixes. The other scripts here are still reports; `popup_run.py`
meets the live providers, which the tests do not.

## Running

```sh
uv sync                                      # Playwright is in pyproject's dev group
.venv/bin/playwright install chromium firefox
make build                                   # they read _site/
.venv/bin/python tools/browser/serve.py --root _site --port 48731 --csp "<policy>" \
    --mode enforce --log .browser-runs/csp-reports.jsonl &
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:48731/   # 200, or nothing below is real
.venv/bin/python tools/browser/csp_run.py chromium 48731 csp-chromium.json [route ...]
```

`--port 0` takes any free port, which the server names on its first line.

**Check that the server answers first.** If it is down, every page fails to
load and the scripts still print `csp=0 … bad=0`; only the `failed` field in
the JSON shows the refused connections.

Results and screenshots go to `$BROWSER_OUT`, or `.browser-runs/` at the
repository root (gitignored). Routes are in `lib.py`: 43, every page type
and the 404 page. `playwright install` fetches the browsers that match the
installed Playwright; there is no WebKit here.
`axe_run.py` needs axe-core 4.13.0 as `axe.min.js` in this directory
(gitignored): `curl -o axe.min.js https://cdn.jsdelivr.net/npm/axe-core@4.13.0/axe.min.js`.

## Scripts

| script | checks |
|---|---|
| `serve.py` | serves `_site/` as the production vhost does: `try_files`, the internal 404 page, `.gz`/`.br` sidecars and Range, the security and framing headers, a given CSP (enforcing or report-only), `/proxy/*` → 404, `/csp-report` logged; with `--fixtures DIR` (e.g. `fixture/`), also `/__fixture/` from that directory |
| `csp_run.py` | per route: CSP violations, console and page errors, element load errors, failed requests, feature probes (PDF.js pages, thumbnails and print among them) |
| `interact_run.py` | keyboard interaction: settings, lightbox, slideshow, math gallery, popups, portals, filters |
| `kbd_run.py` | tab order, focus visibility, skip link, traps, Escape |
| `axe_run.py` | axe-core per route, viewport and theme |
| `nojs_run.py` | pages with JavaScript off |
| `overflow_run.py` | horizontal overflow at several widths |
| `motion_run.py` | reduced motion, from the OS and from the site's setting |
| `perf_run.py` | requests, bytes, LCP and CLS on the local server |
| `popup_run.py` | every link-popup provider |
| `printcheck.py` | PDF.js thumbnails and print images under the CSP |
| `prod_smoke.py` | a few checks against production; aborts `/csp-report` so test traffic never reaches the report log |
| `cls_check.py`, `footer_check.py` | layout shift, and the footer build time from `/build/time.txt` |
