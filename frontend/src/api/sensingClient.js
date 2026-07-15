// Client for /backend/sensing_server. Do not change this API's schema/endpoints from
// the frontend -- if something doesn't line up, that's a mismatch to fix here or flag
// back, not a reason to alter the backend's already-established contract.
const BASE_URL = import.meta.env.VITE_SENSING_SERVER_URL || 'http://localhost:5001'
const REQUEST_TIMEOUT_MS = 2000

async function requestJson(path, options = {}) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)
  try {
    const response = await fetch(`${BASE_URL}${path}`, {
      ...options,
      signal: controller.signal,
    })
    if (!response.ok) {
      throw new Error(`${path} returned HTTP ${response.status}`)
    }
    return await response.json()
  } finally {
    clearTimeout(timer)
  }
}

/** GET /api/v1/vital-signs -- canonical schema, source: "mock" today. */
export function fetchVitalSigns() {
  return requestJson('/api/v1/vital-signs')
}

/** POST /api/v1/sensing/scenario -- scenario: "normal" | "elevated_activity" | "reduced_activity" | "drift" */
export function postScenario(scenario) {
  return requestJson('/api/v1/sensing/scenario', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scenario }),
  })
}

/** POST /api/v1/sensing/reset -- fresh session: baseline buffer + CUSUM cleared, back to normal. */
export function resetSession() {
  return requestJson('/api/v1/sensing/reset', { method: 'POST' })
}
