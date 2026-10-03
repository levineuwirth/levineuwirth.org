.PHONY: test validate audit-viz viz-provenance viz-provenance-check build build-locked deploy deploy-locked validate-locked thumbnails-locked pdf-thumbs-locked deploy-guard deploy-preflight deploy-recheck deploy-rsync-inplace deploy-rsync-atomic deploy-clean sign download-model download-pdfjs download-leaflet compress-assets convert-images thumbnails pdf-thumbs pdfs watch watch-locked clean dev dev-locked audit-marks archive-gc archive-wayback archive-check archive-suggest

# Prerequisite orders (deploy: build -> sign; deploy-clean: clean ->
# deploy) are only correct serially; under `make -j` they could
# interleave. This build has no intra-target parallelism worth
# preserving, so disable it outright.
.NOTPARALLEL:

# Source .env for deploy / GitHub config if it exists.
# .env format: KEY=value (one per line, no `export` prefix, no quotes needed).
# Only the variables explicitly listed below are exported to recipe
# subprocesses — bare `export` would leak every .env key (including any
# future GITHUB_TOKEN) into every child process.
-include .env
export VPS_USER VPS_HOST VPS_PATH GITHUB_REPO

# ---------------------------------------------------------------------------
# Inter-process lock  (B06)
# ---------------------------------------------------------------------------
# _site/ and _cache/ are shared mutable state and nothing about them is
# concurrency-safe. `.NOTPARALLEL:` above only orders prerequisites within
# ONE make invocation; it does nothing about `make watch` in one terminal
# and `make deploy` in another, which is how a half-written mixture of two
# builds gets rsync --delete'd to the VPS.
#
# So each of build / deploy / watch / dev is a two-line wrapper that
# re-enters make under flock, and the real recipe lives in <name>-locked.
# The smaller targets that write _site/, _cache/ or static/ (clean, sign,
# compress-assets, convert-images, thumbnails, pdf-thumbs) and validate,
# which reads _site/, take the same lock. with-lock.sh is re-entrant, so
# when the locked build or deploy runs one of them it passes through.
# GNU make executes any recipe line containing $(MAKE) even under `-n`, and
# passes `-n` down, so `make -n build` still prints the whole real recipe in
# order rather than just the wrapper.
#
# LOCK_TIMEOUT=<seconds> waits for a busy lock instead of failing at once.
LOCK_FILE := data/.site-build.lock
WITH_LOCK  = ./tools/with-lock.sh $(LOCK_FILE)

# Flags handed to the post-build artifact gate (tools/check-site.py).
#
# Empty by default: every check is an error, including a missing /404.html
# (build/Site.hs generates it; see F12 in the audit). Pass
# --allow-missing-404 only while bisecting a broken 404 rule.
#
# Add --require-webp to make "JPEGs present, zero WebP" fatal (P02); that is
# the intended production setting once cwebp is installed everywhere the
# site is built.
#
# `make build CHECK_SITE_FLAGS='--warn-only'` reports
# every finding and still exits 0. That is for seeing the whole picture
# while fixes are landing — a site the gate rejects is not fit to deploy,
# and `make deploy` runs the gate again through `validate` regardless.
CHECK_SITE_FLAGS ?=

# ---------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------
# SITE_ENV is forced to production here (B08). build/Site.hs branches on
# `SITE_ENV == "dev"` to include content/drafts/ in listings, feeds and
# manifests; deleting _site/drafts afterwards does not undo a draft that
# leaked into an index page. A target-specific variable outranks the
# environment, so an inherited SITE_ENV=dev from the parent shell — the
# actual failure mode — cannot reach the compiler. `dev` and `watch` set it
# back to dev for themselves.
build: export SITE_ENV = production
build:
	@$(WITH_LOCK) $(MAKE) --no-print-directory build-locked

build-locked: export SITE_ENV = production
build-locked:
	# ---- Stage 0: snapshot, freshness decision, asset prerequisites -------
	#
	# Auto-snapshot any uncommitted content/ changes BEFORE the build
	# so the stability heuristic in build/Stability.hs sees a stable
	# git history. If a subsequent step fails, the snapshot remains in
	# the history — that's intentional. The next successful build
	# either reuses it (no new content/ changes) or appends another
	# snapshot on top, so failures don't disappear from the log.
	#
	# `git add content/` respects .gitignore, which excludes credential-
	# shaped patterns (.env, *.key, *.pem, id_rsa*, credentials*, etc.)
	# so a stray secret dropped under content/ is NOT auto-staged. To
	# intentionally commit a normally-ignored file, use `git add -f`
	# manually before running `make build`.
	#
	# The commit and its guard are pathspec-limited to content/ so that
	# anything the user had previously staged for other reasons is left
	# staged, not silently swept into the auto-commit.
	#
	# SKIP_SNAPSHOT=1 skips the auto-commit entirely, for building
	# someone else's checkout or verifying a build without touching the
	# history. The build is otherwise identical; only the stability
	# labels of just-edited pieces can differ.
	@if [ "$(SKIP_SNAPSHOT)" = "1" ]; then \
	  echo "build: SKIP_SNAPSHOT=1 — not auto-committing content/"; \
	else \
	  git add content/; \
	  git diff --cached --quiet -- content/ || git commit -m "auto: $$(date -u +%Y-%m-%dT%H:%M:%SZ)" -- content/; \
	fi
	@mkdir -p data
	@date +%s > data/build-start.txt
	# Full-rebuild-or-incremental decision. Four triggers force a clean
	# here (Hakyll rules changed, content deleted/renamed, route-defining
	# frontmatter changed, stale full-rebuild stamp); otherwise the build
	# is incremental. This is what lets `make deploy` skip its old
	# unconditional `clean`.
	@./tools/build-freshness.sh check
	# Responsive photo variants (P01). Must come BEFORE convert-images so
	# each .w480/.w960/.w1440 file gets a .webp companion of its own, and
	# before the dimension sidecars below (which skip variants outright).
	@$(MAKE) -s thumbnails
	@./tools/convert-images.sh
	@$(MAKE) -s pdf-thumbs
	@./tools/download-pdfjs.sh
	@./tools/download-leaflet.sh
	# The semantic-search model (static/models/, gitignored), like the two
	# above: without it the deploy's rsync --delete would remove the
	# published model (audit D07). Skips present files after re-checking
	# their pinned SHA-256.
	@./tools/download-model.sh >/dev/null
	# Photography pipeline (Phase 3): generate per-photo EXIF + palette
	# sidecars under content/photography/**/*.{exif,palette}.yaml so the
	# Hakyll context can merge them with frontmatter at compile time.
	# Plus per-image dimension sidecars across static/images/ and
	# content/** so build/Filters/Images.hs can attach width / height
	# attrs to body images for CLS prevention.
	# Gated on .venv presence, same as embed.py — failures are non-fatal.
	@if [ -d .venv ]; then \
	  uv run python tools/extract-exif.py       || echo "Warning: EXIF extraction failed (build continues with frontmatter only)"; \
	  uv run python tools/extract-palette.py    || echo "Warning: palette extraction failed (build continues with frontmatter only)"; \
	  uv run python tools/extract-dimensions.py || echo "Warning: dimension extraction failed (build continues without width/height attrs)"; \
	else \
	  echo "Photography sidecars skipped: run 'uv sync' to enable EXIF + palette + dimension extraction (build continues with frontmatter only)"; \
	fi
	# Archive pipeline (Phase 1): fetch any manifest URL without a local
	# artifact, extract text, write archive/<slug>/PROVENANCE.json and
	# data/archive-index.json. Gated on .venv, same as embed.py. A SHA or
	# slug-URL integrity error exits non-zero and halts the build; a
	# transient network failure is non-fatal (the entry retries next build).
	@if [ -d .venv ]; then \
	  uv run python tools/archive.py fetch; \
	else \
	  echo "Archive fetch skipped: run 'uv sync' to enable link archiving (build continues)"; \
	fi
	# Code-reference snapshots: fetch any GitHub blob/tree/commit linked from
	# content/ that has no snapshot in code-refs/ yet, for the hover popup.
	# Stdlib only, so not gated on .venv. Network failures are warnings;
	# the link keeps its previous snapshot or gets no code popup.
	@python3 tools/code-refs.py fetch
	# ---- Stage 1: compile (produces the HTML that embed.py reads) --------
	cabal run site -- build
	# Purge dev/watch leftovers BEFORE embedding or indexing: drafts under
	# _site/drafts/ (written only by SITE_ENV=dev builds into this same
	# _site) must never reach the embedding outputs, pagefind, or the VPS.
	# This runs before embed.py specifically so a draft paragraph cannot
	# enter data/semantic-index.bin, which ships to every visitor.
	@if [ -d _site/drafts ]; then \
	  echo "build: removing _site/drafts (dev leftovers)"; \
	  rm -rf _site/drafts; \
	fi
	# ---- Stage 2: embed --------------------------------------------------
	#
	# embed.py reads _site/**/*.html and writes three files back into
	# data/: similar-links.json and the semantic-index.bin /
	# semantic-meta.json pair (copied into _site/data/ by a Hakyll match
	# rule). Then `site footer-data` splits similar-links.json and stage 1's
	# _site/data/backlinks.json into one file per page under data/footer/,
	# rewriting only the files whose entries changed (build/FooterData.hs,
	# audit H01). It runs whether or not embed.py did: backlinks need it too.
	#
	# It used to run AFTER the only compile pass, which meant every one of
	# those three outputs reached the VPS exactly one build late: the
	# published semantic metadata described the previous edit of the site,
	# and a new essay's Related section did not appear until the build
	# after the one that created it. (B01)
	@touch data/.embed-start
	@if [ -d .venv ]; then \
	  HF_HUB_DISABLE_IMPLICIT_TOKEN=1 uv run python tools/embed.py || echo "Warning: embedding failed — data/similar-links.json not updated (build continues)"; \
	else \
	  echo "Embedding skipped: run 'uv sync' to enable similar-links (build continues)"; \
	fi
	cabal run site -- footer-data
	# ---- Stage 3: recompile the consumers of what stage 2 produced -------
	#
	# The footer files and the semantic pair are matched Hakyll resources:
	# a page whose Backlinks or Related changed recompiles, and the semantic
	# pair is copied into _site/data/ — including on a first-ever build,
	# where none of these existed as identifiers during stage 1. Stage 2
	# leaves identical bytes alone, so when nothing it writes is newer than
	# its start there is nothing for this pass to do, and it is skipped
	# rather than paying a second Hakyll start-up and dependency check
	# (audit D16).
	@if [ -n "$$(find data/footer -newer data/.embed-start -print -quit)" ] \
	   || [ data/semantic-index.bin -nt data/.embed-start ] \
	   || [ data/semantic-meta.json -nt data/.embed-start ]; then \
	  echo "cabal run site -- build"; cabal run site -- build; \
	else \
	  echo "build: stage 2 changed nothing — the second compile pass is skipped"; \
	fi
	@./tools/build-freshness.sh stamp
	# Defense in depth: stage 3 runs with SITE_ENV=production and cannot
	# create drafts, but an aborted earlier run could have left some.
	@if [ -d _site/drafts ]; then \
	  echo "build: removing _site/drafts (post-compile)"; \
	  rm -rf _site/drafts; \
	fi
	# Hakyll never deletes an output whose source is gone, and the score
	# pages are gitignored, so build-freshness never sees them go: remove
	# published score files that no longer have a source (audit M02).
	@python3 tools/prune-site.py _site
	# ---- Stage 4: index --------------------------------------------------
	# pagefind never clears its output dir (verified: files it did not
	# write survive a run), so without this rm stale content-hashed
	# fragments would accumulate in _site — and on the VPS — forever.
	# Runs after stage 3 so the keyword index covers the Related sections.
	rm -rf _site/pagefind
	pagefind --site _site
	# ---- Stage 5: stamp --------------------------------------------------
	# Site-wide footer timestamp: rewrite every <span data-build-time>
	# in _site/**/*.html so cached (un-recompiled) pages don't show a
	# stale per-page build time. See tools/stamp-build-time.py for the
	# full rationale. Must run before compress-assets so the .gz/.br
	# sidecars include the fresh stamp.
	#
	# COST (P05, accepted deliberately): this touches EVERY html file on
	# every build, so downstream everything looks changed — compress-assets
	# regenerates every .gz/.br, sign-site.sh re-signs every page, and
	# rsync transfers all of it even when no prose changed. On this site
	# that is ~500 pages of otherwise-avoidable work per deploy. The
	# alternative (a per-page timestamp that silently freezes on cached
	# pages) is a wrong page, which is worse than a slow deploy.
	#
	# SKIP_STAMP=1 opts out: pages then show the build time of the run
	# that last compiled them, which is stale on any page Hakyll reused.
	# Pair it with SIGN_ONLY_CHANGED=1 for the fast path, and only for a
	# local preview — never for a deploy.
	@if [ "$(SKIP_STAMP)" = "1" ]; then \
	  echo "build: SKIP_STAMP=1 — footers keep their per-page compile time (stale on cached pages)"; \
	else \
	  python3 tools/stamp-build-time.py _site; \
	fi
	@./tools/compress-assets.sh _site
	# ---- Stage 6: gate ---------------------------------------------------
	# Reject the finished artifact before anything can sign or ship it:
	# published private/ignored files (S01), figure-render error blocks and
	# unresolved "Figure ?" references that Hakyll happily exits 0 on
	# (B03), draft links (B08), missing images, broken feeds. See
	# tools/check-site.py. `make validate` runs the same gate by hand.
	@python3 tools/check-site.py _site $(CHECK_SITE_FLAGS)
	# IGNORE.txt pins pages against stability changes for one build
	# (build/Stability.hs). Clear it only once the build has passed the
	# gate: a rejected build has not used the pins.
	@: > IGNORE.txt
	@BUILD_END=$$(date +%s); \
	 BUILD_START=$$(cat data/build-start.txt); \
	 echo $$((BUILD_END - BUILD_START)) > data/last-build-seconds.txt.tmp && \
	 mv data/last-build-seconds.txt.tmp data/last-build-seconds.txt

sign:
	@$(WITH_LOCK) ./tools/sign-site.sh

# Download the quantized ONNX model for client-side semantic search.
# Run once; files are gitignored. Safe to re-run (skips existing files).
download-model:
	@./tools/download-model.sh

# Vendor Mozilla's prebuilt PDF.js viewer into static/pdfjs/.
# Runs automatically as part of `build` (skips when already present).
# Files are gitignored; sha256-verified against tools/pdfjs-checksums.sha256.
download-pdfjs:
	@./tools/download-pdfjs.sh

# Vendor Leaflet + leaflet.markercluster into static/leaflet/.
# Used only by /photography/map/. Runs automatically as part of `build`
# (skips when already present). Files are gitignored; sha256-verified
# against tools/leaflet-checksums.sha256.
download-leaflet:
	@./tools/download-leaflet.sh

# Generate .gz and .br sidecars for compressible text assets in _site/.
# Runs automatically as part of `build`. Pairs with `gzip_static` /
# `brotli_static` in the nginx vhost (see nginx/static-assets.conf).
compress-assets:
	@$(WITH_LOCK) ./tools/compress-assets.sh _site

# Convert JPEG/PNG images to WebP companions (also runs automatically in build).
#
# Requires the cwebp binary. On Arch that is libwebp-utils, NOT libwebp —
# libwebp is the library only and installing it leaves cwebp absent, which
# is exactly how this site came to ship 375 JPEGs and zero WebP files while
# every build printed "OK". (C08, P02)
#   Arch    pacman -S libwebp-utils
#   Debian  apt install webp
# The script still exits 0 when cwebp is missing (the <picture> sources are
# only emitted for .webp files that exist, so the site stays correct), but
# it now says so loudly. `make validate REQUIRE_WEBP=1` makes it fatal.
convert-images:
	@$(WITH_LOCK) ./tools/convert-images.sh

# Generate responsive delivery variants for photography (also runs in build).
#
# Every photography surface asked for the full 2400px JPEG: a contact-sheet
# frame is ~220 CSS pixels wide and a map tooltip is 224, so an index page
# cost 32-40 MB to paint thumbnails. This writes a ladder of siblings the
# templates offer through `srcset` and lets the browser choose (P01):
#
#   content/photography/<series>/<name>.jpg
#     -> <name>.w480.jpg  <name>.w960.jpg  <name>.w1440.jpg
#
# Each width only when the source is strictly wider; same directory, same
# extension, same colour profile; JPEG q82 progressive; no EXIF. Reruns
# rewrite nothing (a variant newer than its source is skipped), so this is
# cheap on every build after the first.
#
# The files are gitignored (content/photography/**/*.jpg already covers
# them) and reach the VPS through `make deploy`'s rsync of _site/, exactly
# like the delivery JPEGs they came from.
#
#   make thumbnails                              generate what is missing
#   make thumbnails THUMBNAIL_FLAGS=--dry-run    report, write nothing
#   make thumbnails THUMBNAIL_FLAGS=--force      rewrite every variant
#   make thumbnails THUMBNAIL_FLAGS=--prune      drop orphaned variants
#
# Without Pillow the script prints an install hint and exits 0, the same
# contract convert-images.sh keeps for a missing cwebp: the site stays
# correct, just heavier. tools/check-site.py is what makes a genuinely
# missing srcset target fatal.
thumbnails:
	@$(WITH_LOCK) $(MAKE) --no-print-directory thumbnails-locked

thumbnails-locked:
	@if [ -d .venv ]; then \
	  uv run python tools/generate-thumbnails.py $(THUMBNAIL_FLAGS); \
	else \
	  python3 tools/generate-thumbnails.py $(THUMBNAIL_FLAGS); \
	fi

# Generate first-page thumbnails for the PDFs under static/ (also runs in
# build). Requires pdftoppm: pacman -S poppler  /  apt install poppler-utils
# Each is written as foo.thumb.png beside its PDF. Without pdftoppm the
# target says so and exits 0.
pdf-thumbs:
	@$(WITH_LOCK) $(MAKE) --no-print-directory pdf-thumbs-locked

pdf-thumbs-locked:
	# A failing pdftoppm must at least warn: the `find | while` pipeline's
	# exit status is the last iteration's, so without the `||` a corrupt
	# PDF would silently ship without a thumbnail.
	# Walk ALL of static/ (not just papers/): /cv.pdf and /resume.pdf are
	# the most-linked PDFs on the site and need hover thumbnails too.
	# pdfjs/ is pruned — the vendored viewer ships sample PDFs.
	@if command -v pdftoppm >/dev/null 2>&1; then \
	  find static -path static/pdfjs -prune -o -name '*.pdf' -print 2>/dev/null | while read pdf; do \
	    thumb="$${pdf%.pdf}.thumb"; \
	    if [ ! -f "$${thumb}.png" ] || [ "$$pdf" -nt "$${thumb}.png" ]; then \
	      echo "  pdf-thumb $$pdf"; \
	      pdftoppm -r 100 -f 1 -l 1 -png -singlefile "$$pdf" "$$thumb" \
	        || echo "Warning: pdf-thumb failed for $$pdf (page ships without a thumbnail)" >&2; \
	    fi; \
	  done; \
	else \
	  echo "pdf-thumbs: pdftoppm not found — install poppler (skipping)"; \
	fi

# Rebuild the CV + website résumé from yaml-source/ and refresh static/.
# Standalone helper — NOT a dependency of `build` or `deploy`. Run manually
# after editing a YAML under yaml-source/data/; check-site warns when the
# PDFs are older than their sources (tools/cv-pdfs.py, audit C02). The site build copies
# static/*.pdf through unchanged, so a subsequent `make build` picks them up.
#
# The ATS variant (yaml-source/output/resume_ats.pdf) is intentionally not
# copied to static/ — it's a submission artifact, not a website asset. To
# regenerate it too, run `make -C yaml-source ats` directly.
#
# yaml-source/ IS tracked — its data/, templates/ and build.py are in Git,
# and build/Vita.hs reads yaml-source/data/*.yml to render the Vita page, so
# a fresh clone has the sources. Only the artifacts are ignored
# (yaml-source/build/, yaml-source/output/, yaml-source/variants/private/).
# What a fresh clone can lack is the LaTeX toolchain, and the guard below
# is really about `make -C yaml-source all` needing xelatex. (C08)
pdfs:
	@if [ ! -d yaml-source ]; then \
	  echo "pdfs: yaml-source/ not present — skipping"; \
	  exit 0; \
	fi
	@$(MAKE) -C yaml-source all
	@cp yaml-source/output/cv.pdf static/cv.pdf
	@cp yaml-source/output/resume.pdf static/resume.pdf
	@python3 tools/cv-pdfs.py write
	@echo "pdfs: static/cv.pdf and static/resume.pdf refreshed; commit them with yaml-source/pdfs.sha256."

# ---------------------------------------------------------------------------
# deploy
# ---------------------------------------------------------------------------
# Every source input that is not content/ — build/, templates/, static/,
# data/, yaml-source/, tools/, nginx/, the Makefile, the cabal file — was
# compiled into the site whether or not it was committed, and then
# `git push` advertised a source revision that does not describe the site
# that was just published. The signatures on those pages assert
# provenance, so they were asserting it about a revision nobody can fetch.
#
# deploy-preflight refuses that. It runs BEFORE the build so a dirty tree
# costs a second, not a full compile. (B05)
#
# code-refs/ and archive/ are written by the build itself (Stage 0 fetches
# snapshots for newly linked code and pages) and both are published, so
# deploy-preflight runs those fetchers first: a new snapshot then shows up
# here as an untracked input, in seconds, instead of shipping uncommitted
# (it did on 2026-10-01, audit X1). The root files are those published
# verbatim under /source/ or compiled into the generator.
DIRTY_PATHS := build templates static data yaml-source tools nginx Makefile levineuwirth.cabal \
	code-refs archive cabal.project cabal.project.freeze pyproject.toml uv.lock \
	LICENSE LICENSE-CONTENT THIRD-PARTY.md README.md WRITING.md PHOTOGRAPHY.md

# The build inputs under $(1) that differ from HEAD, one per line: tracked
# modifications, plus untracked files everywhere but data/ (see below).
dirty_inputs = { git status --porcelain --untracked-files=no -- $(1); \
	  git status --porcelain --untracked-files=normal -- $(filter-out data,$(1)) | grep '^??'; } | grep . || true

# deploy-preflight checks the tree before the build; deploy-recheck checks it
# again just before the push, because the build runs for minutes and reads
# its inputs as it goes — it compiles the generator twice (Stages 1 and 3)
# and validate discovers tests/ afresh. On 2026-10-01 a build/ edit made in
# that window was compiled into a published site that the pushed commit did
# not contain. content/ and tests/ are checked here too: the build's
# snapshot committed content/ before it started, so any change there since
# is also one the push would not carry.
RECHECK_PATHS := $(DIRTY_PATHS) content tests

deploy-preflight:
	@branch=$$(git rev-parse --abbrev-ref HEAD); \
	 if [ "$$branch" != "main" ]; then \
	   echo "deploy: on branch '$$branch', not main — refusing." >&2; \
	   echo "        'git push -u origin main' below would push this branch's" >&2; \
	   echo "        commits to main while the site is built from it." >&2; \
	   exit 1; \
	 fi
	# Fetch what the build would fetch before judging the tree, so that a
	# snapshot for a newly linked page or code file is caught below.
	@python3 tools/code-refs.py fetch
	@if [ -d .venv ]; then uv run python tools/archive.py fetch; fi
	# Tracked modifications anywhere in DIRTY_PATHS, plus untracked files in
	# all of them except data/. data/ is excluded from the untracked check
	# on purpose: it is where every build artifact and state file lands
	# (semantic-index.bin, similar-links.json, the freshness stamps), all
	# gitignored or generated, and none of it is a source input a reader
	# could be missing.
	@mkdir -p data; \
	 dirty=$$($(call dirty_inputs,$(DIRTY_PATHS))); \
	 if [ -n "$$dirty" ]; then \
	   if [ "$(ALLOW_DIRTY_DEPLOY)" = "1" ]; then \
	     echo "deploy: ALLOW_DIRTY_DEPLOY=1 — publishing a tree that differs from HEAD:"; \
	     printf '%s\n' "$$dirty" | sed 's/^/    /'; \
	     { echo "# Uncommitted build inputs at deploy time"; \
	       echo "# date: $$(date -u +%Y-%m-%dT%H:%M:%SZ)"; \
	       echo "# HEAD: $$(git rev-parse HEAD)"; \
	       printf '%s\n' "$$dirty"; } > data/last-deploy-dirty.txt; \
	     echo "deploy: recorded in data/last-deploy-dirty.txt (local only — never shipped)"; \
	   else \
	     echo "deploy: uncommitted build inputs — the pushed revision would not" >&2; \
	     echo "        describe the site being published. Refusing." >&2; \
	     printf '%s\n' "$$dirty" | sed 's/^/    /' >&2; \
	     echo "" >&2; \
	     echo "        Commit them, or re-run with ALLOW_DIRTY_DEPLOY=1 to publish" >&2; \
	     echo "        anyway and record the list in data/last-deploy-dirty.txt." >&2; \
	     exit 1; \
	   fi; \
	 else \
	   rm -f data/last-deploy-dirty.txt; \
	   echo "deploy: build inputs are clean at $$(git rev-parse --short HEAD)"; \
	 fi
	# Score pages are ignored by git: a fresh checkout builds without them,
	# but deploying it would remove the published scores.
	@if [ -x .venv/bin/python3 ]; then \
	  .venv/bin/python3 tools/music-import.py check; \
	else \
	  python3 tools/music-import.py check; \
	fi

deploy-recheck:
	@dirty=$$($(call dirty_inputs,$(RECHECK_PATHS))); \
	 if [ -z "$$dirty" ]; then \
	   echo "deploy: build inputs still match $$(git rev-parse --short HEAD)"; \
	 elif [ "$(ALLOW_DIRTY_DEPLOY)" = "1" ]; then \
	   echo "deploy: ALLOW_DIRTY_DEPLOY=1 — inputs that differ from HEAD at push time:"; \
	   printf '%s\n' "$$dirty" | sed 's/^/    /'; \
	 else \
	   echo "deploy: build inputs changed while the build ran. The site was compiled" >&2; \
	   echo "        from a tree the push would not describe. Nothing was pushed or" >&2; \
	   echo "        published:" >&2; \
	   printf '%s\n' "$$dirty" | sed 's/^/    /' >&2; \
	   echo "" >&2; \
	   echo "        Commit or revert them, then re-run 'make deploy'." >&2; \
	   exit 1; \
	 fi

# The document root as the rsync targets use it: blanks stripped and one
# trailing slash removed, matching what tools/deploy-guard.sh accepts.
VPS_DOCROOT = $(patsubst %/,%,$(strip $(VPS_PATH)))

# Everything that must hold before anything is pushed or rsynced. The rsync
# targets depend on it too, so it holds when one is re-run by hand after a
# failed transfer (audit D04).
deploy-guard:
	@test -n "$(strip $(VPS_USER))" || { echo "deploy: VPS_USER not set in .env" >&2; exit 1; }
	@test -n "$(strip $(VPS_HOST))" || { echo "deploy: VPS_HOST not set in .env" >&2; exit 1; }
	@tools/deploy-guard.sh docroot "$(VPS_PATH)" >/dev/null
	# Refuse to deploy a manifestly broken build. _site/index.html must
	# exist and be non-empty before we run rsync --delete on the VPS.
	@test -s _site/index.html || { echo "deploy: _site/index.html is missing or empty — refusing to rsync" >&2; exit 1; }
	# Dev artifacts must never ship. `make build` purges _site/drafts, so
	# this firing means _site was produced by something else (e.g. a raw
	# `cabal run site -- build` after a watch session) — rebuild properly.
	@if [ -d _site/drafts ]; then \
	  echo "deploy: _site/drafts exists — dev drafts must not deploy; run 'make build' (or 'make deploy-clean')" >&2; \
	  exit 1; \
	fi

deploy:
	@$(WITH_LOCK) $(MAKE) --no-print-directory deploy-locked

deploy-locked: deploy-preflight build-locked validate sign
	@$(MAKE) --no-print-directory deploy-guard
	# The revision that was actually compiled. tools/build-freshness.sh
	# writes data/last-build-commit.txt from `git rev-parse HEAD` right
	# after the last successful compile pass; if HEAD has moved since, the
	# push below would advertise a commit the published HTML never saw.
	@test -f data/last-build-commit.txt || { echo "deploy: no data/last-build-commit.txt — run 'make build' first" >&2; exit 1; }
	@built=$$(cat data/last-build-commit.txt); head=$$(git rev-parse HEAD); \
	 if [ "$$built" != "$$head" ]; then \
	   echo "deploy: HEAD ($$(echo $$head | cut -c1-12)) is not the commit that was built ($$(echo $$built | cut -c1-12))." >&2; \
	   echo "        Something committed between the build and the deploy. Re-run 'make deploy'." >&2; \
	   exit 1; \
	 fi
	@$(MAKE) --no-print-directory deploy-recheck
	@command -v notify-send >/dev/null 2>&1 && notify-send "make deploy" "Ready to push & rsync — waiting for auth" || true
	# Push first: a successful push is cheap to roll back, while a
	# half-completed rsync is harder to recover from. If the push
	# fails (auth, branch protection, network), abort before touching
	# the VPS so the public source repo and the live site stay in sync.
	git push -u origin main
	@if [ "$(ATOMIC_DEPLOY)" = "1" ]; then \
	  $(MAKE) --no-print-directory deploy-rsync-atomic; \
	else \
	  $(MAKE) --no-print-directory deploy-rsync-inplace; \
	fi

# The default publication path, unchanged: rsync straight into the live
# document root. Not atomic — for the ~30 seconds rsync runs, a visitor can
# get new HTML with old JS, or a page whose signature has not landed yet.
#
# The dry run first refuses a destination that is not the live site (no
# index.html there) or a transfer that would delete more than
# DEPLOY_MAX_DELETE files — see tools/deploy-guard.sh for the overrides.
deploy-rsync-inplace: deploy-guard
	@tools/deploy-guard.sh target _site "$(strip $(VPS_USER))@$(strip $(VPS_HOST)):$(VPS_DOCROOT)/"
	rsync -avz --delete _site/ "$(strip $(VPS_USER))@$(strip $(VPS_HOST)):$(VPS_DOCROOT)/"

# ---------------------------------------------------------------------------
# ATOMIC_DEPLOY=1 — opt-in release directories  (B06)
# ---------------------------------------------------------------------------
# Publishes into $(VPS_PATH).releases/<utc-timestamp>/ and then flips
# $(VPS_PATH) itself, which must be a SYMLINK, to point at it. The flip is a
# rename(2) over the old symlink, so every request is served entirely by one
# release or entirely by the next.
#
# ONE-TIME SERVER STEP (nothing here does it for you — it moves the live
# document root, so it is yours to run and verify):
#
#     ssh user@host
#     P=/srv/http/levineuwirth.org          # your VPS_PATH
#     mkdir -p "$P.releases"
#     mv "$P" "$P.releases/initial"
#     ln -s "$P.releases/initial" "$P"
#     ls -l "$P"                            # must show a symlink
#     sudo nginx -t && sudo systemctl reload nginx
#
# nginx follows the symlink with its default `disable_symlinks off`. If the
# vhost sets `disable_symlinks on`, point `root` at $(VPS_PATH).releases/current
# instead and skip the symlink-at-VPS_PATH arrangement.
#
# ATOMIC_KEEP (default 3) release directories are retained for rollback:
#
#     ssh user@host 'ln -sfn "$P.releases/<older>" "$P.tmp" && mv -Tf "$P.tmp" "$P"'
#
# --link-dest hard-links unchanged files against the previous release, so a
# retained release costs only what actually changed.
ATOMIC_KEEP ?= 3

deploy-rsync-atomic: deploy-guard
	@set -e; \
	 rel="$(VPS_DOCROOT).releases"; \
	 ts=$$(date -u +%Y%m%dT%H%M%SZ); \
	 echo "deploy: atomic release $$ts under $$rel"; \
	 ssh "$(strip $(VPS_USER))@$(strip $(VPS_HOST))" "test -L '$(VPS_DOCROOT)' || { \
	     echo 'deploy: $(VPS_DOCROOT) is not a symlink — run the one-time server step in the Makefile' >&2; exit 1; }; \
	   mkdir -p '$$rel'"; \
	 prev=$$(ssh "$(strip $(VPS_USER))@$(strip $(VPS_HOST))" "readlink -f '$(VPS_DOCROOT)' 2>/dev/null || true"); \
	 linkdest=""; \
	 if [ -n "$$prev" ]; then linkdest="--link-dest=$$prev"; fi; \
	 rsync -avz --delete $$linkdest _site/ "$(strip $(VPS_USER))@$(strip $(VPS_HOST)):$$rel/$$ts/"; \
	 ssh "$(strip $(VPS_USER))@$(strip $(VPS_HOST))" "set -e; \
	   test -s '$$rel/$$ts/index.html'; \
	   ln -sfn '$$rel/$$ts' '$(VPS_DOCROOT).new'; \
	   mv -Tf '$(VPS_DOCROOT).new' '$(VPS_DOCROOT)'; \
	   ls -1dt '$$rel'/*/ 2>/dev/null | tail -n +$$(( $(ATOMIC_KEEP) + 1 )) | xargs -r rm -rf"; \
	 echo "deploy: $(VPS_DOCROOT) now points at $$rel/$$ts (keeping $(ATOMIC_KEEP) releases)"

# Escape hatch: the old behaviour — full rebuild, then deploy. The
# freshness triggers in tools/build-freshness.sh make this rarely
# necessary; reach for it when local state looks suspicious.
# One lock across both, so a running watch cannot rebuild between them.
deploy-clean:
	@$(WITH_LOCK) $(MAKE) --no-print-directory clean deploy

watch:
	@$(WITH_LOCK) $(MAKE) --no-print-directory watch-locked

watch-locked: export SITE_ENV = dev
watch-locked:
	cabal run site -- watch

clean:
	@$(WITH_LOCK) cabal run site -- clean

# ---------------------------------------------------------------------------
# test / validate
# ---------------------------------------------------------------------------
# `make test` runs BOTH stdlib-unittest suites (B10):
#
#   tests/              site tooling — figures, imports, the artifact gate
#   yaml-source/tests/  the CV/résumé variant resolver
#
# The second used to be invisible to `make test` (`discover -s tests` only
# looks at the top-level directory), so 20 tests never ran here at all.
#
# -v is deliberate: several tests self-skip — tests/test_viz.py needs
# matplotlib and skips without .venv, and its built-page checks skip again
# when _site/ is absent. A quiet run of 35 tests where 21 skipped printed
# "OK" and looked like coverage. With -v every skip names itself.
#
# REQUIRE_VENV=1 turns a missing .venv into a failure instead of a
# degraded run. `validate` sets it, because a deploy gated on a suite that
# silently skipped most of itself is not a gate.
test:
	@if [ -d .venv ]; then \
	  PY="$(CURDIR)/.venv/bin/python3"; \
	elif [ "$(REQUIRE_VENV)" = "1" ]; then \
	  echo "test: REQUIRE_VENV=1 but .venv/ is absent — run 'uv sync'." >&2; \
	  echo "      Without it tests/test_viz.py skips every figure check." >&2; \
	  exit 1; \
	else \
	  PY=python3; \
	  echo "test: .venv/ absent — running with system python3; expect skips."; \
	fi; \
	echo "== tests/ =="; \
	"$$PY" -m unittest discover -s tests -v || exit 1; \
	if [ -d yaml-source/tests ]; then \
	  echo "== yaml-source/tests/ =="; \
	  ( cd yaml-source && "$$PY" -m unittest discover -s tests -v ) || exit 1; \
	else \
	  echo "yaml-source/tests/ not present — skipping"; \
	fi

# The deployment contract, checked in one command: both test suites plus
# the finished-artifact gate over _site/. `deploy` depends on this, so a
# published private file, a figure that failed to render, a broken feed or
# a link into /drafts/ stops the deploy instead of reaching the VPS.
#
#   make validate                      gate an existing _site
#   make validate REQUIRE_WEBP=1       also fail on zero WebP companions
#   make validate CHECK_SITE_FLAGS='--warn-only'  report everything, exit 0
validate:
	@$(WITH_LOCK) $(MAKE) --no-print-directory validate-locked

validate-locked: REQUIRE_VENV = 1
validate-locked: test
	@test -d _site || { echo "validate: _site/ does not exist — run 'make build' first" >&2; exit 1; }
	@python3 tools/check-site.py _site $(CHECK_SITE_FLAGS) $(if $(REQUIRE_WEBP),--require-webp,)
	@$(MAKE) --no-print-directory viz-provenance-check

# Checksum the CSVs behind each figure into figures/data/PROVENANCE.json, so
# a reader who downloads the data can tell it is what the chart was drawn
# from. `write` seeds a TODO source note per file and preserves whatever the
# author writes there; `check` (viz-provenance-check) verifies the recorded
# checksums still match and exits non-zero if not.
viz-provenance:
	@if [ -d .venv ]; then \
	  .venv/bin/python3 tools/viz-provenance.py write; \
	else \
	  python3 tools/viz-provenance.py write; \
	fi

viz-provenance-check:
	@if [ -d .venv ]; then \
	  .venv/bin/python3 tools/viz-provenance.py check; \
	else \
	  python3 tools/viz-provenance.py check; \
	fi

# Render every figure and report what a reader would notice: a mark with no
# variation in it, text that cannot be read against what sits behind it,
# labels too small at the body column, missing alt / desc. Exits 0 — a
# report, like audit-marks. Pass STRICT=1 to fail instead.
#
# This is the complement to `make test`, which checks the pipeline contract
# (colour, determinism, ids, captions). Every visualization bug found in this
# repo so far was invisible in the source and obvious in the render: a
# heatmap drawn from constant data, white labels repainted near-black, 4px
# tick text, a y-axis reading "(imes)".
audit-viz:
	@if [ -d .venv ]; then \
	  .venv/bin/python3 tools/audit-viz.py $(if $(STRICT),--strict,); \
	else \
	  python3 tools/audit-viz.py $(if $(STRICT),--strict,); \
	fi

# Report which content pieces are missing a monogram (mark.svg) and / or
# the epistemic figure (status: frontmatter). Exits 0 unconditionally;
# this is a coverage report, not a build gate. The pre-commit hook at
# tools/hooks/pre-commit-marks.sh runs the same script for newly-staged
# .md files.
audit-marks:
	@if [ -d .venv ]; then \
	  uv run python tools/audit-marks.py; \
	else \
	  python3 tools/audit-marks.py; \
	fi

# Evict archived works: delete archive/<slug>/ directories whose slug is
# recorded in archive/removed.yaml. Opt-in — NEVER run by `make build`.
# Orphan directories (not in manifest.yaml, not in removed.yaml) are
# reported, never deleted. See ARCHIVE.md - Eviction & removal.
archive-gc:
	@if [ -d .venv ]; then \
	  uv run python tools/archive.py gc; \
	else \
	  python3 tools/archive.py gc; \
	fi

# Submit archived URLs to the Wayback Machine and backfill the capture URL
# into each PROVENANCE.json. A slow network job — opt-in, never run by
# `make build`. Always exits 0; an entry without a capture retries next run.
archive-wayback:
	@if [ -d .venv ]; then \
	  uv run python tools/archive.py wayback; \
	else \
	  python3 tools/archive.py wayback; \
	fi

# Print works cited in data/*.bib but not yet archived, as manifest-ready
# lines the author copies by hand. Read-only — it never edits the manifest
# (bibliography auto-seeding is rejected by design; see ARCHIVE.md).
# Offline: scans local files only, no network.
archive-suggest:
	@if [ -d .venv ]; then \
	  uv run python tools/archive.py suggest; \
	else \
	  python3 tools/archive.py suggest; \
	fi

# Probe every archived URL for link rot, updating data/archive-state.json.
# A slow network job — opt-in, never run by `make build`. Asymmetric
# hysteresis: `rotted` needs 3 consecutive failures over >=14 days; a
# single success recovers immediately. The next build consumes the state.
archive-check:
	@if [ -d .venv ]; then \
	  uv run python tools/archive.py check; \
	else \
	  python3 tools/archive.py check; \
	fi

# Dev build includes any in-progress drafts under content/drafts/essays/.
# SITE_ENV=dev is read by build/Site.hs; `make build` now forces
# SITE_ENV=production for itself, so a dev value set here (or exported in
# your shell) can no longer leak into a production compile.
#
# A dev build writes to _site-dev/ with its own store, _cache-dev/
# (build/Utils.hs outputDirFor), never to the _site/ that deploy publishes:
# a draft collection is routed outside /drafts/ in dev, and before the split
# a dev session could leave such a page for the next deploy to sign and
# publish (audit D06). The clean below only clears the dev pair.
dev:
	@$(WITH_LOCK) $(MAKE) --no-print-directory dev-locked

dev-locked: export SITE_ENV = dev
dev-locked:
	cabal run site -- clean
	cabal run site -- build
	python3 -m http.server 8000 --bind 127.0.0.1 --directory _site-dev
