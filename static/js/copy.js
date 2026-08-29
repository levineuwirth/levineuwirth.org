/* copy.js — Copy-to-clipboard button for <pre> code blocks.
 *
 * Injects a .copy-btn into every <pre> element on the page.
 * The button is visually hidden until the block is hovered (CSS handles this).
 * On click: copies the text content of the block, shows "copied" briefly.
 */

(function () {
    'use strict';

    var RESET_DELAY = 1800; /* ms before label reverts to "copy" */

    function attachButton(pre) {
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

    document.addEventListener('DOMContentLoaded', function () {
        document.querySelectorAll('pre').forEach(attachButton);
    });
}());
