# This site's make targets: the engine's (engine/engine.mk: the build and
# its steps, the tests, the reports) and its own, the CV PDFs and the deploy.

.PHONY: pdfs deploy deploy-locked deploy-guard deploy-preflight deploy-recheck deploy-rsync-inplace deploy-rsync-atomic deploy-clean

# Source .env for the deploy target if it exists.
# .env format: KEY=value (one per line, no `export` prefix, no quotes needed).
# Only the variables explicitly listed below are exported to recipe
# subprocesses — bare `export` would leak every .env key (including any
# future GITHUB_TOKEN) into every child process.
-include .env
export VPS_USER VPS_HOST VPS_PATH

# What this site's build reads beyond the engine's BUILD_INPUTS: the CV
# sources, the served nginx configuration, and the documents published
# verbatim under /source/.
SITE_INPUTS := yaml-source nginx LICENSE LICENSE-CONTENT THIRD-PARTY.md README.md WRITING.md PHOTOGRAPHY.md
# The CV and résumé variant resolver's own suite.
SITE_TEST_DIRS := yaml-source

include engine/engine.mk

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
# Every source input that is not content/ — the engine, templates/,
# static/, data/, yaml-source/, tools/, nginx/, the Makefile: BUILD_INPUTS
# in engine/engine.mk, with SITE_INPUTS above — was compiled into the
# site whether or not it was committed, and then
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
# (it did on 2026-10-01, audit X1).

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
RECHECK_PATHS := $(BUILD_INPUTS) content tests

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
	@python3 $(call tool,code-refs.py) fetch
	@if [ -x $(VENV_PY) ]; then $(VENV_PY) $(call tool,archive.py) fetch; fi
	# Tracked modifications anywhere in BUILD_INPUTS, plus untracked files in
	# all of them except data/. data/ is excluded from the untracked check
	# on purpose: it is where every build artifact and state file lands
	# (semantic-index.bin, similar-links.json, the freshness stamps), all
	# gitignored or generated, and none of it is a source input a reader
	# could be missing.
	@mkdir -p data; \
	 dirty=$$($(call dirty_inputs,$(BUILD_INPUTS))); \
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
	@$(PY) $(call tool,music-import.py) check

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
	@$(call tool,deploy-guard.sh) docroot "$(VPS_PATH)" >/dev/null
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

# A deploy requires a WebP companion for every JPEG/PNG: without cwebp
# on the deploying machine, every photograph shipped at full JPEG weight
# until 2026-10-04 while each build only warned. Exported so the validate
# it runs, a sub-make, sees it. `make deploy REQUIRE_WEBP=` overrides it,
# knowingly.
deploy-locked: export REQUIRE_WEBP = 1
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
	@$(call tool,deploy-guard.sh) target _site "$(strip $(VPS_USER))@$(strip $(VPS_HOST)):$(VPS_DOCROOT)/"
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
