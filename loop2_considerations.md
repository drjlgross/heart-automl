# Loop 2 Considerations

*Running scratchpad. Ideas for program.md v2, to be weighed on Saturday against
what loop #1 actually reveals. Append freely during the week; prune on Saturday.*

---

## Empirical findings from pre-loop testing

- **Epoch instability at low-epoch regime.** Baseline is dramatically different
  at 5 vs 10 epochs (10ep: sens 0.45 / spec 0.28 / metric 0.36; 5ep: sens 0.08 /
  spec 0.85 / metric 0.46). Model is landing in fundamentally different
  prediction regimes depending on training duration — not a small gradient
  difference, but a different local mode entirely. Suggests the model is
  under-trained at 5 epochs and the loss landscape is rough in this regime.
  Worth surfacing this as an explicit observation in program.md v2: *"the
  metric surface is highly sensitive to epochs below ~10; investigate whether
  increased epochs + complementary changes (class_weight, threshold) can
  stabilize both sens and spec simultaneously."* This is also a reason to
  weight `training` category exploration in loop #1.

## Likely high-value (built on known priors)

- **Segmentation as a new knob.** Add Springer HMM segmenter as preprocessing,
  expose `use_segmentation` in CONFIG. The 2016 winners' key insight (Potes et al.
  and most top finishers used HMM segmentation into S1 / systole / S2 / diastole
  before feature extraction). Gated on loop #1 not closing the gap via simpler
  fixes. Estimated ~2-4 hr integration. Existing Python ports of Springer's
  MATLAB code likely exist — check before reimplementing.

- **Augmentation knobs.** Time shift, gaussian noise, SpecAugment freq/time masks.
  Deferred from loop #1 because baseline failure modes are class_weight / threshold /
  distribution-shift, not regularization-shaped. Reconsider if loop #1 suggests
  the model is under-regularized (e.g., large train/val gap after the easy fixes
  are made).

## Methodology / loop behavior

- **Explicit Bayesian framing in program.md v2.** Tell the agent that loop #1 was
  uniform prior across categories, and loop #2 samples from the posterior informed
  by loop #1 results. Direct exploration at the trade-off frontier identified in
  loop #1, but hold back some probability mass for continued exploration elsewhere.
  Avoid greedy MAP collapse onto a single promising region.

- **"Almost worked" run analysis.** Filter loop #1 runs where sens OR spec improved
  substantially but the paired metric regressed enough to discard the run. These
  are highest-signal points for program.md v2 — they identify which *levers move
  what direction*, independent of whether the run was kept. Write a Claude Code
  analysis prompt to surface these as part of Saturday morning review.

- **Agent-side meta-reasoning (lighter version of autonomous rewriting).** Tell
  the agent in program.md v2 to read prior results before proposing each run, and
  preferentially propose changes in under-explored regions or near-threshold
  "almost wins." Stops short of autonomous program.md rewriting (which would
  obscure the human contribution in the demo). Worth trying only if loop #1 ran
  cleanly.

- **Mechanical vs interpretive `interactions_noticed`.** Loop #1 has the agent
  set this field post-hoc by reading sens/spec/metric and deciding whether the
  run looks like a known pattern (threshold coupling) or something new. Upside:
  nuance — the agent can flag genuinely novel dynamics (e.g., exp #15's
  symmetric sens/spec trade that did NOT look like the coupling, just a clean
  threshold sweep). Downside: pattern-matching bias (exp #14 got pre-filled
  with `["threshold"]` before the numbers were read), and the field's meaning
  drifts if interpretation norms evolve mid-loop. Loop #2 should consider
  replacing agent-interpretation with a mechanical rule: compute
  `interactions_noticed` directly from confusion-matrix deltas against
  prev_best. E.g., flag `"threshold"` when the sens/spec trade is large but
  near-metric-neutral — specifically `|Δsens| + |Δspec| > k·|Δmetric|` for some
  k (3 is a reasonable starting point) — indicating the model moved along the
  sens/spec frontier rather than improving discrimination. Reliably comparable
  across runs at the cost of losing interpretive nuance. Core question to
  settle before loop #2: is this field for cross-run comparison (→ mechanical)
  or for narrative/science-process signal (→ interpretive)?

- **Threshold as a cross-cutting coupling — pair it with each category.** Loop #1
  observed (exps #8, #9, #10) that every category-change made from the exp #6
  best — preprocessing (clip_seconds↑), training (epochs↑), and architecture
  (kernel_size↑) — produced the same sens-up / spec-collapse pattern. Three
  consecutive `interactions_noticed=["threshold"]` entries. The 0.3 decision
  threshold is aggressive enough that any change shifting the output
  distribution toward higher probabilities gets amplified into a spec collapse,
  so knob effects are hard to read in isolation. Loop #2 should consider pairing
  each category exploration with a threshold sweep — e.g., evaluate each
  candidate config at threshold ∈ {0.3, 0.4, 0.5} — so a knob's effect can be
  read at multiple operating points rather than conditioned on one threshold
  that distorts every other axis. Also worth investigating whether exp #6's
  metric was itself a happy accident of undertrained weights meeting a low
  threshold (no stable non-degenerate neighbor has yet been found).

## Parameter space expansions

- **Clip length.** Currently hardcoded 5s in CONFIG. Heart sound cycles have
  natural cardiac timing; 5s is arbitrary. Let agent try longer (8s, 10s) or
  shorter (3s) windows.

- **Optimizer choice.** Currently Adam-only. Could expose as a small enum
  (`"adam"`, `"adamw"`, `"sgd_momentum"`) if loop #1 doesn't close the gap.

- **Training set heterogeneity.** Training is a five-folder mixture with highly variable per-folder class distributions (training-a 71% abnormal, training-b 21%, training-c 77%, training-d 51%, training-f 30%; aggregate 43.9% abnormal across 1099 recordings). The `auto_train` pos_weight treats this as a single homogeneous distribution, weighting against a fiction. Worth exploring in loop #2: per-folder class weighting, or training-folder ablation to identify which folders contribute most to val generalization.

## Speed / compute considerations

- **Per-run runtime budget.** If loop #1 shows individual runs creeping past a
  threshold on RunPod, program.md v2 should explicitly penalize changes that
  balloon runtime. Calibrate budget against actual cold/warm start timing on
  RunPod once loop #1 is underway.

- **Smaller-model starting point as a speed lever.** `conv_channels` currently
  starts at `(24, 48, 96)` (~52k params). Reducing to `(16, 32, 64)` (~23k
  params) would roughly halve per-run training time again. Not used for loop #1
  because pairing too many starting-point changes at once risks muddying the
  signal. If loop #2 needs more runs per hour than epochs=5 alone provides, this
  is the next lever. Agent can already scale channels up/down via the
  `architecture` category, so changing the default is purely a speed move, not a
  capability restriction.

## Out of scope / parked

- **Ensembling.** Top 2016 teams all used ensembles. But ensembling is a post-hoc
  composition move, not a single-run iteration move — doesn't fit the autoresearch
  paradigm cleanly. Skip for this project.

- **Full architecture replacement.** Swapping the CNN entirely (e.g., for a
  transformer or a pretrained audio model). Too big a swing for an agent
  operating on a single file, and unlikely to beat a well-tuned CNN on this
  data size. Skip.

  - **Honest val-prior estimator (replacement for removed `auto_val_prior`).** The original `auto_val_prior` option computed pos_weight from validation set labels, which leaked target information and invalidated the held-out test. Removed before loop #1 launch. A methodologically honest version would carve a third held-out split from the training folders and use its class distribution as a proxy for val-time prior — letting the model train against an estimate of the deployment distribution without ever touching actual val labels. Worth building in loop #2 if distribution-shift handling emerges as a dominant lever in loop #1 results.


*Last updated: Day 3 (Sun 4/19) — added threshold-coupling observation, mechanical-vs-interpretive question on `interactions_noticed`, and Day 3 loop execution findings.*

mechanical-vs-interpretive question on `interactions_noticed`.*
=======


## Findings and directions surfaced during loop #1 execution (Day 3)

*Appended during live loop #1 execution on Saturday 4/18. Every item below is
traceable to a specific run or decision from today's session. Organized by
theme, not by chronology. Saturday review (tomorrow? later?) should weigh these
against loop #1's actual results and against the preexisting ideas above.*

### Findings about the parameter space

**Threshold is exhausted as a lever in the current architecture+data regime.**
(Exps #6, #15.) Threshold 0.5→0.3 produced the only kept run of the loop
(metric +0.007). Threshold 0.3→0.4 was flat within noise. With prior metrics at
0.5/0.4/0.3 all within 0.007, the ROC curve near the operating point is
effectively flat. Further metric gains require moving the entire ROC curve up —
i.e., changing the model's discriminative capacity — not tuning binarization.
Loop #2 should deprioritize standalone threshold sweeps and treat threshold as
a control to co-tune alongside other knobs.

**The "positive saturation corridor" is a named phenomenon.** (Exps #7, #8, #9,
#10, #11, #14.) Many perturbations of the current best config land the model
in a regime where it predicts positive on nearly all inputs. The common thread
across these runs is that any change shifting the output distribution
rightward — longer clips, wider kernels, more epochs, smaller model, heavier
class weighting — pushes soft outputs past the aggressive 0.3 threshold and
collapses specificity. This isn't a bug in the model; it's a real feature of
the loss landscape at threshold=0.3 with this data. Loop #2 should include
experiments explicitly designed to *escape* this corridor: gradient clipping,
output regularization, label smoothing, different output activations, or
simply running more epochs to see whether the corridor is a transient or a
true attractor.

**Threshold coupling activates on output-distribution magnitude, not on
arbitrary perturbations.** (Exp #12 vs. exps #8/9/10/11.) Small perturbations
that don't meaningfully shift the output distribution (e.g., pos_weight
1.28→1.0) pass cleanly with no coupling triggered. Only perturbations
substantial enough to move the distribution trigger the collapse. Loop #2
should characterize this threshold magnitude explicitly — e.g., by running
dose-response sweeps of pos_weight, lr, and epochs to identify the perturbation
magnitude at which coupling activates. This is the shape of an inducible-vs-
constitutive response study from signal transduction biology.

**Class weighting is a weak lever in the current regime.** (Exp #12.) Removing
auto_train's ~1.28 upweight cost 0.003 metric. Dropping pos_weight=none
produced essentially identical results to exp #6's baseline. The auto_train
heuristic was noise-level. Aggressive weighting (exp #7's 3.0) destroys the
model. There's a narrow band between "no effect" and "degenerate" where
class weighting might matter, but loop #1 saw no evidence of it. Loop #2
should only revisit class weighting in combination with other interventions
(e.g., threshold=0.5 with varied pos_weight), not as a standalone axis.

**High-frequency content (500–1000 Hz) carries some discriminative signal.**
(Exp #13.) Lowering f_max from 1000 to 500 Hz cost ~0.077 metric with mild
coupling. Clinical prior says heart-sound fundamentals are <300 Hz and murmurs
extend to ~400 Hz, so this band should be mostly noise — but removing it
hurt. Loop #2 should investigate whether this reflects real discriminative
signal (unexpected) or whether the model had learned to use high-frequency
content as a noise-conditioned feature (possible). Worth testing: does a
500 Hz model recover if given more epochs? Does a band-pass filter at
25–400 Hz do better than 25–500 Hz? This is also a strong argument for
Springer HMM segmentation (see Out of scope above) — phase-specific spectral
analysis might isolate which band matters in which cardiac phase.

**Smaller models collapse faster, not slower.** (Exp #14.) Reducing
conv_channels from (24,48,96) to (16,32,64) produced full saturation
(sens=1.0, spec=0.004) in 5 epochs, worse than the baseline. Conventional
underfitting/overfitting intuition suggests smaller models should underfit
(lower sens, higher spec) — the opposite of what happened. Hypothesis: the
trivial "always positive" solution is the nearest loss minimum for small
models with imbalanced data, and smaller capacity = less ability to escape
the trivial minimum. Loop #2 should test this directly: explicit parameter-
count sweep at fixed architecture shape, potentially with more epochs per
config so each one gets a chance to actually converge before being compared.

**The 5-epoch baseline may not be a stable optimum.** (Exps #6, #8, #9, #10,
#11 combined.) Every perturbation of exp #6's config by any other knob has
regressed, often sharply. A robust optimum should be locally stable to small
perturbations in multiple directions; exp #6 isn't. The implication is that
exp #6's 0.4725 may reflect an undertrained model that happens to combine with
threshold=0.3 to produce acceptable numbers, not a genuinely learned solution
the loop should anchor to. Loop #2 should consider whether the "best" anchor
needs to be recomputed after a longer-epoch sweep — not because exp #6 is
wrong, but because its stability is suspect.

### Findings about methodology

**`interactions_noticed` schema should probably be mechanized.** (CLAUDE.md
update from Day 3.) The field is currently populated by agent judgment during
post-run interpretation. Today's session included one instance where the
agent hardcoded `["threshold"]` from recent pattern-matching rather than
reading the run's actual numbers, which had to be corrected. The correction
is durable in CLAUDE.md, but the underlying risk is structural: agent
judgment + subjective interpretation = noisy field. Loop #2 could compute
the field mechanically from confusion matrix deltas — e.g., `if (sens shifts
+>0.2) AND (spec shifts <-0.2) → flag "threshold"` — removing interpretation
ambiguity and making cross-run comparison cleaner. The agent judgment layer
could remain for human-readable prose in a separate field.

**Loop #1's kept column is the least informative byte per run.** (Observed
across #6-#15.) Only one run was kept (exp #6). Nine of fifteen runs were
either reverted or degenerate. But each of those reverted runs produced real
directional signal, refined hypotheses, or surfaced methodological issues.
Loop #2 analysis should treat the kept/not-kept distinction as orthogonal
to scientific value, which means the metric-based kept criterion isn't a
good proxy for "which runs should influence loop #2 priors." A better
grouping for analysis might be: "confirming runs" (reproduce known patterns),
"frontier runs" (produce new signal), "structural runs" (reveal coupling or
methodology gaps).

**Baseline instability is a category deserving its own experiments.** If
exp #6 is a narrow corridor rather than a robust optimum (see above), then
"resample exp #6's config under small variations" is itself a loop #2
experimental category. What happens if you run exp #6 at epochs=4? At
epochs=6? Seed=43? Batch size 24 vs 32? These are normally uninteresting
questions, but if the current best is on an unstable ridge, they'd reveal
the structure of the ridge — and potentially find a nearby config that's
more stable.

**The exp #7 degeneracy finding might deserve revisiting once capacity is
understood.** v1.2 correctly quarantined the degenerate run from baseline
comparisons, but the specific phenomenon — "3.0 pos_weight collapses the
model entirely" — only tells us that threshold=0.3 + pos_weight=3.0 is
jointly pathological. Loop #2 could test pos_weight in the 1.5-2.5 range
at threshold=0.5 as a control, or pos_weight=3.0 at threshold=0.5 to see
whether aggressive weighting is always bad or only bad when compounded
with aggressive threshold. This is a coupling question, not a
class-weight-is-useless conclusion.

### Framing and discipline for program.md v2

**Loop #2 sampling framing should be Bayesian-posterior, not uniform
prior.** (Already in loop2 above, but the Day 3 runs make this much more
concrete.) Loop #1's uniform prior over categories gave us coverage;
loop #2 should sample preferentially from regions loop #1 identified as
promising (coupling studies, capacity+epochs joint sweeps, escape-the-
corridor experiments). But hold back some probability mass for controls
and for revisiting exp #6's stability — avoid greedy MAP collapse onto
the most obviously interesting region.

**Degeneracy guard should stay in program.md v2, and may need further
tightening.** v1.2's 5% floor caught exp #14 cleanly. But exp #8 passed
the 5% floor at pn=143 (6.7% of N_val) while still being behaviorally
near-degenerate. Loop #2 should consider whether the floor should be
calibrated against validation base rate (8.5% positive) rather than a
fixed 5%, or whether a secondary softer rule ("kept=uncertain" rather
than "kept=false") should flag the 5-10% zone for human review. Don't
change anything without more data; this is a loop #2 methodology question.

**"Almost worked" runs are where the signal is.** (General observation,
confirmed across #8-#15.) The runs that reverted by a small metric margin
but shifted sens and spec substantially are the highest-signal points.
Loop #2 should either:
(a) explicitly filter results/*.json to surface runs where |sens_delta| > 0.1
or |spec_delta| > 0.1, regardless of kept status, OR
(b) change the kept criterion entirely to reward directional informativeness,
not just metric supremacy. Option (a) is analysis-side and low-cost; option
(b) is a bigger methodology change and deserves more thought before
committing.

**Consider a separate "agent-proposed follow-ups" category in program.md v2.**
Today's agent produced several sharp follow-up hypotheses that didn't fit
cleanly into existing categories ("test pos_weight at threshold=0.5",
"epochs sweep at fixed architecture shape", "band-pass 25-400 Hz"). These
are *responses to loop #1 findings* rather than independent perturbations
from baseline. Program.md v2 could explicitly allow a "follow-up"
change_category tagged with the originating run number, making the
responsive-to-prior-finding runs explicitly different from independent
coverage runs.



# ## Evolving thoughts about program.md mutability ##

**Program.md evolves in-session — feature or bug?** (v1.0 → v1.1 → v1.2
across Day 3, plus a CLAUDE.md rule addition, all prompted by concrete
runs within a four-hour window.) Each patch responded to a specific
empirical finding that couldn't have been anticipated from static review:
exp #7's degenerate collapse revealed the kept criterion was gameable
(v1.1 zero-check); exp #9's quasi-degenerate escape revealed the zero-check
was too narrow (v1.2 5% floor); exp #14's agent shortcut revealed the
interactions_noticed schema needed explicit discipline (CLAUDE.md rule).
The rapid rule evolution could be read two ways:

*As a bug:* for a truly autonomous agent running unattended, rules that
change mid-loop mean the agent is operating under shifting criteria, and
its decisions before a patch aren't comparable to decisions after. A clean
autonomous run would require program.md to be complete and stable before
launch. We have not yet achieved that state — every autonomous flip this
session ended in either a methodological pause or a recovery event.

*As a feature:* for a human-in-the-loop autoresearch paradigm, the rapid
rule evolution is exactly the value proposition. Each patch was cheap
(minutes of agent+human time), empirically grounded (prompted by a specific
failure), and improved the substrate for every subsequent run. The
alternative — trying to anticipate all failure modes statically in v1.0 —
is the exact pre-optimization trap the "do the effing experiment" principle
was designed to avoid. The information value of each patch justified its
cost by a wide margin.

The synthesis: treat in-session program.md evolution as a feature of
*supervised* autoresearch and a bug of *unsupervised* autoresearch. Loop #2
program.md could explicitly name which rules are v2-stable (don't touch
during execution) vs. v2-mutable (can evolve in response to findings), and
require human approval for any mutation to the stable set. This makes the
human/agent partition sharper: the human is not just the scientific
director but also the guardian of which invariants hold across the loop's
lifetime. Worth sketching the stable/mutable distinction explicitly before
drafting program.md v2.



## Design Problem for loop v2 ##

**Principled three-tier rule structure for program.md v2 (design task).**
Loop #1's rule set is a historical record of which failures happened, not a
deliberately designed methodology. Program.md v2 should explicitly
distinguish: (1) hard invariants that must never change without invalidating
prior data (seed, val folder, metric, train/val split, no val-label
contamination); (2) methodological rules that can evolve with evidence but
require documented mutation ceremony (degeneracy guards, sampling floors,
commit discipline, interpretation-field rules); (3) scientific direction
that's explicitly meant to evolve run-by-run (category priorities, runtime
budgets, knob priors). The design question for each rule: what evidence
would justify changing it, and who gets to approve? Needs deliberate thought
before drafting, not accumulation by accident.
