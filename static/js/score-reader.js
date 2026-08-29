/* score-reader.js — Page navigation, zoom and pan for the full score reader.

   Configuration is read from #score-reader-stage data attributes:
     data-page-count  — total number of score pages
     data-pages       — comma-separated list of absolute page SVG URLs

   Pages are fetched and inlined as live SVG rather than pointed at with an
   <img>. Three things follow from that, and they are the reason for it:
   the notation inherits the theme's `color` (an <img>-loaded SVG resolves
   `currentColor` against its own root, so it can only ever draw black);
   zooming is a width change on a vector, not a rescaled bitmap; and the
   elements are in the DOM, which is what any later staff- or measure-level
   feature will need. */
(function () {
    'use strict';

    var stage    = document.getElementById('score-reader-stage');
    var viewport = document.getElementById('score-reader-viewport');
    var pageEl   = document.getElementById('score-page');
    var folio    = document.getElementById('score-folio');
    var prevBtn  = document.getElementById('score-prev');
    var nextBtn  = document.getElementById('score-next');
    var bar      = document.getElementById('score-reader-bar');

    if (!stage || !viewport || !pageEl || !folio || !prevBtn || !nextBtn) return;

    var pages = (stage.dataset.pages || '').split(',').filter(function (p) {
        return p.length > 0;
    });
    var pageCount = pages.length;
    if (pageCount === 0) return;   /* nothing to display */

    var currentPage = 1;
    var ratio       = null;   /* page width / height, learned from page 1 */
    var naturalW    = null;   /* page width in CSS px at 100 % */
    var cache       = new Map();

    /* ------------------------------------------------------------------
       Fetching and inlining
    ------------------------------------------------------------------ */

    /* An ordinary web link, a fragment, or a relative path. Mirrors the
       convention Catalog.safeHref applies on the Haskell side. */
    var SAFE_HREF = /^(https?:|\/|#|\.)/i;

    /* innerHTML and adoptNode never execute a <script>, but inline `on*`
       handlers and SVG anchors survive both — <a xlink:href="javascript:…">
       around a notehead is clickable. Strip them here, with the browser's
       own parser, rather than in a build-time text pass: a hand-rolled
       scanner over a sixty-page orchestral score risks corrupting valid
       markup, which is a worse failure than the one it would prevent.

       Odd hrefs are the common case, not the exotic one. LilyPond emits
       point-and-click anchors by default — hundreds per page, each holding
       the absolute path of the source .ly — so this also keeps a local
       filesystem layout from reaching a reader, and stops every notehead
       from swallowing drags that should be panning the page. A `#`
       fragment survives, because an engraver referencing shared glyphs
       through <use href="#…"> depends on it. */
    function sanitize(svg) {
        Array.prototype.forEach.call(svg.querySelectorAll('script'), function (n) {
            n.parentNode.removeChild(n);
        });
        var walker = document.createTreeWalker(svg, NodeFilter.SHOW_ELEMENT);
        var el = svg;
        while (el) {
            Array.prototype.slice.call(el.attributes).forEach(function (a) {
                if (/^on/i.test(a.name)) {
                    el.removeAttribute(a.name);
                } else if (a.localName === 'href'
                           && !SAFE_HREF.test(a.value.trim())) {
                    el.removeAttribute(a.name);
                }
            });
            el = walker.nextNode();
        }
        return svg;
    }

    function fetchPage(index) {
        if (index < 1 || index > pageCount) return Promise.resolve(null);
        if (cache.has(index)) return Promise.resolve(cache.get(index));

        var p = fetch(pages[index - 1], { credentials: 'same-origin' })
            .then(function (r) {
                if (!r.ok) throw new Error('HTTP ' + r.status);
                return r.text();
            })
            .then(function (text) {
                var doc = new DOMParser().parseFromString(text, 'image/svg+xml');
                if (doc.querySelector('parsererror')) throw new Error('malformed SVG');
                var svg = doc.documentElement;
                if (!svg || svg.localName !== 'svg') throw new Error('not an SVG');
                return sanitize(svg);
            })
            .catch(function (err) {
                cache.delete(index);   /* a failure must not be cached */
                throw err;
            });

        cache.set(index, p);
        return p;
    }

    /* ------------------------------------------------------------------
       Geometry — read the page's own dimensions off the SVG
    ------------------------------------------------------------------ */

    var UNIT_PX = {
        '': 1, px: 1, pt: 96 / 72, pc: 16,
        mm: 96 / 25.4, cm: 96 / 2.54, 'in': 96
    };

    function aspectOf(svg) {
        var vb = svg.getAttribute('viewBox');
        if (vb) {
            var p = vb.trim().split(/[\s,]+/).map(Number);
            if (p.length === 4 && p[2] > 0 && p[3] > 0) return p[2] / p[3];
        }
        /* width and height carry the same unit, so the ratio needs no
           conversion even when that unit is millimetres. */
        var w = parseFloat(svg.getAttribute('width'));
        var h = parseFloat(svg.getAttribute('height'));
        if (w > 0 && h > 0) return w / h;
        return null;
    }

    function naturalWidthOf(svg) {
        var raw = svg.getAttribute('width');
        if (!raw) return null;
        var m = /^\s*([0-9.]+)\s*([a-z%]*)\s*$/i.exec(raw);
        if (!m) return null;
        var unit = (m[2] || '').toLowerCase();
        if (!(unit in UNIT_PX)) return null;   /* %, em, … are not resolvable here */
        return parseFloat(m[1]) * UNIT_PX[unit];
    }

    /* ------------------------------------------------------------------
       Zoom

       Zoom sets the sheet's width in pixels and lets the SVG scale into
       it, so the notation stays vector-crisp at every level. Panning is
       the viewport's native scrolling — no transform bookkeeping, and
       touch momentum comes free.
    ------------------------------------------------------------------ */

    var ZOOM_STEPS = [0.5, 0.75, 1, 1.25, 1.5, 2, 3, 4, 6];
    var mode       = 'fit-height';   /* 'fit-height' | 'fit-width' | 'zoom' */
    var zoomFactor = 1;

    var modeBtn = document.querySelector('[data-action="zoom-cycle"]');
    var inBtn   = document.querySelector('[data-action="zoom-in"]');
    var outBtn  = document.querySelector('[data-action="zoom-out"]');

    function available() {
        var cs = getComputedStyle(viewport);
        return {
            w: viewport.clientWidth
                 - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight),
            h: viewport.clientHeight
                 - parseFloat(cs.paddingTop) - parseFloat(cs.paddingBottom)
        };
    }

    function applySize() {
        if (!ratio) return;
        var avail = available();
        var w;
        if (mode === 'fit-width')       w = avail.w;
        else if (mode === 'fit-height') w = avail.h * ratio;
        else                            w = (naturalW || avail.h * ratio) * zoomFactor;

        pageEl.style.setProperty('--score-page-width',
                                 Math.max(80, Math.round(w)) + 'px');
        updateZoomUi();
        updateGutter();
        requestAnimationFrame(updatePanState);
    }

    /* At fit, the folio sits in the page's own bottom margin and reads as a
       printed page number. Zoomed in it floats over the staves instead, so
       it needs a ground of its own to stop reading as ink on the music. */
    function updatePanState() {
        document.body.classList.toggle('is-panning',
            viewport.scrollWidth  > viewport.clientWidth  + 1 ||
            viewport.scrollHeight > viewport.clientHeight + 1);
    }

    /* The zoom level the sheet is currently at, whatever mode produced it —
       so stepping out of a fit mode continues from what is on screen rather
       than jumping back to whatever the last explicit zoom was. */
    function effectiveFactor() {
        var w = pageEl.getBoundingClientRect().width;
        if (!naturalW || !w) return zoomFactor;
        return w / naturalW;
    }

    function updateZoomUi() {
        if (!modeBtn) return;
        if (mode === 'fit-height')     modeBtn.textContent = 'Fit';
        else if (mode === 'fit-width') modeBtn.textContent = 'Width';
        else modeBtn.textContent = Math.round(effectiveFactor() * 100) + '%';

        var f = effectiveFactor();
        if (inBtn)  inBtn.disabled  = f >= ZOOM_STEPS[ZOOM_STEPS.length - 1] - 0.001;
        if (outBtn) outBtn.disabled = f <= ZOOM_STEPS[0] + 0.001;
    }

    function step(direction) {
        var f = effectiveFactor();
        var next = null;
        if (direction > 0) {
            for (var i = 0; i < ZOOM_STEPS.length; i++) {
                if (ZOOM_STEPS[i] > f + 0.001) { next = ZOOM_STEPS[i]; break; }
            }
        } else {
            for (var j = ZOOM_STEPS.length - 1; j >= 0; j--) {
                if (ZOOM_STEPS[j] < f - 0.001) { next = ZOOM_STEPS[j]; break; }
            }
        }
        if (next === null) return;
        mode = 'zoom';
        zoomFactor = next;
        applySize();
    }

    if (inBtn)  inBtn.addEventListener('click',  function () { step(1); });
    if (outBtn) outBtn.addEventListener('click', function () { step(-1); });
    if (modeBtn) modeBtn.addEventListener('click', function () {
        mode = (mode === 'fit-height') ? 'fit-width' : 'fit-height';
        applySize();
    });

    window.addEventListener('resize', applySize);
    viewport.addEventListener('scroll', function () {
        updatePanState();
        updateGutter();
    }, { passive: true });

    /* ------------------------------------------------------------------
       Navigation
    ------------------------------------------------------------------ */

    /* Keep the canonical URL clean on a plain load: ?p= is only written
       back once one was already present, or the reader has been navigated. */
    var qs      = new URLSearchParams(window.location.search);
    var syncUrl = qs.has('p');
    var initial = parseInt(qs.get('p'), 10);
    if (!isNaN(initial) && initial >= 1 && initial <= pageCount) currentPage = initial;

    function render(index, svg) {
        if (index !== currentPage) return;   /* a later turn already won */

        var node = svg.cloneNode(true);
        node.setAttribute('aria-hidden', 'true');
        node.removeAttribute('width');
        node.removeAttribute('height');
        if (!node.getAttribute('preserveAspectRatio')) {
            node.setAttribute('preserveAspectRatio', 'xMidYMid meet');
        }

        if (ratio === null) {
            ratio    = aspectOf(svg);
            naturalW = naturalWidthOf(svg);
            /* Page shape picks the opening mode. Fit-height shows a whole
               landscape page and stays readable; on a portrait page it
               leaves most of a landscape window empty and, for a large
               ensemble, shrinks the staves past reading. Only the initial
               mode — a later Fit/Width press is the reader's own. */
            if (ratio !== null && ratio < 1) mode = 'fit-width';
            if (ratio) pageEl.style.setProperty('--score-aspect-num', String(ratio));
        }

        pageEl.replaceChildren(node);
        pageEl.classList.remove('is-loading');

        /* Size before measuring: the gutter is a fraction of the laid-out
           page, and every page carries its own — a first page prints full
           instrument names where later ones abbreviate. */
        applySize();
        buildGutter(node);
    }

    /* ------------------------------------------------------------------
       Instrument-label gutter

       Zoomed in far enough to read a large-ensemble page, the left column
       of names scrolls off and there is no way to tell which staff is
       which. That is what makes a 33-stave score unreadable rather than
       merely awkward, so a second copy of the page — clipped to that
       column and pinned to the viewport's left edge — keeps the names in
       view at any zoom.

       Where the column ends is measured, not declared. The leftmost long
       horizontal rule on a page is where the staves begin; everything left
       of it is names and brackets. Measuring through getBoundingClientRect
       rather than parsing coordinates keeps this independent of each
       engraver's units and nested transforms: MuseScore draws staff lines
       as <polyline> in page coordinates and LilyPond as <line> inside
       translated groups, and both measure the same way.
    ------------------------------------------------------------------ */

    var gutterEl    = null;
    var gutterInner = null;
    var gutterFrac  = 0;

    function measureGutter(svgEl) {
        var box = svgEl.getBoundingClientRect();
        if (!box.width) return 0;

        /* A staff line runs the width of its system. Stems, ledger lines
           and barlines do not, which is the whole filter. */
        var minRun = box.width * 0.2;
        var left   = Infinity;
        var rules  = svgEl.querySelectorAll('line, polyline');

        for (var i = 0; i < rules.length; i++) {
            var r = rules[i].getBoundingClientRect();
            if (r.height > 4 || r.width < minRun) continue;
            if (r.left < left) left = r.left;
        }
        if (left === Infinity) return 0;

        var frac = (left - box.left) / box.width;
        /* Reject a page with no label column and a measurement that has
           swallowed most of the page; neither deserves a gutter. */
        return (frac > 0.02 && frac < 0.4) ? frac : 0;
    }

    function buildGutter(node) {
        if (gutterEl && gutterEl.parentNode) gutterEl.parentNode.removeChild(gutterEl);
        gutterEl   = null;
        gutterFrac = measureGutter(node);
        if (!gutterFrac) return;

        gutterInner = document.createElement('div');
        gutterInner.className = 'score-gutter-inner';
        gutterInner.appendChild(node.cloneNode(true));

        gutterEl = document.createElement('div');
        gutterEl.className = 'score-gutter';
        gutterEl.setAttribute('aria-hidden', 'true');   /* the page already says this */
        gutterEl.appendChild(gutterInner);
        pageEl.appendChild(gutterEl);
        updateGutter();
    }

    function updateGutter() {
        if (!gutterEl) return;
        var scrollLeft = viewport.scrollLeft;
        var pageW      = pageEl.getBoundingClientRect().width;

        /* Both widths come from the laid-out sheet rather than from
           --score-page-width. The copy has to be exactly as wide as the
           page for its labels to land where the originals do, and reading
           the box directly means that holds however the width was arrived
           at — a fit expression, a zoom step, or a stylesheet override. */
        gutterInner.style.width = pageW + 'px';

        /* The label column is a fixed share of the page, so the deeper the
           zoom the more of the window it would claim — 42% of a 1600px
           viewport at 4600px wide, which is absurd for a row of names.
           Past a third of the window it is condensed horizontally instead
           of being allowed to grow or being clipped: scaleX leaves every y
           coordinate alone, so the names stay level with their own staves,
           and condensed type is still readable where a truncated name is
           not. */
        var natural = pageW * gutterFrac;
        var cap     = viewport.clientWidth * 0.33;
        var shown   = Math.min(natural, cap);
        var squeeze = natural > 0 ? shown / natural : 1;

        gutterInner.style.transformOrigin = '0 0';
        gutterInner.style.transform =
            squeeze < 1 ? 'scaleX(' + squeeze + ')' : '';
        gutterEl.style.setProperty('--score-gutter-w',
                                   Math.round(shown) + 'px');
        gutterEl.style.transform = 'translateX(' + scrollLeft + 'px)';
        /* Only once the real labels have actually scrolled out from under it;
           before that the gutter would be an exact copy of what is already
           on screen, and its edge rule would be the only visible difference. */
        gutterEl.classList.toggle('is-visible', scrollLeft > 1);
    }

    function fail(index, err) {
        if (index !== currentPage) return;
        pageEl.classList.remove('is-loading');
        var msg = document.createElement('p');
        msg.className = 'score-page-error';
        msg.textContent = 'Could not load page ' + index + '.';
        pageEl.replaceChildren(msg);
        if (window.console) console.error('[score-reader]', err);
    }

    function navigate(page) {
        if (page < 1 || page > pageCount || page === currentPage) return;
        show(page);
    }

    function show(page) {
        currentPage = page;

        folio.textContent = page + ' / ' + pageCount;
        pageEl.setAttribute('aria-label',
                            'Score page ' + page + ' of ' + pageCount);
        prevBtn.disabled = (page === 1);
        nextBtn.disabled = (page === pageCount);
        updateActiveMovement();

        if (syncUrl) history.replaceState(null, '', '?p=' + page);

        pageEl.classList.add('is-loading');
        fetchPage(page)
            .then(function (svg) { render(page, svg); })
            .catch(function (err) { fail(page, err); });

        /* Warm the neighbours so a turn in either direction is instant. */
        if (page > 1)         fetchPage(page - 1).catch(function () {});
        if (page < pageCount) fetchPage(page + 1).catch(function () {});
    }

    /* ------------------------------------------------------------------
       Movement buttons — highlight the movement containing the page
    ------------------------------------------------------------------ */

    var mvtButtons = Array.prototype.slice.call(
        document.querySelectorAll('.score-reader-mvt'));

    function updateActiveMovement() {
        var active = null;
        mvtButtons.forEach(function (btn) {
            var p = parseInt(btn.dataset.page, 10);
            if (!isNaN(p) && p <= currentPage) active = btn;
        });
        mvtButtons.forEach(function (btn) {
            btn.classList.toggle('is-active', btn === active);
        });
    }

    mvtButtons.forEach(function (btn) {
        btn.addEventListener('click', function () {
            var p = parseInt(btn.dataset.page, 10);
            if (!isNaN(p)) navigate(p);
        });
    });

    prevBtn.addEventListener('click', function () { navigate(currentPage - 1); });
    nextBtn.addEventListener('click', function () { navigate(currentPage + 1); });

    /* ------------------------------------------------------------------
       Keyboard
    ------------------------------------------------------------------ */

    document.addEventListener('keydown', function (e) {
        var panel = document.querySelector('.settings-panel');
        if (panel && panel.classList.contains('is-open')) return;
        if (e.metaKey || e.ctrlKey || e.altKey) return;

        switch (e.key) {
        case 'ArrowRight': case 'ArrowDown': case 'PageDown': case ' ':
            navigate(currentPage + 1); e.preventDefault(); break;
        case 'ArrowLeft': case 'ArrowUp': case 'PageUp':
            navigate(currentPage - 1); e.preventDefault(); break;
        case 'Home':
            navigate(1); e.preventDefault(); break;
        case 'End':
            navigate(pageCount); e.preventDefault(); break;
        case '+': case '=':
            step(1); e.preventDefault(); break;
        case '-': case '_':
            step(-1); e.preventDefault(); break;
        case '0':
            mode = 'fit-height'; applySize(); e.preventDefault(); break;
        case 'Escape':
            history.back(); break;
        }
    });

    /* ------------------------------------------------------------------
       Touch — swipe to turn, but only when there is nothing to pan.
       Once the sheet is wider than the viewport a horizontal drag is the
       reader panning across the system, and stealing it to turn the page
       would make an orchestral score unreadable.
    ------------------------------------------------------------------ */

    var touchX = 0, touchY = 0;

    viewport.addEventListener('touchstart', function (e) {
        touchX = e.changedTouches[0].clientX;
        touchY = e.changedTouches[0].clientY;
    }, { passive: true });

    viewport.addEventListener('touchend', function (e) {
        if (viewport.scrollWidth > viewport.clientWidth + 1) return;   /* pannable */
        var dx = e.changedTouches[0].clientX - touchX;
        var dy = e.changedTouches[0].clientY - touchY;
        if (Math.abs(dx) < 50 || Math.abs(dy) > 30) return;
        navigate(currentPage + (dx < 0 ? 1 : -1));
    }, { passive: true });

    /* ------------------------------------------------------------------
       Idle — let the chrome recede so the sheet is the page
    ------------------------------------------------------------------ */

    var IDLE_MS = 3000;
    var idleTimer = null;

    function poke() {
        document.body.classList.remove('is-idle');
        clearTimeout(idleTimer);
        idleTimer = setTimeout(function () {
            var panel = document.querySelector('.settings-panel');
            if (panel && panel.classList.contains('is-open')) return poke();
            if (bar && bar.matches(':hover')) return poke();
            if (bar && bar.contains(document.activeElement)) return poke();
            document.body.classList.add('is-idle');
        }, IDLE_MS);
    }

    ['mousemove', 'mousedown', 'keydown', 'touchstart', 'wheel', 'focusin']
        .forEach(function (evt) {
            document.addEventListener(evt, poke, { passive: true });
        });

    /* ------------------------------------------------------------------
       Init
    ------------------------------------------------------------------ */

    /* Hands sizing over to applySize(); until this lands, the stylesheet's
       own fit-height rules hold the sheet at the right size. */
    document.body.classList.add('js-ready');

    show(currentPage);
    applySize();
    poke();
    syncUrl = true;   /* every later navigate() is a user action */
}());
