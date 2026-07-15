# Frontend

React + Vite dashboard for Ambient Care Sentinel — a faithful visual port of the original
`index.html` design prototype, driven entirely by the real ML backend
(`backend/sensing_server` + `backend/model`).

## Relationship to the original `index.html`

The root `index.html` + `support.js` are the Claude Design prototype (a custom `x-dc`
runtime). This app reuses its markup, class names, CSS, and chart helpers
(`src/dashboard.css` is the prototype's `<style>` block copied verbatim), but all data
now comes from the backend. The root files are left untouched.

Deliberate departures from the original:

1. **Fabricated patient identity removed** — the hard-coded "Room 204 · Subject WC-0142 ·
   Age 68 · Female" and "Dataset Replay Active" badge are replaced with an honest,
   reachability/`source`-driven disclosure pill.
2. **The old "Simulation Mode" popup, `Run Simulation` button, six canned disease
   patterns, and all local drift/tween logic are gone.** Every alert/score is now a real
   backend field.

## Stack

- **Vite + React 19.**
- **Plain ported CSS** (`dashboard.css`), not Tailwind — a verbatim visual port.
  (`@tailwindcss/vite` remains in `vite.config.js` but unused.)

## Structure

```
src/
├── api/sensingClient.js     GET vital-signs; POST scenario (incl. "drift"); POST reset
├── hooks/useVitalsFeed.js   single 2500ms poll -> real anomaly/drift/events; drift/reset actions
├── utils.js                 cosmetic chart helpers (clamp, waveform, motionBars, hypnogram, sparkLine)
├── dashboard.css            original prototype CSS, verbatim (+ source-pill additions)
└── App.jsx                  the dashboard + Drift/Reset demo controls
```

## How data is wired

There is **one data path**: `useVitalsFeed` polls `GET /api/v1/vital-signs` every 2.5s
(matching the backend's 2s tick). No local simulation, tween, or fallback exists. Every
poll response carries real model output, and `deriveView` reads it straight through:

- **Anomaly Score** (hero box) = `anomaly.score` (model probability × 100)
- **Alert theme** (`appCls: 'alert'`, "Requires clinical review", red accents) = the real
  **`drift.alert`** (CUSUM), NOT the per-window `anomaly.flagged` (which is almost always
  true at this recall=1.0 model's threshold and would keep the UI permanently red)
- **Drift Assessment** = "Progressive drift detected" / "No drift detected" +
  `drift.drift_score` (CUSUM) + `anomaly.score` (Model Probability) + top contributing
  feature from `anomaly.contributions`
- **AI Model** tile = real `model_used` ("Model B") — not a fabricated confidence %
- **Event Timeline** = the backend's real `events` log (Session started / Baseline
  calibrated / Drift mode started / Drift alert fired, with real timestamps)
- **Heart Rate** card = `heart_rate_bpm`, labeled "Fabricated (mock) · drives Model B
  verdict" (Model B depends on it directly; it is scenario-locked fake data)
- During the 3-window calibration, `calibrating` shows "Calibrating baseline…"

### Honesty pass on formerly-fake fields

The old dashboard fabricated per-disease names ("Insomnia Pattern"), a model
"confidence" %, a "probability" %, and canned timeline events. The trained model is a
**binary flagged/normal drift classifier only** — there is no per-disease classification —
so those are replaced with the generic-but-accurate "Progressive drift detected", the
real `model_used`, the real `anomaly.score`, and the real backend event log. The session
pill reflects real reachability: "Simulated feed · source: mock" when connected,
"Backend unreachable · retrying" otherwise (`backendReachable` starts unknown, not `true`).

## Demo controls (bottom-right)

Replaces the old Simulation popup, same location:

- **Drift vitals away from baseline** → `POST scenario="drift"`. The backend gently
  climbs (fabricated) heart rate as the dominant driver, while breathing, variability,
  motion, fragmentation trend up and presence trends down so the whole dashboard visibly
  moves. The Anomaly Score eases up gradually and the CUSUM `drift.alert` fires ~15 ticks
  (~30s) later, flipping the dashboard into the red alert state.
- **Reset session** → `POST /api/v1/sensing/reset`. Fresh baseline + CUSUM, back to normal.

## Running

```bash
# Backend (separate terminal) — needs scikit-learn/joblib/numpy (in requirements.txt)
cd ../backend/sensing_server && source venv/bin/activate && pip install -r requirements.txt && python app.py

# Frontend
npm install
npm run dev   # http://localhost:5173
```

CORS is enabled on `sensing_server` for any `localhost`/`127.0.0.1` origin.

## Verified

Drove the app headless (Playwright + system Chrome) against both servers:
- **Normal**: green "No drift detected", Anomaly 14, CUSUM 0.00, Model B, HR 70 bpm.
- **Drift**: clicked "Drift vitals away from baseline" — all vitals trended (HR 68→150,
  breathing/motion/fragmentation up, presence down), the Anomaly Score eased up as a
  gradual S-curve, and the CUSUM alert fired at ~15 ticks (~30s): full red theme,
  "Progressive drift detected", real event timeline ("Drift alert fired"). 0 console errors.
- **Reset**: alert cleared, back to normal, event log reset.
```
