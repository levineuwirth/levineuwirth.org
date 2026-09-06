# Graph theory research moved

The editable graph-theory manuscripts and numerical experiments now live in
`~/Repos/research/meyniel`.

Start with [the research handoff](/home/jeans/Repos/research/meyniel/HANDOFF.md).
Build with `make papers` there; explicitly export reviewed artifacts with:

```sh
make -C "$HOME/Repos/research/meyniel" export WEBSITE="$HOME/Repos/personal/levineuwirth.org"
```

The research repository's `docs/PUBLISHING.md` describes stale-build checks,
public filenames, and the website articles to reconcile when mathematics changes.
The site retains public PDFs, thumbnails, the downloadable demo, and its CSV.
The two domination PDF URLs remain byte-identical compatibility aliases.
Normal site builds use these released files without a research checkout.
