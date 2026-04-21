# Autonomous mandate for rest of loop 1

## Phase 1 — complete coverage
Run experiments until every category (threshold, class_weight, preprocessing, architecture, training) has ≥5 runs. Current tally is threshold 2, class_weight 2, preprocessing 3, architecture 2, training 3. I know many of these will likely re-confirm the corridor finding and be low-information. Run them anyway — coverage is the point, per program.md.

## Phase 2 — extended exploration
After the floor is satisfied, continue running experiments in whatever categories you judge most likely to produce new signal, until you assess that the marginal information per run has dropped low enough that further runs aren't worth it. Your call on when to stop.

## Stopping conditions
Stop if any of:
- You've completed phase 2 per your own judgment.
- Budget: ~6 hours of runtime consumed.
- You hit something you can't handle without my input (real ambiguity, not just wanting validation).

## Logging
At the end, write a run log summarizing: all experiments run, per-category tally, kept vs discarded, key findings surfaced, and — important — your reasoning for why you stopped when you did.

## Approval setup (do this BEFORE starting)
Before launching autonomous mode, propose the minimum set of blanket approvals needed to complete this mandate without per-run prompts. List each command pattern you plan to approve and why. Wait for my go-ahead on the approval set before proceeding.

Guidance on scope: `git checkout -- classify.py` (file-revert only) is approved in principle; do NOT propose a blanket for `git checkout *` because branch-switching must stay gated (deliberate guardrail from earlier today). For the Patch-2 JSON push sequence (`git add -f results/*.json`, `git commit -m "results: ..."`, `git push`), propose the narrowest patterns that cover the actual per-run commands. If Claude Code's approval dialog only offers broader scopes than the narrow ones you want, stop and tell me — I'd rather keep per-approval than silently widen.

## Autonomy (after approval set is agreed)
Approved to proceed through classify.py edits, runs, interpretation, and commit-or-revert without per-run approval. Patch 2 handles results JSON durability automatically per run.
EOF