export type Category = 'person_down' | 'crowd_incident' | 'tailgating';
export type ReviewStatus = 'unreviewed' | 'true_positive' | 'false_positive';
export type ConfidenceStatus = 'confirmed' | 'rule_only' | 'needs_review' | 'uncertain';

// Mirrors app/schemas.py; tolerates absent metadata in older records.
export interface Incident {
  incident_id: number;
  camera_id: string;
  category: Category;
  summary: string;
  confidence: number | null;
  confidence_status: ConfidenceStatus | null;
  start_video_s: number | null;
  end_video_s?: number | null;
  start_wall_time: string | null;
  end_wall_time?: string | null;
  keyframe_path?: string | null;
  track_ids?: number[] | null;
  review_status: ReviewStatus;
  occurrence_count?: number | null;
}
export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/+$/, '');
export class ApiError extends Error {
  constructor(message: string, public status?: number) { super(message); this.name = 'ApiError'; }
}
async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const controller = new AbortController();
  const abort = () => controller.abort();
  init.signal?.addEventListener('abort', abort, { once: true });
  if (init.signal?.aborted) controller.abort();
  const timeout = setTimeout(abort, 12000);
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...init, signal: controller.signal,
      headers: { Accept: 'application/json', ...(init.body ? { 'Content-Type': 'application/json' } : {}), ...init.headers },
    });
    if (!response.ok) {
      const body = await response.json().catch(() => null);
      const detail = typeof body?.detail === 'string' ? body.detail : response.statusText;
      throw new ApiError(`Request failed (${response.status})${detail ? `: ${detail}` : ''}`, response.status);
    }
    return await response.json() as T;
  } catch (error) {
    if (init.signal?.aborted || error instanceof ApiError) throw error;
    throw new ApiError(controller.signal.aborted
      ? 'The backend took too long to respond. Please retry.'
      : `Cannot reach the backend at ${API_BASE_URL}. Check that FastAPI is running and allows this origin.`);
  } finally {
    clearTimeout(timeout);
    init.signal?.removeEventListener('abort', abort);
  }
}
export async function checkHealth(signal?: AbortSignal): Promise<{ status: 'ok' }> {
  const result = await request<{ status: string }>('/health', { signal });
  if (result.status !== 'ok') throw new ApiError('The backend did not report a healthy status.');
  return { status: 'ok' };
}
export const getIncidents = (signal?: AbortSignal) => request<Incident[]>('/incidents', { signal });
export const getIncidentById = (id: number, signal?: AbortSignal) => request<Incident>(`/incidents/${id}`, { signal });
export const reviewIncident = (id: number, status: ReviewStatus) => request<Incident>(`/incidents/${id}/review`, {
  method: 'PATCH', body: JSON.stringify({ review_status: status }),
});
export interface QueryResult {
  query: string;
  filters: { category: Category | null; review_status: ReviewStatus | null; camera_id: string | null };
  count: number;
  incidents: Incident[];
}
export const queryIncidents = (q: string, signal?: AbortSignal) => request<QueryResult>(`/query?${new URLSearchParams({ q })}`, { signal });
