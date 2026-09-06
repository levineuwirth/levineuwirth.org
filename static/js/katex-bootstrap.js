/* katex-bootstrap.js — Render every <span class="math"> / <div class="math">
   block once KaTeX has finished loading.

   Pandoc emits math blocks with the `math` class and the LaTeX source as
   the element's text content. KaTeX is loaded with `defer` so this
   bootstrap can simply run on DOMContentLoaded — KaTeX guarantees its
   own definitions are available by then.

   Used to live as an inline `onload="..."` attribute on the KaTeX
   <script> tag in templates/default.html, which blocked any future
   strict CSP. Externalized here so the entire site can run with
   `script-src 'self'` plus a single CDN allowance.

   Dynamic content (smaller finding 7): rendering used to happen once, on
   DOMContentLoaded, so math inside a transcluded passage stayed as raw
   LaTeX. It now takes a root and listens for `ln:content-added`. Each
   element is marked once rendered, because re-rendering a finished block
   would typeset KaTeX's own output as if it were source.
*/
(function () {
    'use strict';

    function renderIn(root) {
        if (typeof katex === 'undefined') return;
        var scope = root && root.querySelectorAll ? root : document;

        var nodes = Array.from(scope.querySelectorAll('.math'));
        /* querySelectorAll only looks *below* the root; a transcluded
           fragment can itself be the math element. */
        if (scope.nodeType === 1 && scope.classList
            && scope.classList.contains('math')) {
            nodes.unshift(scope);
        }

        nodes.forEach(function (el) {
            if (el.tagName !== 'SPAN' && el.tagName !== 'DIV') return;
            if (el.dataset.katexRendered === '1') return;
            var src = el.textContent;
            try {
                katex.render(src, el, {
                    displayMode:  el.classList.contains('display'),
                    output:       'htmlAndMathml',
                    throwOnError: false
                });
                el.dataset.katexRendered = '1';
            } catch (_) {
                /* leave the original source visible if KaTeX rejects it */
            }
        });
    }

    window.renderMath = renderIn;

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function () {
            renderIn(document);
        });
    } else {
        renderIn(document);
    }

    document.addEventListener('ln:content-added', function (e) {
        renderIn(e.detail && e.detail.container);
    });
})();
