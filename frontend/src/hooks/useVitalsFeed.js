import { useEffect, useMemo, useRef, useState } from 'react'
import { fetchVitalSigns, postScenario, resetSession } from '../api/sensingClient'
import {
  clamp,
  generateHypnogram,
  generateMotionBars,
  generateWaveform,
  sparkLine,
} from '../utils'

const POLL_INTERVAL_MS = 2500 // the single, only data path — matches the 2s backend tick
const WAVE_INTERVAL_MS = 100 // waveform + clock animation cadence (cosmetic only)

function getClock() {
  return new Date().toLocaleTimeString('en-US', { hour12: false })
}

// Map a backend /vital-signs response into the flat shape the render helpers expect.
// Backend uses 0-1 fractions for motion/fragmentation/presence; the dashboard uses
// 0-100 (motion, presence) and events/hr (fragmentation) — the *100 conversion lines up
// with the dashboard's scale (backend normal frag 0.03 -> 3 events/hr). EVERY alert/score
// field here comes straight from the real backend response (anomaly = classify_window,
// drift = track_drift); nothing is locally invented or tweened.
function mapReading(data) {
  return {
    breathVal: data.breathing_rate_bpm.value,
    breathVar: data.breathing_rate_bpm.variability,
    motion: data.motion_index * 100,
    frag: data.sleep_fragmentation_index * 100,
    presence: data.presence_confidence * 100,
    onset: data.sleep_onset_latency,
    heartRate: data.heart_rate_bpm,
    // real ML outputs
    anomaly: data.anomaly, // { score, threshold, flagged, verdict, method, model_used, contributions }
    drift: data.drift, // { drift_score, alert }
    events: data.events, // real state-transition log from the backend
    modelUsed: data.model_used,
    calibrating: data.calibrating,
  }
}

// Turns the latest reading + cosmetic timeOffset into the values the template binds.
// The alert visual state is driven by the real CUSUM drift.alert, NOT by local logic.
function deriveView(state) {
  const v = state.v
  if (!v) {
    // before the first successful poll
    return { pending: true, appCls: '', timeline: [], motionBars: [], hypnoBlocks: [] }
  }
  const drift = v.drift || { drift_score: 0, alert: false }
  const anomaly = v.anomaly || {}
  const calibrating = v.calibrating
  const alert = !!drift.alert
  const score = clamp(Math.round(anomaly.score ?? 0), 0, 100)
  const topDriver = (anomaly.contributions && anomaly.contributions[0]) || null

  return {
    pending: false,
    appCls: alert ? 'alert' : '',
    alert,
    calibrating,
    breathVal: v.breathVal.toFixed(1),
    motionVal: Math.round(v.motion),
    fragVal: Math.round(v.frag),
    presenceVal: Math.round(v.presence),
    heartRateVal: v.heartRate == null ? '—' : Math.round(v.heartRate),
    breathWave: generateWaveform(v.breathVal, v.breathVar, state.timeOffset),
    motionBars: generateMotionBars(v.motion),
    fragSpark: sparkLine(v.frag),
    presenceSpark: sparkLine(v.presence),
    heartSpark: v.heartRate == null ? '' : sparkLine(v.heartRate / 10),
    hypnoBlocks: generateHypnogram(v.frag, v.onset),
    // Real model outputs
    anomalyVal: score,
    driftScore: (drift.drift_score ?? 0).toFixed(2),
    modelUsed: v.modelUsed,
    // Verdict / pattern label: generic + accurate (no fake per-disease names). During the
    // settle window we say "Calibrating"; otherwise it reflects the real CUSUM drift.alert.
    verdictText: calibrating ? 'Calibrating baseline…' : alert ? 'Requires clinical review' : 'No drift detected',
    patternLabel: calibrating ? 'Calibrating baseline…' : alert ? 'Progressive drift detected' : 'No drift detected',
    topDriver: topDriver ? topDriver.feature : null,
    // Probability tile = the real model probability (= anomaly.score). Model tile = model_used.
    probability: score,
    contributions: anomaly.contributions || [],
    timeline: v.events || [],
  }
}

export function useVitalsFeed() {
  const [state, setState] = useState(() => ({
    simOpen: true,
    showSettings: false,
    v: null, // filled from the first poll
    timeOffset: 0,
    timeStr: getClock(),
    source: null,
    backendReachable: null, // unknown until the first poll confirms it
    busy: false, // a drift/reset control request is in flight
  }))

  const stateRef = useRef(state)
  stateRef.current = state

  // Waveform + clock animation (cosmetic only; not a data path).
  useEffect(() => {
    const t = setInterval(() => {
      setState((prev) => ({ ...prev, timeOffset: prev.timeOffset + 1, timeStr: getClock() }))
    }, WAVE_INTERVAL_MS)
    return () => clearInterval(t)
  }, [])

  // The ONLY data path: poll the backend every 2.5s. No local simulation, no fallback.
  useEffect(() => {
    let cancelled = false
    const poll = async () => {
      try {
        const data = await fetchVitalSigns()
        if (cancelled) return
        setState((prev) => ({ ...prev, v: mapReading(data), source: data.source, backendReachable: true }))
      } catch {
        if (cancelled) return
        setState((prev) => ({ ...prev, backendReachable: false }))
      }
    }
    poll()
    const t = setInterval(poll, POLL_INTERVAL_MS)
    return () => {
      cancelled = true
      clearInterval(t)
    }
  }, [])

  async function driftVitals() {
    setState((prev) => ({ ...prev, busy: true }))
    try {
      const data = await postScenario('drift')
      setState((prev) => ({ ...prev, v: mapReading(data), source: data.source, backendReachable: true, busy: false }))
    } catch {
      setState((prev) => ({ ...prev, backendReachable: false, busy: false }))
    }
  }

  async function resetSessionAction() {
    setState((prev) => ({ ...prev, busy: true }))
    try {
      const data = await resetSession()
      setState((prev) => ({ ...prev, v: mapReading(data), source: data.source, backendReachable: true, busy: false }))
    } catch {
      setState((prev) => ({ ...prev, backendReachable: false, busy: false }))
    }
  }

  const view = useMemo(() => deriveView(state), [state])

  return {
    view,
    simOpen: state.simOpen,
    showSettings: state.showSettings,
    timeStr: state.timeStr,
    source: state.source,
    backendReachable: state.backendReachable,
    busy: state.busy,
    toggleSim: () => setState((prev) => ({ ...prev, simOpen: !prev.simOpen })),
    toggleSettings: () => setState((prev) => ({ ...prev, showSettings: !prev.showSettings })),
    driftVitals,
    resetSession: resetSessionAction,
  }
}
