// Chart/hypnogram render helpers, ported verbatim from the original design prototype
// (index.html). These are cosmetic only -- they shape the SVG sparklines/bars from the
// real backend vitals; none of them produce alert or score values.
export const clamp = (v, a, b) => Math.max(a, Math.min(b, v))

export function seededRandom(seed) {
  const x = Math.sin(seed) * 10000
  return x - Math.floor(x)
}

export function generateWaveform(val, varb, offset, w = 200, h = 50) {
  const pts = []
  for (let i = 0; i <= w; i += 4) {
    const t = (i + offset * 2) * 0.05
    const freq = val / 15
    const noise = Math.sin(t * 3.1) * (varb * 2)
    const y = h / 2 + Math.sin(t * freq) * (h / 4) + noise
    pts.push(`${i},${y.toFixed(1)}`)
  }
  return pts.join(' ')
}

export function generateMotionBars(val) {
  const arr = []
  const numBars = 40
  for (let i = 0; i < numBars; i++) {
    const seed = Math.sin(i * 12.34)
    const active = (seed + 1) / 2 < val / 100
    let h = 10
    if (active) {
      h = 15 + Math.abs(Math.cos(i * 7)) * 85
    }
    arr.push(h)
  }
  return arr
}

export function generateHypnogram(frag, onset) {
  const arr = []
  const steps = 48
  let currentBand = 0 // 0=Wake, 1=REM, 2=Light, 3=Deep
  const onsetStep = Math.floor((onset / 120) * steps)
  const transitions = Math.floor(frag / 4)
  let tCount = 0
  const colors = ['var(--hyp-wake)', 'var(--hyp-rem)', 'var(--hyp-light)', 'var(--hyp-deep)']

  for (let i = 0; i < steps; i++) {
    if (i < onsetStep) {
      currentBand = 0
    } else if (i === onsetStep) {
      currentBand = 2
    } else {
      if (tCount < transitions && seededRandom(i * 3.14) < 0.3) {
        currentBand = [1, 2, 3][Math.floor(seededRandom(i * 9.99) * 3)]
        tCount++
      }
      if (seededRandom(i * 7.77) < 0.05) currentBand = 0
    }
    arr.push(colors[currentBand])
  }
  return arr
}

export function sparkLine(val, h = 50) {
  const pts = []
  for (let i = 0; i < 20; i++) {
    pts.push(`${i * 10},${h / 2 + Math.sin(i + val) * 8}`)
  }
  return pts.join(' ')
}
