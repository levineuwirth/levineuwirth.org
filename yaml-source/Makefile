.PHONY: all all_all cv resume resume_ats ats variant list test validate clean install

# Default: build the two website-facing PDFs (cv + 1-page résumé).
# Use `make all_all` to also build the ATS-optimized résumé variant.
all:
	@python3 build.py all

all_all:
	@python3 build.py all_all

cv:
	@python3 build.py cv

resume:
	@python3 build.py resume

# ATS-optimized résumé variant. See templates/resume_ats.tex.j2.
resume_ats ats:
	@python3 build.py resume_ats

# Build any tracked or local-private audience variant, e.g.:
#   make variant NAME=frontier-evals-control
variant:
	@test -n "$(NAME)" || (echo "NAME is required (try: make list)" >&2; exit 2)
	@python3 build.py --variant "$(NAME)"

list:
	@python3 build.py --list

test:
	@python3 -m unittest discover -s tests -v

# Resolve every configuration, run the dependency-light resolver tests, and
# compile every discovered non-abstract variant when xelatex is available.
validate: test
	@python3 build.py --validate-config
	@if command -v xelatex >/dev/null 2>&1; then \
	  python3 build.py --all-variants; \
	else \
	  echo "xelatex not found; PDF builds skipped"; \
	fi

clean:
	@rm -rf build output
	@echo "cleaned."

install:
	@pip install --user pyyaml jinja2
