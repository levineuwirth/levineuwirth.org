/* halloween.js — Blood Moon's decorations (site.yaml's halloween season),
   registered with the stage (engine: static/js/stage.js), which loads
   this file while the season is worn and decides when they run:

   - the moon, full at the top of the page, going into eclipse as the
     reader goes down and copper red at the end. With room in the right
     margin it sits low there, half in the fog, rising a little as the
     eclipse deepens, and dims behind anything sharing its patch of
     margin; without (phones, tablets) it sits small in the header.
   - fog along the foot of the screen, thin over the text, thickening
     over the last stretch of the page.
   - bats, each hanging from the header's foot over a margin. One takes
     off when the pointer comes near, when the page is flung, or now and
     then on its own, flutters about its own side of the page, and comes
     back to a free roost. A flying bat never enters the text column and
     steers out of anything else in the margins.

   Under reduce motion the moon still follows the reading, without
   rising; the bats hang still and the fog stops drifting. */
(function () {
    'use strict';

    var stage = window.stage;
    if (!stage) return;
    var geo = stage.geo, ptr = stage.pointer;

    function clamp(v, a, b) { return v < a ? a : v > b ? b : v; }
    function lerp(a, b, t)  { return a + (b - a) * t; }
    function smooth(a, b, v) { var t = clamp((v - a) / (b - a), 0, 1); return t * t * (3 - 2 * t); }
    function rgba(r, g, b, a) { return 'rgba(' + (r | 0) + ',' + (g | 0) + ',' + (b | 0) + ',' + a.toFixed(3) + ')'; }

    /* How far into the eclipse, from how far down the page: it eases out,
       so the first bite comes early, and totality comes at the end. */
    function eclipse(p) {
        var t = clamp(p / 0.96, 0, 1);
        return 1 - Math.pow(1 - t, 1.6);
    }

    /* ------------------------------------------------------------------
       The moon
    ------------------------------------------------------------------ */

    var MARIA = [   /* x, y, rx, ry, angle, in moon radii */
        [-0.25, -0.30, 0.30, 0.22, 0.4], [0.20, -0.18, 0.22, 0.17, -0.3],
        [0.05, 0.25, 0.26, 0.16, 0.2],   [-0.38, 0.18, 0.14, 0.12, 0],
        [0.42, 0.30, 0.10, 0.08, 0]
    ];

    var moon = {
        season: 'halloween',
        mount: function (ctx) {
            this.layer = ctx.layer;
            this.still = ctx.still;
            this.canvas = document.createElement('canvas');
            this.canvas.className = 'halloween-moon';
            this.canvas.setAttribute('aria-hidden', 'true');
            this.ctx = this.canvas.getContext('2d');
            this.mode = null; this.size = 0; this.drawn = -1; this.top = null; this.opacity = null;
        },
        layout: function () {
            var room = geo.vw - geo.bodyR, slot = null, mode;
            if (room >= 120) mode = 'margin';
            else { slot = stage.headerSlot(); mode = slot ? 'header' : 'none'; }
            var c = this.canvas, st = c.style;
            if (mode !== this.mode) {
                c.remove();
                c.classList.toggle('halloween-moon--header', mode === 'header');
                if (mode === 'margin') this.layer.prepend(c);          /* behind the fog */
                if (mode === 'header') {
                    slot.header.prepend(c);
                    requestAnimationFrame(function () { c.classList.add('is-on'); });
                }
                this.mode = mode; this.top = this.opacity = null;
                st.opacity = '';
            }
            if (mode === 'none') return;
            if (mode === 'margin') {
                this.D = clamp(room * 0.32, 56, 112);
                this.cx = geo.vw - Math.max(this.D * 0.5 + 28, room * 0.24);
            } else {
                this.D = slot.size; this.cx = slot.cx;
                st.top = (slot.cy - slot.header.getBoundingClientRect().top - this.D) + 'px';
            }
            var S = Math.round(this.D * 2);
            st.left = (this.cx - S / 2) + 'px';
            st.width = S + 'px'; st.height = S + 'px';
            if (S !== this.size || geo.dpr !== this.dpr) {
                this.size = S; this.dpr = geo.dpr;
                c.width = S * this.dpr; c.height = S * this.dpr;
                this.drawn = -1;
            }
        },
        frame: function () {
            if (this.mode === 'margin') {
                var D = this.D, s = eclipse(geo.progress);
                var cy = geo.vh - D * (0.72 + (this.still ? 0 : 0.9 * s));
                var top = Math.round(cy - this.size / 2);
                if (top !== this.top) { this.canvas.style.top = top + 'px'; this.top = top; }
                var op = stage.rectBlocked(this.cx - D / 2, cy - D / 2, this.cx + D / 2, cy + D / 2) ? '0.1' : '1';
                if (op !== this.opacity) { this.canvas.style.opacity = op; this.opacity = op; }
            }
            if (this.mode === 'margin' || this.mode === 'header') {
                var p = Math.round(geo.progress * 400) / 400;
                if (p !== this.drawn) { this.draw(eclipse(p)); this.drawn = p; }
            }
            return stage.REST;
        },
        unmount: function () { this.canvas.remove(); },

        draw: function (s) {
            var ctx = this.ctx, S = this.size, R = S / 4, cx = S / 2, cy = S / 2;
            var tot = smooth(0.75, 1, s);
            ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
            ctx.clearRect(0, 0, S, S);

            /* Halo: bone at full moon, blood at totality. */
            var hr = lerp(232, 200, tot), hg = lerp(214, 44, tot), hb = lerp(190, 36, tot);
            var halo = ctx.createRadialGradient(cx, cy, R * 0.9, cx, cy, R * 2);
            halo.addColorStop(0, rgba(hr, hg, hb, lerp(0.20, 0.34, tot)));
            halo.addColorStop(1, rgba(hr, hg, hb, 0));
            ctx.fillStyle = halo;
            ctx.fillRect(0, 0, S, S);

            ctx.save();
            ctx.beginPath(); ctx.arc(cx, cy, R, 0, Math.PI * 2); ctx.clip();
            var disc = ctx.createRadialGradient(cx - R * 0.3, cy - R * 0.3, R * 0.1, cx, cy, R);
            disc.addColorStop(0, '#f3ead8'); disc.addColorStop(1, '#c4b398');
            ctx.fillStyle = disc;
            ctx.fillRect(cx - R, cy - R, 2 * R, 2 * R);
            ctx.fillStyle = 'rgba(110, 92, 74, 0.20)';
            MARIA.forEach(function (m) {
                ctx.beginPath();
                ctx.ellipse(cx + m[0] * R, cy + m[1] * R, m[2] * R, m[3] * R, m[4], 0, Math.PI * 2);
                ctx.fill();
            });

            /* Earth's shadow, coming in from the left: the umbra touches the
               limb at the top of the page and covers the disc at its end. */
            var Ru = R * 2.7;
            var ux = cx - lerp(R + Ru, Ru - R * 1.1, s), uy = cy - R * 0.15 * (1 - s);
            var pen = ctx.createRadialGradient(ux, uy, Ru * 0.97, ux, uy, Ru * 1.25);
            pen.addColorStop(0, 'rgba(36, 12, 8, 0.5)');
            pen.addColorStop(1, 'rgba(36, 12, 8, 0)');
            ctx.fillStyle = pen;
            ctx.fillRect(cx - R, cy - R, 2 * R, 2 * R);

            /* The umbra multiplies, so the maria show through it: dark at
               first against the lit disc, copper red at totality, the limb
               farthest from the shadow's center brightest. */
            var ur = lerp(70, 228, tot), ug = lerp(26, 74, tot), ub = lerp(22, 48, tot);
            var um = ctx.createRadialGradient(ux, uy, 0, ux, uy, Ru);
            um.addColorStop(0,    rgba(ur * 0.45, ug * 0.4, ub * 0.4, 1));
            um.addColorStop(0.93, rgba(ur, ug, ub, 1));
            um.addColorStop(1,    'rgba(255, 255, 255, 1)');
            ctx.globalCompositeOperation = 'multiply';
            ctx.fillStyle = um;
            ctx.fillRect(cx - R, cy - R, 2 * R, 2 * R);
            ctx.globalCompositeOperation = 'source-over';
            ctx.restore();
        }
    };

    /* ------------------------------------------------------------------
       The fog: a small tile of fractal value noise, drawn once into a
       canvas and stretched by CSS, which softens it. It wraps
       horizontally, so the drift (halloween.css) loops without a seam,
       and thins to nothing at its top edge.
    ------------------------------------------------------------------ */

    function fogCanvas(seed, period) {
        var W = 320, H = 80;
        var c = document.createElement('canvas');
        c.width = W * 2; c.height = H;
        var ctx = c.getContext('2d'), img = ctx.createImageData(W, H), px = img.data;
        function hash(ix, iy) {
            var h = (ix * 374761393 + iy * 668265263 + seed * 982451653) | 0;
            h = Math.imul(h ^ (h >>> 13), 1274126177);
            return ((h ^ (h >>> 16)) >>> 0) / 4294967295;
        }
        function noise(x, y, p) {   /* value noise, repeating every p cells in x */
            var ix = Math.floor(x), iy = Math.floor(y), fx = x - ix, fy = y - iy;
            var ux = fx * fx * (3 - 2 * fx), uy = fy * fy * (3 - 2 * fy);
            var x0 = ((ix % p) + p) % p, x1 = (x0 + 1) % p;
            return lerp(lerp(hash(x0, iy), hash(x1, iy), ux),
                        lerp(hash(x0, iy + 1), hash(x1, iy + 1), ux), uy);
        }
        for (var y = 0; y < H; y++) {
            for (var x = 0; x < W; x++) {
                var n = 0, amp = 0.5, p = period;
                for (var o = 0; o < 4; o++) {
                    n += amp * noise(x / W * p, y / H * (p / 4) + o * 7.1, p);
                    amp *= 0.5; p *= 2;
                }
                var a = clamp((n - 0.38) * 2.2, 0, 1) * smooth(0, 0.5, y / H), i = (y * W + x) * 4;
                px[i] = 214; px[i + 1] = 196; px[i + 2] = 184; px[i + 3] = a * 255;
            }
        }
        ctx.putImageData(img, 0, 0);
        ctx.putImageData(img, W, 0);
        return c;
    }

    var fog = {
        season: 'halloween',
        mount: function (ctx) {
            this.el = document.createElement('div');
            this.el.className = 'halloween-fog';
            var inner = document.createElement('div');
            inner.className = 'halloween-fog-inner';
            [['near', 3, 4], ['far', 11, 6]].forEach(function (l) {
                var c = fogCanvas(l[1], l[2]);
                c.className = l[0];
                inner.appendChild(c);
            });
            this.el.appendChild(inner);
            ctx.layer.appendChild(this.el);
            this.depth = null;
        },
        layout: function () {
            this.el.style.setProperty('--fog-body-l', geo.bodyL + 'px');
            this.el.style.setProperty('--fog-body-r', geo.bodyR + 'px');
        },
        frame: function (dt, t, moved) {
            if (moved) {
                var d = geo.scrollable ? smooth(0.7, 1, geo.progress).toFixed(2) : '0';
                if (d !== this.depth) { this.el.style.setProperty('--fog-depth', d); this.depth = d; }
            }
            return stage.REST;
        },
        unmount: function () { this.el.remove(); }
    };

    /* ------------------------------------------------------------------
       The bats
    ------------------------------------------------------------------ */

    var FILL = '#3d221c', RIM = 'rgba(217, 119, 43, 0.5)', EYE = '#ffb347';

    var bats = {
        season: 'halloween',
        mount: function (ctx) {
            this.still = ctx.still;
            this.canvas = document.createElement('canvas');
            this.canvas.className = 'halloween-bats';
            this.ctx = this.canvas.getContext('2d');
            ctx.layer.appendChild(this.canvas);
            var n = window.innerWidth >= 1500 ? 6 : window.innerWidth >= 1000 ? 4 : 1;
            this.list = [];
            for (var i = 0; i < n; i++) {
                this.list.push({
                    x: 0, y: 0, vx: 0, vy: 0, side: 0, rx: null,
                    state: 'roost', timer: 0, wander: 0, box: null,
                    phase: Math.random() * 6.28, flap: 22 + Math.random() * 10,
                    size: 34 + Math.random() * 14, seed: Math.random() * 100,
                    lapIn: 15 + Math.random() * 60
                });
            }
            this.lastDraw = 0;
        },
        layout: function () {
            this.canvas.width = geo.vw * geo.dpr;
            this.canvas.height = geo.vh * geo.dpr;
            this.list.forEach(function (b) { b.box = null; });
            var spots = [], x;
            if (geo.margins) {
                for (x = 26; x < geo.bodyL - 30; x += 48) spots.push(x);
                for (x = geo.vw - 26; x > geo.bodyR + 30; x -= 48) spots.push(x);
            } else {
                spots.push(geo.vw - 22);              /* a phone: one corner */
            }
            this.spots = spots;
            var self = this;
            this.list.forEach(function (b, i) {
                if (b.state === 'roost' && (b.rx === null || spots.indexOf(b.rx) < 0)) {
                    b.rx = self.freeSpot(b, i === 0 ? 1 : 0);
                }
            });
        },
        frame: function (dt, t, moved) {
            var flying = this.update(dt);
            if (flying || moved || t - this.lastDraw > 0.12) {
                this.draw(t);
                this.lastDraw = t;
            }
            return this.still ? stage.REST : flying ? stage.BUSY : stage.IDLE;
        },
        unmount: function () { this.canvas.remove(); },

        freeSpot: function (b, preferSide) {
            var mid = (geo.bodyL + geo.bodyR) / 2, taken = this.list, best = [];
            this.spots.forEach(function (x) {
                if (taken.some(function (o) { return o !== b && o.rx !== null && Math.abs(o.rx - x) < 30; })) return;
                if (Math.hypot(x - ptr.x, geo.top - ptr.y) < 140) return;
                if (stage.blocked(x, geo.top + 12)) return;
                var side = x < mid ? -1 : 1;
                if (preferSide && side !== preferSide) return;
                best.push(x);
            });
            if (!best.length) best = this.spots.slice();
            return best.length ? best[(Math.random() * best.length) | 0] : geo.vw - 22;
        },

        takeOff: function (b, fled) {
            b.state = 'fly';
            b.timer = fled ? 2.5 + Math.random() * 3 : 4 + Math.random() * 5;
            if (!geo.margins) b.timer = Math.min(b.timer, 2.5);
            b.y = geo.top + 4;
            var away = b.x >= ptr.x ? 1 : -1;
            b.vx = fled ? away * (160 + Math.random() * 80) : (Math.random() - 0.5) * 180;
            b.vy = 110 + Math.random() * 80;
            b.wander = Math.atan2(b.vy, b.vx);
            b.side = b.x < (geo.bodyL + geo.bodyR) / 2 ? -1 : 1;
            b.rx = null;
            b.lapIn = 25 + Math.random() * 70;
        },

        update: function (dt) {
            var self = this, flying = false;
            this.list.forEach(function (b) {
                if (b.state === 'roost') {
                    b.x = b.rx; b.y = geo.top;
                    if (self.still) return;
                    b.lapIn -= dt;
                    var near = Math.hypot(b.x - ptr.x, b.y + b.size * 0.35 - ptr.y) < 110;
                    if (near || b.lapIn <= 0 || (stage.flung > 0 && Math.random() < 0.08)) {
                        self.takeOff(b, near);
                    }
                    return;
                }
                flying = true;
                b.phase += dt * b.flap;
                b.timer -= dt;
                if (b.state === 'fly' && b.timer <= 0) {
                    b.state = 'return';
                    b.rx = self.freeSpot(b, geo.margins ? b.side : 0);
                }
                self.steer(b, dt);
            });
            return flying;
        },

        steer: function (b, dt) {
            var ax = 0, ay = 0, i, k, a;

            if (b.state === 'return') {
                /* Arrive: seek the roost, slowing over the last stretch. */
                var dx = b.rx - b.x, dy = geo.top - b.y, d = Math.hypot(dx, dy);
                if (d < 4) { b.state = 'roost'; b.vx = b.vy = 0; return; }
                var want = Math.min(240, d * 2.4);
                ax += (dx / d * want - b.vx) * 4;
                ay += (dy / d * want - b.vy) * 4;
            } else {
                /* Wander, with a flutter. */
                b.wander += (Math.random() - 0.5) * 7 * dt;
                ax += Math.cos(b.wander) * 260 + (Math.random() - 0.5) * 900;
                ay += Math.sin(b.wander) * 260 + (Math.random() - 0.5) * 900;
                /* Flee the pointer. */
                var px = b.x - ptr.x, py = b.y - ptr.y, pd = Math.hypot(px, py);
                if (pd < 150 && pd > 0.1) {
                    ax += px / pd * 2600 * (1 - pd / 150);
                    ay += py / pd * 2600 * (1 - pd / 150);
                }
                /* Keep apart. */
                for (i = 0; i < this.list.length; i++) {
                    var o = this.list[i];
                    if (o === b || o.state === 'roost') continue;
                    var sx = b.x - o.x, sy = b.y - o.y, sd = Math.hypot(sx, sy);
                    if (sd < 44 && sd > 0.1) { ax += sx / sd * 600; ay += sy / sd * 600; }
                }
                /* Soft walls: the viewport, below the header. */
                if (b.y < geo.top + 30) ay += (geo.top + 30 - b.y) * 40;
                if (b.y > geo.vh - 40)  ay -= (b.y - (geo.vh - 40)) * 40;
            }

            /* Away from whatever is in the margins nearby; out of it, if
               inside, toward the nearest free direction. */
            for (k = 0; k < 8; k++) {
                a = k * Math.PI / 4;
                if (stage.blocked(b.x + Math.cos(a) * 30, b.y + Math.sin(a) * 30)) {
                    ax -= Math.cos(a) * 900; ay -= Math.sin(a) * 900;
                }
            }
            if (stage.blocked(b.x, b.y)) {
                search: for (var rad = 40; rad <= 200; rad += 40) {
                    for (k = 0; k < 8; k++) {
                        a = k * Math.PI / 4;
                        if (!stage.blocked(b.x + Math.cos(a) * rad, b.y + Math.sin(a) * rad)) {
                            ax += Math.cos(a) * 3200; ay += Math.sin(a) * 3200;
                            break search;
                        }
                    }
                }
            }

            b.vx += ax * dt; b.vy += ay * dt;
            var sp = Math.hypot(b.vx, b.vy), max = b.state === 'return' ? 260 : 300;
            if (sp > max) { b.vx *= max / sp; b.vy *= max / sp; }
            if (b.state === 'fly' && sp < 90 && sp > 0.1) { b.vx *= 90 / sp; b.vy *= 90 / sp; }
            b.x += b.vx * dt; b.y += b.vy * dt;

            /* Hard walls: a bat keeps to its own margin, whatever the forces. */
            if (geo.margins) {
                var lo = b.side < 0 ? 8 : geo.bodyR + 16,
                    hi = b.side < 0 ? geo.bodyL - 16 : geo.vw - 8;
                if (b.x < lo) { b.x = lo; b.vx = Math.abs(b.vx); b.wander = 0; }
                if (b.x > hi) { b.x = hi; b.vx = -Math.abs(b.vx); b.wander = Math.PI; }
            } else {
                b.x = clamp(b.x, 8, geo.vw - 8);
            }
            b.y = clamp(b.y, geo.top + 2, geo.vh - 8);
        },

        /* Clears only where each bat was last drawn: clearing the whole
           screen every frame was most of the cost on a laptop's GPU. */
        draw: function (t) {
            var ctx = this.ctx, self = this;
            ctx.setTransform(geo.dpr, 0, 0, geo.dpr, 0, 0);
            this.list.forEach(function (b) {
                if (b.box) ctx.clearRect(b.box[0], b.box[1], b.box[2], b.box[3]);
            });
            this.list.forEach(function (b) {
                var s = b.size;
                if (b.state === 'roost') {
                    self.drawHanging(ctx, b, t);
                    b.box = [b.x - s, b.y - 4, 2 * s, 1.1 * s];
                } else {
                    self.drawFlying(ctx, b);
                    b.box = [b.x - s, b.y - s, 2 * s, 2 * s];
                }
            });
        },

        drawFlying: function (ctx, b) {
            var s = b.size, f = Math.sin(b.phase), open = 0.7 + 0.3 * Math.abs(Math.cos(b.phase));
            ctx.save();
            ctx.translate(b.x, b.y);
            ctx.rotate(clamp(b.vx / 700, -0.35, 0.35));
            ctx.fillStyle = FILL; ctx.strokeStyle = RIM; ctx.lineWidth = 1;
            ctx.beginPath();
            [-1, 1].forEach(function (k) {
                var span = s * 0.5 * open, tipY = -f * s * 0.34;
                ctx.moveTo(k * s * 0.05, -s * 0.06);
                ctx.quadraticCurveTo(k * span * 0.5, tipY * 0.55 - s * 0.16, k * span, tipY);
                /* The scalloped trailing edge, finger to finger, back to the body. */
                var fy = tipY * 0.4 + s * 0.12;
                ctx.quadraticCurveTo(k * span * 0.80, fy * 0.5, k * span * 0.68, fy);
                ctx.quadraticCurveTo(k * span * 0.55, fy * 0.55, k * span * 0.40, fy + s * 0.04);
                ctx.quadraticCurveTo(k * span * 0.26, fy * 0.6, k * s * 0.05, s * 0.12);
                ctx.closePath();
            });
            ctx.fill(); ctx.stroke();
            /* Body, head, ears. */
            ctx.beginPath();
            ctx.ellipse(0, s * 0.02, s * 0.075, s * 0.14, 0, 0, Math.PI * 2);
            ctx.moveTo(s * 0.06, -s * 0.10);
            ctx.arc(0, -s * 0.10, s * 0.06, 0, Math.PI * 2);
            ctx.fill(); ctx.stroke();
            ctx.beginPath();
            ctx.moveTo(-s * 0.055, -s * 0.12); ctx.lineTo(-s * 0.05, -s * 0.22); ctx.lineTo(-s * 0.01, -s * 0.15);
            ctx.moveTo(s * 0.055, -s * 0.12);  ctx.lineTo(s * 0.05, -s * 0.22);  ctx.lineTo(s * 0.01, -s * 0.15);
            ctx.fill();
            ctx.fillStyle = EYE;
            ctx.fillRect(-s * 0.03, -s * 0.11, 1.5, 1.5);
            ctx.fillRect(s * 0.03 - 1.5, -s * 0.11, 1.5, 1.5);
            ctx.restore();
        },

        drawHanging: function (ctx, b, t) {
            var s = b.size * 1.25, sway = this.still ? 0 : Math.sin(t * 0.9 + b.seed) * 0.07;
            ctx.save();
            ctx.translate(b.x, b.y);
            ctx.rotate(sway);
            ctx.strokeStyle = RIM; ctx.lineWidth = 1;
            /* Feet on the header's edge. */
            ctx.beginPath();
            ctx.moveTo(-2.5, 0); ctx.lineTo(-2, s * 0.07); ctx.moveTo(2.5, 0); ctx.lineTo(2, s * 0.07);
            ctx.stroke();
            /* Upside down, wrapped in its wings: broad at the top, where the
               elbows stand out, narrowing to the head. */
            ctx.fillStyle = FILL;
            ctx.beginPath();
            [1, -1].forEach(function (k) {
                ctx.moveTo(0, s * 0.06);
                ctx.lineTo(k * s * 0.16, s * 0.03);
                ctx.quadraticCurveTo(k * s * 0.15, s * 0.20, k * s * 0.10, s * 0.32);
                ctx.quadraticCurveTo(k * s * 0.06, s * 0.40, 0, s * 0.44);
                ctx.lineTo(0, s * 0.06);
            });
            ctx.fill(); ctx.stroke();
            ctx.beginPath();                                   /* the fold */
            ctx.moveTo(0, s * 0.10); ctx.lineTo(0, s * 0.38);
            ctx.stroke();
            ctx.beginPath();
            ctx.arc(0, s * 0.47, s * 0.065, 0, Math.PI * 2);
            ctx.moveTo(-s * 0.055, s * 0.50); ctx.lineTo(-s * 0.06, s * 0.60); ctx.lineTo(-s * 0.015, s * 0.53);
            ctx.moveTo(s * 0.055, s * 0.50);  ctx.lineTo(s * 0.06, s * 0.60);  ctx.lineTo(s * 0.015, s * 0.53);
            ctx.fill();
            /* Now and then it blinks. */
            if (this.still || Math.sin(t * 0.7 + b.seed * 3) < 0.97) {
                ctx.fillStyle = EYE;
                ctx.fillRect(-s * 0.035, s * 0.46, 1.5, 1.5);
                ctx.fillRect(s * 0.035 - 1.5, s * 0.46, 1.5, 1.5);
            }
            ctx.restore();
        }
    };

    /* In this order: the moon behind the fog, the bats in front of both. */
    stage.register(moon);
    stage.register(fog);
    stage.register(bats);
})();
