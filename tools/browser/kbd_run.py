"""Keyboard: tab order, focus visibility, hidden-focus, skip link, traps, Escape.
usage: python kbd_run.py <browser> <outname>
"""
import sys
from playwright.sync_api import sync_playwright
from lib import *

browser_name, outname = sys.argv[1], sys.argv[2]
BASE = f'http://127.0.0.1:{PORT_NONE}'
STOPS = 40

KROUTES = ['home', 'essay-proofbroker', 'essay-r6', 'essay-grd', 'photo-index', 'photo-series', 'photo-single',
           'search', 'composition', 'score-reader', 'links', 'library', 'commonplace', 'music-index', 'me', 'current']
VIEWPORTS = [(1440, 1000), (375, 812)]

FOCUS_INFO = r"""
() => {
  const el = document.activeElement;
  if (!el || el === document.body) return {body: true};
  const r = el.getBoundingClientRect();
  const cs = getComputedStyle(el);
  let ah = null, hid = null, inert = null, clipped = null;
  for (let a = el; a; a = a.parentElement) {
    if (a.getAttribute && a.getAttribute('aria-hidden') === 'true' && !ah) ah = a.tagName + '.' + a.className;
    if (a.hidden && !hid) hid = a.tagName + '.' + a.className;
    if (a.inert && !inert) inert = a.tagName + '.' + a.className;
    if (a !== el && a.nodeType === 1) {
      const c = getComputedStyle(a);
      if ((c.overflow === 'hidden' || c.overflowY === 'hidden') && a.getBoundingClientRect().height < 2 && !clipped) clipped = a.tagName + '.' + a.className;
      if (c.visibility === 'hidden' || c.opacity === '0') clipped = clipped || ('invisible:' + a.tagName + '.' + a.className);
    }
  }
  const desc = el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') + (el.classList.length ? '.' + [...el.classList].slice(0,3).join('.') : '');
  const name = (el.getAttribute('aria-label') || el.textContent || el.getAttribute('title') || el.getAttribute('alt') || '').trim().slice(0, 50);
  const ind = {outline: cs.outlineStyle + ' ' + cs.outlineWidth + ' ' + cs.outlineColor, shadow: cs.boxShadow, bg: cs.backgroundColor, td: cs.textDecorationLine, border: cs.borderBottomStyle + ' ' + cs.borderBottomWidth + ' ' + cs.borderBottomColor};
  const fv = el.matches(':focus-visible');
  const inView = r.width > 0 && r.height > 0 && r.bottom > 0 && r.top < innerHeight && r.right > 0 && r.left < innerWidth;
  // The browser's own answer to "can this be seen": opacity, visibility, content-visibility, display.
  const visible = el.checkVisibility ? el.checkVisibility({checkOpacity: true, checkVisibilityCSS: true}) : null;
  return {desc, name, href: el.getAttribute('href'), w: Math.round(r.width), h: Math.round(r.height), inView, ariaHidden: ah, hidden: hid, inert, clipped, visible, ind, fv};
}
"""

UNFOCUSED_STYLE = r"""
(el) => { const cs = getComputedStyle(el); return {outline: cs.outlineStyle + ' ' + cs.outlineWidth + ' ' + cs.outlineColor, shadow: cs.boxShadow, bg: cs.backgroundColor, td: cs.textDecorationLine, border: cs.borderBottomStyle + ' ' + cs.borderBottomWidth + ' ' + cs.borderBottomColor}; }
"""

def tab_walk(page, n=STOPS):
    stops = []
    for i in range(n):
        page.keyboard.press('Tab')
        page.wait_for_timeout(150)   # Firefox finishes scrolling focus into view after 60 ms
        info = page.evaluate(FOCUS_INFO)
        if info.get('body'):
            stops.append({'i': i, 'body': True}); continue
        # compare against unfocused style
        try:
            h = page.evaluate_handle('document.activeElement')
            page.evaluate('el => { el.__lnBlur = true; }', h)
            # clone-free approach: blur, read, refocus
            page.evaluate('el => el.blur()', h)
            un = page.evaluate(UNFOCUSED_STYLE, h)
            page.evaluate('el => el.focus({preventScroll: true})', h)
            # refocus via keyboard semantics isn't possible; :focus-visible may differ after programmatic focus
            info['unfocused'] = un
            info['indicator_diff'] = un != info['ind']
        except Exception as e:
            info['cmp_err'] = str(e)[:100]
        info['i'] = i
        stops.append(info)
    return stops


def run():
    res = {}
    with sync_playwright() as p:
        browser = getattr(p, browser_name).launch()
        for vp in VIEWPORTS:
            ctx = browser.new_context(viewport={'width': vp[0], 'height': vp[1]}, reduced_motion='reduce')
            offline(ctx)
            page = ctx.new_page()
            for name, path in ROUTES:
                if name not in KROUTES:
                    continue
                key = f'{name}|{vp[0]}'
                rec = {}
                try:
                    page.goto(BASE + path, wait_until='load')
                    settle(page, 800)
                    rec['stops'] = tab_walk(page)
                    first = rec['stops'][0] if rec['stops'] else {}
                    rec['skip'] = {'first': first.get('name'), 'href': first.get('href')}
                    if first.get('href', '') and first.get('href').startswith('#'):
                        tgt = first['href'][1:]
                        rec['skip']['target_exists'] = page.evaluate('id => !!document.getElementById(id)', tgt)
                        # activate skip link and check next focus lands in main
                        page.goto(BASE + path, wait_until='load'); settle(page, 300)
                        page.keyboard.press('Tab'); page.keyboard.press('Enter'); page.wait_for_timeout(300)
                        page.keyboard.press('Tab'); page.wait_for_timeout(100)
                        rec['skip']['after'] = page.evaluate("(() => { const el = document.activeElement; const m = document.getElementById('" + tgt + "'); return {desc: el.tagName + '.' + el.className, inTarget: !!(m && m.contains(el))}; })()")
                except Exception as e:
                    rec['err'] = str(e)[:300]
                res[key] = rec
                bad = [s for s in rec.get('stops', []) if not s.get('body') and (s.get('ariaHidden') or s.get('hidden') or s.get('inert') or s.get('clipped') or not s.get('inView') or not s.get('indicator_diff'))]
                print(key, 'stops', len(rec.get('stops', [])), 'suspicious', len(bad), 'skip', rec.get('skip'), flush=True)
                for s in bad[:12]:
                    print('   ', s.get('i'), s.get('desc'), repr(s.get('name')), 'aH=%s hid=%s inert=%s clip=%s view=%s diff=%s' % (s.get('ariaHidden'), s.get('hidden'), s.get('inert'), s.get('clipped'), s.get('inView'), s.get('indicator_diff')), flush=True)
            ctx.close()
        browser.close()
    dump(outname, res)

run()
