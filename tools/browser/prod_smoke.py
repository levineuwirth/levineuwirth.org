from playwright.sync_api import sync_playwright
from lib import *
with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={'width': 1440, 'height': 1000})
    ctx.route('**/csp-report', lambda route: route.abort())   # keep test traffic out of the author's report log
    page = ctx.new_page()
    cons = []
    page.on('console', lambda m: cons.append(m.text[:220]))
    page.goto('https://levineuwirth.org/pdfjs/web/viewer.html?file=/cv.pdf'); settle(page, 3000)
    print('pdfjs', [c for c in cons if 'Content Security Policy' in c or 'Report Only' in c][:4])
    cons.clear()
    page.goto('https://levineuwirth.org/work.html'); settle(page, 1000)
    el = page.query_selector('#markdownBody a[href^="https://git.levineuwirth.org/neuwirth/"]') or page.query_selector('a[href^="https://git.levineuwirth.org/neuwirth/"]')
    print('forge link', el and el.get_attribute('href'))
    if el:
        el.scroll_into_view_if_needed(); el.hover(); page.wait_for_timeout(3500)
        print('forge popup visible', page.evaluate("(() => { const p = document.querySelector('.link-popup'); return p && p.classList.contains('is-visible') && p.innerText.slice(0, 80); })()"))
    print('work console', [c for c in cons if 'CORS' in c or 'git.levineuwirth' in c][:3])
    b.close()
