import assert from 'node:assert/strict';
import { test } from 'node:test';
import { recommendedRoute, routeBalance } from '../src/utils/routeRecommendation.ts';

const route = (id, exposure, seconds, success = true) => ({
  route: { calculated_route_id: id, duration_seconds: seconds },
  risk: { status: { success }, result: { pontuacao_ajustada: exposure } },
});

test('balances exposure and time with equal weights', () => {
  const slow = route(1, 10, 1200);
  const fast = route(2, 12, 600);
  const options = [slow, fast];
  assert.equal(recommendedRoute(options), fast);
  assert.ok(routeBalance(fast, options) > routeBalance(slow, options));
});

test('zero records remain finite and prefer less travel time', () => {
  const options = [route(1, 0, 600), route(2, 0, 1200)];
  assert.equal(routeBalance(options[0], options), 100);
  assert.equal(recommendedRoute(options), options[0]);
  assert.ok(Number.isFinite(routeBalance(options[1], options)));
});

test('missing time and failed analyses do not receive an index', () => {
  const options = [route(1, 0, undefined), route(2, 0, 600, false), route(3, 20, 600)];
  assert.equal(routeBalance(options[0], options), undefined);
  assert.equal(routeBalance(options[1], options), undefined);
  assert.equal(recommendedRoute(options), options[2]);
  assert.equal(recommendedRoute([options[1]]), undefined);
});

test('negative scores and zero durations cannot produce an index', () => {
  const options = [route(1, -1, 600), route(2, 2, 0)];
  assert.equal(routeBalance(options[0], options), undefined);
  assert.equal(routeBalance(options[1], options), undefined);
});
