"""Rolling-window session recorder. `sleep_fragmentation_index` and
`sleep_onset_latency` aren't single-poll fields (02-trd.md sections 3-4): on the
dataset side they come from a whole night's hypnogram; on the live side they must be
derived the same way, from a session's own motion/presence history over time. This
module accumulates that history per session, persists it, and computes the two
derived features from it.

Thresholds below are documented heuristics, not clinically validated values -- see
inline comments for where each number comes from.
"""

import json
import time
from collections import deque
from pathlib import Path
from typing import Any, Deque, Dict, Optional

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "sessions"

# A motion_index at/above this is treated as an "awake-like" epoch, below it as
# "asleep-like". Chosen as the midpoint between sensing_server's own scenario
# baselines (normal=0.12, elevated_activity=0.62) -- the value most likely to
# separate the two, not a derived/clinical threshold.
AWAKE_MOTION_THRESHOLD = 0.3

# Normalizes a raw awake<->asleep transition rate into a 0-1 index. 20 transitions/hour
# is an assumed "maximally fragmented" ceiling; a documented assumption, not fit to data.
MAX_EXPECTED_TRANSITIONS_PER_HOUR = 20.0


class SessionRecorder:
    def __init__(
        self,
        session_id: Optional[str] = None,
        window_size: int = 3600,
        data_dir: Path = DATA_DIR,
    ) -> None:
        self.session_id = session_id or time.strftime("%Y%m%dT%H%M%S")
        self.window: Deque[Dict[str, Any]] = deque(maxlen=window_size)
        self.session_start: Optional[float] = None
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.session_file = self.data_dir / f"{self.session_id}.jsonl"

    def record(self, reading: Dict[str, Any]) -> None:
        """Append one poll's motion/presence fields to the session window and persist
        it as a timestamped JSON line."""
        timestamp = time.time()
        if self.session_start is None:
            self.session_start = timestamp
        entry = {
            "timestamp": timestamp,
            "motion_index": reading["motion_index"],
            "presence_confidence": reading["presence_confidence"],
        }
        self.window.append(entry)
        with self.session_file.open("a") as f:
            f.write(json.dumps(entry) + "\n")

    def _is_awake(self, entry: Dict[str, Any]) -> bool:
        return entry["motion_index"] >= AWAKE_MOTION_THRESHOLD

    def compute_derived_features(self) -> Dict[str, Optional[float]]:
        """Derive sleep_fragmentation_index and sleep_onset_latency from the session
        window recorded so far."""
        if not self.window or self.session_start is None:
            return {"sleep_fragmentation_index": None, "sleep_onset_latency": None}

        onset_latency = None
        for entry in self.window:
            if not self._is_awake(entry):
                onset_latency = (entry["timestamp"] - self.session_start) / 60.0
                break

        transitions = 0
        prev_awake = None
        for entry in self.window:
            awake = self._is_awake(entry)
            if prev_awake is not None and awake != prev_awake:
                transitions += 1
            prev_awake = awake

        elapsed_hours = max(
            (self.window[-1]["timestamp"] - self.session_start) / 3600.0, 1e-6
        )
        transitions_per_hour = transitions / elapsed_hours
        fragmentation_index = min(
            1.0, transitions_per_hour / MAX_EXPECTED_TRANSITIONS_PER_HOUR
        )

        return {
            "sleep_fragmentation_index": round(fragmentation_index, 3),
            "sleep_onset_latency": (
                round(onset_latency, 1) if onset_latency is not None else None
            ),
        }
