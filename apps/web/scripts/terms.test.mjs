import assert from 'node:assert/strict';
import { test } from 'node:test';
import { termRanges } from '../src/lib/terms.ts';

test('Knesset numbers as ranges, with the gaps a party sat out', () => {
  assert.equal(termRanges([26]), '26');
  assert.equal(termRanges([16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26]), '16–26');
  assert.equal(termRanges([18, 25, 26]), '18, 25–26');
  assert.equal(termRanges([24, 16, 17, 24, 20]), '16–17, 20, 24');
  assert.equal(termRanges([]), '');
});
