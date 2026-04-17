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

## Parameter space expansions

- **Clip length.** Currently hardcoded 5s in CONFIG. Heart sound cycles have
  natural cardiac timing; 5s is arbitrary. Let agent try longer (8s, 10s) or
  shorter (3s) windows.

- **Optimizer choice.** Currently Adam-only. Could expose as a small enum
  (`"adam"`, `"adamw"`, `"sgd_momentum"`) if loop #1 doesn't close the gap.

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

---

*Last updated: Day 2 (Friday 4/17) — added epoch instability finding from
pre-loop 5-epoch validation run.*
