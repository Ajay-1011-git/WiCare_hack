import random
import sys
import threading
import time
from pathlib import Path
from typing import List, Literal, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Real ML inference lives in backend/model/infer.py (sibling package dir).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "model"))
import infer  # noqa: E402

app = FastAPI(title="WiCare Sensing Server (mock)")

# Local-dev CORS only: the frontend (Vite dev server, default port 5173) runs on a
# different origin than this API. Matches any localhost/127.0.0.1 port rather than
# hardcoding 5173, since Vite falls back to other ports if 5173 is taken.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class BreathingRate(BaseModel):
    value: float
    variability: float


class Contribution(BaseModel):
    feature: str
    contribution: float


class Anomaly(BaseModel):
    # Real per-window classifier output (backend/model/infer.py). score = model
    # probability * 100. NOTE: at the model's operating threshold (recall=1.0, low
    # precision) almost every window reads flagged=True; the meaningful progressive
    # signal is the CUSUM `drift` block, not this per-window flag.
    score: float
    threshold: int
    flagged: bool
    verdict: str
    method: str  # "ml_model"
    model_used: str  # "A" | "B"
    contributions: List[Contribution]


class Drift(BaseModel):
    # CUSUM over the classifier's probability stream (manifest cusum params). `alert`
    # latches true until POST /api/v1/sensing/reset.
    drift_score: float
    alert: bool


class Event(BaseModel):
    time: str
    desc: str
    alertCls: str


class VitalSigns(BaseModel):
    breathing_rate_bpm: BreathingRate
    motion_index: float
    sleep_fragmentation_index: float
    sleep_onset_latency: float
    presence_confidence: float
    heart_rate_bpm: Optional[float] = None
    anomaly: Anomaly
    drift: Drift
    events: List[Event]
    model_used: str
    calibrating: bool
    source: str = "mock"


# "drift" is not a steady baseline like the others -- it's a progressive trend applied
# on top of the CURRENT vitals (see LiveState._tick_locked). normal/elevated_activity/
# reduced_activity remain alternate steady baselines.
ScenarioName = Literal["normal", "elevated_activity", "reduced_activity", "drift"]


class ScenarioRequest(BaseModel):
    scenario: ScenarioName


# Steady-baseline scenarios. heart_rate_bpm is fabricated (scenario-locked) and DOES
# feed Model B's verdict -- a deliberate, owner-approved choice (see acs_manifest.json
# deployment_note). Only real ESP32+MAX30102 hardware would make it genuine.
SCENARIOS: dict = {
    "normal": {
        "breathing_value": 15.1,
        "breathing_variability": 1.3,
        "motion_index": 0.12,
        "sleep_fragmentation_index": 0.03,
        "sleep_onset_latency": 14.0,
        "presence_confidence": 0.98,
        "heart_rate_bpm": 68.0,
    },
    "elevated_activity": {
        "breathing_value": 15.8,
        "breathing_variability": 2.1,
        "motion_index": 0.62,
        "sleep_fragmentation_index": 0.08,
        "sleep_onset_latency": 15.0,
        "presence_confidence": 0.97,
        "heart_rate_bpm": 78.0,
    },
    "reduced_activity": {
        "breathing_value": 12.5,
        "breathing_variability": 0.8,
        "motion_index": 0.05,
        "sleep_fragmentation_index": 0.02,
        "sleep_onset_latency": 45.0,
        "presence_confidence": 0.92,
        "heart_rate_bpm": 58.0,
    },
}


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


class LiveState:
    """Generates one aggregated mock reading per 2s tick and runs it through the real ML
    inference (infer.process) each tick, so the CUSUM advances once per window regardless
    of HTTP poll rate. In "drift" mode it biases the walk toward the model's flagged band.

    Drift direction note: the deployed model is heart-rate-dominated (see README) -- only
    rising heart_rate_bpm cleanly raises its flagged probability; the other vitals'
    personal-baseline (*_zbase) terms are inversely signed, so pushing them up hard would
    SUPPRESS the alert. Drift therefore climbs HR strongly (elevated/erratic) while the
    other vitals trend up mildly and plateau, so they trend visually without cancelling
    the HR signal. This fires the CUSUM at a median of ~12 ticks (~24s)."""

    TICK_SECONDS = 2.0

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.scenario: str = "normal"
        self.drift_mode = False
        self._apply_scenario_locked("normal")
        self._latest = infer.process(self._reading_locked())
        self._stop = False
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _apply_scenario_locked(self, scenario: str) -> None:
        base = SCENARIOS[scenario]
        self.scenario = scenario
        self.breathing_value = base["breathing_value"]
        self.breathing_variability = base["breathing_variability"]
        self.motion_index = base["motion_index"]
        self.sleep_fragmentation_index = base["sleep_fragmentation_index"]
        self.sleep_onset_latency = base["sleep_onset_latency"]
        self.presence_confidence = base["presence_confidence"]
        self.heart_rate_bpm = base["heart_rate_bpm"]

    def _reading_locked(self) -> dict:
        return {
            "breathing_rate_bpm": {
                "value": self.breathing_value,
                "variability": self.breathing_variability,
            },
            "motion_index": self.motion_index,
            "sleep_fragmentation_index": self.sleep_fragmentation_index,
            "sleep_onset_latency": self.sleep_onset_latency,
            "presence_confidence": self.presence_confidence,
            "heart_rate_bpm": self.heart_rate_bpm,
        }

    def set_scenario(self, scenario: str) -> None:
        with self._lock:
            if scenario == "drift":
                # Do NOT reset the inference session (baseline/CUSUM stay put) -- scores
                # climb from where they are. But snap the NON-HR model features back to
                # the calibration baseline so their inversely-signed *_zbase terms sit at
                # ~0 and don't drag the plateau probability down. Without this, a long
                # normal run lets motion/frag/breathing random-walk away from baseline,
                # adding constant drag that stalls the CUSUM. HR (the real driver) is left
                # at its current value and climbs from there.
                base = SCENARIOS["normal"]
                self.breathing_value = base["breathing_value"]
                self.breathing_variability = base["breathing_variability"]
                self.motion_index = base["motion_index"]
                self.sleep_fragmentation_index = base["sleep_fragmentation_index"]
                self.drift_mode = True
            else:
                self.drift_mode = False
                self._apply_scenario_locked(scenario)
        if scenario == "drift":
            infer.mark_drift_started()

    def reset(self) -> None:
        with self._lock:
            self.drift_mode = False
            self._apply_scenario_locked("normal")
        infer.reset()  # fresh baseline buffer, CUSUM 0, alert un-latched
        with self._lock:
            self._latest = infer.process(self._reading_locked())

    def _tick_locked(self) -> None:
        if self.drift_mode:
            self._drift_tick_locked()
        else:
            self._normal_tick_locked()

    def _normal_tick_locked(self) -> None:
        # Symmetric bounded random walk (steady baseline).
        self.breathing_value = _clamp(
            self.breathing_value + (random.random() - 0.5) * 0.6, 11.0, 20.0
        )
        self.motion_index = _clamp(
            self.motion_index + (random.random() - 0.5) * 0.02, 0.0, 1.0
        )
        self.sleep_fragmentation_index = _clamp(
            self.sleep_fragmentation_index + (random.random() - 0.5) * 0.01, 0.0, 1.0
        )
        self.presence_confidence = _clamp(
            self.presence_confidence + (random.random() - 0.5) * 0.012, 0.85, 1.0
        )
        self.heart_rate_bpm = _clamp(
            self.heart_rate_bpm + (random.random() - 0.5) * 2.0, 50.0, 100.0
        )

    def _drift_tick_locked(self) -> None:
        # Heart rate is the dominant real driver of this model (+0.97 base coef), so it
        # carries the alert -- climbed gently (~4.5 bpm/tick + jitter) so the score eases
        # up as a gradual S-curve rather than spiking. The other model features
        # (breathing, variability, motion, fragmentation) also trend up by a SMALL amount
        # so the whole dashboard visibly moves, not just HR. Their movement is kept modest
        # and capped: their *_zbase terms are inversely signed, so large upward moves would
        # SUPPRESS the alert -- the personal-baseline std floor (infer._STD_FLOOR) bounds
        # that drag enough for mild movement to be safe. Net effect: HR still wins, all
        # vitals trend, CUSUM fires at a median of ~15 ticks (~30s). See the "Drift demo"
        # section of backend/README.md.
        self.heart_rate_bpm = _clamp(
            self.heart_rate_bpm + 4.5 + (random.random() - 0.5) * 1.5, 50.0, 150.0
        )
        self.breathing_value = _clamp(self.breathing_value + 0.12 * random.random(), 11.0, 18.5)
        self.breathing_variability = _clamp(
            self.breathing_variability + 0.05 * random.random(), 0.5, 3.0
        )
        self.motion_index = _clamp(self.motion_index + 0.010 * random.random(), 0.0, 0.35)
        self.sleep_fragmentation_index = _clamp(
            self.sleep_fragmentation_index + 0.004 * random.random(), 0.0, 0.08
        )
        # presence is NOT a model feature -> drifts down for visual life only.
        self.presence_confidence = _clamp(
            self.presence_confidence - 0.006 * random.random(), 0.78, 1.0
        )

    def _run(self) -> None:
        while not self._stop:
            time.sleep(self.TICK_SECONDS)
            with self._lock:
                self._tick_locked()
                reading = self._reading_locked()
            result = infer.process(reading)  # SESSION lock only; not holding self._lock
            with self._lock:
                self._latest = result

    def snapshot(self) -> VitalSigns:
        with self._lock:
            latest = self._latest
            return VitalSigns(
                breathing_rate_bpm=BreathingRate(
                    value=round(self.breathing_value, 2),
                    variability=round(self.breathing_variability, 2),
                ),
                motion_index=round(self.motion_index, 3),
                sleep_fragmentation_index=round(self.sleep_fragmentation_index, 3),
                sleep_onset_latency=round(self.sleep_onset_latency, 1),
                presence_confidence=round(self.presence_confidence, 3),
                heart_rate_bpm=round(self.heart_rate_bpm, 1),
                anomaly=latest["anomaly"],
                drift=latest["drift"],
                events=latest["events"],
                model_used=latest["model_used"],
                calibrating=latest["calibrating"],
            )


state = LiveState()


@app.get("/api/v1/vital-signs", response_model=VitalSigns)
def vital_signs() -> VitalSigns:
    return state.snapshot()


@app.get("/api/v1/sensing/latest", response_model=VitalSigns)
def sensing_latest() -> VitalSigns:
    return state.snapshot()


@app.post("/api/v1/sensing/scenario", response_model=VitalSigns)
def set_scenario(req: ScenarioRequest) -> VitalSigns:
    state.set_scenario(req.scenario)
    return state.snapshot()


@app.post("/api/v1/sensing/reset", response_model=VitalSigns)
def reset_session() -> VitalSigns:
    state.reset()
    return state.snapshot()


@app.get("/api/v1/model-card")
def model_card() -> dict:
    return infer.model_card()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5001)
