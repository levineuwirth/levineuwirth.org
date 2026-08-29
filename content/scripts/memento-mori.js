(function () {
    'use strict';

    // -------------------------------------------------------------------------
    // Constants
    // -------------------------------------------------------------------------

    // Birthday: Monday, December 29, 2003
    const BIRTHDAY  = new Date(2003, 11, 29); // month is 0-indexed
    // End of the 80-year span: December 29, 2083
    const LIFE_END  = new Date(2083, 11, 29);

    const YEARS          = 80;
    const WEEKS_PER_YEAR = 52;
    const TOTAL_WEEKS    = YEARS * WEEKS_PER_YEAR; // 4160

    // A tropical season: 365.25 / 4 days
    const SEASON_MS = 91.25 * 24 * 60 * 60 * 1000;

    // -------------------------------------------------------------------------
    // Utilities
    // -------------------------------------------------------------------------

    function fmtDate(d) {
        return d.toLocaleDateString('en-US', {
            month: 'short', day: 'numeric', year: 'numeric'
        });
    }

    function fmtDayShort(d) {
        return d.toLocaleDateString('en-US', {
            weekday: 'short', month: 'short', day: 'numeric'
        });
    }

    function currentSeasonName() {
        const now = new Date();
        const m = now.getMonth(); // 0-indexed
        const d = now.getDate();
        // Approximate meteorological seasons (northern hemisphere)
        if (m < 2 || (m === 11)) return 'winter';
        if (m < 5) return 'spring';
        if (m < 8) return 'summer';
        return 'autumn';
    }

    // -------------------------------------------------------------------------
    // Grid
    // -------------------------------------------------------------------------

    function buildGrid() {
        const container = document.getElementById('weeks-grid-wrapper');
        if (!container) return;

        const today = new Date();
        today.setHours(0, 0, 0, 0);

        const grid = document.createElement('div');
        grid.className = 'weeks-grid';
        grid.setAttribute('role', 'img');
        grid.setAttribute('aria-label', 'A grid of 4,160 squares representing 80 years of life, one square per week.');

        let globalWeekIndex = 1;

        for (let year = 0; year < YEARS; year++) {

            // Anchor the start of every row exactly to the calendar anniversary.
            const yearStart = new Date(BIRTHDAY.getTime());
            yearStart.setFullYear(yearStart.getFullYear() + year);

            for (let weekInYear = 1; weekInYear <= WEEKS_PER_YEAR; weekInYear++) {

                const start = new Date(yearStart.getTime());
                start.setDate(start.getDate() + (weekInYear - 1) * 7);

                const end = new Date(start.getTime());

                // Stretch week 52 to the eve of the next birthday, absorbing
                // the 365th/366th day so no day falls outside the grid.
                if (weekInYear === WEEKS_PER_YEAR) {
                    const nextBday = new Date(BIRTHDAY.getTime());
                    nextBday.setFullYear(nextBday.getFullYear() + year + 1);
                    end.setTime(nextBday.getTime() - 24 * 60 * 60 * 1000);
                } else {
                    end.setDate(end.getDate() + 6);
                }

                const cell = document.createElement('span');
                cell.className = 'week';

                if (today > end) {
                    cell.classList.add('week--past');
                } else if (today >= start) {
                    cell.classList.add('week--current');
                } else {
                    cell.classList.add('week--future');
                }

                if (weekInYear === 1 && year % 10 === 0) {
                    cell.classList.add('week--decade');
                }

                cell.dataset.start      = fmtDate(start);
                cell.dataset.end        = fmtDate(end);
                cell.dataset.startRaw   = start.getTime();
                cell.dataset.endRaw     = end.getTime();
                cell.dataset.year       = year;
                cell.dataset.weekInYear = weekInYear;
                cell.dataset.index      = globalWeekIndex;

                grid.appendChild(cell);
                globalWeekIndex++;
            }
        }

        container.appendChild(grid);

        const legend = document.createElement('p');
        legend.className = 'weeks-legend';
        legend.textContent =
            'Each row is one year (age 0–79). Each cell is one week. ' +
            'Decade boundaries are marked.';
        container.appendChild(legend);

        initTooltip(grid);
        initWeekPopup(grid);
    }

    // -------------------------------------------------------------------------
    // Tooltip
    // -------------------------------------------------------------------------

    function initTooltip(grid) {
        const tip = document.createElement('div');
        tip.className = 'weeks-tooltip';
        tip.setAttribute('aria-hidden', 'true');
        tip.hidden = true;
        document.body.appendChild(tip);

        grid.addEventListener('mouseover', e => {
            const cell = e.target.closest('.week');
            if (!cell) { tip.hidden = true; return; }

            const year       = parseInt(cell.dataset.year, 10);
            const weekInYear = parseInt(cell.dataset.weekInYear, 10);
            const index      = parseInt(cell.dataset.index, 10);

            const isPast    = cell.classList.contains('week--past');
            const isCurrent = cell.classList.contains('week--current');
            const status    = isPast ? 'elapsed' : isCurrent ? 'this week' : 'remaining';

            tip.innerHTML =
                `<span class="tt-age">age ${year}</span>` +
                `<span class="tt-week">year ${year + 1}, week ${weekInYear}</span>` +
                `<span class="tt-date">${cell.dataset.start} – ${cell.dataset.end}</span>` +
                `<span class="tt-meta">` +
                    `week ${index.toLocaleString()} of ${TOTAL_WEEKS.toLocaleString()}` +
                    ` · ${status}` +
                `</span>`;

            tip.hidden = false;
        });

        grid.addEventListener('mouseleave', () => { tip.hidden = true; });

        document.addEventListener('mousemove', e => {
            if (tip.hidden) return;
            const tw = tip.offsetWidth;
            const th = tip.offsetHeight;
            let x = e.clientX + 14;
            let y = e.clientY - th - 10;
            if (y < 8) y = e.clientY + 16;
            if (x + tw > window.innerWidth - 8) x = e.clientX - tw - 14;
            tip.style.left = x + 'px';
            tip.style.top  = y + 'px';
        });
    }

    // -------------------------------------------------------------------------
    // Week popup — dynamic day count
    // -------------------------------------------------------------------------

    function initWeekPopup(grid) {
        const backdrop = document.createElement('div');
        backdrop.className = 'week-popup-backdrop';
        backdrop.hidden = true;

        const card = document.createElement('div');
        card.className = 'week-popup-card';
        card.setAttribute('role', 'dialog');
        card.setAttribute('aria-modal', 'true');

        backdrop.appendChild(card);
        document.body.appendChild(backdrop);

        function openPopup(cell) {
            const startMs    = parseInt(cell.dataset.startRaw, 10);
            const endMs      = parseInt(cell.dataset.endRaw, 10);
            const year       = parseInt(cell.dataset.year, 10);
            const weekInYear = parseInt(cell.dataset.weekInYear, 10);
            const index      = parseInt(cell.dataset.index, 10);

            const today = new Date();
            today.setHours(0, 0, 0, 0);

            // Dynamically calculate how many days are in this week (7, 8, or 9).
            const daysInWeek = Math.round((endMs - startMs) / (24 * 60 * 60 * 1000)) + 1;

            const header = document.createElement('div');
            header.className = 'week-popup-header';

            const title = document.createElement('div');
            title.className = 'week-popup-title';
            title.textContent = `Age ${year} — year ${year + 1}, week ${weekInYear}`;

            const sub = document.createElement('div');
            sub.className = 'week-popup-sub';
            sub.textContent = `week ${index.toLocaleString()} of ${TOTAL_WEEKS.toLocaleString()}`;

            const closeBtn = document.createElement('button');
            closeBtn.className = 'week-popup-close';
            closeBtn.setAttribute('aria-label', 'Close');
            closeBtn.innerHTML = '×';
            closeBtn.addEventListener('click', closePopup);

            header.appendChild(title);
            header.appendChild(sub);
            header.appendChild(closeBtn);

            const days = document.createElement('div');
            days.className = 'week-popup-days';

            for (let d = 0; d < daysInWeek; d++) {
                const dayDate = new Date(startMs);
                dayDate.setDate(dayDate.getDate() + d);
                dayDate.setHours(0, 0, 0, 0);

                const wday = document.createElement('div');
                wday.className = 'wday';

                if (dayDate < today) {
                    wday.classList.add('wday--past');
                } else if (dayDate.getTime() === today.getTime()) {
                    wday.classList.add('wday--today');
                } else {
                    wday.classList.add('wday--future');
                }

                const dot = document.createElement('div');
                dot.className = 'wday-dot';

                const name = document.createElement('div');
                name.className = 'wday-name';
                // Derive day name from the date itself — never misaligned.
                name.textContent = dayDate.toLocaleDateString('en-US', { weekday: 'short' });

                const date = document.createElement('div');
                date.className = 'wday-date';
                date.textContent = dayDate.toLocaleDateString('en-US', {
                    month: 'short', day: 'numeric'
                });

                const dayNum = Math.floor(
                    (dayDate.getTime() - BIRTHDAY.getTime()) / (24 * 60 * 60 * 1000)
                ) + 1;
                const numEl = document.createElement('div');
                numEl.className = 'wday-daynum';
                numEl.textContent = 'day ' + dayNum.toLocaleString();

                wday.appendChild(dot);
                wday.appendChild(name);
                wday.appendChild(date);
                wday.appendChild(numEl);
                days.appendChild(wday);
            }

            card.innerHTML = '';
            card.appendChild(header);
            card.appendChild(days);

            backdrop.hidden = false;
            closeBtn.focus();
        }

        function closePopup() {
            backdrop.hidden = true;
        }

        grid.addEventListener('click', e => {
            const cell = e.target.closest('.week');
            if (!cell) return;
            openPopup(cell);
        });

        backdrop.addEventListener('click', e => {
            if (e.target === backdrop) closePopup();
        });

        document.addEventListener('keydown', e => {
            if (e.key === 'Escape' && !backdrop.hidden) closePopup();
        });
    }

    // -------------------------------------------------------------------------
    // Countdown
    // -------------------------------------------------------------------------

    function initCountdown() {
        const wrapper = document.getElementById('countdown-wrapper');
        if (!wrapper) return;

        let unit = localStorage.getItem('mm-unit') || 'seconds';

        const labelEl    = document.createElement('div');
        labelEl.className = 'countdown-label';

        const valueEl    = document.createElement('div');
        valueEl.className = 'countdown-value';

        const switcherEl = document.createElement('div');
        switcherEl.className = 'countdown-switcher';

        ['seconds', 'hours', 'seasons'].forEach(u => {
            const btn = document.createElement('button');
            btn.className = 'countdown-btn';
            btn.dataset.unit = u;
            btn.textContent = u;
            if (u === unit) btn.classList.add('is-active');
            btn.addEventListener('click', () => {
                unit = u;
                localStorage.setItem('mm-unit', u);
                switcherEl.querySelectorAll('.countdown-btn').forEach(b =>
                    b.classList.toggle('is-active', b.dataset.unit === u));
                tick();
            });
            switcherEl.appendChild(btn);
        });

        wrapper.appendChild(labelEl);
        wrapper.appendChild(valueEl);
        wrapper.appendChild(switcherEl);

        function format(ms) {
            if (ms <= 0) return '0';
            if (unit === 'seconds') return Math.floor(ms / 1000).toLocaleString();
            if (unit === 'hours')   return Math.floor(ms / (1000 * 60 * 60)).toLocaleString();
            return Math.floor(ms / SEASON_MS).toLocaleString(); // seasons — whole integer
        }

        function label() {
            if (unit === 'seconds') return 'seconds remaining';
            if (unit === 'hours')   return 'hours remaining';
            // seasons: poetic label with current season name
            return 'seasons remaining — it is ' + currentSeasonName();
        }

        function tick() {
            const ms = Math.max(0, LIFE_END.getTime() - Date.now());
            labelEl.textContent = label();
            valueEl.textContent = format(ms);
        }

        tick();
        setInterval(tick, 1000);
    }

    // -------------------------------------------------------------------------
    // Init
    // -------------------------------------------------------------------------

    function init() {
        buildGrid();
        initCountdown();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

}());
