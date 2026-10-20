Daily repository targets, 1–19 October 2026 (UTC)

repository-targets.svg/png: daily shares of repository HTTP 200 responses.
repository-targets-all-requests.svg/png: daily shares across all statuses.
Both include daily totals on a separate logarithmic axis. October 19 is
partial, ending at 19:00 UTC; hatching/open markers identify it.

Named categories: pmacs, levineuwirth.org, epiphany, LeVCS, and Other.
Counts include all methods and user agents, excluding known maintenance
probes. They are neither unique visitors nor confirmed crawler identities.

Canonical source and data:
anubis/observations/2026-10-20/repository-targets/

Rebuild aggregates from retained public tables, from repository root:
  python3 anubis/observations/2026-10-20/repository-targets/aggregate.py
  .venv/bin/python anubis/observations/2026-10-20/repository-targets/plot.py

Standalone plot export, with CSV beside the script:
  python plot-repository-targets.py --output-dir ../figures
Requires NumPy and matplotlib. No live/private log access is needed.

Source metadata record hashes, date boundaries, the small unallocated
summary residual assigned to Other, and the one-response Oct 3 difference
between the hourly cube and the older daily snapshot. Repository shares
and totals here consistently use that hourly cube for October 1–13.
