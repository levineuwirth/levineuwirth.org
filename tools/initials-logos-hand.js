// The logo's hand, A-Z: Spectral's capitals with the mark's sprigs grown from
// their left edges and pale veins in their stems. tools/initials-logos-hand.py
// runs it in a page (it needs a canvas, for a raster of each letter) and
// writes what it returns, {letter: {svg, ...}}. Units are the font's: the cap
// height is H (660), the cap line at 0 and the baseline at H.
(function (data) {
    'use strict';
    var H = data.cap, out = {};

    function rng(str) {
        var h = 1779033703 ^ str.length;
        for (var i = 0; i < str.length; i++) { h = Math.imul(h ^ str.charCodeAt(i), 3432918353); h = (h << 13) | (h >>> 19); }
        return function () {
            h = Math.imul(h ^ (h >>> 16), 2246822507); h = Math.imul(h ^ (h >>> 13), 3266489909); h ^= h >>> 16;
            return (h >>> 0) / 4294967296;
        };
    }
    function between(r, a, b) { return a + (b - a) * r(); }
    function n(v) { return Math.round(v * 10) / 10; }
    function s(v) { return Math.round(v * 100) / 100 + 's'; }

    function bitmap(d, x0, W) {
        var k = 0.45, c = document.createElement('canvas');
        c.width = Math.ceil(W * k); c.height = Math.ceil(H * 1.1 * k);
        var g = c.getContext('2d');
        g.scale(k, k); g.translate(x0, 0);
        g.fill(new Path2D(d));
        var px = g.getImageData(0, 0, c.width, c.height).data, cw = c.width, ch = c.height;
        return function (x, y) {
            var ix = Math.round(x * k), iy = Math.round(y * k);
            if (ix < 0 || iy < 0 || ix >= cw || iy >= ch) return false;
            return px[(iy * cw + ix) * 4 + 3] > 110;
        };
    }

    function grow(r, inside, W) {
        var twigs = [], blobs = [];
        function clear(ax, ay, bx, by) {
            for (var i = 1; i <= 10; i++) {
                var x = ax + (bx - ax) * i / 10, y = ay + (by - ay) * i / 10;
                if (x < H * 0.01 || y < H * 0.01 || y > H * 0.99 || x > W || inside(x, y)) return i > 4 ? (i - 1) / 10 : 0;
            }
            return 1;
        }
        function sprig(x, y, a, len, depth, w, gen) {
            var ex = x + Math.cos(a) * len, ey = y + Math.sin(a) * len, ok = clear(x, y, ex, ey);
            if (!ok) return;
            ex = x + (ex - x) * ok; ey = y + (ey - y) * ok;
            var bend = between(r, -0.3, 0.3) * len, mx = (x + ex) / 2 - Math.sin(a) * bend, my = (y + ey) / 2 + Math.cos(a) * bend;
            var t = 0.35 + 0.22 * gen + between(r, 0, 0.08);
            twigs.push({ d: 'M' + n(x) + ',' + n(y) + 'Q' + n(mx) + ',' + n(my) + ' ' + n(ex) + ',' + n(ey), w: w, t: t });
            if (depth === 0 || ok < 1) {
                var br = H * between(r, 0.010, 0.015), pts = [];
                if (r() < 0.3) for (var k = 0; k < 3; k++) { var ka = a + (k - 1) * 0.9; pts.push([ex + Math.cos(ka) * br * 1.05, ey + Math.sin(ka) * br * 1.05, br * 0.72]); }
                else pts.push([ex, ey, br]);
                blobs.push({ pts: pts, t: t + 0.26 });
                return;
            }
            var kids = r() < 0.8 ? 2 : 1;
            for (var c = 0; c < kids; c++) {
                var spread = between(r, 0.35, 0.8) * (c === 0 ? 1 : -1);
                sprig(ex, ey, a + (kids === 1 ? between(r, -0.4, 0.4) : spread), len * between(r, 0.6, 0.8), depth - 1, w * 0.75, gen + 1);
            }
        }
        for (var y = H * 0.06; y < H * 0.97; y += H * between(r, 0.08, 0.13)) {
            for (var x = 1; x < W; x += 1) {
                if (inside(x, y) && !inside(x - 2, y)) {
                    if (r() < 0.7) sprig(x - 1, y, Math.PI + between(r, -0.75, 0.55), H * between(r, 0.09, 0.14), r() < 0.3 ? 3 : 2, H * 0.009, 0);
                    break;
                }
            }
        }
        return { twigs: twigs, blobs: blobs };
    }

    function veins(r, inside, W) {
        var m = H * 0.016, out = [];
        function interior(x, y, mm) { return inside(x, y) && inside(x - mm, y) && inside(x + mm, y) && inside(x, y - mm) && inside(x, y + mm); }
        for (var vy = H * 0.12; vy < H * 0.9; vy += H * 0.22) {
            var run = [];
            for (var vx = 0; vx < W; vx += 1) if (interior(vx, vy, m)) run.push(vx);
            if (run.length < 4 || run[run.length - 1] - run[0] < H * 0.05) continue;
            var px = run[Math.floor(run.length * between(r, 0.3, 0.7))], py = vy, a = Math.PI / 2 * (r() < 0.5 ? 1 : -1);
            var d = 'M' + n(px) + ',' + n(py);
            for (var st = 0; st < 14; st++) {
                a += between(r, -0.45, 0.45);
                var nx = px + Math.cos(a) * H * 0.018, ny = py + Math.sin(a) * H * 0.018;
                if (!interior(nx, ny, m)) { a += Math.PI * 0.5 * (r() < 0.5 ? 1 : -1); continue; }
                px = nx; py = ny; d += 'L' + n(px) + ',' + n(py);
                if (r() < 0.35) {
                    var sa = a + (r() < 0.5 ? 1 : -1) * between(r, 0.7, 1.2), sx = px, sy = py, sd = 'M' + n(sx) + ',' + n(sy);
                    for (var q = 0; q < 3; q++) {
                        var qx = sx + Math.cos(sa) * H * 0.012, qy = sy + Math.sin(sa) * H * 0.012;
                        if (!interior(qx, qy, m * 0.6)) break;
                        sx = qx; sy = qy; sd += 'L' + n(sx) + ',' + n(sy); sa += between(r, -0.4, 0.4);
                    }
                    d += sd + 'M' + n(px) + ',' + n(py);
                }
            }
            out.push(d);
        }
        return out;
    }

    Object.keys(data.letters).forEach(function (L) {
        var g = data.letters[L], room = H * 0.34, W = Math.round(room + g.w + H * 0.04);
        var inside = bitmap(g.d, room, W), r = rng('logos-hand:' + L);
        var grown = grow(r, inside, W), vs = veins(rng('logos-hand:veins:' + L), inside, W);
        var svg =
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ' + W + ' ' + H + '" focusable="false">' +
            '<!-- ' + L + ' in the logo\'s hand: Spectral\'s capital (The Spectral Project Authors; SIL Open Font License 1.1), ' +
            'with sprigs grown from its left edges and veins in its stems after the site\'s mark; seed logos-hand:' + L + '. -->' +
            '<defs><linearGradient id="initial-ink" x1="0" y1="0" x2="1" y2="1">' +
            '<stop offset="0" style="stop-color:var(--initial-ink-lo, currentColor)"/>' +
            '<stop offset="1" style="stop-color:var(--initial-ink-hi, currentColor)"/></linearGradient></defs>' +
            '<g fill="none" stroke="url(#initial-ink)" stroke-linecap="round">' +
            grown.twigs.map(function (t) {
                return '<path class="initial-cut" pathLength="1" style="--t:' + s(t.t) + ';--d:0.34s" stroke-width="' + n(t.w) + '" d="' + t.d + '"/>';
            }).join('') + '</g>' +
            '<g fill="url(#initial-ink)">' +
            grown.blobs.map(function (b) {
                return b.pts.map(function (p) {
                    return '<circle class="initial-ink" style="--t:' + s(b.t) + ';--d:0.28s" cx="' + n(p[0]) + '" cy="' + n(p[1]) + '" r="' + n(p[2]) + '"/>';
                }).join('');
            }).join('') + '</g>' +
            '<path class="initial-ink" style="--t:0s;--d:0.45s" transform="translate(' + n(room) + ' 0)" fill="url(#initial-ink)" d="' + g.d + '"/>' +
            '<g fill="none" stroke="var(--bg)" stroke-width="' + n(H * 0.0065) + '" stroke-linecap="round" stroke-linejoin="round" opacity="0.92">' +
            vs.map(function (d, i) {
                return '<path class="initial-cut" pathLength="1" style="--t:' + s(0.75 + i * 0.12) + ';--d:0.34s" d="' + d + '"/>';
            }).join('') + '</g>' +
            '</svg>\n';
        out[L] = { svg: svg, twigs: grown.twigs.length, blobs: grown.blobs.length, veins: vs.length };
    });
    return out;
})
