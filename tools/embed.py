#!/usr/bin/env python3
"""
embed.py — Build-time embedding pipeline.

Produces two outputs from _site/**/*.html:

  data/similar-links.json       Page-level similarity (for "Related" footer section)
  data/semantic-index.bin       Paragraph vectors as raw Float32 array (N × PARA_DIM)
  data/semantic-meta.json       Paragraph metadata: [{url, title, heading, excerpt}]

Two models, one process:

  * Pages use nomic-embed-text-v1.5 (768 dims) — build-time only, never
    shipped to the browser. Chosen for its well-separated cosine scores on
    small corpora, which keeps the MIN_SCORE gate meaningful so every essay
    reliably gets a "Related" footer section.

  * Paragraphs use all-MiniLM-L6-v2 (384 dims) — must match what the
    browser runs via transformers.js (static/js/semantic-search.js) since
    query vectors are dotted against the shipped index.

Called by `make build` when .venv exists. Failures are non-fatal.

Staleness: both passes are content-hash cached (data/embed-cache-*.npz),
so an unchanged site re-embeds nothing and loads no model — only the
HTML extraction pass runs. There is deliberately no mtime-based skip:
stamp-build-time.py rewrites every page's footer after this script runs,
so "are outputs newer than the HTML" is always false and a check based
on it can never fire.

Cost of a fully-warm run: each page is read and parsed exactly once
(shared by the page and paragraph extractors, via lxml when available),
and torch / sentence-transformers are imported lazily only when a cache
miss actually requires embedding — so a no-change build pays a few
seconds of extraction, not a model-library import.
"""

import hashlib
import json
import os
import re
import sys
import zipfile
from pathlib import Path

import faiss
import numpy as np
from bs4 import BeautifulSoup

# torch + sentence-transformers cost seconds of import time alone, so
# they are imported lazily inside the cache-miss branches below. A
# fully-warm run (no misses) never pays it.

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

REPO_ROOT      = Path(__file__).parent.parent
SITE_DIR       = REPO_ROOT / "_site"
SIMILAR_OUT    = REPO_ROOT / "data" / "similar-links.json"
SEMANTIC_BIN   = REPO_ROOT / "data" / "semantic-index.bin"
SEMANTIC_META  = REPO_ROOT / "data" / "semantic-meta.json"
# Content-addressed caches, one per pass. Keyed by sha256 of the (prefixed)
# input text; invalidated wholesale on model name/revision/dim change.
# Gitignored — build artifacts, not source. Survive `make clean`.
PAGE_CACHE     = REPO_ROOT / "data" / "embed-cache-pages.npz"
PARA_CACHE     = REPO_ROOT / "data" / "embed-cache-paragraphs.npz"

# Two models, deliberately split:
#
#   PARA_MODEL — embeds paragraphs for data/semantic-index.bin. This index
#   is fetched by the browser at /search/ and ranked against query vectors
#   computed client-side. The client (static/js/semantic-search.js) embeds
#   queries with MiniLM-L6-v2 via transformers.js, so the build-time model
#   must match exactly — both the architecture and the embedding dimension
#   are part of the wire contract.
#
#   PAGE_MODEL — embeds full pages for data/similar-links.json. This file
#   is consumed only at Hakyll-build time (SimilarLinks.hs) and never
#   shipped to the browser, so it is free to use a different, stronger
#   model. nomic-embed-text-v1.5 produces well-separated cosine scores on
#   small corpora (top neighbours at 0.7–0.9 instead of MiniLM's compressed
#   0.1–0.3), so the MIN_SCORE gate below is meaningful and every essay
#   reliably gets a "Related" footer section.
#
# Both pins are deliberate. Bump only when validating and re-run a full
# embed pass to refresh the corresponding output files.

PARA_MODEL_NAME     = "sentence-transformers/all-MiniLM-L6-v2"
PARA_MODEL_REVISION = "c9745ed1d9f207416be6d2e6f8de32d1f16199bf"
PARA_DIM            = 384

PAGE_MODEL_NAME     = "nomic-ai/nomic-embed-text-v1.5"
PAGE_MODEL_REVISION = "e9b6763023c676ca8431644204f50c2b100d9aab"
# The weights repo above declares its modeling code via auto_map in a
# SEPARATE repo (nomic-ai/nomic-bert-2048), which `revision=` does NOT
# pin — without this second pin, trust_remote_code executes whatever is
# at that repo's head at build time.
PAGE_MODEL_CODE_REVISION = "7710840340a098cfb869c4f65e87cf2b1b70caca"
PAGE_DIM            = 768
# Nomic requires task-prefixed input. Documents (corpus side) get
# "search_document: "; queries would get "search_query: ". similar-links
# only ever embeds documents, so the prefix is constant here.
PAGE_PREFIX         = "search_document: "

TOP_N          = 5      # similar-links: neighbours per page
MIN_SCORE      = 0.30   # similar-links: discard weak matches
MIN_PARA_CHARS = 80     # semantic: skip very short paragraphs
MAX_PARA_CHARS = 1000   # semantic: truncate before embedding

# /archive/ is the archive index — a list page that would dominate every
# entry's "Related" set; the individual /archive/<slug>/ pages stay in.
EXCLUDE_URLS = {"/search/", "/build/", "/404.html", "/feed.xml",
                "/music/feed.xml", "/archive/"}

# Whole subtrees kept out of the corpus. /source/ is the repository code
# mirror — source files, not content; left in, they pollute every page's
# "Related" set and semantic search (e.g. a template file surfacing as a
# neighbour, titled with its unrendered "$title$" placeholder).
# /drafts/ exists in _site only when a SITE_ENV=dev build (make dev /
# make watch) has written into the shared output dir. `make build` purges
# it before embedding, but a watch session running in parallel with a
# direct embed.py invocation can still race drafts into _site — draft
# text must never reach the public search index or Related sections.
EXCLUDE_PREFIXES = ("/source/", "/drafts/")

# Pages whose <body data-portal> are portal/landing pages — they aggregate
# excerpts from many entries and would otherwise dominate every page's
# "Related" set with high but uninformative scores. default.html sets the
# attribute when any of the `list-page`, `portal`, or `home` template flags
# is true, so adding `constField "portal" "true"` to a Hakyll rule (or
# `portal: true` to a content file's frontmatter) is enough to exclude it.
PORTAL_BODY_ATTR = "data-portal"

# lxml parses ~2x faster than html.parser and produces byte-identical
# extracted text on this corpus (verified across every page: identical
# page texts and paragraph lists, hence identical content hashes — the
# embed caches survive the switch). Fall back gracefully when absent.
try:
    import lxml  # noqa: F401
    HTML_PARSER = "lxml"
except ImportError:
    HTML_PARSER = "html.parser"


def atomic_write_bytes(path: Path, data: bytes) -> None:
    """Write to a PID-unique temp then os.replace: an interrupt mid-write
    cannot leave a truncated file at the final path, fsync makes the
    rename durable across power loss, and the PID suffix keeps two
    concurrent runs from interleaving writes into one temp file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".tmp.{os.getpid()}")
    try:
        with tmp.open("wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def atomic_write_text(path: Path, text: str) -> None:
    atomic_write_bytes(path, text.encode("utf-8"))


# ---------------------------------------------------------------------------
# Page-embedding cache
# ---------------------------------------------------------------------------
#
# Loading the nomic model and embedding 26 pages on CPU takes ~3 minutes
# every `make build`. Pages rarely change between builds — usually one
# essay is edited and everything else is identical. This cache stores
# one nomic vector per page content hash so unchanged pages are reused
# verbatim and only edited/new pages are re-embedded. A fully-warm cache
# skips the model load entirely.

def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_vec_cache(path: Path, model: str, revision: str,
                   dim: int) -> dict[str, np.ndarray]:
    """Load {hash: vector} from disk. Returns an empty dict if the cache
    is absent, unreadable, or pinned to a different model — in those
    cases save_vec_cache() will overwrite the stale file on next save."""
    if not path.exists():
        return {}
    try:
        npz = np.load(path, allow_pickle=False)
        if (npz["model"].item()    != model or
            npz["revision"].item() != revision or
            int(npz["dim"].item()) != dim):
            return {}
        hashes  = npz["hashes"]
        vectors = npz["vectors"]
        if vectors.shape != (len(hashes), dim):
            return {}
        return {h.item(): vectors[i] for i, h in enumerate(hashes)}
    except (OSError, KeyError, ValueError, EOFError,
            zipfile.BadZipFile) as e:
        print(f"embed.py: cache {path.name} unreadable ({e}) — discarding",
              file=sys.stderr)
        return {}


def save_vec_cache(path: Path, model: str, revision: str, dim: int,
                   cache: dict[str, np.ndarray]) -> None:
    """Atomically persist {hash: vector}. Empty cache writes an empty
    file so a subsequent load returns {} cleanly (instead of falling
    through to the "no file" path)."""
    if cache:
        hashes  = np.array(list(cache.keys()))
        vectors = np.stack(list(cache.values())).astype(np.float32)
    else:
        hashes  = np.array([], dtype="U64")
        vectors = np.zeros((0, dim), dtype=np.float32)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Pass an open file handle, not a path: np.savez_compressed appends
    # ".npz" to bare paths, which would mangle our atomic-rename target.
    # PID-unique temp so concurrent runs can't interleave; fsync so the
    # rename is durable.
    tmp = path.with_suffix(path.suffix + f".tmp.{os.getpid()}")
    try:
        with open(tmp, "wb") as f:
            np.savez_compressed(
                f,
                model=model,
                revision=revision,
                dim=dim,
                hashes=hashes,
                vectors=vectors,
            )
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


STRIP_SELECTORS = [
    "nav", "footer", "#toc", ".link-popup", "script", "style",
    ".page-meta-footer", ".metadata", "[data-pagefind-ignore]",
    # The no-JS footnotes fallback duplicates each sidenote's text
    # verbatim at the document end — indexing it would double every
    # footnote in search results and skew page similarity.
    "section.footnotes",
    # Inline-SVG metadata (matplotlib emits creator boilerplate and,
    # historically, a per-run <dc:date> timestamp). None of it is page
    # content, and the timestamp made every recompile a cache miss.
    "svg metadata",
]

# ---------------------------------------------------------------------------
# HTML parsing helpers
# ---------------------------------------------------------------------------

def _url_from_path(html_path: Path) -> str:
    rel = html_path.relative_to(SITE_DIR)
    if rel.name == "index.html":
        parent = str(rel.parent)
        if parent in (".", ""):
            return "/"
        return "/" + parent + "/"
    return "/" + str(rel)

def _clean_soup(soup: BeautifulSoup) -> None:
    for sel in STRIP_SELECTORS:
        for el in soup.select(sel):
            el.decompose()

def _title(soup: BeautifulSoup, url: str) -> str:
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(" ", strip=True)
    tag = soup.find("title")
    raw = tag.get_text(" ", strip=True) if tag else url
    return re.split(r"\s+[—–-]\s+", raw)[0].strip()

# ---------------------------------------------------------------------------
# Extraction — pages (similar-links) + paragraphs (semantic search)
# ---------------------------------------------------------------------------

def extract_document(html_path: Path) -> tuple[dict | None, list[dict]]:
    """Read and parse a page ONCE; return (page, paragraphs).

    Replaces the former extract_page / extract_paragraphs pair, which
    each re-read and re-parsed the same file. page is None (and
    paragraphs empty) for excluded / portal / non-content pages — the
    paragraph pass only ever ran when the page pass succeeded, and that
    behaviour is preserved here.
    """
    url = _url_from_path(html_path)
    if url in EXCLUDE_URLS or url.startswith(EXCLUDE_PREFIXES):
        return None, []

    raw  = html_path.read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(raw, HTML_PARSER)

    body_tag = soup.body
    if body_tag is not None and body_tag.has_attr(PORTAL_BODY_ATTR):
        return None, []
    body = soup.select_one("#markdownBody")
    if body is None:
        return None, []

    title = _title(soup, url)
    _clean_soup(soup)

    text = re.sub(r"\s+", " ", body.get_text(" ", strip=True)).strip()
    if len(text) < 100:
        return None, []

    page = {"url": url, "title": title, "text": text}

    paras   = []
    heading = title  # track current section heading

    for el in body.find_all(["h1", "h2", "h3", "h4", "p", "li", "blockquote"]):
        if el.name in ("h1", "h2", "h3", "h4"):
            heading = el.get_text(" ", strip=True)
            continue
        ptext = re.sub(r"\s+", " ", el.get_text(" ", strip=True)).strip()
        if len(ptext) < MIN_PARA_CHARS:
            continue
        paras.append({
            "url":     url,
            "title":   title,
            "heading": heading,
            "excerpt": ptext[:200] + ("…" if len(ptext) > 200 else ""),
            "text":    ptext[:MAX_PARA_CHARS],
        })

    return page, paras

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    if not SITE_DIR.exists():
        print("embed.py: _site/ not found — skipping", file=sys.stderr)
        return 0

    # --- Extract pages + paragraphs in one pass ---
    print("embed.py: extracting pages…")
    pages = []
    paragraphs = []

    for html in sorted(SITE_DIR.rglob("*.html")):
        page, paras = extract_document(html)
        if page is None:
            continue
        pages.append(page)
        paragraphs.extend(paras)

    if not pages:
        print("embed.py: no indexable pages found", file=sys.stderr)
        return 0

    # --- Similar-links (page level, nomic, content-hash cached) ---
    cache       = load_vec_cache(PAGE_CACHE, PAGE_MODEL_NAME,
                                 PAGE_MODEL_REVISION, PAGE_DIM)
    page_inputs = [PAGE_PREFIX + p["text"] for p in pages]
    hashes      = [content_hash(t) for t in page_inputs]
    miss_idxs   = [i for i, h in enumerate(hashes) if h not in cache]

    print(f"embed.py: pages: {len(pages) - len(miss_idxs)} cached / "
          f"{len(miss_idxs)} to embed")

    if miss_idxs:
        print(f"embed.py: loading {PAGE_MODEL_NAME}@{PAGE_MODEL_REVISION[:8]}…")
        # Lazy: pulls in torch; only paid when something must be embedded.
        from sentence_transformers import SentenceTransformer
        page_model = SentenceTransformer(
            PAGE_MODEL_NAME, revision=PAGE_MODEL_REVISION, trust_remote_code=True,
            # code_revision pins the auto_map modeling repo; it must reach
            # both AutoConfig and AutoModel.from_pretrained.
            model_kwargs={"code_revision": PAGE_MODEL_CODE_REVISION},
            config_kwargs={"code_revision": PAGE_MODEL_CODE_REVISION},
        )
        new_vecs = page_model.encode(
            [page_inputs[i] for i in miss_idxs],
            normalize_embeddings=True,
            show_progress_bar=True,
            batch_size=8,
        ).astype(np.float32)
        for i, vec in zip(miss_idxs, new_vecs):
            cache[hashes[i]] = vec
        # Drop the model before loading MiniLM below; sentence-transformers
        # holds the full weight tensor in RAM until GC runs.
        del page_model

    # Assemble page_vecs in the original pages[] order.
    page_vecs = np.stack([cache[h] for h in hashes]).astype(np.float32)

    # Prune the cache to only currently-present hashes so a deleted page
    # doesn't keep its vector around forever. Then persist.
    save_vec_cache(PAGE_CACHE, PAGE_MODEL_NAME, PAGE_MODEL_REVISION,
                   PAGE_DIM, {h: cache[h] for h in hashes})

    index = faiss.IndexFlatIP(page_vecs.shape[1])
    index.add(page_vecs)
    scores_all, indices_all = index.search(page_vecs, TOP_N + 1)

    similar: dict[str, list] = {}
    for i, page in enumerate(pages):
        neighbours = []
        for rank in range(TOP_N + 1):
            j, score = int(indices_all[i, rank]), float(scores_all[i, rank])
            if j == i or score < MIN_SCORE:
                continue
            neighbours.append({"url": pages[j]["url"], "title": pages[j]["title"],
                                "score": round(score, 4)})
            if len(neighbours) == TOP_N:
                break
        if neighbours:
            similar[page["url"]] = neighbours

    atomic_write_text(SIMILAR_OUT, json.dumps(similar, ensure_ascii=False, indent=2))
    print(f"embed.py: wrote {len(similar)} similar-links entries")

    # --- Semantic index (paragraph level, MiniLM, content-hash cached) ---
    if not paragraphs:
        print("embed.py: no paragraphs extracted — skipping semantic index")
        return 0

    pcache      = load_vec_cache(PARA_CACHE, PARA_MODEL_NAME,
                                 PARA_MODEL_REVISION, PARA_DIM)
    para_inputs = [p["text"] for p in paragraphs]
    para_hashes = [content_hash(t) for t in para_inputs]
    para_miss   = [i for i, h in enumerate(para_hashes) if h not in pcache]

    print(f"embed.py: paragraphs: {len(paragraphs) - len(para_miss)} cached / "
          f"{len(para_miss)} to embed")

    if para_miss:
        print(f"embed.py: loading {PARA_MODEL_NAME}@{PARA_MODEL_REVISION[:8]}…")
        # Lazy: pulls in torch; only paid when something must be embedded.
        from sentence_transformers import SentenceTransformer
        para_model = SentenceTransformer(PARA_MODEL_NAME,
                                         revision=PARA_MODEL_REVISION)
        new_para_vecs = para_model.encode(
            [para_inputs[i] for i in para_miss],
            normalize_embeddings=True,
            show_progress_bar=True,
            batch_size=64,
        ).astype(np.float32)
        for i, vec in zip(para_miss, new_para_vecs):
            pcache[para_hashes[i]] = vec
        del para_model

    # Assemble in original paragraph order; prune + persist the cache.
    para_vecs = np.stack([pcache[h] for h in para_hashes]).astype(np.float32)
    save_vec_cache(PARA_CACHE, PARA_MODEL_NAME, PARA_MODEL_REVISION,
                   PARA_DIM, {h: pcache[h] for h in para_hashes})

    atomic_write_bytes(SEMANTIC_BIN, para_vecs.tobytes())

    meta = [{"url": p["url"], "title": p["title"],
             "heading": p["heading"], "excerpt": p["excerpt"]}
            for p in paragraphs]
    atomic_write_text(SEMANTIC_META, json.dumps(meta, ensure_ascii=False))

    print(f"embed.py: wrote {len(paragraphs)} paragraphs to semantic index "
          f"({SEMANTIC_BIN.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
