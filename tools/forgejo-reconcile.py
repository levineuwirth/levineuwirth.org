#!/usr/bin/env python3
"""Reconcile explicitly mapped Git branches, checking ancestry before every push.

Config and state are private. Dry run is the default; --execute enables pushes.
No branch discovery, deletion, history replacement, tags, merges, or repository creation.
"""
import argparse
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit


class Held(Exception):
    pass


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def write_json(path, data):
    path = Path(path)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix=".reconcile-")
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(data, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def git(args, cwd=None, endpoint=None, allow_local=False, check=True):
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(GIT_TERMINAL_PROMPT="0", GIT_CONFIG_NOSYSTEM="1",
               GIT_CONFIG_GLOBAL="/dev/null", LC_ALL="C")
    env["GIT_ALLOW_PROTOCOL"] = "ssh:https" + (":file" if allow_local else "")
    if endpoint and endpoint.get("identity_file"):
        env["GIT_SSH_COMMAND"] = shlex.join([
            "ssh", "-F", "/dev/null", "-o", "BatchMode=yes", "-o",
            "IdentitiesOnly=yes", "-o", "StrictHostKeyChecking=yes", "-o",
            "ConnectTimeout=15", "-o", "ServerAliveInterval=15", "-o",
            "ServerAliveCountMax=2", "-o",
            "UserKnownHostsFile=" + endpoint["known_hosts"],
            "-i", endpoint["identity_file"],
        ])
    try:
        result = subprocess.run(["git", *args], cwd=cwd or "/", env=env,
                                capture_output=True, text=True, timeout=180)
    except subprocess.TimeoutExpired as exc:
        raise Held("git command timed out; retry next run") from exc
    if check and result.returncode:
        # Git stderr may contain credential URLs, private paths, or server banners.
        # Keep it out of status/journal; exact command type still identifies the step.
        raise Held(f"git {args[0]} failed (exit {result.returncode}); check access or concurrent updates")
    return result


def branch_ref(branch):
    ref = "refs/heads/" + branch
    if git(["check-ref-format", ref], check=False).returncode:
        raise ValueError("invalid branch name")
    return ref


def validate(config, allow_local=False):
    if not config["repositories"]:
        raise ValueError("at least one repository mapping is required")
    ids = set()
    destinations = set()
    for pair in config["repositories"]:
        if not re.fullmatch(r"[a-zA-Z0-9_-]+", pair["id"]) or pair["id"] in ids:
            raise ValueError("repository IDs must be unique safe names")
        ids.add(pair["id"])
        if pair.get("direction", "both") not in ("both", "github-to-forgejo"):
            raise ValueError("invalid direction")
        for side in ("github", "forgejo"):
            endpoint = pair[side]
            url = endpoint["url"]
            parsed = urlsplit(url)
            local = allow_local and (parsed.scheme == "file" or Path(url).is_absolute())
            if not local and (parsed.scheme not in ("ssh", "https") or not parsed.hostname
                              or parsed.password or parsed.query or parsed.fragment
                              or parsed.username not in (None, "git")):
                raise ValueError("use SSH/HTTPS URLs without embedded credentials")
            if parsed.scheme == "ssh" and not (endpoint.get("identity_file") and endpoint.get("known_hosts")):
                raise ValueError("SSH endpoints require identity_file and known_hosts")
        if not pair["branches"]:
            raise ValueError("at least one explicit branch mapping is required")
        for mapping in pair["branches"]:
            for side in ("github", "forgejo"):
                ref = branch_ref(mapping[side])
                key = (pair[side]["url"], ref)
                if key in destinations:
                    raise ValueError("a remote branch appears in multiple mappings")
                destinations.add(key)


def remote_head(endpoint, ref, allow_local):
    output = git(["ls-remote", "--refs", endpoint["url"], ref],
                 endpoint=endpoint, allow_local=allow_local).stdout
    rows = [line.split() for line in output.splitlines() if line.strip()]
    if not rows:
        return None
    if len(rows) != 1 or rows[0][1] != ref or not re.fullmatch(r"[0-9a-f]{40,64}", rows[0][0]):
        raise Held("unexpected remote branch advertisement")
    return rows[0][0]


def ancestor(cache, older, newer):
    result = git(["merge-base", "--is-ancestor", older, newer], cwd=cache, check=False)
    if result.returncode not in (0, 1):
        raise Held("cannot verify ancestry; preserve the cache and inspect")
    return result.returncode == 0


def reconcile(pair, mapping, cache, baseline, execute, allow_local, save_agreement):
    refs = {side: branch_ref(mapping[side]) for side in ("github", "forgejo")}
    heads = {}
    for side, ref in refs.items():
        endpoint = pair[side]
        if remote_head(endpoint, ref, allow_local) is None:
            raise Held(f"{side} branch is missing; branch creation/deletion requires review")
        git(["fetch", "--no-tags", "--no-write-fetch-head", endpoint["url"],
             f"+{ref}:refs/observed/{side}"], cwd=cache, endpoint=endpoint,
            allow_local=allow_local)
        heads[side] = git(["rev-parse", f"refs/observed/{side}"], cwd=cache).stdout.strip()
    # A prior agreed commit must remain reachable on both sides. This catches a
    # force reset even when the other side could fast-forward it back to that commit.
    if baseline:
        for side, head in heads.items():
            if not ancestor(cache, baseline, head):
                raise Held(f"{side} no longer descends from last agreement; history rewrite requires review")
    gh, forge = heads["github"], heads["forgejo"]
    if gh == forge:
        return {"status": "matched", "sha": gh}, gh
    if ancestor(cache, forge, gh):
        source, target = "github", "forgejo"
    elif ancestor(cache, gh, forge):
        source, target = "forgejo", "github"
    else:
        raise Held("branches diverged; resolve on a host and let the next run retry")
    if pair.get("direction", "both") != "both" and source != "github":
        raise Held("outbound publishing is disabled for this visibility-mismatched pair")
    result = {"status": "would-update", "source": source, "target": target,
              "from": heads[target], "to": heads[source]}
    if not execute:
        return result, None
    # Snapshot freshness check plus an exact-tip lease. The ancestry check above
    # is mandatory: the lease provides compare-and-swap, NEVER permission to
    # replace history. It also prevents recreating a concurrently deleted ref or
    # undoing a concurrent reset, which an ordinary fast-forward push could do.
    for side, ref in refs.items():
        if remote_head(pair[side], ref, allow_local) != heads[side]:
            raise Held("branch changed during inspection; retry next run")
    if baseline is None:
        # Both hosts contain this commit already. Save before the first push,
        # so a crash cannot leave the bootstrap without a history checkpoint.
        save_agreement(heads[target])
    git(["push", "--porcelain", f"--force-with-lease={refs[target]}:{heads[target]}", pair[target]["url"],
         f"{heads[source]}:{refs[target]}"], cwd=cache, endpoint=pair[target], allow_local=allow_local)
    # Only save an agreement after reading it back from both hosts.
    for side, ref in refs.items():
        if remote_head(pair[side], ref, allow_local) != heads[source]:
            raise Held("push completed but branches changed before verification; retry next run")
    result["status"] = "updated"
    return result, heads[source]


def run(config, state_dir, cache_dir, execute=False, allow_local=False):
    validate(config, allow_local)
    state_dir, cache_dir = Path(state_dir), Path(cache_dir)
    for directory in (state_dir, cache_dir):
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (state_dir / "lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        path = state_dir / "agreements.json"
        state = json.loads(path.read_text()) if path.exists() else {"version": 1, "refs": {}}
        if state.get("version") != 1 or not isinstance(state.get("refs"), dict):
            raise ValueError("unsupported agreement state")
        report = {"started_at": now(), "execute": execute, "refs": []}
        for pair in config["repositories"]:
            cache = cache_dir / (pair["id"] + ".git")
            for mapping in pair["branches"]:
                label = pair["id"] + ":" + mapping["github"] + ":" + mapping["forgejo"]
                fingerprint = hashlib.sha256(json.dumps({
                    "github": pair["github"]["url"], "forgejo": pair["forgejo"]["url"],
                    "branches": mapping, "direction": pair.get("direction", "both"),
                }, sort_keys=True).encode()).hexdigest()
                previous = state["refs"].get(label)
                row = {"repository": pair["id"], "branches": mapping, "checked_at": now()}
                try:
                    if previous and previous["mapping"] != fingerprint:
                        raise Held("mapping changed; review and explicitly retire the old agreement")
                    if shutil.disk_usage(cache_dir).free < config.get("minimum_free_bytes", 2 * 1024**3):
                        raise Held("insufficient free disk space for fetch")
                    if not cache.exists():
                        git(["init", "--bare", str(cache)])
                    def save_agreement(sha):
                        state["refs"][label] = {"mapping": fingerprint, "sha": sha, "agreed_at": now()}
                        write_json(path, state)
                    result, agreed = reconcile(pair, mapping, cache,
                                               previous["sha"] if previous else None,
                                               execute, allow_local, save_agreement)
                    row.update(result)
                    if execute and agreed:
                        # Persist each agreement: other repositories can fail independently.
                        save_agreement(agreed)
                except (Held, OSError) as exc:
                    row.update(status="held", reason=str(exc) if isinstance(exc, Held) else "local I/O error")
                report["refs"].append(row)
        report["finished_at"] = now()
        report["held"] = sum(row["status"] == "held" for row in report["refs"])
        report["updated"] = sum(row["status"] == "updated" for row in report["refs"])
        report["matched"] = sum(row["status"] == "matched" for row in report["refs"])
        write_json(state_dir / ("report.json" if execute else "dry-run.json"), report)
        if execute and not report["held"]:
            write_json(state_dir / "last-success.json", {"at": report["finished_at"]})
        return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="/etc/forgejo-reconcile/config.json")
    parser.add_argument("--state-dir", default="/var/lib/forgejo-reconcile")
    parser.add_argument("--cache-dir", default="/var/cache/forgejo-reconcile")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    os.umask(0o077)
    try:
        report = run(json.loads(Path(args.config).read_text()), args.state_dir, args.cache_dir, args.execute)
        print(json.dumps(report, sort_keys=True))
        return 1 if report["held"] else 0
    except (ValueError, KeyError, OSError, Held) as exc:
        print("forgejo-reconcile: configuration/state/lock error (" + type(exc).__name__ + "); inspect private files", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
