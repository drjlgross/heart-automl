# program_loop2.md — heart-automl loop #2

---

**STATUS: Active.** This is the current authoritative direction for the autoresearch loop. The rules in this document govern all experiments numbered #42 onward.

Prior-loop direction documents (`program_loop1.md` and any future archived `program_loop<N>.md` files) are **historical reference only**. Their rules do not apply to current work. They are preserved in the repository to document the project's methodological evolution, not to be re-read as operational guidance.

If any rule in this document conflicts with a rule in an earlier program_loop file, this document wins without exception.

---

## Goal

Improve `challenge_metric = (sensitivity + specificity) / 2` on held-out validation folder `training-e`, continuing from loop 1. Train on folders a, b, c, d, f. Folder e is validation-only; its labels must not influence any CONFIG choice, architecture choice, preprocessing decision, or post-training composition.

Loop 1 ran 41 experiments over ~5 hours of autonomous execution, producing three scientific wins that compose into the current baseline (exp #37, metric 0.4910). Loop 2 is the informed-autonomy phase: the agent operates with the earned priors from loop 1's 41 runs as context, pursues whatever approaches it judges will further improve the metric, and runs for up to 24 hours. The uniform-sampling discipline of loop 1 is replaced with agent judgment shaped by loop 1's evidence.

## Design: three tiers of rules

Loop 2 is a carefully-bounded freedom. The boundaries are organized into three tiers, each with a distinct role.

**Tier 1 — hard invariants.** Rules that must not change during loop 2 because changing them would invalidate loop 1 data, break the loop's scientific record, or destroy the reproducibility assumption that makes inter-run comparison meaningful. Tier 1 items are auto-rejected if a proposal would modify them; an escalation protocol handles the rare case where a finding genuinely seems to require a tier 1 change.

**Tier 2 — methodological rules.** Rules that define how the loop operates — kept criterion, degeneracy guard, session budget, proposal format. These can evolve between loops with explicit decision-making, but are fixed for the duration of a given loop so the data from that loop remains internally comparable. They're mutable across loops, stable within a loop.

**Tier 3 — scientific direction.** Context, observations, and framing that inform the agent's search without constraining it. Tier 3 is earned priors from loop 1 plus the problem space as we currently understand it. It is explicitly not a prescription. The agent is expected to read tier 3 carefully, draw its own conclusions, and pursue whatever directions it judges productive.

The tiered structure exists because loop 1 taught us that useful guidance has different degrees of firmness. Some things must never change (seed, val folder, metric). Some things should change only deliberately (when and how to reject degenerate runs). Some things should evolve run-by-run inside the agent's head (which category to probe next, when to try ensembling, when to give up on a promising-looking lever). Collapsing these into a single flat rule set would either over-constrain the good decisions or under-constrain the dangerous ones. The tiers keep the right things rigid and the right things fluid.

---

## Tier 1: Hard invariants (do not change during loop 2)

Changes to any of these would invalidate loop 1 data or break the integrity of the loop's scientific record. Proposals that would modify these are auto-rejected; if a finding appears to require a tier 1 change, stop and surface it rather than proposing (see escalation protocol below).

- **seed = 42** — reproducibility against all prior runs.

- **val folder = training-e; train folders = training-a, b, c, d, f** — split integrity. Validation labels may only be read inside `evaluate()`.

- **no val-derived information in training** — no CONFIG option or code path may use training-e labels *or statistics derived from training-e labels* (class prior, per-sample predictions, confusion matrix counts, or any function of these) to shape class weighting, threshold selection, loss weighting, early stopping, model selection, or training-time augmentation. Validation labels may only be read inside `evaluate()` to compute the reported metric. The confusion matrix produced by `evaluate()` is visible in results JSONs and in the agent's reading of prior results; this is accepted, but using that visible information as a training-time prior is contamination.

- **challenge metric = (sens + spec) / 2** — comparability with loop 1. May be reconsidered in loop 3; not during loop 2.

- **data source: PhysioNet 2016 training-a..f only** — no external data added, no synthetic labels. Augmentation that only modifies existing samples is permitted (tier 3); augmentation that creates new labeled examples is not.

- **degeneracy-guard principle** — any run whose confusion matrix shows a trivial one-class predictor signature is kept=False regardless of metric. The signature is any of: a zero row or column (tp+fn=0, tn+fp=0, tp+fp=0, or tn+fn=0), or sens<ε, or spec<ε, or tp+fp below a small fraction of N_val, or tn+fn below the same fraction. Rationale: the challenge metric has a known failure mode at 0.500 for one-class predictors, exposed by exp #7. Specific thresholds (ε=0.02, floor=5% of N_val) are tier 2 and may tighten. The principle that a degenerate run cannot be kept is tier 1.

- **no branch switching on the pod during the loop** — Day 3 recovery rule. A `git checkout <branch>` on the pod deleted force-added result JSONs from the working directory because they weren't tracked on the target branch. All snapshotting via sibling clones to `/tmp` or separate repositories, never via branch switches on the loop-active repo.

- **results JSON schema is append-only during a loop** — new fields may be added; existing fields may not be removed or redefined. Rationale: removing or redefining fields makes prior JSONs unparseable by loop-2 analysis tooling and breaks comparability. Additions are safe; subtractions and redefinitions are not.

- **experiment_num = max(prior) + 1** — counter never resets, is robust to missing JSONs, and is computed from the set of JSONs present in `results/` at run start. Loop 2's first experiment is #42.

- **auto-push every JSON (kept=True and kept=False alike)** — patch 2 behavior. Rationale: the #11–#15 data loss event happened because JSONs weren't pushed. If loop 2 removes auto-push and a pod resets, the failure mode recurs.

- **no force-push to main** — preserves every pushed JSON as a recoverable checkpoint on origin. `git add -f` (force past `.gitignore`) is fine and expected; `git push --force` is not.

- **no blanket git-scope approvals for the autonomous agent** — approval scopes must be narrow and explicit (e.g., `Bash(git checkout -- classify.py)`, not `Bash(git *)`). Rationale: the Day 3 autonomous-mode failure was enabled by blanket `Bash(git *)` approval, which permitted branch-switching commands that deleted result JSONs. The specific four-pattern allowlist in use (add, commit, push, checkout -- classify.py, status, log, diff) is tier 2 and may evolve; the principle that every git operation is explicitly enumerated is tier 1.

### Escalation protocol (if a tier 1 change seems necessary)

If a proposed change would touch any tier 1 invariant, stop and produce a message for the human containing:

(a) the finding or situation that seems to call for the change
(b) which tier 1 item would be affected and how
(c) what you would propose if you could
(d) what you'll do instead while waiting

Do not implement any part of the proposed change. Continue working on experiments that don't touch the flagged invariant; do not halt the loop entirely.

### Note on the limits of the contamination rule

The confusion matrix is present in every results JSON, and loop 2 requires the agent to read prior results to propose informed experiments (tier 2). This means aggregate validation statistics — class counts, approximate class prior — are inherently visible to the agent through normal operation of the loop. The rule above prevents explicit use of these statistics in training-time decisions or in hypothesis justifications; it cannot prevent implicit shaping of agent judgment by visible information. This limitation is acknowledged rather than hidden. The discipline is: see the numbers if you must, but do not use them to shape training choices or cite them as justification.

---

## Tier 2: Methodological rules

These rules are fixed for loop 2. They can evolve between loops; they do not evolve during loop 2.

### Kept criterion (unchanged from loop 1)

A run is kept=True if and only if its metric strictly improves on `prev_best` (among non-degenerate prior runs) AND it does not trigger the degeneracy guard. The `kept` flag is a data field used to reconstruct the metric trajectory across the loop; it is not a judgment of scientific value.

Loop 2 differs from loop 1 in how the agent should *use* non-kept runs. In loop 1, discarded runs were scientific noise to be characterized. In loop 2, runs that shift sens or spec substantially without improving metric ("almost worked" runs) are directional signal — they tell you what moves a lever, even if the lever didn't close the gap. The agent should maintain awareness of these runs when proposing subsequent experiments, reference them in the `hypothesis` field when relevant, and factor them into search direction. This is a discipline in the agent's reasoning, not a change in the schema. The `kept` flag remains strict.

### Degeneracy guard (inherited from loop 1 v1.2)

A run is kept=False regardless of metric if its confusion matrix shows a trivial one-class predictor signature: any zero row or column, or sens<0.02, or spec<0.02, or tp+fp < 5% of N_val, or tn+fn < 5% of N_val. This is a hard structural check on the run itself.

Runs that pass the guard but sit in a "near-degenerate" zone (predictions heavily skewed toward one class, high coupling ratios) are *not* rejected — the agent should reason about whether such results represent signal or a near-cheating artifact in the `hypothesis` field of subsequent related proposals.

### Session runtime budget (guidance, not rule)

Loop 2 has a ~24-hour runtime budget on the pod. At ~180s/run average observed in loop 1 this would support ~400 small runs, but loop 2 is expected to include larger swings (segmentation integration, joint-axis moves, corridor-escape experiments) that may take significantly longer individually. The agent should factor expected runtime into proposal decisions — a run projected at 10× baseline runtime is a bigger budget commitment and should correspondingly test a bigger hypothesis. Voluntary stopping when the landscape feels characterized (as in loop 1) is preferred over budget exhaustion. If the agent reaches a natural stopping point well before budget exhaustion, it should stop and write a session capstone rather than filling remaining time with lower-value runs.

### Pre-proposal reading and citation (new in loop 2)

Before proposing each experiment, the agent reads all JSONs in `results/` and reviews the running metric trajectory. Proposals cite at least one prior run in the `hypothesis` field when the proposal builds on, responds to, or tests a finding from that run. "The baseline" is never a sufficient citation — specific experiment numbers and their observed effects are expected.

### `interactions_noticed` — mechanical, computed by classify.py (new in loop 2)

The field is populated automatically from confusion matrix deltas against `prev_best`. Current rule: flag `"threshold"` when `|Δsens| + |Δspec| > 3·|Δmetric|`, indicating the run moved along the sens/spec frontier rather than improving discrimination. Empty `[]` when there is no prev_best (first run) or no prior to compare against. The agent does not populate this field and should not propose changes to its values post-run. Additional rules may be added between loops if new coupling patterns emerge; rule changes require program.md v3.

**Historical note:** `interactions_noticed` was populated by agent interpretation in loop 1 runs (#1–#41). Starting loop 2 (#42+), the field is computed mechanically by classify.py. Analysis tooling that joins across loops should treat the field as loop-scoped — loop 1 values reflect agent judgment, loop 2 values reflect a deterministic rule.

---

## Tier 3: Scientific direction

### Note on enumeration

Lists in this section (routes to improving the metric, category-level observations, parameter space expansions) describe what loop 1's 41 runs made visible. They are not exhaustive and not prescriptive. The agent may pursue approaches, categories, hypotheses, or knobs not enumerated here, provided its reasoning is explicit in the `hypothesis` field and the work does not violate tier 1 invariants or tier 2 rules. Under-enumeration is a bound on our knowledge, not a bound on the search.

### Working baseline

Loop 2 starts from exp #37 (threshold=0.3, kernel_size=7, clip_seconds=3, metric 0.4910, sens 0.765, spec 0.217). This is the composed result of loop 1's three scientific wins: exp #6 (threshold), exp #23 (kernel_size), exp #37 (clip length). Every other CONFIG value remains at loop 1 defaults unless otherwise changed.

**Open question about the baseline.** Loop 1 surfaced a specific concern about whether exp #6 — the first of the three wins and the anchor the other two built on — represents a stable optimum or a narrow ridge. Every perturbation of exp #6's config in loop 1 regressed sharply; a robust optimum should show local stability to small perturbations in multiple directions. The composed #37 baseline may inherit this instability. The agent should address this question explicitly in its first few run hypotheses — whether by probing stability directly, by designing moves that are robust to baseline instability, or by explicitly deferring the question with a stated reason. Ignoring the question silently is the failure mode to avoid.

### The sens/spec landscape

Loop 1's scatter plot showed most runs clustering along a corridor where sens + spec is approximately constant. The three scientific wins (#6, #23, #37) appear to sit slightly above this corridor; the wins suggest the corridor is not a hard ceiling, though how much headroom exists is unknown. Several distinct routes to improving the metric exist, not all of which require moving off the corridor:

- *Moving along the corridor to a better operating point.* The current best (#37) sits on the high-sensitivity, low-specificity side. If the corridor is subtly non-flat, small improvements are available from repositioning.

- *Shifting the corridor upward.* A more discriminative model has a corridor at a higher sens+spec level. Architecture, representation, and training changes are the usual levers.

- *Reducing run-to-run variance.* If training instability at 5 epochs makes individual runs noisy relative to true performance, stability improvements (longer training, different optimizer, better initialization) can lift expected metric without changing the underlying discrimination.

- *Preprocessing that changes what the model sees.* Segmentation (e.g., Springer HMM into S1/systole/S2/diastole), band-pass filtering at specific cardiac frequency bands, or other representation-reshaping moves could lift performance by changing the problem structure rather than fitting harder to the existing structure.

- *Addressing potential train/val distribution mismatch.* The training set is a folder mixture with per-folder abnormal rates ranging from 21% to 77% (aggregate 43.9%); `pos_weight` computed as a single number over the aggregate treats a heterogeneous training distribution as if it were homogeneous. The validation folder's class distribution is visible indirectly through confusion matrices in prior results, but using it as a training-time prior is val-derived contamination and is forbidden. Loop 1's `auto_val_prior` option did exactly this and was removed. A methodologically honest replacement — estimating deployment-time class prior from a held-out slice of *training* folders — is a real lever. Per-folder class weighting and folder-ablation studies are other levers that don't require val-derived information.

- *Ensembling across runs.* Averaging soft outputs from multiple trained models (same config different seeds, or different configs jointly exploring the landscape) is a direct variance-reduction move and also a way to compose loop 1's wins. Top teams on this dataset all used ensembles. Integration requires either extending classify.py to train N models per run or adding a separate ensemble-evaluation path that reads prior saved model states. Either is a real code move but well within loop 2's scope.

**Observed mechanism — the "positive saturation corridor":** At threshold=0.3, soft outputs sit near the decision boundary. Perturbations that shift output distributions rightward push soft outputs past the threshold and collapse specificity. Loop 1 observed this pattern repeatedly (#8, #9, #10, #14). This is a feature of the current operating regime, not a bug. Awareness of this mechanism is useful when interpreting run results and when designing experiments that are robust to it.

### Category-level observations from loop 1

- **threshold:** Produced one scientific win (#6, 0.5 → 0.3). Subsequent sweeps (#15, #18, #34, #38) were flat within noise — values 0.2 through 0.5 all land within ~0.01 metric of each other at the pre-#23 baseline. Threshold is also a cross-cutting knob: any change that shifts output distributions produces a threshold-conditioned response, and loop 1 repeatedly observed this (`interactions_noticed=["threshold"]` in many runs).

- **class_weight:** No scientific wins. `pos_weight=1.0` produced results nearly identical to `auto_train`'s 1.28 (#12); `pos_weight=3.0` produced complete degenerate collapse (#7). Loop 1 did not test the narrow 1.5–2.5 range at varied thresholds or at the composed baseline. Whether class weighting is actually weak or whether the loop 1 sampling missed a coupling-dependent sweet spot is unresolved.

- **preprocessing:** Produced one scientific win (#37, clip_seconds 5 → 3). Also surfaced discriminative signal in the 500–1000 Hz band (#13: removing it cost 0.077 metric, more than expected given the clinical prior that heart sound fundamentals are <300 Hz). Springer HMM segmentation, band-pass variations, alternate spectrogram parameterizations, and augmentation remain untested in loop 1.

- **architecture:** Produced one scientific win (#23, kernel_size 3 → 7). Loop 1 observations at the pre-#23 baseline suggested a non-monotonic sweet spot at k=7 (k=3 stable, k=5 corridor, k=7 peak, k=9 corridor) and a capacity V-shape (23k and 1.1M params degenerate, 283k is the sweet spot at k=7). Whether these hold at the composed baseline is an open question. Larger structural moves remain untested.

- **training:** No scientific wins. Epoch sweeps (#9: 5→10) and learning-rate sweeps (#11: 1e-3 → 3e-4) coupled with threshold. Batch size 32 vs 64 (#16) regressed. Loop 1 observed that baseline runs at 5 epochs vs 10 epochs produce qualitatively different prediction regimes. This category intersects with the baseline-stability question.

- **other:** The four runs in this category were schema baselines and data re-validation, not scientific experiments. Bookkeeping bucket for infrastructure moves.

### Exploration vs. exploitation

Loop 2's 24-hour budget permits both focused exploitation (refining around the composed baseline, probing stability, testing small variants of loop 1's wins) and broad exploration (new representations, structural moves, novel approaches). Greedy optimization — collapsing onto the most immediately promising region — risks getting stuck in local optima and has a specific known failure mode in this setting: the "positive saturation corridor" where aggressive moves produce degenerate one-class predictors. Some mix of exploitation and exploration will produce better final metric than either extreme. The mix itself is the agent's judgment call.

### Parameter space expansions available in loop 2

Loop 2 may extend `CONFIG` in classify.py to expose new knobs. Any new knob needs: (a) a default value preserving current behavior (so existing runs remain reproducible), (b) plumbing into the relevant code path, (c) inclusion in `preproc_cache_tag()` if it affects spectrogram computation (otherwise stale-cache risk), and (d) a hypothesis citing the motivation. Expansions the scratchpad and loop 1 findings flagged as candidates:

- **Segmentation.** Springer HMM segmentation into S1/systole/S2/diastole before feature extraction. Most 2016 Challenge top finishers used this. Integration: add `use_segmentation` (bool) and `segmentation_method` (str) to CONFIG; either find a Python port of Springer's MATLAB code or reimplement.

- **Augmentation.** Time shift, Gaussian noise, SpecAugment frequency/time masks. Integration: add augmentation params to CONFIG; apply in the training data loader only, never to val. Each augmentation is a separate CONFIG flag or set of params.

- **Optimizer choice.** Currently Adam-only. Integration: add `optimizer` (enum: "adam", "adamw", "sgd_momentum") plus optimizer-specific params (momentum, weight_decay).

- **Per-folder class weighting.** Loop 1's `auto_train` pos_weight computed a single number over the folder mixture. Integration: add `pos_weight_mode="per_folder"` that computes weights within each folder's training contribution rather than globally.

- **Honest val-prior estimator.** Replacement for the removed `auto_val_prior`. Hold out some slice of training folders as a proxy for deployment-time prior; specifics of how to carve and cache the hold-out are the agent's choice. Integration: new CONFIG option `pos_weight_mode="held_out_train_prior"` plus logic to carve and cache the hold-out slice.

- **Corridor-escape training modifications.** Gradient clipping (`grad_clip_norm`), output regularization (label smoothing via `label_smoothing`), different output activations (e.g., temperature-scaled sigmoid via `output_temperature`). Each is a separate CONFIG knob.

- **Ensemble-at-inference.** Train multiple models per config (varied seeds) and average soft outputs. Integration path A: extend classify.py to train N models per run and produce one JSON with the ensemble result. Integration path B: add a separate `ensemble.py` that reads saved model states from prior runs and produces an ensemble-evaluation JSON. Constraint: individual model selection or weighting for an ensemble may not use val performance of the individual models. Selection/weighting must use only training-side information (train loss, cross-validation on held-out training folders, or uniform averaging). Agent's choice between paths and between selection strategies.

---

## Proposal format

Each proposed experiment must state:

1. **Hypothesis** — what this run tests, in one sentence or two. Written into the `hypothesis` field of the results JSON. Cites at least one prior run by experiment number when the proposal builds on, responds to, or tests a finding from that run.
2. **Category** — one of threshold / class_weight / preprocessing / architecture / training / other. Use `other` only as an escape hatch for changes that don't fit cleanly.
3. **Change** — the specific CONFIG diff or code change.
4. **Expected runtime** — approximate seconds. State the reasoning if it differs materially from the ~180s loop 1 average.

`interactions_noticed` is populated automatically by classify.py post-run; the agent does not propose values for this field.

## Commit discipline

`classify.py` writes the results JSON atomically at the end of each run, including the `kept` field (True if this run's metric exceeds the prior best, subject to the degeneracy guard).

- If `kept=True`: commit `classify.py` with the template below, then push.
- If `kept=False`: revert `classify.py` to the prior best config via `git checkout -- classify.py`. The results JSON remains in `results/` as a record of the experiment. Do not commit classify.py.

Commit message template:

```
[<category>] <one-line change_description>

metric: <prev> → <new> (<signed delta>)
sens: <prev> → <new> | spec: <prev> → <new>
runtime: <seconds>s | exp #<n>
```

The category and description in the commit message must match the `change_category` and `change_description` fields the agent wrote into classify.py for this run.

Results JSONs are auto-pushed to origin by `_push_result_json()` regardless of kept status (patch 2 behavior, tier 1). This is independent of the classify.py commit above.

## Out of scope for loop 2

- **Modifying tier 1 invariants** — see escalation protocol.
- **Full architecture replacement** (transformers, pretrained audio models) — engineering complexity exceeds the single-file-agent scope; loop 3 candidate.
- **External data or synthetic labels** — tier 1.
- **Val-set modification in any form** — tier 1.

Previously out of scope in loop 1 but now permitted in loop 2: segmentation, augmentation, ensembling, val-prior estimation from held-out training folders, optimizer variation, per-folder class weighting.
