---
title: "Eighty Verified Witnesses, Six Proofs"
subtitle: "Auditing what an untrusted model contributed behind a proof boundary"
date: 2026-10-01
abstract: >
  Proof Broker accepts nothing it cannot check. For R6, I put a live
  language model behind that boundary and asked it for arithmetic proof
  certificates on a census of fifteen obligations from a real Lean
  development, the eleven its interface could pose, eight times each,
  with the analysis frozen before the cohort's first call.
  Every certificate it was asked for that could exist came back and
  verified: 80 of 80. Proof coverage stayed at six of fifteen obligations
  from the first draw to the eighth, because posing goals and turning
  certificates into proofs, not finding certificates, was the constraint.
  This essay reports that result, what an outside reader can verify about
  it, the two amendments made after collection, and what "consumed"
  turned out to mean.
tags:
  - research
  - ai
  - tech
figure-numbering: true
status: "Durable"
confidence: 90
importance: 3
evidence: 4
scope: average
novelty: moderate
practicality: moderate
result-shape: mixed
history:
  - date: "2026-10-01"
    note: "Added what “consumed” meant in R6, and the audit of the 48 proofs' final step (R6 qualification 1 and its addendum)"
  - date: "2026-10-01"
---

If you want to know what a language model contributed to a result, three
accounts are on offer. The model's own should carry no weight; 
that is the premise of putting it behind a boundary. The
harness's is only as good as the harness, and it certainly isn't exhaustive.
Your own reading, chosen after the results are in, is, unfortunately, worth less 
than it feels in many scenarios^[This is especially true as autonomy in the use
of language models is not only increasing, but actively being pushed by essentially
all of the frontier labs. For instance, Anthropic switching Claude Code's default to
auto mode, the new "Dots" autonomous agent product of OpenAI, Meta's Muse, etc. These
developments also apply to open source agents like pi, where the default workflows
are to allow all actions without much manual intervention.].

[Proof Broker](/essays/proof-broker/) accepts nothing it cannot check.
For R6, I put a live language model behind that boundary and asked it
for arithmetic proof certificates on a census of 15 obligations
from a real Lean development, the 11 its interface could pose, 8
times each. The analysis and the auditor were
frozen before the cohort's first call, and every request was reserved
on a ledger against a signed authorization before it was sent. The questions
were simple: how often does one learned proposal become an admissible proof, 
what *does* repetition actually buy, and
where does the deterministic route already provide that proof?

**Every certificate the model was asked for that could exist came back
and verified: 80 of 80.** Proof coverage, nonetheless, stayed at six of
fifteen obligations, equal in the 8th and final draw to the 1st. In
contrast to what one might have intuitively expected, the bottleneck was never the
model.

Everything reported here can be checked from public records, and one
qualification belongs at the top rather than the bottom. I would
encourage an interested reader to glance through. In production, I met two
situations no rehearsal had covered: a shared policy directory, and a
network connection that failed before anything was sent. In both instances, the
frozen machinery stopped rather than guess. Each fix changed only what
the auditor, and once the runner, would accept, and neither touched the
analysis, a recorded outcome, or a run. [Two amendments](#two-amendments)
describes what happened in more detail. A second qualification came
later, from reading the closer itself: in R6, "consumed" meant less than
I first wrote. [What "consumed" means](#what-consumed-means) gives it,
with the audit that followed.

## The experiment on one page

**The boundary has three gates, and the model sits outside all of
them.** The model proposes a **Farkas witness**: one integer multiplier per hypothesis, nonnegative on every inequality,
chosen so that the weighted sum of the hypotheses and
the negated goal cancels every variable and leaves a false statement
about constants (such as $1 \le 0$). An independent checker verifies the
witness. A **closer**, the step that builds a proof term from the
certificate, folds the certificate's multipliers into that term; [what
that guaranteed](#what-consumed-means) is a section of its own. Then the **kernel**, the small trusted checker
at Lean's core, checks the local proof and the whole declaration that
contains it, and the axioms that declaration uses must be unchanged. The
[architecture essay](/essays/proof-broker/) tells the full boundary
story. A concise version to summarize here: nothing the model says is believed
until all three gates have passed it.

**The workload was fixed before the model saw any of it.** The census
takes every `omega` call in VerInf's `Bracket.lean` at one pinned
commit, the same file R4 used: 15 primary obligations in 4
declarations. The declaration, or **family**, is the unit of
independence, since 4 sites in one proof are not 4 separate
pieces of evidence. The frozen SDK refuses the goal form of 4
obligations before any request, which leaves 11 posed. 10 of those
are certificate-feasible. The 11th, l170, is a **negative control**:
its rows are satisfiable, so no valid certificate exists, and an
acceptance there would mean the checker had failed, not that the model
had succeeded.

**The model got only one request per slot, nothing else.** It was
`gpt-5.4-2026-03-05`, through OpenAI's Responses API at medium reasoning
effort, with no tools, one stateless request, at most 4,096 output
tokens and no automatic retries.^[The name is the provider's label. The
frozen policy records it as "a documented dated provider snapshot; not a
model-content hash or an attestation that the returned text came from
it." Nothing in this experiment depends on the attribution, since the
boundary treats any proposer's output the same way. Any claim about
which model did this rests on that label and nothing more.] The prompt's
rules close with: "The witness is checked independently; do not claim acceptance
yourself. Supply a proposal even if uncertain." Each posed obligation
received eight preassigned draws with byte-identical input: 88 slots.
The draws are repeated attempts on the same eleven questions, not 88
independent trials.

**Everything that could be decided in advance was.** The analysis
program was locked on 23 September, before the cohort's first call.^[Earlier
stages of R6 made live calls while building the harness, and two of them
showed the provider one of these fifteen obligations. [Counting what
counts](#counting-what-counts) reports what that means for it.] The auditor that decides whether a
collection is admissible at all was locked before the first block was
signed. The deterministic comparison arm was frozen and run before any
learned draw. Collection ran in two blocks, each under its own signed
authorization: draw 1 on all eleven posed obligations, then draws 2
through 8.

## What happened

::: {.figure #fig-grid script="figures/hero_grid.py" caption="Every slot in R6: fifteen obligations by eight draws, grouped by declaration family. A filled square is a proof whose whole declaration validated with its axioms unchanged; a half-filled square is a witness that verified and was then refused by the closer. To the right, the frozen deterministic arm and, set apart, the reference route, a separate control never pooled with it."}
:::

- **Verified witnesses:** all 80 certificate-feasible slots.
- **Proofs:** 48 of 88 slots ended in a whole-declaration-validated
  proof with the axioms unchanged. They are six obligations proved at
  every draw: l069, l070, l071 and l078 in `lift_cell`, through the ℕ
  closer, and l096 and l099 in `threshold_unique`, through the ℤ closer.
- **Coverage:** six of fifteen obligations at draw 1, and six of fifteen
  at draw 8. Each draw added exactly six proofs, on the same six
  obligations.
- **Refused:** l166, l175, l178 and l204 received verified witnesses at
  all eight draws, and the closer refused all 32.
- **The negative control held:** the verifier rejected l170 at all eight
  draws. No false certificate was accepted, and no observation
  contradicted another.

**Against the deterministic arm, the gain is two obligations in one
family.** The frozen deterministic route, cvc4 1.8 with the SDK's own
Farkas synthesis, proved the same four `lift_cell` obligations. On l096
and l099 it never invoked its backend, and no certificate was minted.
The model closed both, at every draw. On the other posed obligations the
arms agree: both prove the `lift_cell` four, and on l166, l175, l178 and
l204 both produce certificates that verify and then fail at
reconstruction.

## Counting what counts

Obligations are what a proof is about; families
are what is independent; draws are repetitions. "48 of 88" reads like a
55% success rate, but it's really 6 obligations in 2 families, each proved
8 times. So the obligations go beside the slots every time a number
appears, and [](#fig-ladder) follows both units from start to finish.

::: {.figure #fig-ladder script="figures/ladder.py" caption="Where R6's slots and obligations fell away, each panel on its own scale. No drop is a proposal that failed on an obligation where a certificate existed. “Consumed” has R6's meaning: the closer folded a verified certificate and the kernel accepted the result (see [what that means](#what-consumed-means))."}
:::

Nothing in either ladder was lost to a missing or invalid proposal on a
feasible obligation. The losses are the four goals the SDK would not
pose, the negative control doing its job, and the 4 goals the closer
refused.

**Repetition bought diversity, not coverage.** Compared up to positive
scaling, l070 returned 4 distinct verified witnesses over its 8
draws, and only 3 of those slots matched the certificate the
classification had found. l071 returned two, neither matching. Every
other verified site returned the same witness at every draw, equal to
the classification's. The extra witnesses all landed on obligations
that were already proved, so they bought no new proof.

**One obligation may have been seen before.** l070 is the control site
of R6-000, the project's first golden episode. Its obligation, rows and
deterministic witness were visible to the provider in 2 earlier live
calls. The analysis keeps it as a stratum rather than removing it.
Without l070, 40 of 80 slots validate; without its whole family, 16 of
56. The gain over the deterministic arm does not depend on it: that gain
is l096 and l099, and no site but l070 had been extracted or transmitted
before the census.

## Where it stopped

**The four refused obligations had verified certificates every time.**
What failed was the step from certificate to proof. The pinned closer
picks its mode from the extraction. These four contain natural-number
variables, so it selects the ℕ closer, whose goal matcher accepts only
comparisons at `Nat`. The goals themselves are integer comparisons over
casts, such as `↑v0 ≤ z`. The closer refused before the kernel was
asked anything, and the refusal was diagnosed as `nat_closer_int_goal`
from bound evidence alone. These are the four sites the design had
predeclared closer-unreachable from its rehearsals. The live model's
certificates did not move them.

**A route that re-proves the goal cannot answer the question.** The
broker's default route closes through `gated_omega`. Once a certificate
is accepted, it runs `omega` again on the original goal. As a separate
reference, it closed l069 through l078 and exactly the four refused
sites, and missed l096 and l099. That shows the four refused obligations
are provable, which nobody doubted: `omega` proves them in the original
file. It does not show that a retained witness can be consumed, because
on that route the certificate is only a gate. So it is tabled beside
the frozen arm as a control and never pooled with it. No route closed
all ten feasible obligations.

**R6 leaves one sharp question.** The 32 verified certificates at l166,
l175, l178 and l204 are retained. Can a closer suited to their ℤ goals
build proofs from them, consuming the certificate in the strong sense of
the next section? R6-015 tests that offline, preregistered separately and
locked before its replay, with no provider, no credential and no
spending. It does not revise R6's result, which
stands as recorded under its frozen route, and it is reported on its own.

## What "consumed" means {#what-consumed-means}

**After collection, reading the closer, I found that "consumed" claimed
more than the code enforced.** The closer builds the weighted sum $s$
of the certificate's hypotheses and a proof that $s \le 0$. It then
proves $0 < s$ by calling `omega` in the goal's full context, with every
hypothesis in scope. When the multipliers cancel, that call only checks
a positive constant. When they do not, `omega` can supply the missing
argument from the context: a synthetic probe written in review closed a
combination that does not cancel. R6's checker verified every
certificate it passed on by exact cancellation, so every R6 proof is
sound and every combination valid. What the closer did not establish is
that the certificate alone discharged the contradiction.

**So in R6, "consumed" means that the closer folded a verified
certificate and the kernel accepted the result.** I recorded that as a
dated qualification beside the synthesis, rather than rewording the
result.

**Then I audited the 48 proofs themselves.** A separate tool, reviewed,
tested against controls and locked before the audit ran, inspected each
proof's final step (the record discloses the one proof I read while
building it): which hypotheses it refers to, and
whether the certificate's sum alone proves $0 < s$, kernel-checked.

- **l069, l071 and l078, 24 slots:** the final step refers to no
  hypothesis, and the sum alone suffices. These are consumed in the
  strong sense.
- **l070, 8 slots:** the final step drew on context at every draw. At
  seven draws the sum would have sufficed on its own; at the fifth,
  sufficiency could not be established.
- **l096 and l099, 16 slots:** not classified. The run's record names a
  variable that preparation had renamed (`c_` for `c'`), so the audit
  could not bind the record to the proof, and made no classification.

**R6's numbers do not change; their reading does.** There are still 48
proofs on six obligations. The strong sense of "consumed" is established
for 24 of them, on three obligations. The two obligations that carry the
gain over the deterministic arm, l096 and l099, are exactly the two the
audit could not classify: that gain stands in R6's sense of the word, not
yet in the stronger one.

## What an outside reader can check

**A claim like this is only as good as whatever bounds each way it could
be wrong.** The table is the argument. Each row names a failure, the
mechanism that bounds it, and where to look.

| what could go wrong | what bounds it | where to check |
|---|---|---|
| the model's output is trusted | an independent checker, a closer, and the kernel on the whole declaration, axioms unchanged; a negative control where an acceptance would stop everything | the frozen auditor's 4,327 cases |
| the analysis is chosen after the results | the analysis program locked before the cohort's first call; its output reproduces byte for byte | the command below |
| spending exceeds what was authorized | a signed authorization per block; every slot reserved on a hash-chained ledger before sending; pricing admitted before each reservation | net committed equals the authorization; nothing open |
| the harness leaks the credential | scans of the published records with the real credential as the canary; each run bound by a credential commitment and a seal | the scan report: 132,450 files, no disclosures, 89 runs bound |
| a failure is quietly retried or papered over | fail-closed pauses; a retry only under a reviewed rule; a preflight over every existing run before resuming | the pause and incident records |
| the auditor is bent to fit the data | amendments built on synthetic evidence without reading the collected outcomes, reviewed, then locked; every lock retained | the amendment records; locks v1, v2 and v3 |
| a closer's success is read as more than it shows | a dated qualification of "consumed", and an audit of the 48 proofs' final step, locked before it ran | qualification 1 and its addendum: the strong sense established for 24 of 48 |

**The analysis is an empirically replicable experiment rather than a judgment.** Anyone with the
repository at the `r6` tag can rerun it on the recorded input and
compare the bytes:

```bash
cd experiments/r6
python3 analysis_r6.py \
  --input reviews/2026-09-29/R6-014-BLOCK2-ANALYSIS-INPUT.json \
  --policy policies/farkas-cohort-v9.json \
  --output /tmp/r6.json
cmp /tmp/r6.json \
  reviews/2026-09-29/R6-014-BLOCK2-ANALYSIS.json
```

**The money reconciles to the micro-dollar.** The final authorization
covered all 88 slots at 9,011,200 µUSD, about \$9.01. The ledger holds
89 reservation rows totaling 9,113,600 µUSD gross; one pre-send release
returned 102,400, so the net committed is exactly the authorization, and
nothing is open. The provider reported 108,480 input and 44,886 output
tokens, which at the frozen rates prices at 944,490 µUSD, about \$0.94.


**The disclosure scans cover what was published.** Their scope is the
experiment's directory, not the whole repository. The published records
deliberately keep host metadata such as local paths, and never a
credential value.

**Some stops were the machinery working.** The first launch of block 2
was interrupted by an interrupt signal before it reserved anything. The
runner found the sealed attempt on relaunch and paused, and the attempt
was moved aside byte for byte, 175 files with identical digests. Three
stops never fired: the integrity stop for a negative-control acceptance,
any unknown or partial send, and any slot exhausting its attempts.

## Two amendments

**Production met two things no rehearsal had.** The first surfaced on
24 September. The first frozen audit of block 1 rejected the collection
at a layout check, before examining a single run. The check required the
policy directory to hold only the campaign's own files. Every reviewed
fixture had a directory to itself, but production signs into a shared
one, beside every earlier policy and lock. Amendment 1 derived the
campaign's expected files explicitly and ignored unrelated ones; every
other predicate stayed the frozen auditor's. It was reviewed and locked
as `live-evaluation-v2`, and block 1 was accepted with 550 cases. The
rejection is retained beside it.

The second surfaced at 23:34 UTC on 28 September, at l204's sixth draw,
with 64 slots collected. The sender made one connection attempt, and it
failed after 15.7 seconds with nothing sent.^[The host's network probe
dropped at about the same moment. That is circumstantial, and I claim no
cause.] The ledger already had a reviewed rule for this: a release with
termination established and zero sends leaves the slot unconsumed and
retriable, up to three attempts. But neither the live auditor nor the
runner had ever met one, so the runner paused, as its rule required.
Amendment 2 taught the auditor to admit a live pre-send release only on
the sender's complete pre-grant state, not on the ledger's word. It let
the runner retry within the ledger's limit, after a preflight over every
existing run. **Its first review found two real defects before anything
resumed:** contradictory send evidence could still authorize a retry,
and a restart could skip existing attempts. Both were repaired and
reviewed again. With the lock at `live-evaluation-v3`, run 3 retried the
slot and collected the remaining 23 in eighteen minutes.

::: {.figure #fig-timeline script="figures/timeline.py" caption="How R6 was collected. The step line counts slots collected, and the two windows use different time scales. Audit and review events are set in italic."}
:::

| when (UTC) | what happened |
|---|---|
| 24 Sep, 08:56–09:07 | block 1 signed; 11 slots collected |
| 24 Sep, 09:12 | first frozen audit rejects block 1 on the policy-directory layout |
| 24 Sep, 11:02–11:03 | amendment 1 approved, locked as v2; block 1 accepted, 550 cases |
| 25 Sep | block 2 authorized |
| 28 Sep, 20:31 | run 1 interrupted before any reservation; moved aside |
| 28 Sep, 23:00–23:34 | run 2 collects 53 slots; pause 1 on a connection that failed before sending |
| 29 Sep, 10:32–15:20 | amendment 2: reviewed, two defects found, revised, approved, locked as v3 |
| 29 Sep, 15:25–15:43 | run 3: preflight over 54 runs, the retry, 23 more slots; 88 of 88 |
| 29 Sep, 19:10 | complete collection accepted, 4,327 cases; frozen analysis run |

**What changed, and what did not.** Both amendments changed only what
the auditor, and for the second the runner, would accept. Neither
changed the frozen analysis, a recorded outcome, or a run. Both were
built and tested on synthetic evidence first, without reading the
collected outcomes to decide what to accept. R6 is therefore not an
unchanged preregistered evaluation; what it can
claim is that every change is dated, reasoned, reviewed and kept next to
what it replaced.

**The lesson is cheap to apply.** Neither gap was a defect in the
evidence. Both were gaps between what was rehearsed and what production
does. Some might say this is the reason we tend to distinguish between
development and production! 

## Current Limitations

The evidence is narrow, and the result is interesting because it is
bounded.

- **One file.** Fifteen obligations from one file at one commit, in four
  families. They support no claim about a
  repository population, and that is a scale-out that I look forward
  to building.
- **One model, one interface.** One snapshot, through one prompt
  contract, with one stateless request per slot and no tools. The
  snapshot's identity is the provider's label rather than an attestation.
- **One exposed site.** l070 had been visible to the provider before;
  the sensitivities above bound its effect.
- **Money.** The cost is an estimate from provider-reported usage, not
  a bill.
- **Scans.** They cover the experiment's published records, not the
  whole repository.
- **Amendments.** The evaluation was amended twice after collection, as
  described.
- **Consumption.** "Consumed" carries R6's meaning, which is weaker than
  "the certificate alone closed it". The stronger meaning is established
  for 24 of the 48 proofs, [as above](#what-consumed-means).

## Proposal is not the hard part

The case for putting search behind a boundary never rested on the
searcher being trustworthy. R6 shows something narrower: on real goals,
a model that is trusted with nothing can still be measured, and on
these goals it returned a valid certificate every time it was asked for
one that could exist. What decided coverage was the
machinery on either side of it: which goals could be posed, and which
certificates a closer could turn into proofs. That is where the next
work is.

The other half of the problem is the one
[VerInf](/essays/verified-inference/) works on. The policy for this
experiment records, correctly, that nothing attests which model produced
these witnesses. For Proof Broker nothing needs to, because every
witness was checked on its own terms. A claim about the model itself
would need exactly that attestation. Both projects are the same
discipline pointed at different claims: check the claim without trusting
its author, and say plainly what you changed along the way.

::: {.work-entry-links}
[R6 synthesis](https://github.com/levineuwirth/proof-broker/blob/main/experiments/r6/R6-SYNTHESIS.md) ·
[Qualification 1](https://github.com/levineuwirth/proof-broker/blob/fc9c011c2379c8656ecb4f034d58e8a1d586d8c1/experiments/r6/R6-QUALIFICATION-1.md) ·
[Its addendum: the audit](https://github.com/levineuwirth/proof-broker/blob/fc9c011c2379c8656ecb4f034d58e8a1d586d8c1/experiments/r6/R6-QUALIFICATION-1-ADDENDUM-1.md) ·
[Release: R6](https://github.com/levineuwirth/proof-broker/releases/tag/r6) ·
[Code](https://github.com/levineuwirth/proof-broker) ·
[Architecture essay](/essays/proof-broker/)
:::
