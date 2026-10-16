import type { Incident } from '../services/api';
export const categoryLabels: Record<string, string> = { person_down: 'Person down', crowd_incident: 'Crowd incident', tailgating: 'Tailgating' };
export const reviewLabels: Record<string, string> = { unreviewed: 'Awaiting review', true_positive: 'Reviewed', false_positive: 'False positive' };
export const confidenceLabels: Record<string, string> = { confirmed: 'Confirmed', rule_only: 'Rule only', needs_review: 'Needs review', uncertain: 'Uncertain' };
export const label = (value: string | null | undefined, labels: Record<string, string>) => value ? labels[value] ?? value.replace(/_/g, ' ') : 'Not provided';
export function timestamp(value?: string | null): number | null {
  if (!value) return null;
  const result = new Date(value).getTime();
  return Number.isFinite(result) ? result : null;
}
export function formatDate(value?: string | null, short = false): string {
  const time = timestamp(value);
  return time === null ? 'Not provided' : new Date(time).toLocaleString(undefined, {
    month: 'short', day: 'numeric', ...(!short ? { year: 'numeric' as const } : {}), hour: '2-digit', minute: '2-digit',
  });
}
export function localDay(value?: string | null): string {
  const time = timestamp(value);
  if (time === null) return '';
  const d = new Date(time);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}
export const confidencePercent = (value?: number | null) => value == null || !Number.isFinite(value) ? 'Not provided' : `${Math.round(value * 100)}%`;
export type SortOrder = 'newest' | 'oldest' | 'confidence_high' | 'confidence_low';
export interface Filters { search: string; camera: string; category: string; review: string; from: string; to: string; sort: SortOrder }
export const defaultFilters: Filters = { search: '', camera: '', category: '', review: '', from: '', to: '', sort: 'newest' };
export function filterIncidents(incidents: Incident[], filters: Filters): Incident[] {
  const rawQuery = filters.search.trim().toLowerCase().replace(/^#/, '');
  const query = /^\d+$/.test(rawQuery) ? String(Number(rawQuery)) : rawQuery;
  return incidents.filter(i => {
    const haystack = [i.incident_id, i.camera_id, i.category, label(i.category, categoryLabels), i.summary].join(' ').toLowerCase();
    const day = localDay(i.start_wall_time);
    return (!query || haystack.includes(query)) && (!filters.camera || i.camera_id === filters.camera) && (!filters.category || i.category === filters.category)
      && (!filters.review || i.review_status === filters.review)
      && (!filters.from || (!!day && day >= filters.from)) && (!filters.to || (!!day && day <= filters.to));
  }).sort((a, b) => {
    const byConfidence = filters.sort.startsWith('confidence');
    const av = byConfidence ? a.confidence : timestamp(a.start_wall_time);
    const bv = byConfidence ? b.confidence : timestamp(b.start_wall_time);
    if (av == null && bv == null) return b.incident_id - a.incident_id;
    if (av == null) return 1;
    if (bv == null) return -1;
    return (filters.sort === 'oldest' || filters.sort === 'confidence_low' ? av - bv : bv - av) || b.incident_id - a.incident_id;
  });
}
export function groupCounts(incidents: Incident[], field: 'category' | 'review_status' | 'camera_id', labels: Record<string, string> = {}) {
  const counts = new Map<string, number>();
  for (const incident of incidents) {
    const name = label(incident[field], labels);
    counts.set(name, (counts.get(name) ?? 0) + 1);
  }
  return Array.from(counts, ([name, count]) => ({ name, count })).sort((a, b) => b.count - a.count);
}
export function dailyActivity(incidents: Incident[]) {
  const counts = new Map<string, number>();
  for (const i of incidents) { const day = localDay(i.start_wall_time); if (day) counts.set(day, (counts.get(day) ?? 0) + 1); }
  return Array.from(counts, ([day, count]) => ({ day, name: new Date(`${day}T12:00:00`).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: '2-digit' }), count }))
    .sort((a, b) => a.day.localeCompare(b.day));
}
export function confidenceDistribution(incidents: Incident[]) {
  const bins = ['0–19%', '20–39%', '40–59%', '60–79%', '80–100%'].map(name => ({ name, count: 0 }));
  for (const i of incidents) if (i.confidence != null && Number.isFinite(i.confidence) && i.confidence >= 0 && i.confidence <= 1) bins[Math.min(4, Math.floor(i.confidence * 5))].count++;
  return bins;
}
export function cameraSources(incidents: Incident[]) {
  return groupCounts(incidents.filter(i => !!i.camera_id), 'camera_id').map(camera => ({ ...camera,
    lastSeen: filterIncidents(incidents.filter(i => i.camera_id === camera.name), defaultFilters)[0]?.start_wall_time,
  }));
}

