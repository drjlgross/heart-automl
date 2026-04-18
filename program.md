# program.md — heart-automl loop #1

## Goal

Improve `challenge_metric = (sensitivity + specificity) / 2` on held-out validation folder `training-e` for the PhysioNet 2016 heart sound classification task (normal vs abnormal). Train on folders a, b, c, d, f. Folder e is validation-only: its labels must not influence any CONFIG choice, architecture choice, or preprocessing decision. Never mix it into training.

This is loop #1 of a two-loop design. Loop #1 is exploration: sample the action space broadly to surface which dimensions matter. Loop #2 (authored separately after reviewing loop #1 results) will concentrate on the regions loop #1 identifies as promising.

## What is known

Baseline (experiment #3, 5 epochs, default CONFIG):
- metric 0.4657
- sensitivity 0.082
- specificity 0.847
- runtime 98s on the pod

Prior 10-epoch run (experiment #1):
- metric 0.3645
- sensitivity 0.448
- specificity 0.281

Training data (folders a, b, c, d, f): 1099 recordings total, 482 abnormal / 617 normal (43.9% abnormal).

PhysioNet 2016 recordings range from approximately 5s to 120s in length.

The seed (42) is fixed and must not be modified. Fixed-seed reproducibility is the assumption that makes inter-run metric comparisons meaningful. A seed change invalidates all prior results as a point of comparison.

Parameter knobs in CONFIG are not independent. A result from any single run is conditional on the rest of CONFIG at that moment; changing one knob may shift the effective optimum of others. Loop #1 is not attempting to isolate individual effects — controlled sweeps with all other variables held fixed are a loop #2 problem. The agent should keep coupling in mind when interpreting prior results, but loop #1 exploration proceeds without any attempt to control for it.

## Action space

All knobs live in the `CONFIG` dict at the top of `classify.py`. Loop #1 categories and their knobs:

- **threshold**: `decision_threshold`
- **class_weight**: `pos_weight_mode` (auto_train / none / manual), `pos_weight_manual`
- **preprocessing**: `clip_seconds`, `n_mels`, `win_ms`, `hop_ms`, `f_min`, `f_max`
- **architecture**: `conv_channels`, `kernel_size`
- **training**: `epochs`, `batch_size`, `lr`

The `other` category exists as an escape hatch for changes that don't fit. Do not use it as a default. If a change can be cleanly categorized as one of the five above, categorize it that way.

## Loop #1 exploration discipline

**Uniform prior across categories.** Loop #1's goal is coverage, not optimization. The agent must not concentrate on a single category based on early results.

**Hard sampling floor:** Until every category (threshold, class_weight, preprocessing, architecture, training) has accumulated at least 5 runs (kept or discarded, tracked via results/*.json), no category may exceed 2x the run count of the least-sampled category. This rule is non-negotiable and takes precedence over the agent's judgment about which experiments look promising.

**Read before proposing.** Before each proposal, the agent must scan results/*.json to understand what has already been tried. Proposals must reason from prior results, not be made in isolation. Do not repeat a near-identical configuration that has already been run.

## Proposal format

Each proposed experiment must state:

1. **Hypothesis**: what this run tests, in one sentence. This is written into the `hypothesis` field of the results JSON.
2. **Category**: one of threshold / class_weight / preprocessing / architecture / training / other.
3. **Change**: the specific CONFIG diff.
4. **Expected runtime**: approximate seconds. State the reasoning if it differs materially from the ~100s baseline.

## Runtime and budget

The pod sustains ~100s per 5-epoch run. Overnight budget is roughly 8 hours. Coverage of the action space is what creates value; runtime is the constraint that limits coverage. The goal is not "more runs" — trivial variations that pad the count are actively harmful. The goal is to use the available runtime to test as many genuinely distinct hypotheses as possible.

- Proposed runtime over 200s requires the justification to explicitly name (a) the expected metric gain and (b) why a cheaper experiment can't test the same hypothesis.
- When two proposals test equally distinct hypotheses, prefer the cheaper one.
- Do not bundle unrelated variations into a single expensive run. Serialize them — the second run becomes a separate data point that sharpens analysis later.
- Actual runtime is logged automatically in each results JSON.

## Commit discipline

`classify.py` writes the results JSON atomically at the end of each run, including the `kept` field (true if this run's metric exceeds the prior best).

- If `kept: true`: commit `classify.py` with the template below, then push.
- If `kept: false`: revert `classify.py` to the prior best config via `git checkout -- classify.py`. The results JSON remains in results/ as a record of the failed experiment. Do not commit.

Commit message template:

```
[<category>] <one-line change_description>

metric: <prev> → <new> (<signed delta>)
sens: <prev> → <new> | spec: <prev> → <new>
runtime: <seconds>s | exp #<n>
```

The category and description in the commit message must match the `change_category` and `change_description` fields the agent wrote into classify.py for this run.

## Out of scope for loop #1

- Segmentation (Springer HMM or otherwise) — deferred to loop #2.
- Augmentation (time shift, SpecAugment, noise injection) — deferred.
- Ensembling — not in scope for this project.
- Full architecture replacement (transformers, pretrained audio models) — not in scope.
- Modifying the validation folder, metric definition, train/val split, or seed — never.
