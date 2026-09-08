/* nav.js — Portal row expand/collapse with localStorage persistence.
   Loaded with defer.
*/
(function () {
    const STORAGE_KEY = 'portals-open';

    /* A09: one effective reduced-motion preference — the union of the
       site's own Reduce Motion setting ([data-reduce-motion] on <html>,
       stamped by theme.js and toggled by settings.js) and the operating
       system's prefers-reduced-motion. Read at the moment of use rather
       than cached, so a change to either input takes effect on the very
       next interaction with no listener to keep in sync. The same union
       is expressed in CSS in components.css. */
    const motionQuery = window.matchMedia
        ? window.matchMedia('(prefers-reduced-motion: reduce)')
        : null;

    function reducedMotion() {
        if (document.documentElement.hasAttribute('data-reduce-motion')) return true;
        return !!(motionQuery && motionQuery.matches);
    }

    /* --nav-height: the sticky header's real height, published to <html>
       as an inline style so base.css's static estimate is superseded.
       Four rules depend on it — scroll-padding-top (the landing offset
       for every in-page anchor), the TOC's sticky top and max-height,
       and the sticky-footer math — and a wrong value shows up as an
       anchor jump that lands the heading under the nav.

       An estimate cannot be right on its own: the header is one row on
       desktop and three on a phone, grows again when the Portals row is
       opened, changes when a web font swaps in, and collapses to nothing
       under focus mode. A ResizeObserver on the header catches all five
       without a listener per cause. */
    function initNavHeight() {
        var header = document.querySelector('body > header:not(.essay-frontmatter)');
        if (!header) return;

        var last = null;
        function sync() {
            var h = Math.round(header.getBoundingClientRect().height);
            if (h === last) return;          /* no needless style invalidation */
            last = h;
            document.documentElement.style.setProperty('--nav-height', h + 'px');
        }

        sync();

        if (window.ResizeObserver) {
            new ResizeObserver(sync).observe(header);
        } else {
            window.addEventListener('resize', sync, { passive: true });
        }

        /* A font swapping in after first paint changes the nav's height
           without resizing anything the observer above is watching in
           browsers that lack ResizeObserver. */
        if (document.fonts && document.fonts.ready) {
            document.fonts.ready.then(sync).catch(function () {});
        }
    }

    document.addEventListener('DOMContentLoaded', function () {
        initNavHeight();

        // Return-to-top button. Scripted scrolling is motion the CSS
        // override cannot reach — behavior is decided here instead.
        var totop = document.querySelector('.footer-totop');
        if (totop) {
            totop.addEventListener('click', function () {
                window.scrollTo({
                    top: 0,
                    behavior: reducedMotion() ? 'auto' : 'smooth'
                });
            });
        }

        const portals = document.querySelector('.nav-portals');
        const toggle  = document.querySelector('.nav-portal-toggle');
        if (!portals || !toggle) return;

        // safeStorage (utils.js, loaded synchronously before us) so a
        // storage-blocked context can't throw before the click listener
        // below binds; guarded like theme.js in case utils.js itself
        // failed to load.
        const store = window.lnUtils && window.lnUtils.safeStorage;

        function setOpen(open) {
            portals.classList.toggle('is-open', open);
            toggle.setAttribute('aria-expanded', String(open));
            // Rotate arrow indicator if present.
            const arrow = toggle.querySelector('.nav-portal-arrow');
            if (arrow) arrow.textContent = open ? '▲' : '▼';
            if (store) store.set(STORAGE_KEY, open ? '1' : '0');
        }

        // Restore persisted state; default is collapsed.
        const stored = store ? store.get(STORAGE_KEY) : null;
        setOpen(stored === '1');

        toggle.addEventListener('click', function () {
            setOpen(!portals.classList.contains('is-open'));
        });
    });
})();
