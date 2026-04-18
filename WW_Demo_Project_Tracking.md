# WW Demo Project Tracking

Running chronological log of work completed on the Heart-AutoML project. Source material for the demo video.

---

## Day 1 — Thursday, April 16, 2026

- Locked in project concept: heart sound classification on PhysioNet 2016 dataset, optimized via an autoresearch-style autonomous loop (Claude Code edits `classify.py` → runs experiment → checks metric → keeps or discards → repeats).
- Downloaded PhysioNet 2016 Challenge dataset (~3,100 .wav files across training-a through training-f) via Kaggle after initial `wget` attempt returned competition submissions instead of training data.
- Set up project file structure: `ww_demo/heart-automl/` with `data/`, `results/`, flat hierarchy after removing the `archive/` wrapper.
- Acquired CAD Audio CX2 USB audio interface from Micro Center.
- Ordered piezo contact microphones from Amazon (2x, Saturday 4/18 delivery) after confirming compatibility with CX2.
- Consulted HacDC Hardware Hacking Night — no piezo available on-site, but biosignal-experienced members eyeballed the CX2 + piezo plan and confirmed the setup should work cleanly.
- Set up Python environment: fresh venv in project directory, Claude Code integrated and running with autonomous edit permissions.
- Wrote baseline `classify.py` end-to-end: loads .wav files, resamples to 2000 Hz, extracts mel spectrograms (64 bins, 25ms/10ms windows), caches to disk, trains a ~50K param CNN for 10 epochs, evaluates on held-out folder e, writes timestamped JSON results.
- Executed first run: baseline challenge metric = 0.36 (sens 0.45, spec 0.28). Below random, but diagnostically — model overpredicts abnormal due to class weights applied on top of a training distribution (65% abnormal) that inverts the validation distribution (20% abnormal).
- Discovered MacBook Air thermal throttling constraint: cold run 484s, warm run 1,747s. Local hardware cannot host the iteration loop at any settings
- Planned mitigation: pre-paid RunPod CPU instance ($20 credit, no auto-reload) for Friday morning.
- Mapped full-week timeline with redundancies: cloud compute fallback for Friday, HacDC Monday night as hardware troubleshooting backup, Tuesday as video/submission buffer.

---

## Day 2 — Friday, April 17, 2026

First session: infrastructure 
- Established project convention for the week: Claude chat for strategy, science, analysis decisions, and drafting Claude Code prompts; Claude Code for execution (file patches, git ops, running experiments). Wrote `CLAUDE.md` in project root encoding this as two modes (focused patches vs. autoresearch loop iteration) and locked in program.md as human-authored only.
- Extended `classify.py` schema to support downstream autoresearch-loop analysis: exposed `pos_weight_mode` (auto_train / auto_val_prior / none / manual) as a CONFIG knob to replace the hardcoded class-weight computation, and added `experiment_num`, `kept`, `prev_best`, `vs_prev_best`, `change_category`, `change_description` fields to each run's output JSON.
- Locked in a controlled vocabulary for the `change_category` field (threshold / class_weight / preprocessing / architecture / training / other) so downstream analysis can color-code trade-off maps rather than parsing free-form text.
- Cut default `epochs` from 10 to 5 as a loop #1 starting point — still agent-tunable, but halves per-run wall-clock to expand overnight exploration budget.
- Started `loop2_considerations.md` as a running scratchpad for ideas deferred from loop #1 — segmentation, augmentation knobs, smaller-model speed lever, Bayesian framing, "almost worked" run analysis.
- Set up GitHub repo (public, `drjlgross/heart-automl`) and committed Day 1 baseline JSON as the first milestone commit. Results folder gitignored by default, with selective milestone runs force-added.
- Validated the patched schema end-to-end on Mac: 5 epochs, warm-throttled, metric 0.4644 / sens 0.082 / spec 0.847 in 284s. All new JSON fields populated correctly. Second Day 2 milestone commit pushed to GitHub.
- Set up RunPod account with $20 credit loaded via a Privacy.com virtual card (merchant-locked to RunPod, $35 total cap) rather than linking a real payment method directly — one-time vendor-signup cost for a pattern that generalizes to future cloud-compute vendors.
- Deployed a CPU pod: 4 vCPU / 5 GHz / compute-optimized / 8 GB RAM / 20 GB disk at $0.14/hr. Jupyter disabled, no SSH (web terminal only), no network volume.
- Hit a Python version mismatch on the pod: Ubuntu 20.04's default `python3` points to 3.8, but `pip` was installed against 3.13 — symlinked `/usr/local/bin/python3 → /usr/bin/python3.13` so both target the same interpreter and `pip install` behavior is consistent with the Mac.
- First pod run crashed on `torchaudio.load()`: `torchaudio 2.11` delegates audio loading to a separate `torchcodec` package that isn't pulled in automatically. Didn't surface locally because the Mac has older `torchaudio`. Installed `torchcodec`, then pushed a commit adding `torchcodec>=0.11` to `requirements.txt` so future pods or contributors don't hit the same failure.
- Validated the full pipeline on the pod: 5 epochs, warm, metric 0.4657 / sens 0.082 / spec 0.849 in 98s. Functionally identical to the Mac run — fixed-seed reproducibility confirmed across OS and Python version.
- Measured real pod runtime: ~100s per 5-epoch run, warm, no thermal throttling. Implies ~290 runs in an 8-hour overnight window, ~4x better per-run than the Mac could sustain.
- Noted an unexpected epoch sensitivity while comparing the 5-epoch and 10-epoch baselines: they land in qualitatively different prediction regimes (sens 0.08 / spec 0.85 at 5 epochs vs. sens 0.45 / spec 0.28 at 10 epochs), not small gradient differences. Model is under-trained and the loss landscape is rough at low epochs. Flagged in `loop2_considerations.md` as a hypothesis for program.md v2.
- Committed the pod validation run as a third milestone on GitHub, establishing the git-log narrative as Day 1 baseline → Day 2 schema + milestone → torchcodec discovery → pod validation.
- Configured `credential.helper store` on the pod so the autoresearch loop's overnight commits and pushes don't need human authentication after the initial PAT setup.

***

Second session: building out program.md, logging the reasoning, and staging/commiting everything to run tomorrow:
- Opened a drafting thread for program.md v1 with the goal of preparing the scientific direction document before launching loop #1 overnight.
- Worked through structural questions for program.md: decided on six sections (goal, what is known, action space, exploration discipline, proposal format, runtime/commit, out of scope) targeting ~1.5 pages.
- Decided against listing ranked hypotheses or pre-baked priors in program.md, in favor of pure factual "what is known" framing as a deliberate negative-control setup for a possible future comparison of context-vs-no-context loops.
- Operationalized the uniform-prior exploration rule as a hard sampling floor: minimum 5 runs per category (threshold / class_weight / preprocessing / architecture / training) before any category can exceed 2x the least-sampled category's run count.
- Decided runtime budget phrasing should name coverage, not quantity, as the source of value: "more runs is better" was rejected in favor of "prefer cheaper experiments when they test equally distinct hypotheses" after explicit challenge on whether the quantity framing was accurate.
- Locked in commit discipline: classify.py writes JSONs atomically including the kept field; agent commits on kept:true with a structured template (category + description + metric deltas + runtime + experiment number), reverts on kept:false, no commit on failed runs.
- Caught and corrected a major methodological issue: the auto_val_prior option in pos_weight_mode computed class weighting from validation set labels, leaking target information into training and invalidating the held-out generalization test. Removed it entirely via Claude Code rather than caveating its use.
- Caught and corrected a directionally wrong prior: the "~65% abnormal in training" working estimate was actually 43.9% abnormal (482 abnormal / 617 normal of 1099 recordings), making training mildly normal-majority rather than abnormal-majority.
- Flagged per-folder class distribution variability (training-a 71% abnormal vs training-b 21% abnormal) as a loop #2 consideration but deliberately excluded per-folder breakdowns from program.md to avoid nudging the agent toward per-folder thinking in loop #1.
- Added a hypothesis field to the results JSON schema via Claude Code so the agent's reasoning trail is captured per run, including for discarded experiments where commit messages don't exist.
- Committed the auto_val_prior removal and hypothesis field addition as two separate commits (1f7786f and ce31c9f) using git add -p to stage selectively.
- Finalized program.md v1 after an explicit audit pass verifying consistency with the loop #1 design thesis: rigorous coverage of the sample space plus analysis of directional results plus deliberate evidence-shaped activism in loop 2 yields better final metric than letting the agent go crazy on pass 1 and pre-baking in personal guesses and biases. The underlying conviction from prior scientific training: never later wished for fewer or messier controls, particularly negative controls.
- Committed program.md to the repo (7ab8542); this activates Mode B in CLAUDE.md for any future Claude Code session opened in the project root.
- Merged the three local commits with a pod-side milestone commit (d3a6e2b) that had landed on origin in parallel, producing merge commit b668330; pushed all four commits to GitHub.
- Appended two items to loop2_considerations.md: training set heterogeneity (five-folder mixture with highly variable per-folder class distributions) as a per-folder weighting or folder-ablation consideration, and a methodologically honest val-prior estimator built from a held-out slice of training folders as a replacement for the removed auto_val_prior.
- Deferred loop #1 launch from tonight to Saturday morning to catch first-run problems with fresh eyes rather than after 7 hours of unsupervised autonomous runtime.

---

## Day 3 — Saturday, April 18, 2026

*(to be filled in)*

---

## Day 4 — Sunday, April 19, 2026

*(to be filled in)*

---

## Day 5 — Monday, April 20, 2026

*(to be filled in)*

---

## Day 6 — Tuesday, April 21, 2026

*(to be filled in)*

---

## Day 7 — Wednesday, April 22, 2026

*(submission day)*
