import assert from 'node:assert/strict';
import { test } from 'node:test';
import { pointLabel } from '../src/utils/pointLabel.ts';

const selectedPoint = { lat: -23.55, lon: -46.63 };

test('a selected point does not show indefinite loading when geocoding is disabled', () => {
  assert.equal(pointLabel(selectedPoint, '', false), 'Ponto selecionado no mapa');
});

test('a point awaiting an enabled geocoder shows the pending lookup', () => {
  assert.equal(pointLabel(selectedPoint, '', true), 'Identificando rua…');
});

test('resolved street names and lookup failure messages remain visible', () => {
  for (const enabled of [true, false]) {
    assert.equal(pointLabel(selectedPoint, 'Avenida Paulista', enabled), 'Avenida Paulista');
    const message = 'Endereço indisponível — ponto selecionado no mapa';
    assert.equal(pointLabel(selectedPoint, message, enabled), message);
  }
});

test('an empty selection asks the user to choose a point', () => {
  for (const enabled of [true, false]) {
    assert.equal(pointLabel(null, '', enabled), 'Selecione no mapa');
  }
});
