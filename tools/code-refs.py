#!/usr/bin/env python3
"""code-refs.py — build-time snapshots of the GitHub code that prose links to.

A link such as

    https://github.com/<owner>/<repo>/blob/<sha>/analysis/results.md

used to get the same hover popup as a link to the bare repository: the
repository's description and its star count, fetched live from
api.github.com. This tool fetches what the link actually points at, once,
and stores it in the site so the popup can show it from the same origin.

    fetch   Scan content/**/*.md for GitHub blob / tree / commit links,
            fetch any snapshot that is missing, and rewrite
            code-refs/index.json. Wired into `make build`.
    gc      Delete snapshots that no current link references
            (--dry-run lists them instead).

What gets stored, under code-refs/github/<owner>/<repo>/<sha>/:

    commit.json          message, author, date, diffstat, changed files —
                         fetched for every commit any link resolves to, so
                         blob and tree popups can say which revision (and
                         when) they show
    blob/<path>.txt      the file's raw bytes. The .txt suffix is load-
                         bearing: an .html or .svg from someone else's
                         repository must never be served as a document
                         from this origin.
    tree/<path>.json     the directory listing, plus the README's opening
                         (tree/_root.json for the repository root)

Pinned links (a hex commit id in the URL) are immutable: they are fetched
once and never again, which is why the store is tracked in Git rather than
regenerated — it is also the only copy left if the upstream history is
rewritten or the repository disappears. Branch links (…/tree/main) are
re-resolved on every run and snapshotted at the commit the branch points
to at build time; the popup says "as of" that date.

Network failures are warnings, never build failures. A link whose fetch
failed keeps its previous snapshot if it had one, and simply has no code
popup otherwise (the next build retries).

Unauthenticated, the GitHub REST API allows 60 requests an hour. A pinned
link costs at most two requests, ever; raw file contents come from
raw.githubusercontent.com, which is not metered the same way. Set
GITHUB_TOKEN in the environment to raise the limit.

Limits (deliberate): only github.com; a branch name is taken to be the
first path segment after blob/ or tree/, so branch names containing '/'
are not recognised; files over MAX_BLOB_BYTES and binary files are skipped.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = ROOT / "content"
STORE_DIR = ROOT / "code-refs"
INDEX_PATH = STORE_DIR / "index.json"
PUBLIC_PREFIX = "/code-refs/"

MAX_BLOB_BYTES = 1_000_000
MAX_COMMIT_FILES = 100
MAX_README_CHARS = 4000
TIMEOUT = 20

# Owner and repository name as GitHub permits them; the rest of the path is
# taken up to the first character that cannot belong to a Markdown link
# target. The fragment is not captured — it selects within the snapshot
# (a line range or a heading) and is the popup's business, not the store's.
URL_RE = re.compile(
    r"https://github\.com/"
    r"(?P<owner>[A-Za-z0-9](?:[A-Za-z0-9-]{0,38}))/"
    r"(?P<repo>[A-Za-z0-9._-]+)/"
    r"(?P<kind>blob|tree|commit)/"
    r"(?P<rest>[^\s)\]>\"'#?]+)"
)
FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
SHORT_SHA_RE = re.compile(r"^[0-9a-f]{7,39}$")
README_RE = re.compile(r"^readme(\.(md|markdown|txt|rst))?$", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Link discovery
# ---------------------------------------------------------------------------

def canonical_url(owner: str, repo: str, kind: str, rest: str) -> str:
    return f"https://github.com/{owner}/{repo}/{kind}/{rest}"


def parse_link(match: re.Match) -> dict | None:
    """Split a matched URL into its parts, or None if it is not usable."""
    owner, repo, kind = match["owner"], match["repo"], match["kind"]
    rest = match["rest"].rstrip(".,;:").rstrip("/")
    if not rest:
        return None
    ref, _, path = rest.partition("/")
    path = urllib.parse.unquote(path)
    # The path becomes a filesystem path under the store; refuse anything
    # that could step outside it.
    if path and any(seg in ("", ".", "..") for seg in path.split("/")):
        return None
    pinned = bool(FULL_SHA_RE.match(ref) or SHORT_SHA_RE.match(ref))
    if kind == "commit" and (path or not pinned):
        return None
    elif kind == "blob" and not path:
        return None
    return {
        "url": canonical_url(owner, repo, kind, rest),
        "kind": kind,
        "owner": owner,
        "repo": repo,
        "ref": ref,
        "path": path,
        "pinned": pinned,
    }


def discover_links(content_dir: Path = CONTENT_DIR) -> dict[str, dict]:
    links: dict[str, dict] = {}
    for md in sorted(content_dir.rglob("*.md")):
        try:
            text = md.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for m in URL_RE.finditer(text):
            link = parse_link(m)
            if link:
                links.setdefault(link["url"], link)
    return links


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

class FetchError(Exception):
    pass


def http_get(url: str, *, api: bool) -> bytes:
    headers = {"User-Agent": "levineuwirth.org code-refs"}
    if api:
        headers["Accept"] = "application/vnd.github+json"
        token = os.environ.get("GITHUB_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.read(MAX_BLOB_BYTES + 1)
    except urllib.error.HTTPError as e:
        hint = ""
        if e.code == 403 and e.headers.get("x-ratelimit-remaining") == "0":
            hint = " (API rate limit; set GITHUB_TOKEN)"
        raise FetchError(f"HTTP {e.code} for {url}{hint}") from None
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise FetchError(f"{url}: {e}") from None


def api_json(path: str):
    return json.loads(http_get("https://api.github.com" + path, api=True))


def quote_path(path: str) -> str:
    return urllib.parse.quote(path, safe="/")


# ---------------------------------------------------------------------------
# Snapshots
# ---------------------------------------------------------------------------

def sha_dir(owner: str, repo: str, sha: str) -> Path:
    return STORE_DIR / "github" / owner / repo / sha


def public(path: Path) -> str:
    return PUBLIC_PREFIX + path.relative_to(STORE_DIR).as_posix()


def write_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".partial")
    tmp.write_bytes(data)
    tmp.replace(path)


def write_json(path: Path, obj) -> None:
    write_atomic(path, (json.dumps(obj, indent=1, ensure_ascii=False) + "\n").encode())


def ensure_commit(owner: str, repo: str, ref: str) -> dict:
    """Commit metadata for `ref`, from the store when the ref is a full SHA
    already fetched; otherwise from the API (which also resolves short SHAs
    and branch names to the full SHA)."""
    if FULL_SHA_RE.match(ref):
        cached = sha_dir(owner, repo, ref) / "commit.json"
        if cached.exists():
            return json.loads(cached.read_text())
    data = api_json(f"/repos/{owner}/{repo}/commits/{urllib.parse.quote(ref, safe='')}")
    files = data.get("files") or []
    commit = {
        "sha": data["sha"],
        "message": data["commit"]["message"],
        "author": (data["commit"].get("author") or {}).get("name", ""),
        "date": (data["commit"].get("committer") or {}).get("date", ""),
        "parents": [p["sha"] for p in data.get("parents", [])],
        "stats": data.get("stats") or {},
        "files_total": len(files),
        "files": [
            {k: f.get(k) for k in ("filename", "status", "additions", "deletions")}
            for f in files[:MAX_COMMIT_FILES]
        ],
    }
    write_json(sha_dir(owner, repo, commit["sha"]) / "commit.json", commit)
    return commit


def ensure_blob(owner: str, repo: str, sha: str, path: str) -> Path:
    dest = sha_dir(owner, repo, sha) / "blob" / (path + ".txt")
    if dest.exists():
        return dest
    raw = http_get(
        f"https://raw.githubusercontent.com/{owner}/{repo}/{sha}/{quote_path(path)}",
        api=False,
    )
    if len(raw) > MAX_BLOB_BYTES:
        raise FetchError(f"{path}: larger than {MAX_BLOB_BYTES} bytes, skipped")
    if b"\0" in raw[:8192]:
        raise FetchError(f"{path}: binary file, skipped")
    try:
        raw.decode("utf-8")
    except UnicodeDecodeError:
        raise FetchError(f"{path}: not UTF-8 text, skipped") from None
    write_atomic(dest, raw)
    return dest


def ensure_tree(owner: str, repo: str, sha: str, path: str) -> Path:
    dest = sha_dir(owner, repo, sha) / "tree" / ((path or "_root") + ".json")
    if dest.exists():
        return dest
    api_path = f"/repos/{owner}/{repo}/contents"
    if path:
        api_path += "/" + quote_path(path)
    listing = api_json(api_path + "?ref=" + sha)
    if not isinstance(listing, list):
        raise FetchError(f"{path or '/'}: not a directory at {sha[:7]}")
    entries = sorted(
        ({"name": e["name"], "type": e["type"], "size": e.get("size", 0)} for e in listing),
        key=lambda e: (e["type"] != "dir", e["name"].lower()),
    )
    readme = None
    for e in entries:
        if e["type"] == "file" and README_RE.match(e["name"]):
            rpath = f"{path}/{e['name']}" if path else e["name"]
            try:
                text = http_get(
                    f"https://raw.githubusercontent.com/{owner}/{repo}/{sha}/{quote_path(rpath)}",
                    api=False,
                ).decode("utf-8", errors="replace")
                readme = {"name": e["name"], "text": text[:MAX_README_CHARS]}
            except FetchError as err:
                warn(f"README for {path or '/'}: {err}")
            break
    write_json(dest, {"path": path, "entries": entries, "readme": readme})
    return dest


def snapshot(link: dict) -> dict:
    """Fetch (or find) the snapshot for one link; return its index entry."""
    owner, repo = link["owner"], link["repo"]
    commit = ensure_commit(owner, repo, link["ref"])
    sha = commit["sha"]
    kind = link["kind"]
    if kind == "blob":
        src = ensure_blob(owner, repo, sha, link["path"])
    elif kind == "tree":
        src = ensure_tree(owner, repo, sha, link["path"])
    else:
        src = sha_dir(owner, repo, sha) / "commit.json"
    return {
        "kind": kind,
        "host": "github",
        "owner": owner,
        "repo": repo,
        "ref": link["ref"],
        "sha": sha,
        "path": link["path"],
        "pinned": link["pinned"],
        "src": public(src),
        "commit": public(sha_dir(owner, repo, sha) / "commit.json"),
        "date": commit.get("date", ""),
        "fetched": dt.date.today().isoformat(),
    }


def snapshot_present(entry: dict) -> bool:
    return all(
        (STORE_DIR / entry[k][len(PUBLIC_PREFIX):]).exists() for k in ("src", "commit")
    )


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def warn(msg: str) -> None:
    print(f"code-refs: warning: {msg}", file=sys.stderr)


def load_index() -> dict:
    try:
        return json.loads(INDEX_PATH.read_text())
    except (OSError, ValueError):
        return {}


def cmd_fetch(_args) -> int:
    links = discover_links()
    old = load_index()
    new: dict[str, dict] = {}
    fetched = failed = 0
    for url, link in sorted(links.items()):
        prev = old.get(url)
        if prev and prev.get("pinned") and snapshot_present(prev):
            new[url] = prev
            continue
        try:
            new[url] = snapshot(link)
            fetched += 1
        except (FetchError, KeyError, ValueError) as e:
            failed += 1
            warn(str(e))
            if prev and snapshot_present(prev):
                new[url] = prev
    if new != old:
        STORE_DIR.mkdir(exist_ok=True)
        write_json(INDEX_PATH, dict(sorted(new.items())))
    print(
        f"code-refs: {len(new)} linked snapshots"
        f" ({fetched} fetched, {failed} failed, {len(links) - len(new)} without a snapshot)"
    )
    return 0


def cmd_gc(args) -> int:
    index = load_index()
    keep = {
        (STORE_DIR / e[k][len(PUBLIC_PREFIX):]).resolve()
        for e in index.values() for k in ("src", "commit")
    }
    gh = STORE_DIR / "github"
    doomed = [p for p in gh.rglob("*") if p.is_file() and p.resolve() not in keep] if gh.exists() else []
    for p in doomed:
        print(("would remove " if args.dry_run else "removed ") + str(p.relative_to(ROOT)))
        if not args.dry_run:
            p.unlink()
    if not args.dry_run and gh.exists():
        for d in sorted((d for d in gh.rglob("*") if d.is_dir()), key=lambda d: -len(d.parts)):
            if not any(d.iterdir()):
                d.rmdir()
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("fetch", help="snapshot every linked GitHub blob/tree/commit")
    gc = sub.add_parser("gc", help="delete snapshots no link references")
    gc.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    return {"fetch": cmd_fetch, "gc": cmd_gc}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
