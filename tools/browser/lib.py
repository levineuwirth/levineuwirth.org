import json, os, time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
# Results and screenshots go to $BROWSER_OUT or .browser-runs/ (gitignored),
# not beside the scripts.
OUT = os.environ.get('BROWSER_OUT') or os.path.join(REPO, '.browser-runs')
SHOTS = os.path.join(OUT, 'shots')
os.makedirs(SHOTS, exist_ok=True)

PORT_ENFORCE = 48731
PORT_THUMB = 48732
PORT_NONE = 48733

ROUTES = [
    ('home', '/'),
    ('essay-r6', '/essays/eighty-witnesses-six-proofs/'),
    ('essay-verified', '/essays/verified-inference/'),
    ('essay-proofbroker', '/essays/proof-broker/'),
    ('essay-simd', '/essays/where-does-simd-help-post-quantum-cryptography/'),
    ('essay-notes', '/essays/notes-from-underground.html'),
    ('essay-grd', '/essays/growing-radius-domination.html'),
    ('essay-scaling', '/essays/scaling_outage.html'),
    ('essays-index', '/essays/'),
    ('poetry-index', '/poetry/'),
    ('poem', '/poetry/sonnet-60.html'),
    ('fiction', '/fiction/'),
    ('photo-index', '/photography/'),
    ('photo-series', '/photography/copenhagen/'),
    ('photo-single', '/photography/denmark/copenhagen-005/'),
    ('photo-map', '/photography/map/'),
    ('photo-contact', '/photography/contact-sheet/'),
    ('photo-year', '/photography/by-year/2024/'),
    ('music-index', '/music/'),
    ('composition', '/music/bassoon-concerto/'),
    ('score-reader', '/music/bassoon-concerto/score/'),
    ('research', '/research/'),
    ('tag-page', '/research/graph-theory/'),
    ('pdfjs', '/pdfjs/web/viewer.html?file=/cv.pdf'),
    ('search', '/search.html'),
    ('current', '/current.html'),
    ('cv-about', '/about.html'),
    ('cv-projects', '/cv/projects/'),
    ('me', '/me.html'),
    ('links', '/links.html'),
    ('colophon', '/colophon.html'),
    ('bibliography', '/bibliography/'),
    ('commonplace', '/commonplace.html'),
    ('archive-index', '/archive/'),
    ('archive-snapshot', '/archive/djb-aes-speed/'),
    ('archive-pdf', '/archive/nist-fips-203/'),
    ('library', '/library.html'),
    ('work', '/work.html'),
    ('new', '/new.html'),
    ('memento', '/memento-mori.html'),
    ('build', '/build/'),
    ('stats', '/stats/'),
    ('404', '/does-not-exist'),
]

CSP_INIT = r"""
(() => {
  if (window.__cspInstalled) return; window.__cspInstalled = true;
  window.__cspv = [];
  const h = e => { try { window.__cspv.push({
      directive: e.violatedDirective, effective: e.effectiveDirective,
      blocked: e.blockedURI, source: e.sourceFile, line: e.lineNumber,
      col: e.columnNumber, sample: e.sample, disposition: e.disposition,
      doc: e.documentURI}); } catch (_) {} };
  document.addEventListener('securitypolicyviolation', h, true);
  window.__errs = [];
  // Captured, an error event also reports elements that failed to load
  // (img, script, link); those go to __reserrs, not among script errors.
  window.__reserrs = [];
  window.addEventListener('error', e => {
    const t = e.target;
    if (t && t !== window && t.tagName) {
      window.__reserrs.push(t.tagName.toLowerCase() + ' ' + (t.getAttribute('src') ?? t.getAttribute('href') ?? '(no src)'));
      return;
    }
    window.__errs.push(String(e.message) + ' @' + (e.filename||'') + ':' + (e.lineno||''));
  }, true);
  window.addEventListener('unhandledrejection', e => { window.__errs.push('unhandledrejection: ' + String(e.reason && (e.reason.stack || e.reason.message) || e.reason)); });
})();
"""

THEME_INIT = """
try { localStorage.setItem('theme', '%s'); } catch (e) {}
"""

def dump(name, obj):
    p = os.path.join(OUT, name)
    with open(p, 'w') as f:
        json.dump(obj, f, indent=1, default=str)
    return p


def settle(page, ms=600):
    try:
        page.wait_for_load_state('load', timeout=20000)
    except Exception:
        pass
    try:
        page.wait_for_load_state('networkidle', timeout=8000)
    except Exception:
        pass
    page.wait_for_timeout(ms)


def scroll_through(page, step=900, max_steps=60):
    try:
        h = page.evaluate('document.scrollingElement.scrollHeight')
        y = 0; n = 0
        while y < h and n < max_steps:
            y += step; n += 1
            page.evaluate(f'window.scrollTo(0, {y})')
            page.wait_for_timeout(60)
            h = page.evaluate('document.scrollingElement.scrollHeight')
        page.evaluate('window.scrollTo(0, 0)')
    except Exception:
        pass
