/* utils.js — Tiny shared helpers loaded before any other script.
   Loaded synchronously (no `defer`) from templates/partials/head.html so
   that defer'd scripts can rely on `window.lnUtils` existing at run time.

   Keep this file dependency-free and minimal. It's the lowest-level
   layer in the JS stack — anything heavier should live in a feature
   module instead. */
(function (global) {
    'use strict';

    var lnUtils = global.lnUtils || {};

    /* Escape a string for safe interpolation into HTML text content or
       double-quoted attribute values. The order of replacements matters:
       `&` MUST come first, otherwise the `&amp;` injected by other rules
       gets re-escaped to `&amp;amp;`.

       Mirror of `Utils.escapeHtml` in build/Utils.hs. */
    lnUtils.escapeHtml = function (s) {
        return String(s)
            .replace(/&/g,  '&amp;')
            .replace(/</g,  '&lt;')
            .replace(/>/g,  '&gt;')
            .replace(/"/g,  '&quot;')
            .replace(/'/g,  '&#39;');
    };

    /* Safe localStorage wrapper. Safari throws SecurityError in private
       browsing mode on every access — including writes — so reads AND
       writes need to be guarded. Every consumer that touches storage
       should route through this helper so degradation is uniform. */
    lnUtils.safeStorage = {
        get: function (key) {
            try { return localStorage.getItem(key); }
            catch (_) { return null; }
        },
        set: function (key, value) {
            try { localStorage.setItem(key, value); return true; }
            catch (_) { return false; }
        },
        remove: function (key) {
            try { localStorage.removeItem(key); return true; }
            catch (_) { return false; }
        }
    };

    /* The page's identity for anything stored per-URL (audit C03).

       A directory-routed page — every content/<section>/<slug>/index.md —
       is served under two paths: /essays/x/ and /essays/x/index.html.
       The site's own links, canonical tag, sitemap and feed all say the
       first; nginx serves the second to anyone who types it, and a
       from-disk preview only has the second. Scripts that key on
       location.pathname therefore had two identities for one page, and a
       reader who collapsed a section or highlighted a sentence under one
       spelling found neither under the other.

       `current` is the canonical spelling and the one to write. `legacy`
       is the index.html spelling — null for a flat .html page, where
       there is only ever one — and consumers should read it as a
       fallback so state saved before this fix is still found.

       Deliberately not migrated on read: rewriting storage on page load
       is a side effect for a problem that costs one extra lookup. */
    lnUtils.pagePaths = function (pathname) {
        var path  = typeof pathname === 'string' ? pathname : location.pathname;
        var INDEX = 'index.html';
        /* The separator is part of the test: /essays/reindex.html is a
           flat page whose name happens to end in those ten characters. */
        var isDirIndex = path.slice(-(INDEX.length + 1)) === '/' + INDEX;
        var current = isDirIndex ? path.slice(0, -INDEX.length) : path;
        return {
            current: current,
            legacy:  current.charAt(current.length - 1) === '/'
                ? current + INDEX
                : null
        };
    };

    global.lnUtils = lnUtils;
})(window);
