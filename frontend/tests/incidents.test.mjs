import { test } from 'node:test';
import assert from 'node:assert/strict';
import { loadTs } from './load-ts.mjs';
const u = await loadTs('../src/utils/incidents.ts');
const incident = (id, fields = {}) => ({ incident_id: id, camera_id: 'cam1', category: 'crowd_incident', summary: 'Entrance crowd', confidence: 0.85, confidence_status: 'confirmed', start_wall_time: '2026-10-16T12:00:00', review_status: 'unreviewed', ...fields });
const records = [incident(1), incident(2, { camera_id: 'cam10', category: 'person_down', review_status: 'false_positive', confidence: 1, start_wall_time: '2026-10-15T12:00:00' }), incident(3, { confidence: null, start_wall_time: null })];
test('combines search, exact camera, category, review, and inclusive local dates', () => {
  assert.deepEqual(u.filterIncidents(records, { ...u.defaultFilters, search: 'ENTRANCE', camera: 'cam1', category: 'crowd_incident', review: 'unreviewed', from: '2026-10-16', to: '2026-10-16' }).map(i => i.incident_id), [1]);
  assert.equal(u.filterIncidents(records, { ...u.defaultFilters, search: 'nothing-matches' }).length, 0);
  assert.deepEqual(u.filterIncidents(records, { ...u.defaultFilters, search: '#0002' }).map(i => i.incident_id), [2]);
});
test('sorts time and confidence in both directions with missing values last', () => {
  for (const [sort, expected] of [['newest', [1, 2, 3]], ['oldest', [2, 1, 3]], ['confidence_high', [2, 1, 3]], ['confidence_low', [1, 2, 3]]]) assert.deepEqual(u.filterIncidents(records, { ...u.defaultFilters, sort }).map(i => i.incident_id), expected);
  assert.equal(records[0].incident_id, 1, 'must not reorder shared data');
});
test('counts records and excludes missing dates/confidence instead of inventing data', () => {
  assert.equal(u.dailyActivity(records).reduce((sum, d) => sum + d.count, 0), 2);
  assert.equal(u.confidenceDistribution(records).at(-1).count, 2);
  assert.equal(u.confidenceDistribution([incident(1, { confidence: 0 }), incident(2, { confidence: .2 }), incident(3, { confidence: 1 })]).reduce((sum, d) => sum + d.count, 0), 3);
  assert.equal(u.groupCounts(records, 'category', u.categoryLabels).find(d => d.name === 'Crowd incident').count, 2);
  assert.equal(u.cameraSources(records).find(d => d.name === 'cam1').lastSeen, '2026-10-16T12:00:00');
  assert.equal(u.formatDate(null), 'Not provided');
  assert.equal(u.confidencePercent(null), 'Not provided');
  assert.deepEqual(u.dailyActivity([]), []);
});
