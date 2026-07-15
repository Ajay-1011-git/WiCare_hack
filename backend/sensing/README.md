# sensing

Implements the `SensingSource` interface from `02-trd.md` §6.3.

```
SensingSource (interface)
├── DatasetReplaySource   — stub; reserved for the Sleep-EDF/CAP + Colab batch pipeline
├── LiveMockSource        — polls backend/sensing_server, maps to canonical schema
└── LiveHardwareSource    — stub; reserved for the real ESP32 CSI pipeline (§7)
```

`SensingSource.poll()` is the only method every source implements. Callers only ever
depend on that one method returning the canonical schema shape (`02-trd.md` §3) —
swapping which concrete source is active is a configuration change, not a rewrite.

## `DatasetReplaySource` (`dataset_replay_source.py`)

Stub only. The Sleep-EDF SC/CAP feature-extraction pipeline it will eventually replay
from doesn't exist yet — every method raises `NotImplementedError`. Do not fill in its
internals until that pipeline (EDF parsing, per-epoch features, ground-truth
validation, cached Parquet/JSON) is actually built.

## `LiveMockSource` (`live_source.py`)

Polls `backend/sensing_server`'s `GET /api/v1/sensing/latest` and maps the response
into the canonical schema. Since the mock server already emits that shape directly,
the mapping is close to 1:1 (see `_map()`).

### CLI smoke test

```bash
cd backend/sensing_server && source venv/bin/activate && python app.py &   # start the mock server
cd ../..
python3 -m venv backend/venv && source backend/venv/bin/activate
pip install -r backend/sensing/requirements.txt
python -m backend.sensing.live_source --poll 5
```

Prints 5 mapped canonical-schema dicts, one per second, polled from the running mock
server.

## `LiveHardwareSource` (`live_hardware_source.py`)

Shell only — no ESP32 hardware exists in-hand yet. `__init__` and `poll()` mirror
`LiveMockSource`'s signatures exactly and both raise `NotImplementedError`. The class
docstring is the full spec for what each method will do once real hardware arrives
(poll two ESP32 boards running `esp-csi`'s `csi_send`/`csi_recv`, run the Pulse-Fi-style
processing pipeline per `02-trd.md` §7, return the canonical schema with
`"source": "esp32_csi"`). Per §6.3, filling in this one file's method bodies should be
the entire hardware-integration task.

## `session_recorder.py`

`sleep_fragmentation_index` and `sleep_onset_latency` aren't available as single-poll
fields (`02-trd.md` §3-4) — they're derived from a session's motion/presence history
over time, mirroring how the dataset side derives them from a whole night's hypnogram.

`SessionRecorder`:
- `record(reading)` — appends the poll's `motion_index`/`presence_confidence` to an
  in-memory rolling window (`deque(maxlen=window_size)`) and appends the same entry as
  a JSON line to `backend/data/sessions/<session_id>.jsonl`.
- `compute_derived_features()` — from the window recorded so far:
  - `sleep_onset_latency`: minutes from session start to the first "asleep-like"
    epoch (`motion_index < AWAKE_MOTION_THRESHOLD`, currently `0.3` — the midpoint
    between `sensing_server`'s own `normal` (0.12) and `elevated_activity` (0.62)
    baselines; a documented heuristic, not a clinical threshold).
  - `sleep_fragmentation_index`: awake↔asleep transition count in the window,
    normalized to transitions/hour and capped at 1.0 assuming 20/hour as a
    "maximally fragmented" ceiling (also a documented, not derived, assumption).

Both are `None` until at least one reading has been recorded (and `sleep_onset_latency`
stays `None` if no asleep-like epoch has occurred yet).

## Data layout

```
backend/data/sessions/<session_id>.jsonl   # one JSON object per line, per poll
```

`session_id` defaults to a `YYYYMMDDTHHMMSS` timestamp if not supplied.
