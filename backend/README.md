# Backend

Ambient Care Sentinel's sensing + inference layer. The mock `sensing_server` emits one
aggregated vital-signs reading per 2s tick and runs each reading through a **real trained
ML drift-detection model** (`backend/model/infer.py`). Every alert/score the dashboard
shows traces to an actual `classify_window()` + `track_drift()` call — there is no
hardcoded or locally-simulated alert behaviour anywhere.

## Layout

```
backend/
├── model/               deployed model bundle + inference
│   ├── acs_manifest.json          model card, cusum params, deployed = "B"
│   ├── acs_model_{A,B}.joblib      LogisticRegression classifiers
│   ├── acs_model_{A,B}_norm.json   feature_order + per-source z-score + impute + settle
│   └── infer.py                    SessionState, feature mapping, classify_window, track_drift
├── sensing_server/      FastAPI mock server (app.py) — the live feed + inference host
├── sensing/             SensingSource interface, LiveMockSource, session_recorder (unchanged)
└── scripts/             smoke_test.py
```

## Run

```bash
cd backend/sensing_server
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt          # fastapi, uvicorn, scikit-learn, joblib, numpy
python app.py                            # http://localhost:5001
```

## The model

Two `LogisticRegression` classifiers trained on curated Sleep-EDF SC + CAP windows.
Normal class = healthy; flagged class = CAP SDB + PLM + insomnia. Figures from
`acs_manifest.json` (small-N curated subset — indicative, not clinical):

| Model | Uses HR? | AUC | Recall | Precision | F1 |
|---|---|---|---|---|---|
| **B (deployed)** | yes (16 feats) | 0.627 | 1.00 | 0.693 | 0.819 |
| A (fallback) | no (13 feats) | 0.578 | 1.00 | 0.535 | 0.697 |

`classify_window()` uses **Model A whenever `heart_rate_bpm` is missing**, else the
deployed Model B. Recall is 1.0 with low precision, so at the operating threshold almost
every single window reads `flagged=true` — **the per-window `anomaly.flagged` is NOT the
demo's alert signal**. The meaningful, progressive signal is the CUSUM `drift.alert`.

### Feature pipeline (per window)

`infer.py` maps the live reading to training feature names (the live payload nests
breathing under `breathing_rate_bpm.{value,variability}`; training used flat
`breathing_rate_bpm`/`breathing_var`), then builds the vector in `feature_order`:

- **base**: breathing_rate_bpm, breathing_var, motion_index, sleep_fragmentation_index,
  sleep_onset_latency, heart_rate_bpm
- **`*_zbase`**: z-score of each base feature vs THIS session's personal baseline
  (mean/std of the first `settle_windows`=3 readings)
- **`*_delta`**: current − previous reading

Each entry is z-normalized with `per_source_zscore["cap:<feature>"]` and missing values
imputed with `impute_fill` (both from the model's norm.json). `cap` is the only source
Model B carries and best matches the mock's CAP-style windows.

### CUSUM drift detector

`track_drift(probability)` runs a one-sided upper CUSUM over the classifier's probability
stream using `manifest["cusum"]` (target 0.4525, k 0.164, h 1.639). `drift.alert`
**latches true until `POST /api/v1/sensing/reset`** — it never auto-resets. In training,
CUSUM detected drift at a **median of ~8.5 windows**; the mock fires at ~15 ticks
(~30s at the 2s tick — the heart-rate climb is deliberately gentle so the score eases up
gradually). (Training also false-alarmed on 3/8 normal subjects — CUSUM
`target/k/h` are fit to that run's normal-score distribution; re-fit if the model changes.)

### Windowing note

Training used 180s aggregated windows over raw signal. This mock already emits one
aggregated reading per tick with no raw signal to window, so **each tick's reading is
treated as one window's features directly** (one `classify_window()`+`track_drift()` per
tick). Real ESP32/MAX30102 hardware would need a genuine 180s signal-aggregation stage
before `infer.py`.

## API

`GET /api/v1/vital-signs` and `GET /api/v1/sensing/latest` return the full reading:

```jsonc
{
  "breathing_rate_bpm": { "value": 15.1, "variability": 1.3 },
  "motion_index": 0.12,
  "sleep_fragmentation_index": 0.03,
  "sleep_onset_latency": 14.0,
  "presence_confidence": 0.98,
  "heart_rate_bpm": 70.0,
  "anomaly": {                       // classify_window() — real model output
    "score": 14.0,                   // model probability * 100
    "threshold": 1,                  // operating_threshold * 100 (very low; see above)
    "flagged": true,                 // per-window; almost always true — NOT the alert
    "verdict": "Requires clinical review",
    "method": "ml_model",
    "model_used": "B",               // "A" if heart_rate_bpm missing
    "contributions": [ { "feature": "heart_rate_bpm", "contribution": 3.85 }, ... ]
  },
  "drift": {                         // track_drift() — the real CUSUM, THIS is the alert
    "drift_score": 0.0,
    "alert": false                   // latches true until /reset
  },
  "events": [ { "time": "12:18:37", "desc": "Baseline calibrated", "alertCls": "" }, ... ],
  "model_used": "B",
  "calibrating": true,               // true during the first settle_windows readings
  "source": "mock"
}
```

- `POST /api/v1/sensing/scenario` — body `{"scenario": "normal"|"elevated_activity"|"reduced_activity"|"drift"}`
- `POST /api/v1/sensing/reset` — fresh session (baseline buffer + CUSUM cleared, alert un-latched, back to normal)
- `GET /api/v1/model-card` — deployed model metrics + cusum params

## Demo controls

- **"Drift vitals away from baseline"** (`scenario=drift`): progressively pushes the
  session toward the flagged band **without** resetting the baseline/CUSUM, so this
  session's own scores climb from where they are. Watch the Anomaly Score climb and the
  CUSUM alert fire ~15 ticks (~30s) later.
- **"Reset session"**: fresh `SessionState`, mock generator back to normal.

### Why drift is heart-rate-dominant (important judgment call)

The task spec described drift as pushing *breathing variability, fragmentation, motion,
and heart rate* all up together. Empirically, **this delivered model is heart-rate-
dominated**: `heart_rate_bpm` has a large positive coefficient (+0.97) while the other
vitals' `*_zbase` terms are strongly *negatively* signed (motion_zbase −1.25,
frag_zbase −0.77). So pushing motion/fragmentation up actually *suppresses* the flagged
probability and prevents the alert. Only rising heart rate cleanly raises it. This is
consistent with the manifest's own note: *"Demo heart rate is fabricated (scenario-
locked) and DOES feed Model B's verdict — a deliberate, owner-approved choice."*

So `drift` climbs **heart rate** as the dominant driver (fabricated, elevated/erratic,
~68→150 bpm, gently so the score eases up). The other model features (breathing,
variability, motion, fragmentation) also trend up by a **small, capped** amount and
presence drifts down, so the whole dashboard visibly moves — not just HR. Their movement
is kept modest on purpose: their inversely-signed `zbase` terms would suppress the alert
if pushed too far, and the personal-baseline std floor (below) bounds that drag enough
for mild movement to be safe. On drift start it snaps motion/frag/breathing back to
baseline (so a long prior normal run doesn't leave them drifted and dragging the score
down) — this does not reset the CUSUM or baseline.

### Personal-baseline std floor

The mock's calibration readings are very smooth, so the std of the first 3 readings can
be near-zero, making `zbase = (value−mean)/std` hypersensitive — ordinary normal-mode
wander then spikes the probability and **false-alarms the CUSUM**. `infer._STD_FLOOR`
floors each feature's personal std to a realistic within-subject spread, which removes
normal-mode false alarms (verified 0 over 6×300 ticks) while keeping drift firing. Real
180s hardware windows would have natural variance and would not need this.

## Fabricated heart rate

`heart_rate_bpm` is **fabricated** (scenario-locked) by the mock server. It is the demo's
main verdict driver by design (see above), but it is not a real physiological reading —
only genuine **ESP32 + MAX30102** hardware would make it real. Every raw reading is still
stamped `"source": "mock"`; this must never be silently dropped or hidden.

## Adding real hardware

`02-trd.md` §7: acquire 2× ESP32 + 1× MAX30102, flash `esp-csi` `csi_send`/`csi_recv`,
implement `backend/sensing/live_hardware_source.py` (raw CSI → Pulse-Fi-style pipeline →
canonical schema with `"source": "esp32_csi"`), add the 180s windowing stage before
`infer.py`, and re-fit the CUSUM `target/k/h` on real normal-window scores. The model,
inference, and dashboard are otherwise unchanged — the dashboard already switches its
"Live sensor" label on `source == "esp32_csi"`.
```
