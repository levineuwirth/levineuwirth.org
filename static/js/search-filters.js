/* search-filters.js — Epistemic effort + archive filters for the search page.
 *
 * Loads /data/epistemic-meta.json (a map of URL → epistemic fields) and
 * /data/archive-meta.json (a map of /archive/ page URL → link-rot status)
 * and hides search results whose source page doesn't match the active
 * filters.  Works for both Pagefind keyword results and semantic results.
 *
 * Naming: the epistemic `status` filter (draft / working model / …) and
 * the archive link status (live / moved / rotted / error) are distinct
 * dimensions — the latter lives under `archiveMode` / `archiveStatus`
 * and its own button classes, never touching the epistemic namespace.
 *
 * Reuses the same CSS classes and filter-panel markup as library.html
 * so the two pages look and behave identically.
 */
(function () {
    'use strict';

    var KEY = 'search-filter-state';

    var SCALES = {
        scope:        ['personal', 'average', 'broad', 'civilizational'],
        novelty:      ['conventional', 'moderate', 'idiosyncratic', 'innovative'],
        practicality: ['abstract', 'moderate', 'high', 'exceptional'],
        stability:    ['volatile', 'revising', 'fairly stable', 'stable', 'established']
    };

    var state = {
        status: [],
        confidence: null,
        importance: null,
        evidence: null,
        score: null,
        scope: null,
        novelty: null,
        practicality: null,
        stability: null,
        archiveMode: null,     /* null | 'exclude' | 'only' */
        archiveStatus: []      /* link-rot statuses; archive results only */
    };

    var epistemicMeta = null;  /* URL → {status, confidence, …} loaded lazily */
    var archiveMeta = null;    /* /archive/ URL → {status: live|moved|…} */

    /* ---- Persistence ---- */

    function load() {
        try {
            var raw = localStorage.getItem(KEY);
            if (raw) {
                var obj = JSON.parse(raw);
                for (var k in state) {
                    if (obj.hasOwnProperty(k)) state[k] = obj[k];
                }
            }
        } catch (e) {}
    }

    function save() {
        try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (e) {}
    }

    /* ---- Metadata loading ---- */

    var metaPromise = null;
    var archiveMetaPromise = null;

    function loadEpistemicMeta() {
        if (epistemicMeta) return Promise.resolve(epistemicMeta);
        if (metaPromise) return metaPromise;
        metaPromise = fetch('/data/epistemic-meta.json')
            .then(function (r) { return r.ok ? r.json() : {}; })
            .catch(function () { return {}; })
            .then(function (data) { epistemicMeta = data; return data; });
        return metaPromise;
    }

    function loadArchiveMeta() {
        if (archiveMeta) return Promise.resolve(archiveMeta);
        if (archiveMetaPromise) return archiveMetaPromise;
        archiveMetaPromise = fetch('/data/archive-meta.json')
            .then(function (r) { return r.ok ? r.json() : {}; })
            .catch(function () { return {}; })
            .then(function (data) { archiveMeta = data; return data; });
        return archiveMetaPromise;
    }

    /* Both maps load together: epistemicMeta doubles as the
       "metadata is ready" marker in the apply/observer paths. */
    function loadMeta() {
        return Promise.all([loadEpistemicMeta(), loadArchiveMeta()]);
    }

    /* ---- Filtering logic ---- */

    function passes(meta) {
        if (!meta) return true;  /* no metadata = don't filter out */

        if (state.status.length) {
            var s = (meta.status || '').toLowerCase();
            if (!s || state.status.indexOf(s) === -1) return false;
        }
        if (state.confidence !== null) {
            if (!meta.confidence || +meta.confidence < state.confidence) return false;
        }
        if (state.importance !== null) {
            if (!meta.importance || +meta.importance < state.importance) return false;
        }
        if (state.evidence !== null) {
            if (!meta.evidence || +meta.evidence < state.evidence) return false;
        }
        if (state.score !== null) {
            if (!meta.score || +meta.score < state.score) return false;
        }

        var ords = ['scope', 'novelty', 'practicality', 'stability'];
        for (var i = 0; i < ords.length; i++) {
            var k = ords[i];
            if (state[k] !== null) {
                var v = (meta[k] || '').toLowerCase();
                var idx = SCALES[k].indexOf(v);
                if (idx === -1 || idx < state[k]) return false;
            }
        }

        return true;
    }

    /* Archive dimension. `archiveMode` governs whether /archive/ pages
       appear at all (exclude) or alone (only); `archiveStatus` further
       restricts archive results to the selected link-rot statuses and
       never affects non-archive results. */
    function isArchiveUrl(p) {
        return !!p && p.indexOf('/archive/') === 0;
    }

    function passesArchive(url) {
        var isArch = isArchiveUrl(url);
        if (state.archiveMode === 'exclude' && isArch) return false;
        if (state.archiveMode === 'only' && !isArch) return false;
        if (state.archiveStatus.length && isArch && archiveMeta) {
            var rec = archiveMeta[url];
            var s = rec && rec.status;
            if (!s || state.archiveStatus.indexOf(s) === -1) return false;
        }
        return true;
    }

    function hasActiveFilters() {
        if (state.status.length) return true;
        if (state.archiveMode !== null || state.archiveStatus.length) return true;
        var fields = ['confidence', 'importance', 'evidence', 'score',
                      'scope', 'novelty', 'practicality', 'stability'];
        for (var i = 0; i < fields.length; i++) {
            if (state[fields[i]] !== null) return true;
        }
        return false;
    }

    /* ---- URL extraction ---- */

    /* Normalise a URL to a pathname for lookup in epistemicMeta.
       Pagefind results use full URLs; semantic results use relative paths.
       epistemicMeta keys are emitted as routed paths (".../index.html"),
       while result links use the clean directory form (".../"), so the
       trailing-slash form must be expanded before lookup. */
    function normUrl(href) {
        if (!href) return null;
        try {
            var u = new URL(href, window.location.origin);
            var p = u.pathname;
            if (p.charAt(p.length - 1) === '/') p += 'index.html';
            return p;
        } catch (e) {
            return href;
        }
    }

    /* ---- Apply filters to rendered results ---- */

    function applyToPagefind() {
        if (!epistemicMeta || !hasActiveFilters()) {
            /* Remove any previous filtering */
            document.querySelectorAll('.pagefind-ui__result.search-filtered').forEach(function (el) {
                el.classList.remove('search-filtered');
            });
            return;
        }
        document.querySelectorAll('.pagefind-ui__result').forEach(function (el) {
            var link = el.querySelector('.pagefind-ui__result-link');
            if (!link) return;
            var url = normUrl(link.getAttribute('href'));
            var meta = url ? epistemicMeta[url] : null;
            el.classList.toggle('search-filtered',
                !(passesArchive(url) && passes(meta)));
        });
    }

    function applyToSemantic() {
        if (!epistemicMeta || !hasActiveFilters()) {
            document.querySelectorAll('.semantic-result.search-filtered').forEach(function (el) {
                el.classList.remove('search-filtered');
            });
            return;
        }
        document.querySelectorAll('.semantic-result').forEach(function (el) {
            var link = el.querySelector('.semantic-result-title');
            if (!link) return;
            var url = normUrl(link.getAttribute('href'));
            var meta = url ? epistemicMeta[url] : null;
            el.classList.toggle('search-filtered',
                !(passesArchive(url) && passes(meta)));
        });
    }

    function applyFilters() {
        applyToPagefind();
        applyToSemantic();
        syncUI();
        save();
    }

    /* ---- UI sync ---- */

    function activeCount() {
        var n = 0;
        if (state.status.length) n++;
        if (state.archiveMode !== null) n++;
        if (state.archiveStatus.length) n++;
        var fields = ['confidence', 'importance', 'evidence', 'score',
                      'scope', 'novelty', 'practicality', 'stability'];
        for (var i = 0; i < fields.length; i++) {
            if (state[fields[i]] !== null) n++;
        }
        return n;
    }

    function syncUI() {
        var badge = document.querySelector('.filter-toggle-badge');
        var n = activeCount();
        if (badge) badge.textContent = n ? ' (' + n + ')' : '';

        document.querySelectorAll('.filter-status-btn').forEach(function (btn) {
            btn.classList.toggle('is-active', state.status.indexOf(btn.dataset.value) !== -1);
        });

        document.querySelectorAll('.filter-archive-mode-btn').forEach(function (btn) {
            btn.classList.toggle('is-active', state.archiveMode === btn.dataset.value);
        });

        document.querySelectorAll('.filter-archive-status-btn').forEach(function (btn) {
            btn.classList.toggle('is-active', state.archiveStatus.indexOf(btn.dataset.value) !== -1);
        });

        var ci = document.getElementById('filter-confidence');
        if (ci) ci.value = state.confidence !== null ? state.confidence : '';
        var si = document.getElementById('filter-score');
        if (si) si.value = state.score !== null ? state.score : '';

        document.querySelectorAll('.filter-threshold-btn').forEach(function (btn) {
            btn.classList.toggle('is-active', state[btn.dataset.field] === +btn.dataset.value);
        });

        document.querySelectorAll('.filter-ordinal-btn').forEach(function (btn) {
            btn.classList.toggle('is-active', state[btn.dataset.field] === +btn.dataset.index);
        });
    }

    /* ---- Init ---- */

    document.addEventListener('DOMContentLoaded', function () {
        load();

        var panel  = document.getElementById('search-filters');
        var toggle = document.querySelector('.library-filter-toggle');

        if (activeCount() > 0 && panel && toggle) {
            panel.hidden = false;
            toggle.setAttribute('aria-expanded', 'true');
        }

        syncUI();

        /* Load metadata eagerly if filters are active */
        if (hasActiveFilters()) {
            loadMeta().then(applyFilters);
        }

        /* Toggle panel */
        if (toggle && panel) {
            toggle.addEventListener('click', function () {
                var opening = panel.hidden;
                panel.hidden = !opening;
                toggle.setAttribute('aria-expanded', opening ? 'true' : 'false');
            });
        }

        /* Status buttons */
        document.querySelectorAll('.filter-status-btn').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var v = btn.dataset.value;
                var i = state.status.indexOf(v);
                if (i === -1) state.status.push(v);
                else state.status.splice(i, 1);
                loadMeta().then(applyFilters);
            });
        });

        /* Archive mode buttons (exclude / only) — single-select toggle */
        document.querySelectorAll('.filter-archive-mode-btn').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var v = btn.dataset.value;
                state.archiveMode = (state.archiveMode === v) ? null : v;
                loadMeta().then(applyFilters);
            });
        });

        /* Archive link-status buttons — multi-select, archive results only */
        document.querySelectorAll('.filter-archive-status-btn').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var v = btn.dataset.value;
                var i = state.archiveStatus.indexOf(v);
                if (i === -1) state.archiveStatus.push(v);
                else state.archiveStatus.splice(i, 1);
                loadMeta().then(applyFilters);
            });
        });

        /* Threshold buttons (importance, evidence) */
        document.querySelectorAll('.filter-threshold-btn').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var f = btn.dataset.field;
                var v = +btn.dataset.value;
                state[f] = (state[f] === v) ? null : v;
                loadMeta().then(applyFilters);
            });
        });

        /* Ordinal buttons (scope, novelty, practicality, stability) */
        document.querySelectorAll('.filter-ordinal-btn').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var f = btn.dataset.field;
                var idx = +btn.dataset.index;
                state[f] = (state[f] === idx) ? null : idx;
                loadMeta().then(applyFilters);
            });
        });

        /* Number inputs (confidence, trust/score) */
        ['confidence', 'score'].forEach(function (field) {
            var el = document.getElementById('filter-' + (field === 'score' ? 'score' : field));
            if (!el) return;
            el.addEventListener('input', function () {
                var v = el.value.trim();
                var n = parseInt(v, 10);
                /* Non-numeric input deactivates the filter (null) rather
                   than coercing to an always-matching >= 0 threshold. */
                state[field] = (v !== '' && !isNaN(n))
                    ? Math.max(0, Math.min(100, n))
                    : null;
                loadMeta().then(applyFilters);
            });
        });

        /* Clear all */
        var clearBtn = document.querySelector('.filter-clear-btn');
        if (clearBtn) {
            clearBtn.addEventListener('click', function () {
                state.status = [];
                state.confidence = null;
                state.importance = null;
                state.evidence = null;
                state.score = null;
                state.scope = null;
                state.novelty = null;
                state.practicality = null;
                state.stability = null;
                state.archiveMode = null;
                state.archiveStatus = [];
                applyFilters();
            });
        }

        /* Observe Pagefind result changes to re-apply filters.
           Pagefind dynamically rebuilds the results container. */
        var searchEl = document.getElementById('search');
        if (searchEl) {
            new MutationObserver(function () {
                if (hasActiveFilters() && epistemicMeta) {
                    applyToPagefind();
                }
            }).observe(searchEl, { childList: true, subtree: true });
        }

        /* Observe semantic results container */
        var semanticEl = document.getElementById('semantic-results');
        if (semanticEl) {
            new MutationObserver(function () {
                if (hasActiveFilters() && epistemicMeta) {
                    applyToSemantic();
                }
            }).observe(semanticEl, { childList: true, subtree: true });
        }
    });
}());
