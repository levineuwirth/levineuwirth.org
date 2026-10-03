"""Exercise the annotation anchor's real JavaScript text and offset mapping."""

import json
from pathlib import Path
import shutil
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which("node"), "node is needed to exercise annotation anchoring")
class AnnotationAnchorTests(unittest.TestCase):
    def run_anchor(self, cases):
        source = (ROOT / "static/js/annotations.js").read_text()
        start = source.index("    function collapse(")
        end = source.index("    function applyAnnotation(")
        script = r"""
let nodes;
const NodeFilter = {SHOW_TEXT: 4};
const document = {
    createTreeWalker() {
        let i = 0;
        return {nextNode: () => nodes[i++] || null};
    },
    createRange() {
        return {
            setStart(node, offset) { this.start = [nodes.indexOf(node), offset]; },
            setEnd(node, offset) { this.end = [nodes.indexOf(node), offset]; }
        };
    }
};
""" + source[start:end] + "\nconst cases = " + json.dumps(cases) + r""";
const results = cases.map(c => {
    nodes = c.nodes.map(n => ({nodeValue: n.text.repeat(n.repeat || 1),
        parentElement: {closest: () => n.marked || null}}));
    return findTextRange(c.needle, {});
});
console.log(JSON.stringify(results));
"""
        # The previous per-character charAt flattened the growing string:
        # 600k characters took ~20 s; the linear scan takes under 0.2 s.
        # A generous timeout catches the freeze without timing tiny inputs.
        result = subprocess.run(["node"], input=script, text=True,
                                capture_output=True, check=True, timeout=10)
        return json.loads(result.stdout)

    def test_whitespace_across_nodes_maps_to_original_offsets(self):
        result = self.run_anchor([
            {"nodes": [{"text": "  alpha\n "}, {"text": "\tbeta\u00a0gamma  "}],
             "needle": "alpha beta gamma"},
            {"nodes": [{"text": "hidden", "marked": True}, {"text": "visible"}],
             "needle": "visible"},
            {"nodes": [{"text": "text"}], "needle": " \n\t"},
            {"nodes": [{"text": "text"}], "needle": "absent"},
        ])
        self.assertEqual(result, [
            {"start": [0, 2], "end": [1, 11]},
            {"start": [1, 0], "end": [1, 7]}, None, None,
        ])

    def test_long_page_does_not_freeze_while_locating_a_quote(self):
        result = self.run_anchor([{
            "nodes": [{"text": "hello world ", "repeat": 50000}, {"text": "the end"}],
            "needle": "world the end",
        }])
        self.assertEqual(result, [{"start": [0, 599994], "end": [1, 7]}])
