export type Category = 'person_down' | 'tailgating' | 'crowd_incident'
export type ConfidenceStatus = 'confirmed' | 'rule_only' | 'needs_review' | 'uncertain'
export type ReviewStatus = 'unreviewed' | 'true_positive' | 'false_positive'

export interface Incident {
  incident_id: number
  camera_id: string
  category: Category
  summary: string
  confidence: number
  confidence_status: ConfidenceStatus
  start_video_s: number
  end_video_s: number | null
  start_wall_time: string
  end_wall_time: string | null
  keyframe_path: string | null
  track_ids: number[]
  review_status: ReviewStatus
  occurrence_count: number
}

export interface Health {
  status: 'ok' | string
}

const configuredBase = import.meta.env.VITE_API_BASE_URL?.trim()
export const defaultApiBase = (configuredBase || 'http://127.0.0.1:8000').replace(/\/$/, '')

export function getApiBase(): string {
  return (localStorage.getItem('sentinel.apiBase') || defaultApiBase).replace(/\/$/, '')
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), 8000)
  try {
    const response = await fetch(`${getApiBase()}${path}`, {
      ...init,
      signal: controller.signal,
      headers: { Accept: 'application/json', ...init?.headers },
    })
    const body = await response.text()
    if (!response.ok) {
      let detail = body || `HTTP ${response.status}`
      try {
        const parsed = JSON.parse(body) as { detail?: unknown }
        if (typeof parsed.detail === 'string') detail = parsed.detail
      } catch { /* Keep the server's raw response when it is not JSON. */ }
      throw new Error(`${response.status}: ${detail}`)
    }
    try {
      return JSON.parse(body) as T
    } catch {
      throw new Error('Backend returned malformed JSON.')
    }
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new Error('Backend request timed out after 8 seconds.')
    }
    throw error
  } finally {
    window.clearTimeout(timeout)
  }
}

function validateIncident(value: unknown): value is Incident {
  if (!value || typeof value !== 'object') return false
  const item = value as Partial<Incident>
  return Number.isInteger(item.incident_id)
    && typeof item.camera_id === 'string'
    && ['person_down', 'tailgating', 'crowd_incident'].includes(String(item.category))
    && typeof item.summary === 'string'
    && typeof item.confidence === 'number'
    && ['confirmed', 'rule_only', 'needs_review', 'uncertain'].includes(String(item.confidence_status))
    && typeof item.start_video_s === 'number'
    && typeof item.start_wall_time === 'string'
    && ['unreviewed', 'true_positive', 'false_positive'].includes(String(item.review_status))
    && (item.end_video_s === null || typeof item.end_video_s === 'number')
    && (item.end_wall_time === null || typeof item.end_wall_time === 'string')
    && (item.keyframe_path === null || typeof item.keyframe_path === 'string')
    && Array.isArray(item.track_ids) && item.track_ids.every(Number.isInteger)
    && Number.isInteger(item.occurrence_count)
    && item.confidence >= 0 && item.confidence <= 1
}

export async function getHealth(): Promise<Health> {
  const health = await request<unknown>('/health')
  if (!health || typeof health !== 'object' || (health as Health).status !== 'ok') {
    throw new Error('Backend health response was not the expected { status: "ok" } shape.')
  }
  return health as Health
}

export async function getIncidents(): Promise<Incident[]> {
  const result = await request<unknown>('/incidents')
  if (!Array.isArray(result)) throw new Error('Backend returned an invalid incidents response (expected an array).')
  const malformed = result.findIndex((item) => !validateIncident(item))
  if (malformed >= 0) throw new Error(`Backend incident at list position ${malformed + 1} has an unexpected shape.`)
  return result as Incident[]
}

export async function getIncident(id: number): Promise<Incident> {
  const result = await request<unknown>(`/incidents/${id}`)
  if (!validateIncident(result)) throw new Error('Backend returned an invalid incident response.')
  return result
}

export async function updateReview(id: number, review_status: ReviewStatus): Promise<Incident> {
  const result = await request<unknown>(`/incidents/${id}/review`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ review_status }),
  })
  if (!validateIncident(result)) throw new Error('Backend returned an invalid updated incident response.')
  return result
}
