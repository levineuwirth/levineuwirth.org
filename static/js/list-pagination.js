(function () {
    var STORAGE_KEY = 'list-page-count';
    var DEFAULT     = 25;

    function applyCount(n) {
        var entries = document.querySelectorAll('.item-card');
        var limit   = (n === 'all') ? Infinity : parseInt(n, 10);
        entries.forEach(function (el, i) {
            el.hidden = i >= limit;
        });
        document.querySelectorAll('.list-count-btn').forEach(function (btn) {
            btn.classList.toggle('is-active', btn.dataset.count === String(n));
        });
        try { localStorage.setItem(STORAGE_KEY, n); } catch (e) {}
    }

    document.addEventListener('DOMContentLoaded', function () {
        var saved;
        try { saved = localStorage.getItem(STORAGE_KEY); } catch (e) {}
        applyCount(saved || DEFAULT);

        document.querySelectorAll('.list-count-btn').forEach(function (btn) {
            btn.addEventListener('click', function () { applyCount(btn.dataset.count); });
        });
    });
}());
