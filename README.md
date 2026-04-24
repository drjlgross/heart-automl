# heart-automl

Autonomous ML loop for heart-sound classification on the PhysioNet 2016 Challenge dataset, developed for the Worldwide Fellows AI-for-Science Spring 2026 program.

**Status:** loops 1 and 2 complete. Loop 1 closed at experiment #41 with an agent-authored capstone (`autonomous_loop1_run_log.md`). Loop 2 closed at experiment #54 with a voluntary agent stop and a structural characterization of the problem (documented in `WW_Demo_Project_Tracking.md`).

## What this is

An adaptation of Andrej Karpathy's "autoresearch" idea: Claude Code edits `classify.py`, runs the experiment, checks whether the metric improved, and keeps or reverts accordingly — autonomously, in a loop. The loop's scientific direction is specified in a human-authored `program_loop<N>.md` document; the agent executes within those rules.

What's distinctive about this implementation:

- **Human authors the science, agent executes.** Research strategy and methodological rules live in `program_loop<N>.md` and are edited by me. The agent proposes, runs, and evaluates experiments but cannot change the rulebook.
- **Three-tier rule structure in loop 2**: PROHIBIT (hard invariants that break the setup — seed, data split, source), CO-DECIDE (methodology I want to reason about jointly, with a structured escalation protocol), AGENT (context, earned priors, and framing that inform the search without constraining it).
- **Mechanical degeneracy guards.** A one-class-collapse check and a 5% output-floor rule, both enforced in `classify.py`, prevent the optimizer from "winning" the metric by predicting everything positive (or negative).
- **Earned priors carried across loops.** Loop 1 was a deliberately disciplined sweep with a minimum-5-runs-per-category sampling floor. Its findings became the tier-3 context for loop 2, rather than being baked into loop 1 as pre-existing biases.
- **Full experiment history preserved.** Every run, kept or discarded, writes a JSON to `results/` and is committed — the trajectory is the artifact, not just the best model.

## Repo map

- `program_loop2.md` — active research methodology (tier 1/2/3 structure)
- `program_loop1.md` — historical, loop 1's methodology (preserved for provenance)
- `CLAUDE.md` — operating rules for the agent: Mode A (focused patches) vs Mode B (autoresearch loop)
- `classify.py` — single-file training and evaluation pipeline; all knobs exposed via CONFIG
- `results/` — one JSON per experiment across loops 1 and 2, including discarded runs
- `autonomous_loop1_run_log.md` — loop 1's agent-authored capstone: findings, category tally, stopping rationale
- `autonomous_mandate_loop1.md` — the autonomous operating mandate for loop 1 (provenance)
- `loop2_considerations.md` — running scratchpad of ideas deferred from loop 1
- `pod_setup.md` — battle-tested RunPod setup sequence for reproducibility
- `WW_Demo_Project_Tracking.md` — chronological play-by-play of the full build
- `requirements.txt` — Python dependencies (CPU-only torch, torchaudio, torchcodec)

## License

MIT — see `LICENSE`.
