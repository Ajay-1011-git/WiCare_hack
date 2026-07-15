# Sensing Server

A small, self-contained local mock server standing in for the live-sensing layer described in
`02-trd.md` §6. This is the first backend in the repo — previously WiCare was frontend-only
(static dashboard).

This server generates believable, fabricated readings server-side, matching the canonical
feature schema (`02-trd.md` §3). It is explicitly documented as fabricated data, not a claim
of real sensing — this is what "Live" mode talks to today, pending a future, independently
verified real-hardware `LiveHardwareSource` (see `02-trd.md` §6.3).

## Framework choice: FastAPI

No existing backend language/framework was established in this repo, so this defaults to
Python/FastAPI: minimal boilerplate for a couple of JSON GET endpoints, built-in request
validation and response schemas via Pydantic, and free interactive docs at `/docs`.

## Setup

```bash
cd backend/sensing_server
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

Server runs on `http://localhost:5001`.

## Endpoint contract

Both endpoints return the same JSON shape (canonical schema, `02-trd.md` §3):

```json
{
  "breathing_rate_bpm": { "value": 15.19, "variability": 1.3 },
  "motion_index": 0.114,
  "sleep_fragmentation_index": 0.034,
  "sleep_onset_latency": 14.0,
  "presence_confidence": 0.97,
  "heart_rate_bpm": 70.3,
  "source": "mock"
}
```

- `breathing_rate_bpm.value` / `.variability` — breaths per minute, and variability of that rate
- `motion_index` — normalized (0-1) motion activity level
- `sleep_fragmentation_index` — normalized (0-1) sleep fragmentation score
- `sleep_onset_latency` — minutes to sleep onset
- `presence_confidence` — confidence (0-1) that a person is present
- `heart_rate_bpm` — beats per minute; nullable/optional per the TRD (new field, hardest to
  get reliable, treated as a stretch goal not a dependency). Currently a fabricated, drifting
  simulated value in this mock server; a real value would eventually come from the future
  ESP32 CSI + Pulse-Fi-style pipeline (§7), which this server does not implement
- `source` — always `"mock"` on every response from this server, so downstream consumers (and
  demo materials) can never mistake this for real sensor output

### `GET /api/v1/vital-signs`

Breathing/motion/confidence fields for the current live (drifting) reading.

### `GET /api/v1/sensing/latest`

Same shape as above — latest raw sensing frame, includes `source` per TRD §6.2.

### `POST /api/v1/sensing/scenario`

Forces the server into a named state, snapping all fields to that scenario's baseline (drift
then continues from there). Body: `{"scenario": "normal" | "elevated_activity" |
"reduced_activity"}`. Returns the resulting vital-signs snapshot (same shape as the GET
endpoints). Unknown scenario names are rejected with `422`.

## Live drift

Values aren't static — a background tick every 2 seconds nudges `breathing_rate_bpm.value`,
`motion_index`, `sleep_fragmentation_index`, `presence_confidence`, and `heart_rate_bpm` by a
small random amount off their *previous* value, clamped to fixed bounds (bounded random walk,
not independent jumps). This mirrors the dashboard's own `ambientTick()` in `index.html`
(2s interval, `clamp(v + (Math.random()-0.5)*delta, lo, hi)`), scaled from the dashboard's
0-100 units into this API's 0-1 fractions where applicable. `sleep_onset_latency` and
`breathing_rate_bpm.variability` stay fixed per scenario, same as the dashboard — its
`ambientTick()` never drifts those two either. `heart_rate_bpm` has no dashboard-side
equivalent to mirror (no ECG channel upstream — see TRD §3), so it's nudged in the same
random-walk style but with this server's own fabricated, resting-range bounds (50-100 bpm).

## Scenarios

The three named scenarios reuse the dashboard's own `REF` reference data (`index.html`),
converted into this API's units (motion/fragmentation/presence: dashboard's 0-100 ÷ 100):

| Scenario | Dashboard source | breathing (bpm) | motion_index | fragmentation | onset (min) | presence | heart_rate_bpm* |
|---|---|---|---|---|---|---|---|
| `normal` | `REF.healthy` | 15.1 ± 1.3 | 0.12 | 0.03 | 14.0 | 0.98 | 68 |
| `elevated_activity` | `REF.rem_behavior` (closest dashboard match for high motion) | 15.8 ± 2.1 | 0.62 | 0.08 | 15.0 | 0.97 | 78 |
| `reduced_activity` | `REF.unknown` (closest dashboard match for low motion) | 12.5 ± 0.8 | 0.05 | 0.02 | 45.0 | 0.92 | 58 |

\* `heart_rate_bpm` has no dashboard equivalent — these baselines are this server's own
fabricated placeholders, not derived from `index.html`.

Note: the dashboard has no scenarios literally named `elevated_activity`/`reduced_activity` —
its actual scenario keys are `healthy`, `apnea`, `insomnia`, `rem_behavior`, `rls`,
`narcolepsy`, `unknown`. The two picked above are the closest numeric matches (by
`motion_index`) to "more/less motion than baseline."

## Current status

Simulation only. `heart_rate_bpm` in particular is fabricated end-to-end here — real
heart-rate sensing is a separate, later, hardware-dependent effort (TRD §7), not attempted
by this server.
