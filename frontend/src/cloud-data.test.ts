import assert from 'node:assert/strict';
import { test } from 'node:test';
import { cloudData, distanceKm } from './cloud-data.ts';

test('nearest complete source is selected without sending GPS coordinates', async () => {
  const requests: string[] = [];
  const original = globalThis.fetch;
  globalThis.fetch = (async (url: string) => {
    requests.push(url);
    return Response.json(url.includes('air_locations?') ? [
      { station_id: 'partial', name: 'Nearby', latitude: 28.73, longitude: 77.12, comparison_snapshots: [{ complete: false }] },
      { station_id: 'full', name: 'Rohini', latitude: 28.74, longitude: 77.12, comparison_snapshots: [{ complete: true }] },
    ] : [{ phases: [] }]);
  }) as typeof fetch;
  try {
    const signal = new AbortController().signal;
    const result = await cloudData('/comparison', signal, { latitude: 28.73, longitude: 77.12 }) as { area: string };
    assert.equal(result.area, 'Rohini');
    assert.match(requests[1], /station_id=eq.full/);
    assert.ok(requests.every(url => !url.includes('28.73') && !url.includes('77.12')));
    await assert.rejects(cloudData('/comparison', signal, { latitude: 0, longitude: 0 }), /only have Delhi/);
    await assert.rejects(cloudData('/comparison', signal, { latitude: NaN, longitude: 77 }), /valid location/);
    assert.equal(distanceKm(28.73, 77.12, { name: 'Rohini', latitude: 28.73, longitude: 77.12 }), 0);
  } finally { globalThis.fetch = original; }
});
