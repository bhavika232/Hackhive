import { test } from 'node:test';
import assert from 'node:assert/strict';
import { loadTs } from './load-ts.mjs';
const api = await loadTs('../src/services/api.ts');
const response = (value, status = 200) => new Response(JSON.stringify(value), { status, headers: { 'Content-Type': 'application/json' } });
test('uses real paths, exact PATCH contract, and encoded query parameters', async t => {
  const calls = [];
  t.mock.method(globalThis, 'fetch', async (url, init) => { calls.push({ url, init }); return response({ status: 'ok', incident_id: 7, review_status: 'true_positive' }); });
  await api.checkHealth(); await api.getIncidents(); await api.getIncidentById(7);
  const updated = await api.reviewIncident(7, 'true_positive');
  await api.queryIncidents('crowd & camera 1');
  assert.deepEqual(calls.slice(0, 4).map(c => c.url), ['http://127.0.0.1:8000/health', 'http://127.0.0.1:8000/incidents', 'http://127.0.0.1:8000/incidents/7', 'http://127.0.0.1:8000/incidents/7/review']);
  assert.equal(calls[3].init.method, 'PATCH'); assert.equal(calls[3].init.headers['Content-Type'], 'application/json');
  assert.deepEqual(JSON.parse(calls[3].init.body), { review_status: 'true_positive' }); assert.equal(updated.review_status, 'true_positive');
  assert.equal(new URL(calls[4].url).searchParams.get('q'), 'crowd & camera 1');
});
test('surfaces HTTP and network failures without mock fallback', async t => {
  const mock = t.mock.method(globalThis, 'fetch', async () => response({ detail: 'Incident not found' }, 404));
  await assert.rejects(api.getIncidentById(999), /404.*Incident not found/);
  mock.mock.mockImplementation(async () => { throw new TypeError('Failed to fetch'); });
  await assert.rejects(api.getIncidents(), /Cannot reach the backend/);
});
test('verifies health and passes empty results through unchanged', async t => {
  const mock = t.mock.method(globalThis, 'fetch', async () => response({ status: 'broken' }));
  await assert.rejects(api.checkHealth(), /did not report a healthy status/);
  mock.mock.mockImplementation(async () => response([])); assert.deepEqual(await api.getIncidents(), []);
});
