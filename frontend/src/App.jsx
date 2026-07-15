import { useVitalsFeed } from './hooks/useVitalsFeed'
import './dashboard.css'

// Faithful port of the original design prototype (index.html), wired to the real ML
// backend. EVERY alert/score shown here comes straight from the backend response
// (anomaly = classify_window, drift = track_drift on the deployed model); there is no
// local simulation, tween, or hardcoded alert behaviour. The old fabricated patient
// identity is replaced with an honest source/reachability disclosure.

function Sidebar({ showSettings, toggleSettings }) {
  return (
    <aside className="sidebar">
      <div className="sb-logo">
        <svg viewBox="0 0 24 24"><path d="M22 12h-4l-3 9L9 3l-3 9H2"></path></svg>
      </div>
      <div className="sb-nav">
        <div className="sb-item active">
          <svg className="sb-icon"><rect x="3" y="3" width="7" height="7"></rect><rect x="14" y="3" width="7" height="7"></rect><rect x="14" y="14" width="7" height="7"></rect><rect x="3" y="14" width="7" height="7"></rect></svg>
          <span className="sb-label">Dashboard</span>
        </div>
        <div className="sb-item">
          <svg className="sb-icon"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M23 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path></svg>
          <span className="sb-label">Patients</span>
        </div>
        <div className="sb-item">
          <svg className="sb-icon"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
          <span className="sb-label">Live</span>
        </div>
        <div className="sb-item">
          <svg className="sb-icon"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
          <span className="sb-label">Replay</span>
        </div>
        <div className="sb-item">
          <svg className="sb-icon"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>
          <span className="sb-label">Model</span>
        </div>
        <div className="sb-item">
          <svg className="sb-icon"><ellipse cx="12" cy="5" rx="9" ry="3"></ellipse><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"></path><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"></path></svg>
          <span className="sb-label">Datasets</span>
        </div>
      </div>

      <div style={{ marginTop: 'auto', display: 'flex', flexDirection: 'column', gap: '16px', alignItems: 'center' }}>
        <svg className="hdr-icon" onClick={toggleSettings}><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path><path d="M13.73 21a2 2 0 0 1-3.46 0"></path></svg>
        <svg className="hdr-icon" onClick={toggleSettings}><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg>
        <div className="hdr-avatar" onClick={toggleSettings}>AR</div>

        {showSettings && (
          <div className="settings-menu">
            <div className="sm-item"><svg className="sm-icon"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg> Profile</div>
            <div className="sm-item"><svg className="sm-icon"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg> Settings</div>
            <div className="sm-item" style={{ color: 'var(--color-red)' }}><svg className="sm-icon" style={{ stroke: 'var(--color-red)' }}><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path><polyline points="16 17 21 12 16 7"></polyline><line x1="21" y1="12" x2="9" y2="12"></line></svg> Log out</div>
          </div>
        )}
      </div>
    </aside>
  )
}

const statLabel = { fontSize: '10px', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '8px' }
const statVal = { fontSize: '14px', fontWeight: 500, color: 'var(--text-main)', display: 'flex', alignItems: 'center', gap: '6px' }
const dot = (bg) => ({ width: '6px', height: '6px', borderRadius: '50%', background: bg })

function SessionCard({ view, source, backendReachable }) {
  const isLive = source === 'esp32_csi'
  const reachable = backendReachable !== false
  const activityColor = view.calibrating ? 'var(--color-blue)' : view.alert ? 'var(--color-red)' : 'var(--color-green)'
  const activityText = view.calibrating ? 'Calibrating' : view.alert ? 'Elevated' : 'Calm'
  return (
    <div className="card" style={{ padding: '24px 32px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '24px' }}>
        <div>
          <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '8px' }}>Ambient Session · Local Demo</div>
          <div style={{ fontSize: '24px', fontWeight: 700, color: 'var(--text-main)', marginBottom: '8px' }}>Ambient Session — Bedroom Sensor Array</div>
          <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Fabricated sensor feed · no real subject · responds to anyone in the room</div>
        </div>
        {/* Source + reachability disclosure (one consistent label reflecting real state). */}
        <div className={`source-pill ${reachable ? (isLive ? 'live' : 'mock') : 'mock'}`}>
          <div className="source-dot"></div>
          {!reachable
            ? 'Backend unreachable · retrying'
            : `${isLive ? 'Live sensor' : 'Simulated feed'} · source: ${source}`}
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', borderTop: '1px solid var(--border)', paddingTop: '20px' }}>
        <div style={{ borderRight: '1px solid var(--border)', paddingRight: '20px' }}>
          <div style={statLabel}>AI Model</div>
          {/* Real deployed model id (not a fabricated confidence %). */}
          <div style={statVal}><div style={dot('var(--color-green)')}></div> Ready · Model {view.modelUsed}</div>
        </div>
        <div style={{ borderRight: '1px solid var(--border)', padding: '0 20px' }}>
          <div style={statLabel}>Ambient Presence</div>
          <div style={statVal}><div style={dot('var(--color-blue)')}></div> {view.presenceVal}% confidence</div>
        </div>
        <div style={{ borderRight: '1px solid var(--border)', padding: '0 20px' }}>
          <div style={statLabel}>Drift Detector</div>
          <div style={statVal}><div style={dot('var(--color-purple)')}></div> CUSUM {view.driftScore}</div>
        </div>
        <div style={{ paddingLeft: '20px' }}>
          <div style={statLabel}>Current Activity</div>
          <div style={statVal}><div style={dot(activityColor)}></div> {activityText}</div>
        </div>
      </div>
    </div>
  )
}

function SignalCards({ view }) {
  return (
    <div className="col-left">
      <div className="card" style={{ flex: 1 }}>
        <div className="card-header">
          <div className="card-title"><div className="card-dot dot-blue"></div> Breathing</div>
          <div className="card-val">{view.breathVal}<span className="card-unit">br/min</span></div>
        </div>
        <svg className="card-chart" viewBox="0 0 200 50" preserveAspectRatio="none"><polyline className="stroke-blue" fill="none" strokeWidth="2" points={view.breathWave}></polyline></svg>
        <div className="card-footer">Normal range 12–18 br/min</div>
      </div>

      {/* Heart Rate — Model B depends on this feature directly, so surface it. It is
          fabricated (scenario-locked) by the mock server; only real ESP32+MAX30102
          hardware would make it genuine. */}
      <div className="card" style={{ flex: 1 }}>
        <div className="card-header">
          <div className="card-title"><div className="card-dot" style={{ background: 'var(--color-red)' }}></div> Heart Rate</div>
          <div className="card-val">{view.heartRateVal}<span className="card-unit">bpm</span></div>
        </div>
        <svg className="card-chart" viewBox="0 0 200 50" preserveAspectRatio="none"><polyline fill="none" stroke="var(--color-red)" strokeWidth="2" points={view.heartSpark}></polyline></svg>
        <div className="card-footer">Fabricated (mock) · drives Model B verdict</div>
      </div>

      <div className="card" style={{ flex: 1 }}>
        <div className="card-header">
          <div className="card-title"><div className="card-dot dot-green"></div> Presence Conf.</div>
          <div className="card-val">{view.presenceVal}<span className="card-unit">%</span></div>
        </div>
        <svg className="card-chart" viewBox="0 0 200 50" preserveAspectRatio="none"><polyline className="stroke-green" fill="none" strokeWidth="2" points={view.presenceSpark}></polyline></svg>
        <div className="card-footer">Target ≥ 85%</div>
      </div>

      <div className="card" style={{ flex: 1 }}>
        <div className="card-header">
          <div className="card-title"><div className="card-dot dot-purple"></div> Sleep Frag.</div>
          <div className="card-val">{view.fragVal}<span className="card-unit">events/hr</span></div>
        </div>
        <svg className="card-chart" viewBox="0 0 200 50" preserveAspectRatio="none"><polyline className="stroke-purple" fill="none" strokeWidth="2" points={view.fragSpark}></polyline></svg>
        <div className="card-footer">Normal range 0–5 events/hr</div>
      </div>
    </div>
  )
}

function HeroCenter({ view }) {
  return (
    <div className="col-center">
      <video className="hero-video" src="/uploads/humanbodyvid.webm" autoPlay muted loop playsInline></video>
      <div className="hero-score-box">
        <div className="hs-label">Anomaly Score</div>
        <div className="hs-val">{view.anomalyVal}</div>
      </div>
    </div>
  )
}

function RightColumn({ view }) {
  return (
    <div className="col-right">
      <div className="card">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '11px', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '12px', textTransform: 'uppercase' }}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M22 12h-4l-3 9L9 3l-3 9H2" /></svg>
          Drift Assessment
        </div>
        <div style={{ background: 'var(--bg-main)', padding: '16px', borderRadius: '8px', marginBottom: '16px', border: '1px solid var(--border)' }}>
          <div style={{ fontSize: '16px', fontWeight: 600, color: view.alert ? 'var(--color-red)' : 'var(--color-green)', marginBottom: '8px' }}>{view.patternLabel}</div>
          <div style={{ display: 'inline-block', padding: '4px 10px', background: 'rgba(255,255,255,0.1)', borderRadius: '12px', fontSize: '12px' }}>{view.verdictText}</div>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
          <div style={{ textAlign: 'center', padding: '12px', border: '1px solid var(--border)', borderRadius: '8px' }}>
            <div style={{ fontSize: '20px', fontWeight: 700 }}>{view.probability}%</div>
            <div style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase', marginTop: '4px' }}>Model Probability</div>
          </div>
          <div style={{ textAlign: 'center', padding: '12px', border: '1px solid var(--border)', borderRadius: '8px' }}>
            <div style={{ fontSize: '20px', fontWeight: 700 }}>{view.driftScore}</div>
            <div style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase', marginTop: '4px' }}>CUSUM Drift</div>
          </div>
        </div>
        {view.topDriver && (
          <div style={{ marginTop: '12px', fontSize: '11px', color: 'var(--text-muted)' }}>
            Model {view.modelUsed} · top contributing feature: <span style={{ color: 'var(--text-main)' }}>{view.topDriver}</span>
          </div>
        )}
      </div>

      <div className="card">
        <div className="card-header">
          <div className="card-title"><div className="card-dot dot-orange"></div> Motion Index</div>
          <div className="card-val">{view.motionVal}<span className="card-unit">/100</span></div>
        </div>
        <div className="flex-chart">
          {view.motionBars.map((b, i) => (
            <div key={i} style={{ flex: 1, height: `${b}%`, background: 'var(--color-orange)', borderRadius: '2px' }}></div>
          ))}
        </div>
        <div className="card-footer">Baseline for this subject: 10–18</div>
      </div>

      <div className="card" style={{ flex: 1 }}>
        <div style={{ fontSize: '14px', fontWeight: 600, marginBottom: '16px' }}>Event Timeline</div>
        <div style={{ overflowY: 'auto' }}>
          {view.timeline.length === 0 && <div style={{ fontSize: '12px', color: 'var(--text-faint)' }}>No events yet.</div>}
          {view.timeline.map((ev, i) => (
            <div className="tl-item" key={i}>
              <div className="tl-time">{ev.time}</div>
              <div className="tl-dot-wrap">
                <div className={`tl-dot-inner ${ev.alertCls || ''}`}></div>
                <div className="tl-line"></div>
              </div>
              <div className="tl-desc">{ev.desc}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function Hypnogram({ view }) {
  const legend = (bg, label) => (
    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
      <div style={{ width: '12px', height: '12px', background: bg, borderRadius: '2px' }}></div> {label}
    </div>
  )
  return (
    <div className="card" style={{ marginTop: '8px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '20px' }}>
        <div className="card-title"><div className="card-dot dot-blue"></div> Sleep Stage Timeline</div>
        <div className="card-unit" style={{ fontSize: '13px' }}>— hypnogram, 22:00–06:00</div>
      </div>
      <div className="flex-chart" style={{ height: '60px', marginBottom: '16px' }}>
        {view.hypnoBlocks.map((hb, i) => (
          <div key={i} style={{ flex: 1, height: '100%', background: hb, borderRadius: '2px' }}></div>
        ))}
      </div>
      <div className="card-footer" style={{ display: 'flex', gap: '20px', alignItems: 'center' }}>
        {legend('var(--hyp-wake)', 'Wake')}
        {legend('var(--hyp-rem)', 'REM')}
        {legend('var(--hyp-light)', 'Light')}
        {legend('var(--hyp-deep)', 'Deep')}
      </div>
    </div>
  )
}

function DashboardFooter() {
  const p = { color: 'var(--text-muted)', fontSize: '12px', lineHeight: 1.6 }
  return (
    <footer className="footer" style={{ flexDirection: 'column', alignItems: 'stretch', gap: '40px' }}>
      <div style={{ maxWidth: '1000px' }}>
        <h3 style={{ color: 'var(--text-main)', fontSize: '14px', fontWeight: 600, marginBottom: '16px', marginTop: 0 }}>About this system</h3>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '40px' }}>
          <div>
            <p style={{ ...p, marginTop: 0, marginBottom: '12px' }}>Wearables need compliance. They only work while worn and charged, and overnight adherence drops exactly when monitoring matters most.</p>
            <p style={{ ...p, marginBottom: 0 }}>Cameras need consent. Continuous video in a bedroom is rarely acceptable for most homes and care settings.</p>
          </div>
          <div>
            <p style={{ ...p, marginTop: 0, marginBottom: '12px' }}>Ambient sensing needs neither. Nothing worn, nothing recorded — Wicare reads coarse physiological signals from the room itself, with no device on the body and no image captured.</p>
            <p style={{ ...p, marginBottom: 0 }}>Ambient sensing responds to any person present in the monitored room, not only the intended individual. Readings may reflect a second occupant, a visitor, or a pet, and are surfaced for human review — never as a standalone determination.</p>
          </div>
        </div>
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid var(--border)', paddingTop: '24px' }}>
        <div>© 2026 WiCare Ambient Care Sentinel. All Rights Reserved.</div>
        <div className="footer-links">
          <a href="#">Privacy Policy</a>
          <a href="#">Terms of Service</a>
          <a href="#">Clinical Documentation</a>
          <a href="#">Support</a>
        </div>
      </div>
    </footer>
  )
}

// Replaces the removed "Simulation Mode" popup, in the same UI location. Both controls
// hit the real backend; there is no local simulation path.
function DemoControls({ simOpen, toggleSim, driftVitals, resetSession, busy, view }) {
  return (
    <div className="sim-popup">
      <div className="sp-header" onClick={toggleSim}>
        <div className="sp-header-title">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M22 12h-4l-3 9L9 3l-3 9H2" /></svg>
          Drift Detection Demo
        </div>
        {simOpen ? (
          <svg className="sp-collapse-icon"><line x1="5" y1="12" x2="19" y2="12"></line></svg>
        ) : (
          <svg className="sp-collapse-icon"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
        )}
      </div>
      {simOpen && (
        <div className="sp-body">
          <div className="sp-group">
            <label>Live model · CUSUM detector</label>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              Model {view.modelUsed} · drift score {view.driftScore}
              {view.alert && <span style={{ color: 'var(--color-red)', fontWeight: 600 }}> · ALERT</span>}
            </div>
          </div>
          <button className="sp-btn" onClick={driftVitals} disabled={busy}>
            Drift vitals away from baseline
          </button>
          <button
            className="sp-btn"
            style={{ background: 'transparent', border: '1px solid var(--border)', color: 'var(--text-main)' }}
            onClick={resetSession}
            disabled={busy}
          >
            Reset session
          </button>
        </div>
      )}
    </div>
  )
}

function ConnectingScreen({ backendReachable }) {
  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: '12px' }}>
      <div style={{ fontSize: '18px', fontWeight: 600 }}>
        {backendReachable === false ? 'Sensing backend unreachable' : 'Connecting to sensing backend…'}
      </div>
      <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
        {backendReachable === false
          ? 'Start it: cd backend/sensing_server && source venv/bin/activate && python app.py'
          : 'Waiting for the first reading from localhost:5001'}
      </div>
    </div>
  )
}

function App() {
  const feed = useVitalsFeed()
  const { view } = feed

  if (view.pending) {
    return <ConnectingScreen backendReachable={feed.backendReachable} />
  }

  return (
    <div className={`app ${view.appCls} layout`}>
      <Sidebar showSettings={feed.showSettings} toggleSettings={feed.toggleSettings} />

      <main className="main">
        <header className="header">
          <div className="hdr-left">
            <span className="hdr-brand">WiCare</span>
            <span className="hdr-divider">·</span>
            <span className="hdr-subtitle">Live Monitoring</span>
          </div>
          <div className="hdr-right">
            <div className="status-pill">
              <div className="status-dot"></div> {view.verdictText}
            </div>
            <div className="hdr-time">{feed.timeStr}</div>
          </div>
        </header>

        <div className="content">
          <SessionCard view={view} source={feed.source} backendReachable={feed.backendReachable} />

          <div className="three-col-grid">
            <SignalCards view={view} />
            <HeroCenter view={view} />
            <RightColumn view={view} />
          </div>

          <Hypnogram view={view} />
        </div>

        <DashboardFooter />
      </main>

      <DemoControls
        simOpen={feed.simOpen}
        toggleSim={feed.toggleSim}
        driftVitals={feed.driftVitals}
        resetSession={feed.resetSession}
        busy={feed.busy}
        view={view}
      />
    </div>
  )
}

export default App
