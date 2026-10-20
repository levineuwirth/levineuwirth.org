Commit-response study: frozen reproduction copy for the essay draft

This is a presentation copy of the reviewed 2026-10-20 analysis, not a new
collection or experiment. Request data stop at 2026-10-19 22:00 UTC; the
publication snapshot was collected at 22:23:19 UTC that day.

REPORT.html is a readable rendering of REPORT.md. Source, reviewed tables,
results, the original plan, amendments and independent spot-check accompany it.
Private logs, addresses, individual user-agent strings and pseudonyms are not
included. Internal handoff/provisional files and scratch literature notes are
omitted from this presentation copy. The canonical study remains at:
anubis/observations/2026-10-20/commit-response/ in the website repository.

From this extracted directory, use Python with NumPy, SciPy and matplotlib
(the recorded versions are in REPORT.md):

    python source/test_commitstats.py
    python source/analysis.py
    python source/hash_analysis.py
    python source/power.py
    python source/exploratory_bursts.py
    MPLCONFIGDIR=/tmp/commit-response-matplotlib python source/plots.py

The timing snippets in the essay run with this source directory on PYTHONPATH:

    PYTHONPATH=source python example.py

The CSV/gzip tables are already frozen inputs; no SSH access is necessary for
these commands. Do not run the collection/private-source scripts to reproduce
local results: they are included to document the read-only collection method
and require the author's private VPS. Data and result generation uses fixed
seeds; plot rendering may depend on installed fonts. Matplotlib config/cache
should be directed to a writable temporary directory.

PROVENANCE.json records the canonical source files and the exact hashes copied.
MANIFEST.sha256 covers the presentation files before bundling. The archive does
not contain itself. Future experiments should use a separate observation folder.
