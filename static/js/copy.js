/* copy.js — Copy-to-clipboard button for <pre> code blocks.
 *
 * Injects a .copy-btn into every <pre> element on the page.
 * The button is visually hidden until the block is hovered (CSS handles this).
 * On click: copies the text content of the block, shows "copied" briefly.
 *
 * Dynamic content (smaller finding 7): this used to run once, on
 * DOMContentLoaded, so a code block arriving later — a transcluded passage,
 * anything else injected after load — had no copy button. It now attaches
 * over an arbitrary root and listens for `ln:content-added`, the event
 * transclude.js dispatches after injecting content. Attaching is idempotent
 * per <pre> (a data flag), so a container enhanced twice gets one button.
 */

(function () {
    'use strict';

    var RESET_DELAY = 1800; /* ms before label reverts to "copy" */

    function attachButton(pre) {
        if (pre.dataset.copyButton === '1') return;
        pre.dataset.copyButton = '1';

        var btn = document.createElement('button');
        btn.className = 'copy-btn';
        btn.textContent = 'copy';
        btn.setAttribute('aria-label', 'Copy code to clipboard');

        btn.addEventListener('click', function () {
            var code = pre.querySelector('code');
            var text;
            if (code) {
                text = code.innerText;
            } else {
                /* Code-less <pre>: clone and strip the injected button so
                   its label is not copied along with the content. */
                var clone = pre.cloneNode(true);
                var cloneBtn = clone.querySelector('.copy-btn');
                if (cloneBtn) cloneBtn.remove();
                text = clone.innerText;
            }

            navigator.clipboard.writeText(text).then(function () {
                btn.textContent = 'copied';
                btn.setAttribute('data-copied', '');
                setTimeout(function () {
                    btn.textContent = 'copy';
                    btn.removeAttribute('data-copied');
                }, RESET_DELAY);
            }).catch(function () {
                btn.textContent = 'error';
                setTimeout(function () {
                    btn.textContent = 'copy';
                }, RESET_DELAY);
            });
        });

        pre.insertBefore(btn, pre.firstChild);
    }

    /* Attach to every <pre> at or below `root` (a document, an element, or
       nothing at all — in which case the whole document). */
    function initCopyButtons(root) {
        var scope = root && root.querySelectorAll ? root : document;
        if (scope.nodeType === 1 && scope.tagName === 'PRE') attachButton(scope);
        scope.querySelectorAll('pre').forEach(attachButton);
    }

    window.initCopyButtons = initCopyButtons;

    document.addEventListener('DOMContentLoaded', function () {
        initCopyButtons(document);
    });

    /* Content injected after load (transclusions, and anything else that
       calls window.lnEnhance). */
    document.addEventListener('ln:content-added', function (e) {
        initCopyButtons(e.detail && e.detail.container);
    });
}());
