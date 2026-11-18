EXPONENTIAL BEHAVIOR IN MAGIC: THE GATHERING

Companion code, data, and figures

Figure 1 models Scute Swarm, life gained from new Scutes, and Liliana's
Zombies. Figure 2 plots three emblem-resolution times from one replay
against that turn's starting Zombie count. The turn 44 and 58 battlefield
screenshots were captured from the defending seat. To reproduce them,
see code/battlefield-capture.txt.

To regenerate the two plots from the site root:

  .venv/bin/python content/essays/exponential-magic/code/plot-figures.py

The plotting script also accepts --output-dir PATH. It reads the bundled
JSON, needs matplotlib, and does not rerun the engine or contact a service.

Code
  liliana-emblem.rs      The actual count-and-create implementation.
  evolve-scan.rs         The scan repeated for each entering creature.
  attack-list-cap.rs    Singles consume the list before all-in attacks.
  loop-detection.rs     Repeated settled-state fingerprints end the game.
  counter-addition.rs   u32 counter addition.
  counter-to-power.rs   counters cast to i32.

The Rust files are verbatim excerpts, not standalone compilation units.
Each gives its pinned commit, source lines, and URL; imports and enclosing
context may be absent.
The source's original comments are historical implementation commentary.
The code-sources.json manifest records source and excerpt hashes.

  python3 code/growth-model.py       prints the theoretical CSV
  python3 code/attack-menu-demo.py   demonstrates the cap with four defenders

The Python demonstrations are explanatory models, separate from the Rust
excerpts. Eligible attackers are not the same as all controlled creatures.

Data and interpretation
  data/figure-data.json contains plot values, model assumptions, provenance,
    field-deck dates, and official rules links. CSV views are alongside it.
  data/replay-growth.txt and replay-timing.txt are the existing source logs;
    their hashes are recorded in figure-data.json.
  Observation commit: ebb52566. Engine commit: 4265da60.
  Featured game: seed 20261156; uniform-random policies; seat 0 deck 18,
    seat 1 deck 1; action cap 20,000.

Keep turn-start population counts separate from the precise inputs/outputs
of a timed step: the incident note mixed those in its timing table. Timings
are laptop release replays under load; they are not a controlled scaling
benchmark. The quadratic explanation is supported by code and sampled
stacks, not by a profiler's breakdown. The proposed engine optimizations
are not implemented or measured in this bundle. The later board cap is an
observation-harness limit, not a Magic rule or a completed engine repair.

Scute Swarm is absent from the registered catalog at the incident commit.
Separately, all 64 field-deck dates predate its September 2020 release.
The modeled Scute/Warden setup is illustrative.
Two simultaneous land entries differ from sequential entries with all
triggers resolved in between. The model assumes the latter.

The initial observation results and the detailed incident account remain
in the author's Arcana incident note dated 2026-11-10. This bundle includes
the selected replay evidence and figures, not all 48 cluster shard files.

Source code excerpts retain Arcana's MIT license (code/ARCANA-LICENSE.txt).
