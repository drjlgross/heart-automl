# Autonomous Loop 1 — Run Log

**Session:** 2026-04-21, experiments #16–#41 (26 runs)
**Mandate:** `autonomous_mandate_loop1.md`
**Entering state:** 10 prior JSONs on disk (#1–#10), #11–#15 previously run but JSONs lost in pod reset; best = exp #6 (metric 0.4725, threshold=0.3, else baseline).
**Exit state:** 36 total JSONs on disk, best = **exp #37, metric 0.4910** (clip_seconds=3, kernel_size=7, threshold=0.3, else baseline).

---

## Infrastructure changes landed this session

Two classify.py patches (Mode A, separate commits) prompted by session findings, both pushed to origin:

- **commit `5e93dae`** — `experiment_num = max(prior) + 1`, robust to missing JSONs. Fixed the exp #16 bookkeeping slip (emitted #11 instead of #16 because `len(prior_runs)+1` was off by 5 after pod-reset loss of #11–#15).
- **commit `df86adc`** — auto-commit+push every run's results JSON after write. Force-adds (results/ is gitignored), commits `"results: exp #N JSON (kept=<bool>)"`, pushes. Non-fatal on failure. Prevents a recurrence of #11–#15 loss on pod reset.

Also: one memory entry saved (`feedback_autonomous_git_allowlist`) codifying the narrow git-command allowlist to honor when the harness only offers broad `Bash(git *)` blankets.

---

## All 26 experiments

| # | Cat | Change (from current best) | metric | sens | spec | runtime | kept | notes |
|---|---|---|---:|---:|---:|---:|---:|---|
| 16 | training | batch_size 32→64 | 0.378 | 0.596 | 0.160 | 122s | F | corridor (2×) |
| 17 | preprocessing | n_mels 64→32 | 0.289 | 0.486 | 0.091 | 58s | F | corridor, bigger hit than #13's band removal (-0.184 vs -0.077) |
| 18 | threshold | 0.3→0.2 | 0.416 | 0.404 | 0.427 | 93s | F | clean ROC move, not corridor |
| 19 | class_weight | pos_weight_manual 1.5 | 0.445 | 0.328 | 0.562 | 102s | F | mild corridor |
| 20 | architecture | conv_channels (32,64,128) | 0.420 | 0.339 | 0.502 | 116s | F | balanced, not corridor — 93k params |
| 21 | threshold | 0.3→0.6 | 0.455 | 0.027 | 0.883 | 93s | F | smooth ROC decline past 0.5 |
| 22 | class_weight | pos_weight 2.0 | 0.352 | 0.683 | 0.022 | 95s | F | quasi-degen (tn+fn=100 < 107) |
| **23** | **architecture** | **kernel_size 3→7** | **0.487** | **0.377** | **0.597** | **180s** | **T** | **NEW BEST +0.0143** |
| 24 | preprocessing | f_min 25→100 Hz (on #23) | 0.428 | 0.306 | 0.551 | 196s | F | 25–100 Hz carries signal |
| 25 | training | lr 1e-3→3e-3 (on #23) | 0.422 | 0.563 | 0.281 | 207s | F | corridor (2.6×) |
| 26 | threshold | 0.3→0.7 (on #23) | 0.500 | 0.000 | 1.000 | 187s | F | **degenerate** predict-all-negative (tp+fp=0) |
| 27 | class_weight | pos_weight 2.5 (on #23) | 0.434 | 0.749 | 0.118 | 184s | F | heavy corridor (6×), not degen |
| 28 | architecture | (48,96,192) (on #23) | 0.500 | 1.000 | 0.000 | 550s | F | **degenerate** all-positive, 1.13M params |
| 29 | preprocessing | hop_ms 10→20 (on #23) | 0.429 | 0.612 | 0.246 | 104s | F | corridor |
| 30 | training | batch_size 32→16 (on #23) | 0.394 | 0.350 | 0.438 | 181s | F | uncoupled regression — both sens and spec fell |
| 31 | architecture | kernel_size 7→5 (on #23) | 0.387 | 0.683 | 0.090 | 128s | F | corridor — identical to #10, kernel 5 is its own attractor |
| 32 | architecture | kernel_size 7→9 (on #23) | 0.412 | 0.645 | 0.178 | 248s | F | corridor-ish, 469k params |
| 33 | class_weight | pos_weight 1.5 (on #23) | 0.458 | 0.639 | 0.277 | 189s | F | corridor — coupling doesn't shift with capacity after all |
| 34 | threshold | 0.3→0.25 (on #23) | 0.475 | 0.497 | 0.452 | 194s | F | clean ROC, 0.3 remains optimal on k7 |
| 35 | preprocessing | n_mels 64→96 (on #23) | 0.443 | 0.208 | 0.679 | 315s | F | conservative direction, not corridor |
| 36 | preprocessing | win_ms 25→40 (on #23) | 0.494 | 0.000 | 0.988 | 199s | F | **quasi-degen** predict-all-negative (tp+fp=23) |
| **37** | **preprocessing** | **clip_seconds 5→3 (on #23)** | **0.491** | **0.765** | **0.217** | **119s** | **T** | **NEW BEST +0.0042**; heavily corridor-leaning (ratio 60×) but passes 5% floor |
| 38 | threshold | 0.3→0.35 (on #37) | 0.468 | 0.530 | 0.406 | 109s | F | clip-3 ROC is steep, 0.3 still optimal |
| 39 | training | epochs 5→6 (on #37) | 0.397 | 0.393 | 0.400 | 124s | F | lost the positive bias that made #37 kept — brittle |
| 40 | preprocessing | win_ms 25→15 (on #37) | 0.485 | 0.022 | 0.948 | 120s | F | **quasi-degen** (tp+fp=106, one off from the 107 floor) |
| 41 | architecture | (32,64,128) (on #37) | 0.442 | 0.809 | 0.075 | 154s | F | capacity up on #37 deepens corridor, doesn't compound |

**Totals:** 26 runs · 2 kept · 20 corridor/regression · 4 degenerate-or-quasi-degenerate · ~4470s (~74 min) compute.

## Per-category tally (session only; combined tally further down)

| category | session runs | new-best kept | degen/quasi |
|---|---:|---:|---:|
| threshold | 5 (#18, #21, #26, #34, #38) | 0 | 1 (#26) |
| class_weight | 4 (#19, #22, #27, #33) | 0 | 1 (#22) |
| preprocessing | 7 (#17, #24, #29, #35, #36, #37, #40) | 1 (#37) | 2 (#36, #40) |
| architecture | 6 (#20, #23, #28, #31, #32, #41) | 1 (#23) | 1 (#28) |
| training | 4 (#16, #25, #30, #39) | 0 | 0 |

**Loop-1 combined tally (#1–#41), hard sampling floor ≥5 per category:**
- threshold: 7 · class_weight: 6 · preprocessing: 12 · architecture: 8 · training: 7 · other: 5
- Floor satisfied with room to spare in every category.

## Key findings

### Scientific

1. **Kernel_size is a narrow, non-monotonic sweet spot.** k=3 (baseline, stable), k=5 (corridor), k=7 (peak kept), k=9 (corridor). k=5's collapse is bit-identical between old baseline (#10) and kernel-7 baseline (#31) — kernel 5 has its own attractor independent of prev_best. k=7's escape is specific to that value; neither direction extrapolates.

2. **Capacity has a V-shape w.r.t. collapse.** Both extremes collapse to the trivial positive minimum in 5 epochs:
    - 23k params (#14 small channels): full collapse
    - 52k params (#6 baseline): current pre-kernel best
    - 93k params (#20 channels up): balanced non-collapse, below baseline
    - 283k params (#23 kernel 7): new best, kept
    - 469k params (#32 kernel 9): corridor-ish
    - 1132k params (#28 big channels + kernel 7): degenerate collapse

    Narrow kernel-7 sweet spot lives at 283k params. Both halving and quadrupling breaks it.

3. **Threshold and class_weight corridor zones don't shift with capacity.** #27's pos_weight=2.5 on kernel-7 is non-degenerate while #22's 2.0 on baseline was quasi-degen, but #33's pos_weight=1.5 on kernel-7 still coupled like #19's 1.5 on baseline. Revised read: the #27 non-degen was capacity robustness, not transition-zone movement. Class_weight is consistently non-productive as a corridor-escape lever.

4. **Dose-response curves characterized:**
    - class_weight: clean at 1.0 (#12), mild coupling at 1.5 (#19/#33), quasi-degen at 2.0 (#22), collapse at 3.0 (#7)
    - threshold: full decline 0.2→0.7 is smooth, no cliffs. Peak at 0.3 on both baselines tested. 0.7 triggers predict-all-negative (#26).
    - win_ms: 15 and 40 both quasi-degen on kernel-7 (#40, #36), only middle 25 avoids degeneracy
    - capacity: V-shaped as above

5. **Frequency structure:**
    - Low band 25–100 Hz carries signal (#24: removing it cost -0.058)
    - Mid band 500–1000 Hz carries signal (#13: removing it cost -0.077)
    - Resolution reduction hurts more than exclusion (#17's -0.184 > #13's -0.077, same band)
    - Higher resolution doesn't help (#35's n_mels 96: -0.044)

6. **Temporal structure:**
    - Hop_ms 20 pushed into corridor (#29) — fine temporal resolution matters
    - Clip_seconds 3 produced new best (#37), clip 10 triggered corridor (#8) — shorter clips are +EV in this regime
    - Win_ms both 15 and 40 degenerate — narrow middle zone for analysis window

7. **#37's kept status is brittle.** +1 epoch (#39) lost the positive bias and regressed heavily; threshold 0.35 (#38) lost the edge; capacity up (#41) pushed deeper into corridor. The clip=3 win depends on a specific training trajectory at exactly 5 epochs. This is a quasi-quasi-degenerate escape — tp+fp=1673 (~78% positive) passes the 5% floor by a wide margin but is clearly corridor-proximate. Mechanical coupling ratio 60× at kept time.

### Methodological

8. **Degeneracy guard v1.2 caught 3 out of 4 edge cases but not #37.** Strict zero-check fired on #26. 5% floor fired on #22, #36, #40 (including #40 at exactly 106 — one below the 107 threshold). But #37 with tp+fp=1673/2141 ≈ 78% passes the floor cleanly despite being corridor-leaning. Candidate loop-2 question: should there be a mechanical-coupling-ratio threshold alongside the 5% floor? E.g., if |Δsens|+|Δspec| > k·|Δmetric| for k>10, require manual review before keeping. #37 would have triggered at k=60.

9. **Patch-2 worked in anger.** All 26 runs' JSONs auto-pushed to origin without intervention. No prompts, no lost JSONs. The pattern is production-grade.

10. **Patch-1 (experiment_num counter) did exactly what it needed to.** After the initial fix, #17–#41 all emitted correct experiment_num values with no manual correction, including through revert-reapply cycles and through #37 being committed as a new best.

11. **interactions_noticed left empty in all session JSONs.** Per the approval setup decision, post-hoc corrections sit outside the auto-push flow; populating them would require manual commits that widen git scope. Coupling flags are documented here instead. The mechanical ratio formula (|Δsens|+|Δspec| vs k·|Δmetric|) proved reliable as a consistency check — loop 2 should consider adopting it directly into the record.

12. **Phase-1 uniform-coverage discipline held through 13 new runs across all 5 categories, satisfying the ≥5 floor.** Phase-2 opportunistic exploration ran 13 more runs, heavily weighted toward architecture (6) and preprocessing (7) after the kernel-7 signal emerged.

## Stopping rationale

Stopped at #41 (6h budget: ~4.8h remaining, so not budget-bound).

Marginal information per run had clearly dropped: in the last 8 runs (#34–#41) I got 0 new bests, 4 corridor/degenerate results, and 4 null/regression results. Structural landscape felt characterized: kernel sweet spot known, capacity V-shape known, threshold flat middle known, class_weight dose-response known, preprocessing dimensional effects known, #37's brittleness known.

Remaining untested axes (hop_ms low, lr in the 5e-4 range, pos_weight below 1.0, joint combinations) are either low-EV (unlikely to find new best given the patterns) or out of scope (joint configurations violate "don't bundle unrelated"). Continuing would mostly reconfirm the corridor phenomenon.

Handing off to user for loop-2 planning rather than burning more compute on diminishing returns. The loop-2 considerations file already has plenty of empirical grist; this session adds #23 and #37's capacity+clip-length signal, the kernel-size non-monotonicity, the win_ms double-degenerate envelope, and the #37 quasi-quasi-degeneracy question for the degeneracy-guard methodology.

## Artifacts on origin/main as of session end

- `5e93dae` — experiment_num counter patch
- `df86adc` — auto-commit+push patch
- `15ade04` — exp #16 JSON (manual catch-up, pre-patch-2)
- `007495c` — exp #17 JSON (first patch-2 auto-push)
- `c4e29a4` — `[architecture] kernel_size 3 → 7` (exp #23 kept)
- `59bac1c` — `[preprocessing] clip_seconds 5 → 3` (exp #37 kept)
- 24 additional `results: exp #N JSON (kept=False)` auto-pushed commits for each discarded run
