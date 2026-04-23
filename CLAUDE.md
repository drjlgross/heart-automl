# heart-automl

Autoresearch-style autonomous iteration loop for PhysioNet 2016 heart sound
classification. Built as a fellowship demo for Worldwide Fellows "AI for Science."

## Core convention: human writes science, agent executes

Julia uses two separate tools for this project:
- **Claude chat** (claude.ai) for strategy, science, analysis decisions, and
  drafting prompts
- **Claude Code** (this tool) for execution: writing/patching files, git ops,
  running experiments

This separation is load-bearing for the project's demo narrative. Do not blur it.

## Files and their roles

- `classify.py` — single-file experiment script. All hyperparameters live in the
  `CONFIG` dict at the top. The autoresearch loop iterates on this file.
- `program_loop<N>.md` — scientific direction document for the current
  autoresearch loop. **Authored by Julia only.** Do not write, edit, or
  draft these files. If asked to help with program content, redirect:
  "program files are human-authored; I can help you think through ideas
  but shouldn't write them." The presence of any `program_loop*.md`
  signals that autoresearch loop mode is active. The highest-numbered
  file is the current loop's authoritative direction; prior-loop files
  are historical.
- `results/run_<ISO-timestamp>.json` — one file per experiment run. Schema is
  visible in the most recent file. Includes metric, sens, spec, config, kept/
  discarded status, change_category, change_description, and deltas vs prior best.
- `loop2_considerations.md` — Julia's scratchpad for future loop ideas.
  **Do not integrate these into current-loop work.** If an idea surfaces during a
  session that seems loop-2-shaped, flag it to Julia rather than acting on it.
- `WW_Demo_Project_Tracking.md` — chronological daily log. Julia appends to it;
  don't rewrite prior entries.
- `data/` — PhysioNet .wav files and cached spectrograms. Gitignored. Don't
  commit or move.

## Task metric

`challenge_metric = (sensitivity + specificity) / 2` on held-out folder `training-e`.
Abnormal = positive class. Train on folders a, b, c, d, f. Validation folder is
non-negotiable — do not mix it into training.

## Controlled vocab for `change_category` field

One of: `threshold`, `class_weight`, `preprocessing`, `architecture`, `training`,
`other`. Use `other` as escape hatch for changes that don't fit cleanly.

## Reproducibility

Fixed seed (42) everywhere. Metric deltas between runs should be real signal,
not RNG. Do not introduce nondeterminism without explicit instruction.

## Two modes of operation

This project runs in one of two distinct modes. Determine which mode you're in
at the start of every session.

### Mode A: Focused patch (default)

You are in this mode when:
- Julia has given you a specific, scoped task (e.g., "add this CONFIG knob,"
  "write this analysis script," "fix this bug")
- The task is not framed as "run an experiment" or "iterate on classify.py"

In this mode:
- Do not run `classify.py` after patching — Julia reviews the diff first
- Do not commit or push — git ops are a separate, explicit step Julia initiates
- Show the full diff before finishing
- Verify syntax with `python -c "import ast; ast.parse(open('classify.py').read())"`

### Mode B: Autoresearch loop iteration

You are in this mode when:
- A `program_loop<N>.md` file exists in the project root (read the
  highest-numbered one as authoritative)
- The task is framed as running an experiment, proposing the next experiment,
  or iterating on classify.py to improve the metric

In this mode:
- Read `program_loop<N>.md` (the highest-numbered one in the project root) for scientific direction — it specifies what to test
- Read prior `results/*.json` files to understand what's been tried
- Edit `classify.py` per your proposed change
- Run the script: `python classify.py`
- The script writes a new `results/run_<timestamp>.json` automatically
- If the run improved the metric (check the `kept` field), commit the change
  with a descriptive message
- If the run did not improve, revert classify.py to the prior best config
  before the next iteration
- Skip diff review and approval steps — this mode is autonomous by design

If you are ever uncertain which mode you're in, default to Mode A and ask Julia.
