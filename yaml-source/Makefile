.PHONY: all all_all cv resume resume_ats ats clean install

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

clean:
	@rm -rf build output
	@echo "cleaned."

install:
	@pip install --user pyyaml jinja2
