#!/usr/bin/env python3
"""Graph-paper source builds moved to ~/Repos/research/meyniel.

In that checkout, run `make papers`, then explicitly export reviewed assets:
    make export WEBSITE="$HOME/Repos/personal/levineuwirth.org"
See its HANDOFF.md and docs/PUBLISHING.md.
"""

import sys

if __name__ == "__main__":
    print(__doc__.strip())
    raise SystemExit(0 if any(arg in {"-h", "--help"} for arg in sys.argv[1:]) else 2)
