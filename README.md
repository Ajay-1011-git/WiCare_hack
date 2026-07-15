# WiCare — Ambient Care Sentinel

**Passive, contactless sleep and vital-signs monitoring — no wearable, no camera, no
compliance burden.** WiCare reads coarse physiological signals out of the radio
environment of a room using WiFi Channel State Information (CSI), and runs them through
a machine-learned drift-detection pipeline trained on real clinical sleep-study data to
flag when someone's sleep pattern is progressively deviating from their own baseline.

This repo contains the full software stack: a FastAPI sensing/inference backend, two
trained ML models + a statistical drift detector, and a React dashboard — all wired
together end to end and demoable today, standing in for the physical ESP32 sensor that
completes the picture.

---

## Why WiFi, why not a wearable or a camera

The two existing approaches to home health monitoring both fail in ways that matter most
overnight:

- **Wearables need compliance.** They only work while worn and charged, and overnight
  adherence drops exactly when monitoring matters most.
- **Cameras need consent.** Continuous video in a bedroom is rarely acceptable in most
  homes or care settings, and raises real privacy questions the moment it's recording.

**Ambient WiFi sensing needs neither.** Nothing is worn, nothing is recorded as an image.
A pair of commodity ESP32 boards exchange WiFi packets across a room; the *Channel State
Information* of those packets — how the signal's amplitude and phase are perturbed by
everything in its path — carries a faint but real signature of a chest rising and
falling, a body shifting in bed, or a limb twitching. No video frame is ever produced;
the sensor reads a radio channel, not a scene. It does, honestly, respond to *any* body
in the room, not only the intended one — a second occupant, a visitor, a pet — so
readings are always surfaced for human review, never as a standalone diagnosis.

## Why a trained model + a statistical drift detector, not a simple threshold

A single "breathing rate outside 12–18 br/min" rule is brittle: normal sleep is noisy,
and every person's baseline is slightly different. This project instead:

1. **Learns what "flagged" looks like from real polysomnography (PSG) data** — Sleep-EDF
   SC (healthy controls) and CAP (clinically diagnosed sleep-disordered breathing,
   periodic limb movement, and insomnia recordings) — rather than hand-picked cutoffs.
2. **Normalizes against the person being monitored**, not just the population: every
   feature is expressed both as a personal-baseline z-score (`*_zbase`, computed from
   that session's own first few minutes) and as a tick-over-tick delta (`*_delta`), so
   the model reasons about *this person's* deviation, not absolute values.
3. **Separates two different questions** that a single number tends to conflate:
   - *"Does this moment look statistically like the flagged class?"* — a
     `LogisticRegression` classifier, run fresh on every reading.
   - *"Is this person's signal progressively drifting away from where it started,
     sustained over time?"* — a **CUSUM (cumulative sum) drift detector**, the
     classical statistical-process-control tool for catching a persistent shift buried
     in noisy, high-recall-but-low-precision classifier output. This is what actually
     drives the dashboard's alert — not the noisier per-moment classification.

## The ML, specifically

Two logistic regression models, trained via cross-validated (`GroupKFold` by recording,
so no subject leaks between train/test) evaluation on curated PSG windows:

| Model | Features | Uses heart rate? | AUC | Recall | Precision | F1 | Training windows |
|---|---|---|---|---|---|---|---|
| **B — deployed** | 16 (adds heart-rate value/baseline-z/delta) | ✅ | 0.627 | 1.00 | 0.693 | 0.819 | 2,075 (26 recordings) |
| A — fallback | 13 (no heart rate) | ❌ | 0.578 | 1.00 | 0.535 | 0.697 | 3,440 (43 recordings) |

The backend automatically falls back from B to A whenever `heart_rate_bpm` is missing
from a reading — the same interface, the same response shape, just a different model
underneath, chosen per-request.

Both models are deliberately simple (logistic regression, not a deep net): the curated
training set is small (dozens of recordings, thousands of non-overlapping 180-second
windows), and a more data-hungry architecture would be over-fit far more than it would
be honest. **Recall is a perfect 1.0 at the operating threshold** — the models are tuned
to never miss a flagged window — which means precision is moderate and a single reading
being "flagged" happens often; that's exactly why the CUSUM drift detector, not the raw
per-window flag, is what actually triggers a dashboard alert.

The **CUSUM detector** accumulates the classifier's flagged-probability stream against a
fitted `target`/`k`/`h` (from the same training run's normal-window score distribution)
and only fires once the *sustained*, one-sided deviation crosses `h` — in training this
found real drift at a median of ~8.5 windows (≈25 minutes at the real 180-second
window length) after onset, while resisting one-off noisy spikes.

*(Honesty note, straight from the model card: this is a small-N curated research subset
— indicative of what's possible, not a clinical claim. PSG-channel features are used as
proxies for what a radio sensor would eventually measure; real hardware will need its
own calibration pass before these exact numbers transfer.)*

## Where WiFi sensing is today vs. where it's going

**Today:** the actual ESP32 pair hasn't been acquired yet, so the backend runs a
realistic **mock sensing server** that emits the same canonical reading shape a real
sensor would (breathing rate + variability, motion index, sleep fragmentation, sleep
onset latency, presence confidence, heart rate) and feeds it through the *exact same*
real model + CUSUM pipeline described above — nothing about the ML or the dashboard is
simulated, only the sensor input is. Every reading is honestly stamped
`"source": "mock"` end to end, in the API response and in the UI, specifically so
fabricated data can never be mistaken for a real signal.

**The hardware plan (documented, not yet built):** two ESP32 WROOM-32E boards running
Espressif's official `esp-csi` firmware (`csi_send` on one, `csi_recv` on the other),
feeding a Pulse-Fi-inspired processing pipeline (bandpass + peak detection for breathing
and motion; a small LSTM stage for heart rate, calibrated against a MAX30102
pulse-oximeter reference) that outputs the identical schema with `"source": "esp32_csi"`.

**The reason this swap is a configuration change, not a rewrite:** every sensor,
real or mock, implements one interface —

```
SensingSource (interface)
├── LiveMockSource        — polls the mock server (what's wired in today)
├── LiveHardwareSource    — full method-signature shell + spec already written;
│                           every method raises NotImplementedError until hardware exists
└── DatasetReplaySource   — reserved for streaming precomputed PSG features (future batch)
```

Filling in `LiveHardwareSource`'s two methods (`__init__`, `poll()`) is meant to be the
*entire* integration task. The feature mapping, the trained models, the CUSUM detector,
and the dashboard don't change.

## What's actually running

```
┌─────────────────────┐      poll GET /api/v1/vital-signs      ┌──────────────────────┐
│   React dashboard    │ ───────────────────────────────────►  │   FastAPI backend     │
│   (frontend/)         │ ◄───────────────────────────────────  │  (sensing_server)     │
└─────────────────────┘   anomaly + drift + events, every 2.5s └──────────┬────────────┘
                                                                            │
                                                        classify_window()  │  track_drift()
                                                                            ▼
                                                              ┌───────────────────────┐
                                                              │  backend/model         │
                                                              │  LogisticRegression A/B │
                                                              │  + CUSUM detector       │
                                                              │  (trained on Sleep-EDF  │
                                                              │   + CAP PSG data)       │
                                                              └───────────────────────┘
```

- **`backend/sensing_server`** — FastAPI mock sensing server + inference host. Emits one
  reading every 2 seconds, runs it through the real model on every tick, exposes demo
  controls (`drift` scenario to walk a session toward the flagged band; `reset` to clear
  a session's personal baseline and re-arm the CUSUM).
- **`backend/model`** — the deployed model bundle (`acs_manifest.json`, both
  `.joblib` classifiers + their normalization files) and `infer.py`, the only place
  live readings are mapped into training feature space, normalized, classified, and run
  through CUSUM.
- **`backend/sensing`** — the `SensingSource` interface described above, plus a
  session-recorder utility (not currently wired into the live server) and the stubs for
  future dataset-replay and real-hardware sources.
- **`frontend`** — a React + Vite dashboard, a faithful visual port of the original
  design prototype, polling the backend every 2.5 seconds and rendering the real
  anomaly score, CUSUM drift state, and a live event timeline — no hardcoded or
  locally-simulated alert logic anywhere in it.
- **`index.html` / `support.js` / `uploads/`** — the original Claude Design prototype
  export this project's UI was built from. Kept as-is for reference; the active app is
  `frontend/`.

## Running it

```bash
# 1. Backend — mock sensor + real ML inference
cd backend/sensing_server
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt          # fastapi, uvicorn, scikit-learn, joblib, numpy
python app.py                            # http://localhost:5001

# 2. Frontend — dashboard
cd frontend
npm install
npm run dev                              # http://localhost:5173
```

Open the dashboard, watch the live (mock-sourced, model-scored) baseline for a few
seconds while the session calibrates, then use **"Drift vitals away from baseline"** to
watch the Anomaly Score climb and the CUSUM alert fire, or **"Reset session"** to start
over. See `backend/README.md` and `frontend/README.md` for the full API contract, the
exact feature pipeline, and the demo-control judgment calls.

## Project docs

- [`backend/README.md`](backend/README.md) — API contract, feature pipeline, CUSUM
  parameters, demo-control design notes
- [`frontend/README.md`](frontend/README.md) — dashboard data flow, what's real vs.
  cosmetic, honesty-pass notes on every field
- [`backend/sensing/README.md`](backend/sensing/README.md) — the `SensingSource`
  interface and hardware-swap plan in detail
