/* now.js — Keep the Current page's "Last updated" relative phrase
   honest.

   build/Now.hs renders `.now-stamp-relative` ("3 days ago") at build
   time, relative to the build machine's clock. A page served days
   later from cache/CDN would then lie. We recompute the phrase in the
   browser from the `<time datetime>` attribute (an unambiguous
   YYYY-MM-DD), against the visitor's own clock.

   The bucket thresholds below mirror `relativeTime` in build/Now.hs
   exactly — keep the two in sync. The server-rendered text remains the
   no-JS fallback and is only replaced once we've recomputed. */
(function () {
    'use strict';

    function relative(days) {
        if (days < 0)   return '';            // future / clock skew
        if (days === 0) return 'today';
        if (days === 1) return 'yesterday';
        if (days < 7)   return days + ' days ago';

        var n, unit;
        if (days < 28)       { n = Math.floor(days / 7);   unit = 'week';  }
        else if (days < 365) { n = Math.floor(days / 30);  unit = 'month'; }
        else                 { n = Math.floor(days / 365); unit = 'year';  }
        return n === 1 ? ('1 ' + unit + ' ago')
                       : (n + ' ' + unit + 's ago');
    }

    function update() {
        var stamp = document.querySelector('.now-stamp');
        if (!stamp) return;

        var timeEl = stamp.querySelector('.now-stamp-date');
        if (!timeEl) return;

        var iso = timeEl.getAttribute('datetime');
        var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso || '');
        if (!m) return;   // unparseable — leave the SSR fallback as-is

        // Calendar-day difference, computed via UTC epoch days so DST
        // transitions can't add or drop a day. "today" uses the
        // visitor's *local* date components, matching what they'd
        // read off a wall calendar.
        var then = Date.UTC(+m[1], +m[2] - 1, +m[3]);
        var local = new Date();
        var today = Date.UTC(
            local.getFullYear(),
            local.getMonth(),
            local.getDate()
        );
        var days = Math.round((today - then) / 86400000);
        var text = relative(days);

        var rel = stamp.querySelector('.now-stamp-relative');
        if (!text) {
            // No meaningful relative phrase (e.g. dated in the future):
            // drop any stale server-rendered one rather than keep a lie.
            if (rel) rel.remove();
            return;
        }
        if (!rel) {
            rel = document.createElement('span');
            rel.className = 'now-stamp-relative';
            stamp.appendChild(rel);
        }
        rel.textContent = text;
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', update);
    } else {
        update();
    }
})();
