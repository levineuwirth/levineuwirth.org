# GitHub ↔ Forgejo reconciliation

`tools/forgejo-reconcile.py` runs on the VPS as the unprivileged `forge-sync`
user. It polls an explicit private list of repositories and branch mappings.
The initial rollout manages default branches only; the configuration accepts
multiple explicit branch mappings per pair for a later feature-branch rollout.
Issues, pull requests, releases, tags, branch settings and other host metadata
are outside its scope.

For each branch pair, the job fetches both histories into an isolated bare
cache. If one tip descends from the other, it advances the lagging host.
An update requires both an ancestry check and an exact destination-tip lease
(`git push --force-with-lease=<ref>:<observed-sha>`). The lease supplies an
atomic expected-value check; the script never permits a non-fast-forward
update. It rejects a concurrent advance, reset or deletion instead of
overwriting it. The source is also checked immediately before a push; no
two-host operation can make source and destination changes atomic together.

The job holds a branch if it diverges, disappears, stops descending from the
last agreement, or fails an access check. It never deletes or creates branches,
merges, rebases, or creates repositories. Other configured branch pairs still
run, and the timer retries after a failed run. Initial missing branches also
require review. A first fast-forward saves the previously shared commit
before pushing; subsequent agreements are saved only after both hosts verify.

Configuration lives at `/etc/forgejo-reconcile/config.json`, readable only
by root and `forge-sync`. Each endpoint has its own repository deploy key;
GitHub and loopback Forgejo SSH host keys are pinned. The VPS does not hold
the owner's personal GitHub token. A future GitHub App could replace the
per-repository keys. Deploy keys do not enforce the branch allowlist on the
server; the private configuration and script enforce that scope.

Example (public project names only; the live inventory is private):

```json
{
  "minimum_free_bytes": 2147483648,
  "repositories": [{
    "id": "epiphany",
    "github": {
      "url": "ssh://git@github.com/levineuwirth/epiphany.git",
      "identity_file": "/etc/forgejo-reconcile/keys/epiphany-github",
      "known_hosts": "/etc/forgejo-reconcile/known_hosts"
    },
    "forgejo": {
      "url": "ssh://git@127.0.0.1:2222/neuwirth/epiphany.git",
      "identity_file": "/etc/forgejo-reconcile/keys/epiphany-forgejo",
      "known_hosts": "/etc/forgejo-reconcile/known_hosts"
    },
    "branches": [{"github": "main", "forgejo": "main"}]
  }]
}
```

For a public GitHub project paired with a private Forgejo project, set
`"direction": "github-to-forgejo"` until outbound publication is explicitly
approved. Default branches with different names can be mapped directly.
No setting or branch rename is needed.

Inspect or operate on the VPS:

```bash
systemctl status forgejo-reconcile.timer forgejo-reconcile.service
journalctl -u forgejo-reconcile.service --since today
cat /var/lib/forgejo-reconcile/report.json
sudo -u forge-sync /usr/local/bin/forgejo-reconcile.py  # dry run, no pushes
systemctl start forgejo-reconcile.service              # execute now
systemctl disable --now forgejo-reconcile.timer        # stop scheduling
```

Disabling the timer does not interrupt an already running service; stop that
unit too when editing mappings, keys or state. The job locks its state directory
to prevent overlapping manual/scheduled runs. `report.json` contains per-ref
results and timestamps; `dry-run.json` records dry runs without changing
agreements. `last-success.json` advances only when every managed pair verifies.
`tools/vps-status` shows check age, all-pairs success age, held count and timer
state. The journal/report can contain private repository identifiers; do not
publish their full contents.

For a divergence, fetch both hosts in a normal checkout and resolve/review
there. For an intentional reset, first stop the service, preserve the private
state, and review both tips. Explicitly retire only the relevant agreement
entry after accepting the replacement history. Never clear all agreement
state as a routine repair. Changing endpoint URLs or allowed directions also
requires reviewing the saved mapping fingerprint.

`vps-config-backup.sh` includes configuration, scoped keys and agreement state
in its private local archive and encrypted off-host backup. It excludes the
disposable caches. Restoring old state cannot detect a reset of commits newer
than that backup: inspect current tips before re-enabling after a restore.

Do not run Forgejo native push mirrors against the same refs: they force
updates and compete with reconciliation. The old manual `forgejo-sync.sh`
pushes local checkouts and is separate from this service.

Before adding features, decide how to handle branch creation and deletion.
Simply discovering a name on one host and copying it can resurrect a branch
deleted on the other. Existing feature branches can be enrolled explicitly
after an ancestry audit; automatic new-branch enrollment needs recorded
presence/deletion history. The known divergent feature branch stays outside
this first rollout.

Validation: `python3 -m unittest discover -s tests -p test_forgejo_reconcile.py`.
Tests use real local bare repositories, including races between inspection
and push. There is no production option to enable the test-only local protocol.

Initial rollout, 16 October 2026: nine default-branch pairs, including one
inbound-only pair across a public/private boundary. Six pairs needed a
fast-forward; three already matched. The old website push mirror was removed.
The live repository names, mappings, key IDs and first-run report are kept
privately on the VPS rather than in this public repository.
