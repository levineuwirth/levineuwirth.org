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

    document.addEventListener('DOMContentLoaded', function () {
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
