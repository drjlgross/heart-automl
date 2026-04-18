"""Heart-sound classifier on PhysioNet 2016 Challenge data.

Run:  python classify.py
Deps: see requirements.txt  (torch, torchaudio, numpy, soundfile)
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import random
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torchaudio
from torch.utils.data import DataLoader, Dataset

warnings.filterwarnings("ignore")

# --------------------------------------------------------------------------- #
# All knobs live here so the autoresearch loop can patch one place.
# --------------------------------------------------------------------------- #
CONFIG: dict = {
    "seed": 42,

    # Data
    "data_root": str(Path(__file__).parent / "data"),
    "cache_dir": str(Path(__file__).parent / "data" / "cache"),
    "results_dir": str(Path(__file__).parent / "results"),
    "train_folders": ["training-a", "training-b", "training-c",
                      "training-d", "training-f"],
    "val_folders":   ["training-e"],

    # Audio / spectrogram
    "sample_rate": 2000,         # Hz, target after resample
    "clip_seconds": 5.0,
    "n_mels": 64,
    "win_ms": 25.0,
    "hop_ms": 10.0,
    "f_min": 25.0,
    "f_max": 1000.0,             # Nyquist of 2 kHz

    # Model
    "conv_channels": (24, 48, 96),
    "kernel_size": 3,

    # Training
    "epochs": 5,    # loop #1 starting point; agent may scale up in "training" category
    "batch_size": 32,
    "lr": 1e-3,
    "num_workers": 0,            # CPU box: 0 avoids fork overhead
    "decision_threshold": 0.3,

    # Class weighting for BCEWithLogitsLoss pos_weight.
    #   "auto_train"      — neg/pos from training set (historical default)
    #   "none"            — disable class weighting (pos_weight = 1.0)
    #   "manual"          — use pos_weight_manual verbatim
    "pos_weight_mode": "auto_train",
    "pos_weight_manual": 1.0,
}


# --------------------------------------------------------------------------- #
# Reproducibility
# --------------------------------------------------------------------------- #
def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.use_deterministic_algorithms(True, warn_only=True)
    os.environ["PYTHONHASHSEED"] = str(seed)


# --------------------------------------------------------------------------- #
# Label parsing — REFERENCE.csv: <recording_id>,<label in {-1,0,1}>
# Map -1 -> 0 (normal), 1 -> 1 (abnormal). Drop 0 / unsure.
# --------------------------------------------------------------------------- #
def load_index(data_root: Path, folders: list[str]) -> list[tuple[Path, int]]:
    items: list[tuple[Path, int]] = []
    for folder in folders:
        ref = data_root / folder / "REFERENCE.csv"
        with open(ref, newline="") as fh:
            for rec_id, raw_label in csv.reader(fh):
                lab = int(raw_label)
                if lab not in (-1, 1):  # drop 0 / unsure
                    continue
                wav = data_root / folder / f"{rec_id}.wav"
                if wav.exists():
                    items.append((wav, 1 if lab == 1 else 0))
    return items


# --------------------------------------------------------------------------- #
# Spectrogram pipeline — built once and reused for every wav.
# --------------------------------------------------------------------------- #
def build_mel_transform(cfg: dict) -> nn.Module:
    sr = cfg["sample_rate"]
    n_fft = int(round(cfg["win_ms"] / 1000.0 * sr))
    hop   = int(round(cfg["hop_ms"] / 1000.0 * sr))
    # Round n_fft up to a power of two for FFT efficiency without changing window length.
    pow2 = 1
    while pow2 < n_fft:
        pow2 *= 2
    return nn.Sequential(
        torchaudio.transforms.MelSpectrogram(
            sample_rate=sr,
            n_fft=pow2,
            win_length=n_fft,
            hop_length=hop,
            n_mels=cfg["n_mels"],
            f_min=cfg["f_min"],
            f_max=cfg["f_max"],
            power=2.0,
        ),
        torchaudio.transforms.AmplitudeToDB(stype="power", top_db=80.0),
    )


def compute_spectrogram(wav_path: Path, mel: nn.Module, cfg: dict) -> np.ndarray:
    waveform, sr = torchaudio.load(str(wav_path))
    if waveform.shape[0] > 1:                               # to mono
        waveform = waveform.mean(dim=0, keepdim=True)
    if sr != cfg["sample_rate"]:
        waveform = torchaudio.functional.resample(waveform, sr, cfg["sample_rate"])

    target_len = int(cfg["clip_seconds"] * cfg["sample_rate"])
    if waveform.shape[1] >= target_len:
        waveform = waveform[:, :target_len]
    else:
        pad = target_len - waveform.shape[1]
        waveform = torch.nn.functional.pad(waveform, (0, pad))

    with torch.no_grad():
        spec = mel(waveform).squeeze(0)                     # (n_mels, T)
    return spec.numpy().astype(np.float32)


# --------------------------------------------------------------------------- #
# Cache keying — any CONFIG field that affects spectrogram content must be
# hashed into the cache filename, or edits silently reuse stale specs.
# --------------------------------------------------------------------------- #
_PREPROC_CACHE_FIELDS = (
    "clip_seconds", "n_mels", "win_ms", "hop_ms", "f_min", "f_max", "sample_rate",
)


def preproc_cache_tag(cfg: dict) -> str:
    payload = "|".join(f"{k}={cfg[k]}" for k in sorted(_PREPROC_CACHE_FIELDS))
    return hashlib.sha256(payload.encode()).hexdigest()[:8]


# --------------------------------------------------------------------------- #
# Dataset — caches spectrograms to .npy on first touch, mmaps thereafter.
# --------------------------------------------------------------------------- #
class HeartSoundDataset(Dataset):
    """All spectrograms are computed (or read from cache) once at construction,
    then held in a single contiguous tensor. Per-epoch I/O is therefore zero —
    critical for the < 60 s warm-run budget on CPU.
    """
    def __init__(self, items: list[tuple[Path, int]], cache_dir: Path,
                 mel: nn.Module, cfg: dict):
        cache_dir.mkdir(parents=True, exist_ok=True)
        tag = preproc_cache_tag(cfg)
        specs: list[np.ndarray] = []
        labels: list[int] = []
        for wav_path, label in items:
            cp = cache_dir / f"{wav_path.parent.name}__{wav_path.stem}__{tag}.npy"
            if cp.exists():
                spec = np.load(cp)
            else:
                spec = compute_spectrogram(wav_path, mel, cfg)
                np.save(cp, spec)
            specs.append(spec)
            labels.append(label)
        # (N, 1, n_mels, T) — single contiguous block, no per-item allocation.
        self.x = torch.from_numpy(np.stack(specs)).unsqueeze(1).contiguous()
        self.y = torch.tensor(labels, dtype=torch.float32)

    def __len__(self) -> int:
        return self.x.shape[0]

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor]:
        return self.x[idx], self.y[idx]


# --------------------------------------------------------------------------- #
# Tiny CNN — ~50K params with channels (24, 48, 96).
# --------------------------------------------------------------------------- #
class HeartCNN(nn.Module):
    def __init__(self, channels=(24, 48, 96), kernel_size: int = 3):
        super().__init__()
        c1, c2, c3 = channels
        pad = kernel_size // 2

        def block(in_c: int, out_c: int) -> nn.Sequential:
            return nn.Sequential(
                nn.Conv2d(in_c, out_c, kernel_size, padding=pad, bias=False),
                nn.BatchNorm2d(out_c),
                nn.ReLU(inplace=True),
                nn.MaxPool2d(2),
            )

        self.features = nn.Sequential(
            block(1,  c1),
            block(c1, c2),
            block(c2, c3),
        )
        self.gap = nn.AdaptiveAvgPool2d(1)
        self.head = nn.Linear(c3, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.features(x)
        x = self.gap(x).flatten(1)
        return self.head(x).squeeze(1)                      # raw logits


# --------------------------------------------------------------------------- #
# Train + eval
# --------------------------------------------------------------------------- #
def train_one_epoch(model, loader, optim, loss_fn, device) -> float:
    model.train()
    total, n = 0.0, 0
    for x, y in loader:
        x, y = x.to(device), y.to(device)
        optim.zero_grad()
        logits = model(x)
        loss = loss_fn(logits, y)
        loss.backward()
        optim.step()
        total += loss.item() * x.size(0)
        n += x.size(0)
    return total / max(n, 1)


@torch.no_grad()
def evaluate(model, loader, threshold: float, device) -> dict:
    model.eval()
    tp = tn = fp = fn = 0
    for x, y in loader:
        x = x.to(device)
        prob = torch.sigmoid(model(x)).cpu().numpy()
        pred = (prob >= threshold).astype(np.int64)
        true = y.numpy().astype(np.int64)
        tp += int(((pred == 1) & (true == 1)).sum())
        tn += int(((pred == 0) & (true == 0)).sum())
        fp += int(((pred == 1) & (true == 0)).sum())
        fn += int(((pred == 0) & (true == 1)).sum())
    sens = tp / (tp + fn) if (tp + fn) else 0.0
    spec = tn / (tn + fp) if (tn + fp) else 0.0
    return {
        "sensitivity": sens,
        "specificity": spec,
        "challenge_metric": 0.5 * (sens + spec),
        "tp": tp, "tn": tn, "fp": fp, "fn": fn,
    }


# --------------------------------------------------------------------------- #
# Prior-run bookkeeping — feeds experiment_num / kept / prev_best into results.
# --------------------------------------------------------------------------- #
def _load_prior_runs(results_dir: Path) -> list[dict]:
    """Return prior result JSONs in chronological order.

    Sorts by ``experiment_num`` when present; legacy records lacking that field
    fall back to their filename timestamp (``run_<UTC stamp>.json`` sorts
    alphabetically == chronologically). Malformed files are skipped silently.
    """
    if not results_dir.exists():
        return []
    entries: list[tuple[int, str, dict]] = []
    for path in sorted(results_dir.glob("run_*.json")):
        try:
            with open(path) as fh:
                rec = json.load(fh)
        except (OSError, json.JSONDecodeError):
            continue
        exp_num = rec.get("experiment_num")
        entries.append((exp_num if isinstance(exp_num, int) else -1, path.name, rec))
    entries.sort(key=lambda t: (t[0], t[1]))
    return [rec for _, _, rec in entries]


def _is_degenerate_confusion(c: dict) -> bool:
    """program.md v1.2 guard. A predictor is degenerate if either:
    (a) the confusion matrix has a zero row or column (strict zero-check), or
    (b) fewer than 5% of validation samples are assigned to either class
        (5% prediction floor — catches quasi-degenerate collapses that
        narrowly escape the strict check with a handful of lucky predictions).
    """
    tp = c.get("tp", 0); tn = c.get("tn", 0)
    fp = c.get("fp", 0); fn = c.get("fn", 0)
    if (tp + fn == 0) or (tn + fp == 0) or (tp + fp == 0) or (tn + fn == 0):
        return True
    n_val = tp + tn + fp + fn
    return (tp + fp) < 0.05 * n_val or (tn + fn) < 0.05 * n_val


def _compute_pos_weight(cfg: dict,
                        train_items: list[tuple[Path, int]]) -> float:
    mode = cfg["pos_weight_mode"]
    if mode == "auto_train":
        pos = sum(lab for _, lab in train_items)
        neg = len(train_items) - pos
        return neg / max(pos, 1)
    if mode == "none":
        return 1.0
    if mode == "manual":
        return float(cfg["pos_weight_manual"])
    raise ValueError(f"unknown pos_weight_mode: {mode!r}")


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main(cfg: dict) -> dict:
    t0 = time.time()
    set_seed(cfg["seed"])
    device = torch.device("cpu")

    data_root = Path(cfg["data_root"])
    train_items = load_index(data_root, cfg["train_folders"])
    val_items   = load_index(data_root, cfg["val_folders"])
    assert train_items and val_items, "Empty train or val split"

    mel = build_mel_transform(cfg)

    train_ds = HeartSoundDataset(train_items, Path(cfg["cache_dir"]), mel, cfg)
    val_ds   = HeartSoundDataset(val_items,   Path(cfg["cache_dir"]), mel, cfg)

    pos_weight = torch.tensor(
        [_compute_pos_weight(cfg, train_items)], dtype=torch.float32
    )

    train_loader = DataLoader(
        train_ds, batch_size=cfg["batch_size"], shuffle=True,
        num_workers=cfg["num_workers"], drop_last=False,
    )
    val_loader = DataLoader(
        val_ds, batch_size=cfg["batch_size"], shuffle=False,
        num_workers=cfg["num_workers"], drop_last=False,
    )

    model = HeartCNN(cfg["conv_channels"], cfg["kernel_size"]).to(device)
    n_params = sum(p.numel() for p in model.parameters())

    loss_fn = nn.BCEWithLogitsLoss(pos_weight=pos_weight.to(device))
    optim = torch.optim.Adam(model.parameters(), lr=cfg["lr"])

    for epoch in range(1, cfg["epochs"] + 1):
        loss = train_one_epoch(model, train_loader, optim, loss_fn, device)
        print(f"epoch {epoch:>2}/{cfg['epochs']}  train_loss={loss:.4f}")

    metrics = evaluate(model, val_loader, cfg["decision_threshold"], device)
    runtime = time.time() - t0

    print(f"\nchallenge_metric = {metrics['challenge_metric']:.4f}  "
          f"(sens={metrics['sensitivity']:.4f}, spec={metrics['specificity']:.4f})")
    print(f"runtime = {runtime:.1f}s  params = {n_params}  "
          f"train_n = {len(train_items)}  val_n = {len(val_items)}")

    results_dir = Path(cfg["results_dir"])
    prior_runs = _load_prior_runs(results_dir)
    experiment_num = len(prior_runs) + 1

    prev_best: dict | None = None
    eligible = [r for r in prior_runs
                if isinstance(r.get("confusion"), dict)
                and not _is_degenerate_confusion(r["confusion"])]
    if eligible:
        best = max(eligible, key=lambda r: r.get("metric", float("-inf")))
        prev_best = {
            "experiment_num": best.get("experiment_num"),
            "metric":         best.get("metric"),
            "sensitivity":    best.get("sensitivity"),
            "specificity":    best.get("specificity"),
        }

    this_metric = metrics["challenge_metric"]
    this_degenerate = _is_degenerate_confusion(metrics)
    if prev_best is None:
        kept = not this_degenerate
        vs_prev_best = None
    else:
        kept = (not this_degenerate) and (this_metric > prev_best["metric"])
        vs_prev_best = {
            "metric":      this_metric           - prev_best["metric"],
            "sensitivity": metrics["sensitivity"] - prev_best["sensitivity"],
            "specificity": metrics["specificity"] - prev_best["specificity"],
        }

    record = {
        "experiment_num":     experiment_num,
        "metric":             this_metric,
        "sensitivity":        metrics["sensitivity"],
        "specificity":        metrics["specificity"],
        "confusion":          {k: metrics[k] for k in ("tp", "tn", "fp", "fn")},
        "n_train":            len(train_items),
        "n_val":              len(val_items),
        "n_params":           n_params,
        "runtime_sec":        runtime,
        "kept":               kept,
        "prev_best":          prev_best,
        "vs_prev_best":       vs_prev_best,
        "hypothesis":         "Lowering decision_threshold from 0.5 to 0.3 will raise the challenge metric by recovering sensitivity from its 0.082 floor at modest cost to specificity, since the current operating point is far below the ~44% positive base rate.",
        "change_category":    "threshold",
        "change_description": "decision_threshold 0.5 → 0.3",
        "interactions_noticed": [],
        "config":             cfg,
    }
    results_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = results_dir / f"run_{stamp}.json"
    with open(out, "w") as fh:
        json.dump(record, fh, indent=2, default=str)
    print(f"wrote {out}")

    return record


if __name__ == "__main__":
    main(CONFIG)
