# Browser harness

Playwright scripts that drive Chromium and Firefox over the built site, from
the 2026-10-01 audit and later checks. They print a line per route and dump
JSON; **they assert nothing yet.** Turning them into tests is open work.

## Running

```sh
make build                                   # they read _site/
cd tools/browser
python3 serve.py --root ../../_site --port 48731 --csp "<policy>" --mode enforce \
    --log ../../.browser-runs/csp-reports.jsonl &
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:48731/   # 200, or nothing below is real
uvx --with playwright python csp_run.py chromium 48731 csp-chromium [route ...]
```

**Check that the server answers first.** If it is down, every page fails to
load and the scripts still print `csp=0 … bad=0`; only the `failed` field in
the JSON shows the refused connections.

Results and screenshots go to `$BROWSER_OUT`, or `.browser-runs/` at the
repository root (gitignored). Routes are in `lib.py` (42, every page type).
Playwright downloads its browsers on first use; there is no WebKit here.
`axe_run.py` needs axe-core 4.13.0 as `axe.min.js` in this directory
(gitignored): `curl -o axe.min.js https://cdn.jsdelivr.net/npm/axe-core@4.13.0/axe.min.js`.

## Scripts

| script | checks |
|---|---|
| `serve.py` | serves `_site/` as the production vhost does: `try_files`, the internal 404 page, `.gz`/`.br` sidecars and Range, the security and framing headers, a given CSP (enforcing or report-only), `/proxy/*` → 404, `/csp-report` logged |
| `serve_fixture.py` | the same, plus `/__fixture/` serving `fixture/` |
| `csp_run.py` | per route: CSP violations, console and page errors, failed requests, feature probes |
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
