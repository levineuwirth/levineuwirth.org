---
title: "LeVCS: A Distributed Version Control System"
date: 2026-05-01
abstract: >
  LeVCS is a distributed version control system in the lineage of git, fossil, pijul, and sapling — content-addressed
  objects, signed history, three-way merge — with five things deliberately rebuilt: identity in the protocol, federation
  as a first-class concept, a cascading merge engine that dispatches per-file to format-aware and tree-sitter handlers,
  BLAKE3 hashing throughout, and releases as signed artifacts rather than mutable name pointers. v0.1.0 ships the
  protocol substrate; the workflow surface — review, issues, web UI — is the next layer up.
tags: [systems, projects, releases]
status: "Working model"
confidence: 85
importance: 3
evidence: 5
scope: broad
novelty: innovative
practicality: moderate
---

Naming a version control system after yourself is a mild hubris. Linus has been candid that this is exactly what he did with git — *"I'm an egotistical bastard, and I name all my projects after myself. First 'Linux', now 'git'."* LeVCS — Levi's [VCS]{.smallcaps} — admits the same joke up front and gets on with it. The work itself is the substrate: an object model, a federation [API]{.smallcaps}, a merge engine, and a small instance server, written in Rust, sized to fit on a [VPS]{.smallcaps} and audit-able by one person in a weekend.

The first instance will be at [levcs.levineuwirth.org](https://levcs.levineuwirth.org); the source lives at [git.levineuwirth.org/neuwirth/levcs](https://git.levineuwirth.org/neuwirth/levcs) and is mirrored by the same git infrastructure that hosts everything else. v0.1.0 is what is described here. The workflow surface — the [PR]{.smallcaps} review object, issue tracking, web [UI]{.smallcaps}, [CI]{.smallcaps} conventions — is intentionally not part of v0.1.0 and is the next document in the series.

This page describes what LeVCS is, why it diverges from git on five specific axes, and how to use and operate it today.

---

## What It Is

LeVCS is a distributed version control system. It uses the same conceptual primitives as every other modern [DVCS]{.smallcaps}: content-addressed objects, a directed-acyclic-graph history, signed commits, three-way merge. The substrate is small — about ten Rust crates, ~194 passing tests at v0.1.0, full `cargo test` under a minute on a laptop.

The short version of what comes with it:

- **Content addressing with [BLAKE3]{.smallcaps}** — 32-byte object identifiers everywhere, tree-hashed, ~5 [GiB]{.smallcaps}/s on a laptop. No [SHA-1]{.smallcaps} transition story to live through.
- **Signed authority chain** — repository membership is a first-class object with explicit roles (Reader / Contributor / Maintainer / Owner), versioned, signed with [Ed25519]{.smallcaps}, chained by predecessor. Push authorization is protocol-level, not server policy.
- **Federation as the normal mode** — every repository has a global `repo_id` (the [BLAKE3]{.smallcaps} of its genesis authority), and instances mirror each other in three storage modes: *full* (everything reachable), *release* (only releases and their trees), *metadata* (authority chain and ref headers, no content).
- **Cascading merge engine** — per-file dispatch to a handler ranked by aggressiveness: textual fallback, format-aware ([JSON]{.smallcaps} / [YAML]{.smallcaps} / [TOML]{.smallcaps} / [XML]{.smallcaps} / Markdown / prose), tree-sitter for source code (Rust, Python, [JS]{.smallcaps}/[TS]{.smallcaps}, Go, C/[C++]{.smallcaps}, Java, Ruby, Bash), and wasm-sandboxed plugins for the long tail. Each merged file produces a `FileRecord` in `.levcs/merge-record`, signed with the resulting commit.
- **Releases as signed objects** — not mutable name pointers. Each release carries the released tree, the predecessor commit, the parent release in the chain, the authority hash at release time, the declarer's public key, and signed release notes.
- **A small federation server** — a single binary, `levcs-instance`, fronted by Caddy or nginx, with a protocol surface of ten endpoints. Storage is a directory tree; a consistent backup is an `rsync` of `/var/lib/levcs`.
- **A reproducible benchmark suite** — `scripts/bench.sh` with metadata capture (rustc version, kernel, [CPU]{.smallcaps}, git rev), parsed summaries, and optional flamegraphs.

The dependency list is short: a recent stable Rust toolchain (workspace [MSRV]{.smallcaps} is 1.75) and a [C]{.smallcaps} compiler for the tree-sitter grammars. No database server, no message broker, no external service.

---

## Why a New VCS?

Git is the dominant [DVCS]{.smallcaps}, and there is no good case for replacing it on the strength of taste alone. The case for replacing it rests on five specific places where its 2005 design has aged poorly enough that bolt-on solutions have stopped paying their freight:

- **Identity is no longer optional.** Many projects need to know not just *who claims to have authored a commit* but who is *authorized to alter the repository's history*. Signed commits are an opt-in (`gpg-sign` since 2014, `ssh-sign` since 2021), but even when signed they answer "did *some* key sign this?" — not "is the signer authorized to write to this repo right now?"^[The right question — *is this writer in the current authority — turns into a hosting-platform toggle in practice. GitHub branch-protection rules are the de-facto authority chain for most projects, and the chain doesn't travel with the repository.]
- **Replication is more complex than push/pull.** Mirrors, archives, cold-storage replicas, and read-only forks are all common; git treats them with the same primitives as the source-of-truth remote. There is no first-class concept of *kinds* of mirror, and no protocol-level enforcement that a mirror remains consistent with what it is mirroring.
- **Merge conflicts are still mostly resolved at the line level.** [JSON]{.smallcaps}, [YAML]{.smallcaps}, [TOML]{.smallcaps}, source code with semantic structure — the line-diff treatment is wrong for all of these and produces false conflicts on reformats every team has hit. Custom merge drivers exist (`gitattributes`) but are awkward, single-purpose, and don't compose.
- **[SHA-1]{.smallcaps} is broken.** [SHAttered]{.smallcaps} (2017) was a practical collision. Git's [SHA-256]{.smallcaps} transition has been "in progress" for most of a decade and is unlikely to ever finish for the long tail of git infrastructure.
- **Tags are names, not artifacts.** A git tag is a string ref that points to a commit (or, if you remember `-a`, to a tag object). Either way, releases are conventions sitting on top of name pointers — not first-class signed objects with a chain you can audit.

LeVCS is an attempt at a clean restart that takes the [DAG]{.smallcaps} model and content addressing as obvious wins, and rebuilds identity, federation, merging, hashing, and releases as **protocol-level concerns** rather than conventions or sidecar tools.

---

## The Shape of the System

LeVCS is layered. Each layer has a clean interface to the one below it:

```
┌───────────────────────────────────────────────────────────┐
│ Workflow tools (TBD: review, issues, web UI)              │
├───────────────────────────────────────────────────────────┤
│ CLI: `levcs init / commit / push / merge / release`       │
├───────────────────────────────────────────────────────────┤
│ Federation HTTP API (instances, mirrors, releases)        │
├───────────────────────────────────────────────────────────┤
│ Object model: Blob / Tree / Commit / Release / Authority  │
│ Merge engine: textual → format-aware → tree-sitter        │
│ Trust root: signed authority chain (Ed25519)              │
│ Content addressing: BLAKE3                                │
└───────────────────────────────────────────────────────────┘
```

Five object kinds, all content-addressed by their [BLAKE3]{.smallcaps} digest:

- **Blob** — raw file contents.
- **Tree** — `(name, type, mode, hash)` entries; sorted, no duplicates.
- **Commit** — tree + parents + authority + author key + message, signed.
- **Release** — first-class artifact: tree + predecessor commit + parent release + label + notes, signed by a maintainer or owner.
- **Authority** — the *membership document* for a repository: who has what role, signed and chained by predecessor.

A repository is the set of these objects plus a `refs/` map (`branches/*`, `releases/*`, `authority/{genesis,current}`) indexing into them. The `repo_id` is the [BLAKE3]{.smallcaps} of the genesis authority — globally unique by construction, no central registrar needed.

---

## What's Different from Git

| Axis | git | LeVCS |
|:-----|:----|:------|
| Hash | [SHA-1]{.smallcaps} (deprecated, transitioning) | [BLAKE3]{.smallcaps} |
| Identity | Author string in commit | Signed authority object with explicit roles |
| Push authorization | Server-side hook or hosting platform | Protocol-level role check |
| Force-push rule | Server policy (off-protocol) | Protocol enforces maintainer-or-owner role |
| Federation | [URL]{.smallcaps}-bound remotes | Global `repo_id` + replicating instances |
| Mirror replication | `git fetch --mirror` (best-effort) | First-class with three storage modes |
| Tags / releases | Mutable string refs (often) | Signed objects with predecessor + parent-release chain |
| Merge granularity | Line-level (myers / patience) | Cascade: textual → format → tree-sitter → plugin |
| Merge audit | No artifact | `.levcs/merge-record` [TOML]{.smallcaps}, signed with the commit |
| Web [UI]{.smallcaps} / issues | Hosting platform | Out of scope for v1 |

The rest of this section unpacks each axis worth unpacking.

### Identity in the Protocol, Not on Top

Git stores `Author: Name <email>` and `Committer: Name <email>` strings in commits. There is nothing cryptographic about either. Even signed commits answer the wrong question — *is some key behind this signature?* — instead of the right one: *is this signer currently authorized to write to this repository?*

LeVCS makes membership a first-class object. An **authority body** has:

```
schema_version  repo_id  previous_authority  version  created_micros
members:        [(public_key, handle, role, added_micros, added_by), ...]
policy:         [(key, value), ...]
```

Roles form a strict order: `Reader < Contributor < Maintainer < Owner`. Every commit references the authority hash that was current when it was signed. Updating membership is a versioned operation: you write a new authority object, signed by an Owner, with `previous_authority` pointing at the prior one. The instance walks the chain on push and rejects any push whose author key isn't a current member.

The practical consequence is that *"give Bob push access"* is not a hosting-platform toggle. It is a signed authority update that travels in the repository and is auditable for the lifetime of the project.^[This is the design choice I care most about. The alternative — that authorization is a dashboard somewhere — means the repository is not actually self-describing. You can't tell, from the repository alone, who could have written this history. With a chained authority object you can.]

### Federation, Not "Remotes"

A git remote is a [URL]{.smallcaps} plus some credentials. There is no fact-of-the-matter about whether two URLs refer to the *same* repository — git checks by walking commits, but "same project" is a convention.

LeVCS has a **global `repo_id`** — the [BLAKE3]{.smallcaps} of the genesis authority object, so two clones of the same project have the same `repo_id` even if they live on instances on opposite continents. An instance is a federation peer: it serves `/levcs/v1/repos/<repo_id>/...` endpoints and replicates state from other instances when configured to. Mirroring is the protocol's normal mode, not a `git fetch --mirror` cron job.

This composes with three **storage modes**:

- **Full** — every reachable object. The source-of-truth instance.
- **Release** — only release objects, their reachable trees and blobs, and the authority chain. Skips inter-release commits. For long-lived archive replicas.
- **Metadata** — authority objects, release headers, signed refs only. No content. For "is this project still alive?" pings.

The instance enforces these on push. A release-mode replica refuses pushes that update branches; a metadata-mode replica refuses all pushes (it is populated entirely by mirroring). A migrating maintainer can move the source-of-truth role from one instance to another with `levcs migrate`, replaying the full history at the destination — the `repo_id` is unchanged, because the genesis authority is unchanged.

### The Merge Cascade

This is the technical centerpiece.

A traditional three-way merge — git, mercurial, fossil — works at the line level. It is correct for prose and acceptable for code, but it generates false conflicts on reformats (linters, prettifiers, whitespace-policy bumps), key reorderings in [JSON]{.smallcaps} / [YAML]{.smallcaps} / [TOML]{.smallcaps}, imports lists in source files that two branches both edited, and Markdown files where two contributors modified disjoint sections of the same paragraph.

LeVCS dispatches per-file to a **handler cascade** ranked by aggressiveness:

```
rank 0  textual           universal line-level fallback
rank 1  format-aware      json | yaml | toml | xml | markdown | prose
rank 2  tree-sitter       rust | python | js | ts | go | c | cpp |
                          java | ruby | bash
rank 3  plugin            wasm-sandboxed, user-supplied
```

A repository's `.levcs/merge.toml` maps glob patterns to handlers. Per-user `.levcs/merge.local.toml` can **demote** but never promote, so a distrusted plugin can be locally turned off without a repo edit. Each merged file produces a `FileRecord` in `.levcs/merge-record` listing the handler used and its hash; the merge-record blob is committed alongside the resolved tree, so every merge in history is auditable.

Two examples illustrate the practical difference:

**Format-aware example.** `package.json` where Alice adds a dependency at the top of `dependencies` and Bob adds one at the bottom. Git produces a conflict because the lines are adjacent. The [JSON]{.smallcaps} handler parses both sides, computes the structural diff, and merges them — both new entries appear in the output, no conflict.

**Tree-sitter example.** Two contributors add unrelated `use` statements to a Rust file. Line diff conflicts. The tree-sitter handler treats the `use_declaration` list as an ordered set, merges both additions, no conflict.

The cascade is fail-safe. A tree-sitter handler that bails on a syntax error falls through to the format-aware handler if applicable, then to textual. The textual handler always merges — it might produce conflicts, but it never fails to produce *some* output. This matters for [CI]{.smallcaps} and for automated mirror sync: there is no merge that the engine simply refuses to attempt.

### Hashing

Git uses [SHA-1]{.smallcaps}. [SHAttered]{.smallcaps} (2017) was a practical collision, and the [SHA-256]{.smallcaps} transition is incomplete in 2026. LeVCS uses [BLAKE3]{.smallcaps} from day one — faster than [SHA-256]{.smallcaps} in practice (~5 [GiB]{.smallcaps}/s on a laptop for blob serialize-plus-hash), tree-hashed, no commitment to a specific length-tag convention. Object [ID]{.smallcaps}s are 32 bytes everywhere, with no migration story to live through.

### Releases as Objects

Git tags are refs that point to commits — or to tag objects, if you remember to use `-a`. Either way, they are *names*, not artifacts. A release in LeVCS is a signed object:

```
tree            commit's root tree
predecessor     commit being released
parent_release  prior release in the chain (or zero)
authority       authority hash at release time
declarer_key    public key of the signing maintainer/owner
timestamp       Unix micros
label           "v1.0.0" or similar
notes           release notes (UTF-8, up to 4 GiB)
```

The chain `parent_release → parent_release → ...` gives a clean release history independent of branch topology. The replica modes above can replicate just releases (and their trees and authority) for archive instances that don't need the inter-release commit history — a useful primitive for long-tail preservation.

---

## How You Use It

### Bootstrap

```sh
levcs key generate --label primary
levcs init --key primary
levcs track --all
levcs commit -m "initial import"
```

After `init`, `.levcs/` exists alongside the working tree. The genesis authority names the chosen key as the sole Owner; the `repo_id` is fixed forever. After `commit`, the repository has one commit on `refs/branches/main`.

### Branch and Merge

```sh
levcs branch feature/x
# ... edit files ...
levcs commit -m "wip on x"
levcs branch main
levcs merge feature/x
```

If the merge produces conflicts, drop into the resolution [TUI]{.smallcaps}:

```sh
levcs merge --resolve
```

The [TUI]{.smallcaps} shows each conflicted file with the ours/base/theirs panes the handler emitted, plus the cascade decision (which handler ran, and why it fell through if it did). On accept, it writes the resolved file and a signed `.levcs/merge-record` entry.

### Release

```sh
levcs release v1.0.0 --notes "first release"
```

Writes a Release object with the current commit as `predecessor`, signs it with the active key, and adds `refs/releases/v1.0.0`. If prior releases exist, `parent_release` chains to the most recent one automatically.

### Federation

```sh
levcs instance --set https://levcs.levineuwirth.org/levcs/v1
levcs push refs/branches/main
```

The first push to a fresh instance auto-inits the repository using the genesis authority. Subsequent pushes are role-checked. Pulls are public-read by default (the `public_read` policy bit on the genesis authority).

To migrate to a new home:

```sh
levcs migrate https://new-host.example.com/levcs/v1 --set-active
```

`migrate` re-inits and replays the full history at the destination, then points the local repository at it. The `repo_id` is unchanged — same project, new location.

---

## Operating an Instance

A single binary, `levcs-instance`, reads a [TOML]{.smallcaps} config and listens on [HTTP]{.smallcaps}. Production deployments terminate [TLS]{.smallcaps} at a reverse proxy; the instance binds to localhost. The full walkthrough — systemd unit, Caddy and nginx examples, firewall, laptop-side bootstrap — lives in `deploy/README.md` in the repository.

The protocol surface is small:

```
GET  /health
GET  /levcs/v1/instance/info
GET  /levcs/v1/instance/peers
GET  /levcs/v1/repos/<repo_id>/info
GET  /levcs/v1/repos/<repo_id>/refs
GET  /levcs/v1/repos/<repo_id>/objects/<hash>
GET  /levcs/v1/repos/<repo_id>/pack?have=...&want=...
POST /levcs/v1/repos/<repo_id>/init
POST /levcs/v1/repos/<repo_id>/push
```

That is the whole [API]{.smallcaps}. No admin endpoints, no users-and-passwords table, no web [UI]{.smallcaps} to firewall. POSTs require a signed `LeVCS-Signature` header ([Ed25519]{.smallcaps}-over-canonical-request, with timestamp and nonce for replay protection); GETs are public unless the genesis authority's policy turned that off.

Storage is a directory tree. Per-object atomic writes via temp-then-rename, per-repository serializing mutex on push. A consistent backup is just a snapshot of `/var/lib/levcs`. The first instance — `levcs.levineuwirth.org` — is configured exactly this way, fronted by Caddy on a small [VPS]{.smallcaps}, dogfooding the federation surface against the source-of-truth Forgejo at [git.levineuwirth.org](https://git.levineuwirth.org).

---

## What LeVCS Isn't (Yet)

The honest list of things you would want for a full project home that LeVCS does not provide:

- **Code review.** No [PR]{.smallcaps} object, no review threads, no comments. The workflow spec coming next defines these.
- **Issue tracking.** Same — protocol substrate doesn't cover it.
- **[CI]{.smallcaps} integration.** No webhooks. [CI]{.smallcaps} systems would need to poll `/refs` on a cadence, which works but isn't turnkey.
- **Web [UI]{.smallcaps}.** No branch browser, no diff view, no blame. These can be built atop the existing [GET]{.smallcaps} endpoints; nothing in the protocol is hostile to a [UI]{.smallcaps}, but none ship.
- **Search.** No `git grep` equivalent on the server side. Local-only.
- **Submodules / monorepo tooling.** No analog yet.

If a use case requires any of the above today, the right pattern is to run LeVCS *parallel* to an existing platform. Forgejo, GitHub, or Gitea continues to host the workflow; the LeVCS instance acts as a dogfood replica that gets the same commits via a `push-both` wrapper. When the workflow surface lands, the migration story flips. This is how `levcs.levineuwirth.org` will be operated for the foreseeable future.

---

## What Is True Today (and How We Know)

The repository at v0.1.0 has 194 passing tests covering:

- The full §2–§7 object model and protocol surface.
- A 14-scenario merge conformance corpus, eight of which are git-false-conflict cases the cascade resolves cleanly.
- Property tests on the pack codec and object parsers (fuzz plus structured proptest round-trip).
- An end-to-end "dogfood" integration test that stands up three instances (source-of-truth, peer, mirror), pushes a chain of commits plus a release, replicates via mirror sync, migrates to the peer, and asserts byte-for-byte object equality across all three.

A baseline microbenchmark suite lives in `scripts/bench.sh` with metadata capture (rustc version, kernel, [CPU]{.smallcaps}, git rev) for run-to-run comparison. On a Ryzen 7 laptop, headline numbers:

- **Pack decode** of a 10 × 1 [MiB]{.smallcaps} pack: ~2.3 ms (4.3 [GiB]{.smallcaps}/s).
- **[BLAKE3]{.smallcaps} + serialize** on 1 [MiB]{.smallcaps} blobs: ~190 µs (5.1 [GiB]{.smallcaps}/s).
- **Textual three-way merge** of a 100 [KiB]{.smallcaps} document: ~4.6 ms (~80 [MiB]{.smallcaps}/s).
- **Pack encode** is the throughput floor at ~380 [MiB]{.smallcaps}/s — bottlenecked by zstd level 3 on incompressible data.

Numbers are reproducible via `scripts/bench.sh --quick`.

---

## The Roadmap

The immediate priorities, in order:

1. **Workflow spec** — the missing layer above. [PR]{.smallcaps}/review object, discussion threads, [CI]{.smallcaps} hook conventions, web [UI]{.smallcaps} design. This is the document the rest of v1 builds toward.
2. **Reference workflow tools** — a minimal web [UI]{.smallcaps} that reads the federation [API]{.smallcaps} and lets you browse, review, and merge. Probably a separate repository and process, not bundled into the instance binary.
3. **[CI]{.smallcaps} conventions** — a published webhook protocol so existing [CI]{.smallcaps} systems can integrate without polling.
4. **Plugin handler examples** — a few real wasm handlers (e.g. protobuf, [SQL]{.smallcaps} migrations) to validate the plugin protocol against real formats.
5. **Git import** — a one-way import path so existing projects can adopt LeVCS without hand-replaying history.

The substrate guarantees the workflow layer can lean on:

- Signed objects with a verifiable authority chain.
- Per-file merge records that travel with each commit.
- A content-addressed object store that doesn't care what kind of content it stores.
- Federation as a normal operating mode rather than a special case.

A "[PR]{.smallcaps}" is just an object kind LeVCS doesn't have yet; an "issue" is another; the storage modes already define how a [CI]{.smallcaps} system would replicate the metadata it needs without pulling source.

---

## Trying It

Build:

```sh
git clone https://git.levineuwirth.org/neuwirth/levcs
cd levcs
cargo build --release
sudo install -m 0755 \
    target/release/levcs target/release/levcs-instance \
    /usr/local/bin/
```

Local single-machine tour:

```sh
levcs key generate --label me
mkdir /tmp/demo && cd /tmp/demo
echo "hello" > a.txt
levcs init --key me
levcs track --all
levcs commit -m "first"
levcs log
```

Push to the public instance once it lands at `levcs.levineuwirth.org`:

```sh
levcs instance --set https://levcs.levineuwirth.org/levcs/v1
levcs push refs/branches/main
```

Read the technical report in the repository at `doc/technical-report.md`. Read the code: every crate is small and documented. `crates/levcs-core` is the object model, `crates/levcs-merge` is the cascade, `crates/levcs-instance` is the server, `crates/levcs-cli` is the user-facing tool.

---

## License and Repository

The code is released under the [Apache License 2.0]{.smallcaps} — see `LICENSE` in the repository for the full text. The choice is deliberate: the patent grant and the explicit contributor license are worth the slight ceremony for a substrate other people may build on. Frameworks should not take a stake in the work they compile, but they should be unambiguous about what compiling against them does and doesn't permit.

The repository is at [git.levineuwirth.org/neuwirth/levcs](https://git.levineuwirth.org/neuwirth/levcs). The first federation instance will be at [levcs.levineuwirth.org](https://levcs.levineuwirth.org). The next document in the series is the workflow spec; until it lands, comments and corrections on the substrate itself are welcome, addressable to your's truly!
