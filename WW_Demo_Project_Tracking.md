# WW Demo Project Tracking

Running chronological log of work completed on the Heart-AutoML project. Source material for the demo video.

---

## Day 1 — Thursday, April 16, 2026

- Locked in project concept: heart sound classification on PhysioNet 2016 dataset, optimized via an autoresearch-style autonomous loop (Claude Code edits `classify.py` → runs experiment → checks metric → keeps or discards → repeats)
- Downloaded PhysioNet 2016 Challenge dataset (~3,100 .wav files across training-a through training-f) via Kaggle after initial `wget` attempt returned competition submissions instead of training data
- Set up project file structure: `ww_demo/heart-automl/` with `data/`, `results/`, flat hierarchy after removing the `archive/` wrapper
- Acquired CAD Audio CX2 USB audio interface from Micro Center
- Ordered piezo contact microphones from Amazon (2x, Saturday 4/18 delivery) after confirming compatibility with CX2
- Consulted HacDC Hardware Hacking Night — no piezo available on-site, but biosignal-experienced members eyeballed the CX2 + piezo plan and confirmed the setup should work cleanly
- Set up Python environment: fresh venv in project directory, Claude Code integrated and running with autonomous edit permissions
- Wrote baseline `classify.py` end-to-end: loads .wav files, resamples to 2000 Hz, extracts mel spectrograms (64 bins, 25ms/10ms windows), caches to disk, trains a ~50K param CNN for 10 epochs, evaluates on held-out folder e, writes timestamped JSON results
- Executed first run: baseline challenge metric = 0.36 (sens 0.45, spec 0.28). Below random, but diagnostically — model overpredicts abnormal due to class weights applied on top of a training distribution (65% abnormal) that inverts the validation distribution (20% abnormal)
- Discovered MacBook Air thermal throttling constraint: cold run 484s, warm run 1,747s. Local hardware cannot host the iteration loop at any settings
- Planned mitigation: pre-paid RunPod CPU instance ($20 credit, no auto-reload) for Friday morning
- Mapped full-week timeline with redundancies: cloud compute fallback for Friday, HacDC Monday night as hardware troubleshooting backup, Tuesday as video/submission buffer

---

## Day 2 — Friday, April 17, 2026

*(to be filled in)*

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
