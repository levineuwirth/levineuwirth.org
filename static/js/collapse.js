/* collapse.js — Collapsible h2/h3 sections in essay body.
   Self-guards via #markdownBody check; no-ops on non-essay pages.
   Persists collapsed state per heading in localStorage.
   Retriggered sidenote positioning after each transition via window resize.

   Exposes window.reinitCollapse(container) for use by transclude.js when
   newly injected content contains collapsible headings.
*/
(function () {
    'use strict';

    /* Keys are namespaced by pathname: Pandoc auto-slugs (#introduction,
       #background) recur across essays, and an un-namespaced key would
       collapse the same-named section on every page.

       C03: the namespace is the canonical path, so /essays/x/ and
       /essays/x/index.html — the same page under two spellings — share
       one set of keys. LEGACY_PREFIX is the index.html spelling, read as
       a fallback so state saved before that fix is still honoured. */
    var paths  = window.lnUtils && window.lnUtils.pagePaths
        ? window.lnUtils.pagePaths()
        : { current: location.pathname, legacy: null };
    var PREFIX = 'section-collapsed:' + paths.current + ':';
    var LEGACY_PREFIX = paths.legacy
        ? 'section-collapsed:' + paths.legacy + ':'
        : null;
    var store  = window.lnUtils && window.lnUtils.safeStorage;

    function initHeading(heading) {
        // Idempotence guard: reinitCollapse may be called more than once on
        // the same container — never re-wrap a section or stack toggle
        // buttons (matches the popups.js/sidenotes.js convention).
        if (heading.dataset.collapseBound === '1') return;

        var level   = parseInt(heading.tagName[1], 10);
        var content = [];
        var node    = heading.nextElementSibling;

        // Collect sibling elements until the next same-or-higher heading.
        while (node) {
            if (/^H[1-6]$/.test(node.tagName) &&
                parseInt(node.tagName[1], 10) <= level) break;
            content.push(node);
            node = node.nextElementSibling;
        }
        if (!content.length) return;
        heading.dataset.collapseBound = '1';

        // Wrap collected nodes in a .section-body div.
        var wrapper   = document.createElement('div');
        wrapper.className = 'section-body';
        wrapper.id        = 'section-body-' + heading.id;
        heading.parentNode.insertBefore(wrapper, content[0]);
        content.forEach(function (el) { wrapper.appendChild(el); });

        // Inject toggle button into the heading.
        //
        // A03: every toggle used to be announced as "Toggle section", so a
        // screen-reader user moving by control heard the same name a dozen
        // times on one page. Name it from the heading's own text instead —
        // read BEFORE the button is appended, so the button never names
        // itself. Fall back to the old wording if a heading is somehow
        // empty.
        var title = (heading.textContent || '').trim();
        var btn = document.createElement('button');
        btn.className = 'section-toggle';
        btn.setAttribute('type', 'button');
        btn.setAttribute('aria-label', title ? 'Toggle section: ' + title : 'Toggle section');
        btn.setAttribute('aria-controls', wrapper.id);
        heading.appendChild(btn);

        // Restore persisted state without transition flash.
        var key       = PREFIX + heading.id;
        var stored    = store ? store.get(key) : null;
        if (stored === null && store && LEGACY_PREFIX) {
            stored = store.get(LEGACY_PREFIX + heading.id);
        }
        var collapsed = stored === '1';

        /* A03: max-height:0 + overflow:hidden only makes the panel
           invisible. Its links and buttons stayed in the tab order and in
           the accessibility tree, so focus disappeared into a section the
           reader had closed. `hidden` removes it from both; `inert` is set
           alongside for browsers that honour it, and because `hidden` is
           the thing being animated away it must not be applied until the
           close transition has finished (see the transitionend handler).

           Opening does the reverse first: the panel has to be rendered
           before its scrollHeight can be measured. */
        function reveal() {
            wrapper.removeAttribute('hidden');
            wrapper.removeAttribute('inert');
        }

        function conceal() {
            // Only if we are still closed — a fast reopen must not conceal.
            if (!wrapper.classList.contains('is-collapsed')) return;
            wrapper.setAttribute('hidden', '');
            wrapper.setAttribute('inert', '');
        }

        function setCollapsed(c, animate) {
            if (!animate) wrapper.style.transition = 'none';
            if (c) {
                wrapper.style.maxHeight = '0';
                wrapper.classList.add('is-collapsed');
                btn.setAttribute('aria-expanded', 'false');
                // With no transition to wait for, hide immediately.
                if (!animate) conceal();
            } else {
                reveal();
                // Animate: transition 0 → scrollHeight, then release to 'none'
                // in transitionend so late-rendering content (e.g. KaTeX) is
                // never clipped. No animation: go straight to 'none'.
                wrapper.style.maxHeight = animate
                    ? wrapper.scrollHeight + 'px'
                    : 'none';
                wrapper.classList.remove('is-collapsed');
                btn.setAttribute('aria-expanded', 'true');
            }
            if (!animate) {
                // Re-enable transition after layout pass.
                requestAnimationFrame(function () {
                    requestAnimationFrame(function () {
                        wrapper.style.transition = '';
                    });
                });
            }
        }

        setCollapsed(collapsed, false);

        btn.addEventListener('click', function (e) {
            e.stopPropagation();
            var isCollapsed = wrapper.classList.contains('is-collapsed');
            if (isCollapsed) {
                // Un-hide first: a hidden element measures 0 and cannot be
                // transitioned from.
                reveal();
            } else {
                // Pin height before collapsing so CSS transition has a from-value.
                wrapper.style.maxHeight = wrapper.scrollHeight + 'px';
                void wrapper.offsetHeight; // force reflow
            }
            setCollapsed(!isCollapsed, true);
            if (store) store.set(key, isCollapsed ? '0' : '1');
        });

        // After open animation: release the height cap so late-rendering
        // content (KaTeX, images) is never clipped.
        // After close animation: cap is already 0, nothing to do.
        // Also retrigger sidenote layout after each transition.
        wrapper.addEventListener('transitionend', function (e) {
            if (e.target !== wrapper || e.propertyName !== 'max-height') return;
            if (wrapper.classList.contains('is-collapsed')) {
                conceal();
            } else {
                wrapper.style.maxHeight = 'none';
            }
            window.dispatchEvent(new Event('resize'));
        });

        /* A03: a deep link into a collapsed section must open it, otherwise
           the target is `hidden` and the browser has nothing to scroll to.
           Exposed on the wrapper so the document-level hash handler below
           can reach any section without keeping its own registry. */
        wrapper.lnExpand = function () {
            if (!wrapper.classList.contains('is-collapsed')) return;
            reveal();
            setCollapsed(false, false);
            if (store) store.set(key, '0');
        };
    }

    /* Reveal the section containing the current hash target, at load and on
       every subsequent hash change. Runs for any element inside a collapsed
       .section-body, including nested ones, outermost first. */
    function revealHashTarget() {
        var id = location.hash ? decodeURIComponent(location.hash.slice(1)) : '';
        if (!id) return;
        var target = document.getElementById(id);
        if (!target) return;

        var chain = [];
        var node = target.closest ? target.closest('.section-body') : null;
        while (node) {
            chain.unshift(node);
            node = node.parentElement && node.parentElement.closest
                ? node.parentElement.closest('.section-body')
                : null;
        }
        if (!chain.length) return;

        chain.forEach(function (w) { if (w.lnExpand) w.lnExpand(); });

        // The anchor was hidden when the browser first tried to scroll to it.
        requestAnimationFrame(function () {
            target.scrollIntoView({
                block: 'start',
                behavior: reducedMotion() ? 'auto' : 'smooth'
            });
        });
    }

    /* One effective reduced-motion preference: the site's own setting and
       the OS media query, unioned. Mirrors the CSS override in
       components.css and the helper in nav.js. */
    function reducedMotion() {
        if (document.documentElement.hasAttribute('data-reduce-motion')) return true;
        return !!(window.matchMedia
            && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
    }

    document.addEventListener('DOMContentLoaded', function () {
        var body = document.getElementById('markdownBody');
        if (!body) return;
        if (body.hasAttribute('data-no-collapse')) return;

        var headings = Array.from(body.querySelectorAll('h2[id], h3[id]'));
        if (!headings.length) return;

        headings.forEach(initHeading);
        revealHashTarget();
    });

    window.addEventListener('hashchange', revealHashTarget);

    // Public entry point for transclude.js: initialize collapse toggles on
    // headings inside a newly injected fragment.
    window.reinitCollapse = function (container) {
        Array.from(container.querySelectorAll('h2[id], h3[id]'))
            .forEach(initHeading);
    };
}());
