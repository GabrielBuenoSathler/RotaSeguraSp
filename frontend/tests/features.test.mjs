import assert from 'node:assert/strict';
import { test } from 'node:test';
import { parseFeatures } from '../src/services/features.ts';

test('unknown or malformed configuration keeps optional features off', () => {
  for (const value of [null, undefined, '', {}, { geocoding: 'false', route_alternatives: 1 }]) {
    assert.deepEqual(parseFeatures(value), { geocoding: false, route_alternatives: false });
  }
});

test('only explicit boolean flags enable features', () => {
  assert.deepEqual(parseFeatures({ geocoding: true, route_alternatives: false, secret: 'ignored' }), {
    geocoding: true, route_alternatives: false,
  });
  assert.deepEqual(parseFeatures({ geocoding: false, route_alternatives: true }), {
    geocoding: false, route_alternatives: true,
  });
});
