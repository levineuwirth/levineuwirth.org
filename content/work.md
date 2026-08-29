---
title: Work
work: true
description: Research engineer working on technical AI assurance — verifiable inference, model evaluations, systems and cryptography.
history:
  - date: "2026-08-29"
  - date: "2026-08-28"

---

::: {.work-name}
Levi Neuwirth
:::

::: {.work-lede}
I work on technical AI assurance: establishing verifiable claims about what a
model actually did, when the operator, the evaluator, or the model itself may
not be trusted. That question spans cryptography, systems, evaluations, and
mathematics, which is roughly the shape of my background.

I am a MARS V fellow with the [Cambridge AI Safety Hub](https://caish.org/mars),
mentored by James Petrie (Future of Life Institute), and a graduate student in
computer science and engineering at DTU; previously computer science and
mathematics at Brown.

**Open to full-time research and research-engineering positions worldwide.**
:::

::: {.work-links}
[CV](/cv.pdf) · [GitHub](https://github.com/levineuwirth) ·
[Projects](/cv/projects/) · [Email](mailto:ln@levineuwirth.org)
:::

## Selected work

::: {.work-entry}
### [Verifiable LLM inference](/essays/verified-inference/)

::: {.work-meta}
MARS V fellowship · Cambridge AI Safety Hub · ongoing
:::

An operator who claims to have run a model may not have, and the logs that would
settle it are written by the party under suspicion.

[VerInf](https://github.com/JamesPetrie/VerInf), a Future of Life Institute project led by James Petrie, proves
LLM inference in zero knowledge with no trusted setup by bounding the
*unexplained information* in an output stream rather than re-running the
computation. I have contributed the dry-run profiler (manifest contract, cost model,
execution DAG, partition scorecard) and an RMSNorm cost-model correction. My current
work is on proving multi-GPU, which is the ceiling on model scale, context
length, and mixture-of-experts breadth.

::: {.work-limit}
**Ongoing.** The multi-GPU work is unmerged and its results are preliminary.
Technical write-up expected Q4 2026, for review and publication.
:::

::: {.work-entry-links}
[Merged pull requests](https://github.com/JamesPetrie/VerInf/pulls?q=is%3Apr+author%3Alevineuwirth) ·
[Upstream repository](https://github.com/JamesPetrie/VerInf) ·
[MARS](https://caish.org/mars)
:::
:::

::: {.work-entry}
### [Frontier-model evaluation and red-teaming](/essays/specification-dilemma/)

::: {.work-meta}
Independent research contracts · ongoing
:::

I design evaluation environments and scoring rubrics for frontier language
models, execute models against them, debug agent scaffolds when they fail, and
analyze the failures that result. I have led environment design and evaluator
calibration; most of it is built in [Harbor](https://github.com/harbor-framework/harbor).

Calibration passes often reveal that a rubric is measuring something other than
what the task was designed to measure: a task-design failure, not a grading one.
I calibrate before a task is scaled, because redesigning a task is cheap and
rescoring a finished run is not.

For a similar methodology on public data, see [The Specification
Dilemma](/essays/specification-dilemma/) — pre-registered, matched-pairs, with
its instrumentation failures reported in full.

::: {.work-limit}
**Disclosure.** Client identities and specific results are confidential. I can
discuss the technical categories of work and my own engineering
responsibilities.
:::

::: {.work-entry-links}
[Code and results](https://github.com/levineuwirth/specification-dilemma)
:::
:::

::: {.work-entry}
### Proof Broker

::: {.work-meta}
Independent · OCaml · ongoing research program
:::

Lean 4 and Rocq can outsource proof search to external provers — SMT solvers,
automated theorem provers, even LLMs — without extending what they trust. Proof
Broker routes a goal out to those provers, checks whatever comes back, and lifts
the result into a proof term the home system verifies for itself. The provers
stay untrusted; the kernel remains the trusted base.

Concretely: a function-composition goal closes under `by proof_broker` through a
real Vampire invocation, axiom-free.

::: {.work-limit}
**Boundary.** Individual inference steps are not re-derived — the kernel check
is what closes the proof. Breadth is in progress: the Vampire path is complete
end-to-end, other backends are not.
:::

::: {.work-entry-links}
[Repository](https://github.com/levineuwirth/proof-broker)
:::
:::

::: {.work-entry}
### [Order-invariant ICD-10-CM embeddings](/essays/beyond-comorbidity-indices/)

::: {.work-meta}
Research engineering · manuscript under review
:::

Comorbidity indices compress a patient's diagnosis history into a single
weighted score, discarding both order and interaction. This work learns a
permutation-invariant representation over ICD-10-CM diagnosis-code sets and
predicts 30-day unplanned readmission and 30-day post-discharge mortality,
trained on 113M+ adult hospitalizations from the Nationwide Readmissions
Database. On the temporal test split it reaches 0.750 AUROC for readmission
against 0.655 for the Charlson index. The calculator is deployed.

::: {.work-limit}
**Status.** Under review at *JAMIA*; results are unrefereed.
:::

::: {.work-entry-links}
[Repository](https://github.com/levineuwirth/icd_embeddings) ·
[Calculator](https://levineuwirth.github.io/icd_embeddings)
:::
:::

## The question

::: {.work-thesis}
Those four are one problem approached from different sides. Cryptography works
from below, certifying properties of a computation without trusting the party
that ran it. Evaluations work from above, measuring what a model actually does
under conditions you control. Formal methods supply the machinery for checking a
claim without trusting its author.

The question underneath all of it: how do you establish trustworthy claims about
an AI system when the system, the operator, and the evaluator may each be
untrusted?
:::

## More work

::: {.work-more}
### Systems and performance

- [pmacs](https://github.com/levineuwirth/pmacs) — Rust-cored, Lua-scripted editor
- [kyber-simd-profiling](https://github.com/levineuwirth/kyber-simd-profiling) — SIMD post-quantum cryptography across AVX2, ARM NEON-SVE, and RISC-V V, with hardware counters and RAPL energy
- [LeVCS](https://github.com/levineuwirth/LeVCS) — federated version control with signed authority chains
- [arcana](https://github.com/levineuwirth/arcana) — Magic: The Gathering rules engine, built as a substrate for reinforcement-learning research
- Weenix — Unix kernel
- TCP/IP stack — written from scratch in Go

### Mathematics

- [Branch-tube persistence and static coverage in tree-ball geometry](/essays/branch-based-local-capture-in-tree-balls/) — preprint, revising
- [The annealed critical window for growing-radius domination in random regular graphs](/essays/near-critical-growing-radius-domination.html) — preprint, revising

### Research engineering

- [NeuroPose](https://github.com/levineuwirth/neuropose) — 3D pose estimation and kinematic analysis, built in Liqi Shu's laboratory at Brown Neurology
- [NeuroAI](https://neuroai.health) — ongoing research engineering

### Writing

- [Essays](/nonfiction/) — on the above, and on much else
- [Current](/current.html) — what is actually moving this month
- [Vita](/about.html) — the formal record, and [résumé](/resume.pdf)
:::
