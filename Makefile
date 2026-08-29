.PHONY: build deploy sign download-model download-pdfjs download-leaflet compress-assets convert-images pdf-thumbs pdfs watch clean dev audit-marks archive-gc archive-wayback archive-check archive-suggest

# deploy's prerequisite order (clean -> build -> sign) is only correct
# serially; under `make -j` they could interleave. This build has no
# intra-target parallelism worth preserving, so disable it outright.
.NOTPARALLEL:

# Source .env for deploy / GitHub config if it exists.
# .env format: KEY=value (one per line, no `export` prefix, no quotes needed).
# Only the variables explicitly listed below are exported to recipe
# subprocesses — bare `export` would leak every .env key (including any
# future GITHUB_TOKEN) into every child process.
-include .env
export VPS_USER VPS_HOST VPS_PATH GITHUB_REPO

build:
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
	@git add content/
	@git diff --cached --quiet -- content/ || git commit -m "auto: $$(date -u +%Y-%m-%dT%H:%M:%SZ) [skip ci]" -- content/
	@mkdir -p data
	@date +%s > data/build-start.txt
	@./tools/convert-images.sh
	@$(MAKE) -s pdf-thumbs
	@./tools/download-pdfjs.sh
	@./tools/download-leaflet.sh
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
	cabal run site -- build
	pagefind --site _site
	@if [ -d .venv ]; then \
	  HF_HUB_DISABLE_IMPLICIT_TOKEN=1 uv run python tools/embed.py || echo "Warning: embedding failed — data/similar-links.json not updated (build continues)"; \
	else \
	  echo "Embedding skipped: run 'uv sync' to enable similar-links (build continues)"; \
	fi
	# Site-wide footer timestamp: rewrite every <span data-build-time>
	# in _site/**/*.html so cached (un-recompiled) pages don't show a
	# stale per-page build time. See tools/stamp-build-time.py for the
	# full rationale. Must run before compress-assets so the .gz/.br
	# sidecars include the fresh stamp.
	@python3 tools/stamp-build-time.py _site
	@./tools/compress-assets.sh _site
	> IGNORE.txt
	@BUILD_END=$$(date +%s); \
	 BUILD_START=$$(cat data/build-start.txt); \
	 echo $$((BUILD_END - BUILD_START)) > data/last-build-seconds.txt.tmp && \
	 mv data/last-build-seconds.txt.tmp data/last-build-seconds.txt

sign:
	@./tools/sign-site.sh

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
	@./tools/compress-assets.sh _site

# Convert JPEG/PNG images to WebP companions (also runs automatically in build).
# Requires cwebp: pacman -S libwebp  /  apt install webp
convert-images:
	@./tools/convert-images.sh

# Generate first-page thumbnails for PDFs in static/papers/ (also runs in build).
# Requires pdftoppm: pacman -S poppler  /  apt install poppler-utils
# Thumbnails are written as static/papers/foo.thumb.png alongside each PDF.
# Skipped silently when pdftoppm is not installed or static/papers/ is empty.
pdf-thumbs:
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
# after editing a YAML under yaml-source/data/. The site build copies
# static/*.pdf through unchanged, so a subsequent `make build` picks them up.
#
# The ATS variant (yaml-source/output/resume_ats.pdf) is intentionally not
# copied to static/ — it's a submission artifact, not a website asset. To
# regenerate it too, run `make -C yaml-source ats` directly.
#
# Silently skipped on hosts without the pipeline (e.g., the VPS): yaml-source/
# is gitignored, so it's absent on a fresh clone, and that's the expected
# state wherever the LaTeX toolchain isn't installed.
pdfs:
	@if [ ! -d yaml-source ]; then \
	  echo "pdfs: yaml-source/ not present — skipping (pipeline is local-only)"; \
	  exit 0; \
	fi
	@$(MAKE) -C yaml-source all
	@cp yaml-source/output/cv.pdf static/cv.pdf
	@cp yaml-source/output/resume.pdf static/resume.pdf
	@echo "pdfs: static/cv.pdf and static/resume.pdf refreshed."

deploy: clean build sign
	@test -n "$(VPS_USER)" || (echo "deploy: VPS_USER not set in .env" >&2; exit 1)
	@test -n "$(VPS_HOST)" || (echo "deploy: VPS_HOST not set in .env" >&2; exit 1)
	@test -n "$(VPS_PATH)" || (echo "deploy: VPS_PATH not set in .env" >&2; exit 1)
	# Refuse to deploy a manifestly broken build. _site/index.html must
	# exist and be non-empty before we run rsync --delete on the VPS.
	@test -s _site/index.html || { echo "deploy: _site/index.html is missing or empty — refusing to rsync" >&2; exit 1; }
	# Defense-in-depth: refuse rsync --delete to obviously dangerous
	# parents in case VPS_PATH was typo'd (e.g. trailing-slash mistake).
	@case "$(VPS_PATH)" in /|/srv|/srv/http|/var|/var/www|/home|/root|"") echo "deploy: VPS_PATH=$(VPS_PATH) looks unsafe — refusing" >&2; exit 1 ;; esac
	@command -v notify-send >/dev/null 2>&1 && notify-send "make deploy" "Ready to push & rsync — waiting for auth" || true
	# Push first: a successful push is cheap to roll back, while a
	# half-completed rsync is harder to recover from. If the push
	# fails (auth, branch protection, network), abort before touching
	# the VPS so the public source repo and the live site stay in sync.
	git push -u origin main
	rsync -avz --delete _site/ "$(VPS_USER)@$(VPS_HOST):$(VPS_PATH)/"

watch: export SITE_ENV = dev
watch:
	cabal run site -- watch

clean:
	cabal run site -- clean

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
# SITE_ENV=dev is read by build/Site.hs; drafts are otherwise invisible to
# every build (make build / make deploy / cabal run site -- build directly).
dev: export SITE_ENV = dev
dev:
	cabal run site -- clean
	cabal run site -- build
	python3 -m http.server 8000 --bind 127.0.0.1 --directory _site
