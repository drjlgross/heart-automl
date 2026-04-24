# Pod Setup — heart-automl

How to go from a fresh RunPod instance to an autonomous Claude Code loop running `classify.py`. Captured from the loop 2 launch sequence (2026-04-22), which hit enough gotchas along the way that a script-from-memory approach was meaningfully slower than following this doc would have been.

**Who this is for:** future-me, or a collaborator standing up a fresh pod for this project or a fork of it. Assumes familiarity with the project's intent (autoresearch loop over heart-sound classification) and with running basic shell/git commands. Not a tutorial — a reproducible sequence.

**How to use:** run the steps in order. Verify each paste-checkpoint before moving on. If something deviates from the expected output, stop and check the appendix before pushing through.

---

## Part 1 — Provision the pod

**On RunPod web dashboard:**

1. Create new pod. Recommended spec: **4 vCPUs, 8GB RAM, compute-optimized, 5GHz clock**. No GPU needed — this is CPU-only inference / small CNN training.
2. Pod template: **Runpod Ubuntu 20.04** (`runpod/base:0.7.0-ubuntu2004`).
3. Overrides:
   - **Container disk: 40 GB** (the max allowed, and enough — see appendix A1)
   - **Volume mount: `/workspace`** (default)
   - **Expose TCP 22, no HTTP ports** (web terminal is used, not SSH)
4. Pod name: descriptive and versioned, e.g., `heart-automl-loop2`. Makes dashboard/billing attribution cleaner when multiple pods coexist.
5. Uncheck both **SSH terminal access** and **Start Jupyter notebook**. Web terminal is sufficient.
6. Deploy.

**Wait for pod to show as Running**, then click **Connect → Start Web Terminal**.

---

## Part 2 — Shell and tmux

From the fresh web terminal prompt (`root@<hostname>:/workspace#`):

```bash
apt update && apt install tmux -y
tmux new -s loop<N>    # e.g., loop2, loop3
```

All subsequent work happens inside tmux. If the web terminal drops, `tmux attach -t loop<N>` resumes without losing state.

---

## Part 3 — Clone repo

```bash
git clone https://github.com/drjlgross/heart-automl.git
cd heart-automl
```

---

## Part 4 — Python 3.13 via deadsnakes

The Ubuntu 20.04 base image ships with Python 3.8, which is too old for the project's torch pinning. Install 3.13 via the deadsnakes PPA.

```bash
apt install -y software-properties-common
add-apt-repository -y ppa:deadsnakes/ppa
apt update
apt install -y python3.13 python3.13-venv python3.13-dev
python3.13 --version    # expect: Python 3.13.x
```

**Verification checkpoint:** `python3.13 --version` prints 3.13.5 or newer. If not, do not proceed.

---

## Part 5 — Create venv (with the symlink fix)

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python --version    # expect: Python 3.13.x — BUT IT MIGHT SAY 3.8.10
```

**If `python --version` shows 3.8.10 instead of 3.13.x**, the venv has broken internal symlinks — see appendix A2. Fix:

```bash
cd .venv/bin
rm python python3
ln -s python3.13 python3
ln -s python3.13 python
cd /workspace/heart-automl
python --version    # should now say 3.13.x
```

**Verification checkpoint:** activated-venv `python --version` reports 3.13.x. If not, fix before proceeding.

---

## Part 6 — Install torch (CPU-only, explicit index)

**Critical:** if you skip the explicit index URL and just run `pip install torch`, pip pulls CUDA-bundled wheels (5+ GB of NVIDIA libraries) and will blow past the 40 GB disk limit. See appendix A3.

```bash
pip install --index-url https://download.pytorch.org/whl/cpu torch torchaudio
```

**Verification checkpoint:** the final line should read `Successfully installed ... torch-2.X.X+cpu torchaudio-2.X.X+cpu ...`. The `+cpu` suffix confirms CPU-only wheels. Wheel names should include `cp313` (matches Python 3.13). If either is wrong, stop.

---

## Part 7 — Install remaining requirements

```bash
pip install -r requirements.txt
```

`torch` and `torchaudio` should show "Requirement already satisfied." New installs include `torchcodec`, `numpy`, `soundfile`, `cffi`, `pycparser`.

**Verification checkpoint:** final line reads `Successfully installed ...` and does not include torch/torchaudio (those were satisfied). No error messages.

---

## Part 8 — Sanity-check imports

```bash
python -c "import torch, torchaudio, torchcodec; print('all imports ok')"
```

**Verification checkpoint:** exactly `all imports ok`. Any ImportError at this stage means the environment is broken and must be fixed before continuing — it will only get harder to diagnose once data and Claude Code are in the picture.

---

## Part 9 — Download PhysioNet data

```bash
wget https://archive.physionet.org/pn3/challenge/2016/training.zip -O training.zip
unzip training.zip -d data/
rm training.zip
```

**Verification checkpoint — data is in the expected place:**

```bash
ls data/
# Expected: training-a  training-b  training-c  training-d  training-e  training-f
```

---

## Part 10 — Verify data layout matches classify.py expectations

The extracted data includes both `.wav` audio files and PhysioNet metadata files (`MD5SUMS`, `RECORDS`, `RECORDS-abnormal`, `.hea` files, `.newsums`). Whether classify.py is robust to these depends on how it enumerates files. **Always verify, never assume.**

```bash
grep -n "glob\|\.wav\|listdir\|scandir" classify.py | head -20
```

**Interpret the output:**

- If classify.py uses **direct path construction** — e.g., `wav = data_root / folder / f"{rec_id}.wav"` — the metadata files are invisible. No cleanup needed.
- If classify.py uses **`glob("*")` or `listdir()` without a `.wav` filter** — it will try to process metadata files as audio. Clean up with:
  ```bash
  find data/ -type f ! -name "*.wav" -delete
  ```

**Spot-check the data exists as expected:**

```bash
ls data/training-a/ | grep "\.wav$" | head -3      # expect a0001.wav, a0002.wav, a0003.wav
ls data/training-a/*.wav | wc -l                    # expect 409
```

If counts diverge from expected (a=409, b=490, c=31, d=55, e=2141, f=114), data is incomplete or misplaced.

---

## Part 11 — Install Claude Code

```bash
curl -fsSL https://claude.ai/install.sh | bash
claude --version    # expect: 2.1.XXX
```

Claude Code lands at `~/.local/bin/claude`, which is already on PATH on this base image. No shell config edits needed.

---

## Part 12 — Git identity + PAT authentication

Set identity (needed before any commit):

```bash
git config --global user.email "drjlgross@users.noreply.github.com"
git config --global user.name "drjlgross"
git config credential.helper store
```

Create a fresh GitHub Personal Access Token (fine-grained):

1. Browser: **github.com/settings/tokens** → Fine-grained tokens → **Generate new token**
2. Name: `<pod-name>` (e.g., `heart-automl-loop2-pod`)
3. Expiration: 30 days
4. Repository access: **Only select repositories** → `drjlgross/heart-automl`
5. Repository permissions: **Contents: Read and write**. (Metadata: Read is auto-required.)
6. Generate, **copy token immediately** (shows once only)

**Store the token safely.** Password manager preferred. A plain-text Typora scratchpad is acceptable temporarily but MUST be deleted or moved within 24 hours.

Pre-flight the push to seed the credential cache (so the autonomous agent's pushes don't hang on a credential prompt at 3am):

```bash
git commit --allow-empty -m "pod <pod-name> ready for loop <N>"
git push
# Username: drjlgross
# Password: <paste PAT>   ← characters hidden; that's normal
```

**Verification checkpoint:** push output includes `main -> main` and no password prompt on a *subsequent* empty commit/push. If credentials weren't cached, redo from the git config lines.

---

## Part 13 — Launch Claude Code

```bash
claude
```

1. First-run: walk through login (device code flow, quick if already signed into Claude Max on another device).
2. Confirm workspace trust when prompted.
3. The `/effort` setting defaults to xhigh — leave as-is (see appendix A4).
4. Paste the Mode B launch prompt below.

### Mode B launch prompt (copy-paste)

```
You are in Mode B (autoresearch loop).

Read CLAUDE.md and program_loop<N>.md in full to understand the current
direction — program_loop<N>.md is authoritative and supersedes any prior
program_loop*.md rules.

Then read results/*.json to understand the prior-loop trajectory.

After reading, propose the scoped approval allowlist per
program_loop<N>.md's tier 1 rule on git-scope approvals. Once I approve
the allowlist, proceed autonomously per program_loop<N>.md for the
budget window specified in the doc.

Voluntary stopping when the landscape feels characterized is preferred
over budget exhaustion, per tier 2 guidance.
```

Replace `<N>` with the current loop number. The agent will read files, propose an allowlist, and pause for your approval before the first experiment — that's expected and correct behavior.

---

## Part 14 — (Optional) monitoring terminal

In a second web terminal tab (NOT inside tmux — this is view-only):

```bash
cd /workspace/heart-automl
source .venv/bin/activate
watch -n 30 'ls -la results/ | tail -5'
```

Shows new JSONs as they land. Useful for glancing at loop progress without attaching to the tmux session Claude Code is running in.

---

## Done.

Total time on a clean pod, following this sequence without deviations: ~15-20 minutes, most of which is waiting for `apt install` and `pip install` to run. First-time tonight: ~90 minutes because we rediscovered half the gotchas live.

---

# Appendix — Gotchas and design decisions

## A1. Why 40 GB disk

The RunPod UI caps container disk at 40 GB on the CPU-optimized instances used here. In loop 1, CUDA-bundled torch + data + caches + Claude Code peaked around 18 GB; with explicit CPU-only torch and no ensemble checkpoints, realistic peak is ~10-15 GB. 40 GB provides a 2.5x+ margin. If RunPod later offers >40 GB on this tier, going larger isn't harmful but isn't necessary either.

**Note on ephemerality:** the container disk is temporary. If the pod is stopped (not just disconnected), everything is wiped. The autoresearch workflow mitigates this by pushing every results JSON to GitHub in real time — the worst-case recovery is re-running this setup doc. Do not stop the pod mid-loop.

## A2. Venv symlink bug on Ubuntu 20.04 + deadsnakes

When `python3.13 -m venv .venv` runs on this base image, the venv's `bin/python` and `bin/python3` can end up symlinked to the system `/usr/bin/python3` (which is 3.8.10) rather than to the venv's own `python3.13` binary. The third symlink, `bin/python3.13`, correctly points to `/usr/bin/python3.13`.

Root cause: unclear, possibly an interaction between the deadsnakes package structure and `ensurepip`'s symlink resolution. Recreating the venv does not reliably fix it.

Fix: manually redirect `python` and `python3` to the venv's `python3.13`. The three-line fix in Part 5 works reliably.

**Why this matters:** if left broken, classify.py's shebang-less invocations (e.g., agent runs `python classify.py`) will silently use Python 3.8, which may succeed installation of some packages but fail at runtime in subtle ways — or succeed but produce numerically-different results from loop 1. Either failure mode is very hard to diagnose hours into an autonomous loop.

## A3. Why CPU-only torch matters for disk

Default `pip install torch` resolves to a wheel that bundles NVIDIA CUDA libraries (cudnn ~366 MB, cublas ~423 MB, nccl ~196 MB, plus torch itself ~530 MB). Total footprint exceeds 2 GB per package. Combined with torchaudio's CUDA bundle, and the other dependencies, a default install can push container disk past 20 GB before data is even downloaded.

On loop 1's initial setup, this caused disk fullness that blocked subsequent pip installs. The `--index-url https://download.pytorch.org/whl/cpu` flag pins pip to the CPU-only wheel index, pulling ~190 MB for torch and ~7 MB for torchaudio. Saves >1 GB instantly and keeps the environment simple.

If you ever do want CUDA (e.g., GPU pod), drop the `--index-url` flag and let pip resolve normally.

## A4. `/effort` xhigh vs defaults

Claude Code exposes an `/effort` knob controlling reasoning depth. `xhigh` (current default) trades inference speed for reasoning quality. For this project's autoresearch mode, deeper per-hypothesis reasoning dominates wall-clock cost (classify.py training takes ~2-3 min; agent thinking adds ~1 min under xhigh, proportionally small). Given the 24-hour budget and the scientific-decision-heavy workload, xhigh is the right setting. Don't change it without a specific reason.

## A5. Pre-flighting the push (why not let the agent trigger it)

The credential helper caches credentials after a successful push. On a fresh pod, no push has happened yet, so the credential store is empty. If the autonomous agent is the first to push (at an unpredictable moment when `kept=True` fires), git will open an interactive prompt that the agent can't satisfy — the pod hangs silently until you notice.

Pre-flighting a manual push seeds the cache so the agent's first push flows through without prompting. The trivial empty commit (`git commit --allow-empty`) is the simplest way to trigger a real push without needing any actual content change.

## A6. Why fine-grained PAT over classic

Fine-grained PATs can be scoped to a single repository. If the pod is compromised, blast radius is limited to `heart-automl` — not the entire account. Slightly more fiddly to set up (the permissions UI is less obvious than classic's `repo` checkbox), but worth the 30 seconds.

Classic tokens with `repo` scope would also work for this project and are the fallback if fine-grained has issues.

## A7. Pod naming matters (slightly)

The pod name appears in the RunPod dashboard and billing records. It does NOT appear in shell hostnames, commit history, or anywhere in code. Naming pods descriptively (`heart-automl-loop2` rather than the default random string) makes it trivial to distinguish pods when multiple are running or when reviewing spend later. Low-value but zero-cost hygiene.

## A8. Metadata files in PhysioNet extraction

The canonical PhysioNet 2016 zip includes per-folder `MD5SUMS`, `RECORDS`, `RECORDS-abnormal`, `.newsums`, and per-recording `.hea` files. Whether these cause problems depends on classify.py's enumeration strategy, NOT on the extraction path. Part 10's grep check is the authoritative way to know — rely on it rather than memory about what the previous pod needed.

---

*Last updated: 2026-04-22 during loop 2 launch. If additions are needed after future pods, keep this doc evergreen — the goal is that following it exactly works from a clean pod, every time.*
