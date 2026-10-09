import assert from 'node:assert/strict';
import { test } from 'node:test';
import { scoreParties, parseAnswers } from '../src/lib/match.ts';

test('one comparable answer never ranks; missing, abstain, split and uncertain votes remain excluded', () => {
  const votes = ['for', 'abstain', 'mixed', 'none', 'ambiguous', undefined].map((s) => ({ stands: s ? { 1: s } : {} }));
  const [p] = scoreParties(votes, [{ id: 1, name: 'A' }], ['f','f','f','f','f','f']);
  assert.equal(p.eligible, false);
  assert.equal(p.rank, 0);
  assert.deepEqual(p.agreed, [0]);
  assert.deepEqual(p.differed, []);
  assert.deepEqual(p.excluded, [1, 2, 3, 4, 5]);
});

test('equal rates share a rank with unequal coverage; skips do not count as disagreement', () => {
  const votes = Array.from({ length: 9 }, (_, i) => ({ stands: { 1: 'for', 2: i < 6 ? 'for' : 'abstain', 3: i < 4 ? 'for' : 'against' } }));
  const scores = scoreParties(votes, [1,2,3].map((id) => ({ id, name: String(id) })), ['f','f','f','f','f','f','f','f','s']);
  assert.deepEqual(scores.map((p) => [p.id, p.rank, p.tied, p.comparable]), [[1,1,true,8], [2,1,true,6], [3,3,false,8]]);
  assert.deepEqual(scores[2].agreed, [0,1,2,3]);
  assert.deepEqual(scores[2].differed, [4,5,6,7]);
});

test('partial shared answers survive; malformed or overlong answer strings are rejected', () => {
  assert.deepEqual(parseAnswers('fas', 12), ['f','a','s']);
  assert.deepEqual(parseAnswers('fx', 12), []);
  assert.deepEqual(parseAnswers('fffffff', 6), []);
});
