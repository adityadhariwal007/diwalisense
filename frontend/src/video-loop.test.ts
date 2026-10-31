import { strict as assert } from 'node:assert';
import { test } from 'node:test';
import { videoOpacity } from './video-loop.ts';

test('video fades at both loop boundaries and stays visible between them', () => {
  for (const [time, opacity] of [[0, 0], [0.25, 0.5], [0.5, 1], [5, 1], [9.75, 0.5], [10, 0]]) {
    assert.equal(videoOpacity(time, 10), opacity);
  }
  assert.equal(videoOpacity(0, NaN), 0);
  assert.equal(videoOpacity(0, Infinity), 0);
  assert.equal(videoOpacity(0, 0), 0);
  assert.equal(videoOpacity(-1, 10), 0);
  assert.equal(videoOpacity(11, 10), 0);
});
