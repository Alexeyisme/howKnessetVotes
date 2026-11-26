import assert from 'node:assert/strict';
import { test } from 'node:test';
import { byDay, cell, likeKey, numbered, twoGroups } from '../src/lib/termNow.ts';

const v = (id, occurred_on) => ({ id, occurred_on });

test('votes are numbered in the order they were held', () => {
  const n = numbered([v(46745, '2026-11-23'), v(46744, '2026-11-24'), v(46716, '2026-11-11'), v(46741, '2026-11-24')]);
  assert.deepEqual([46716, 46745, 46741, 46744].map((id) => n.get(id)), [1, 2, 3, 4]);   // by day, then by id
});

test('days newest first; a run of look-alike votes is one entry', () => {
  const votes = [v(4, '2026-11-24'), v(3, '2026-11-24'), v(2, '2026-11-24'), v(9, '2026-11-23'), v(1, '2026-11-18'), v(0, '2026-11-18')];
  const key = (x) => ({ 4: 'k', 3: 'k', 2: 'other', 9: 'k', 1: null, 0: null })[x.id];
  const days = byDay(votes, key);
  assert.deepEqual(days.map((d) => d.on), ['2026-11-24', '2026-11-23', '2026-11-18']);
  assert.deepEqual(days.map((d) => d.entries.map((e) => e.map((x) => x.id))), [[[4, 3], [2]], [[9]], [[1], [0]]]);   // a run does not cross a day; null never joins
});

test('look-alike: the same kind, outcome and factions on each side, in any order', () => {
  assert.equal(likeKey('arrangementsProposal', true, [3, 1, 2], [9, 8]), likeKey('arrangementsProposal', true, [1, 2, 3], [8, 9]));
  assert.notEqual(likeKey('arrangementsProposal', true, [1, 2, 3], [8, 9]), likeKey('arrangementsProposal', true, [1, 2, 3], [8]));
  assert.notEqual(likeKey('arrangementsProposal', true, [1], [8]), likeKey('arrangementsProposal', false, [1], [8]));
  assert.equal(likeKey(null, true, [1], [8]), null);
});

test('two groups: the same division in every vote where factions were on opposite sides', () => {
  const fights = [{ for: [1, 2, 3], against: [7, 8, 9] }, { for: [1, 2, 3], against: [7, 8] }, { for: [7, 8, 9], against: [1, 2] }];
  assert.deepEqual(twoGroups(fights), { a: [1, 2, 3], b: [7, 8, 9], votes: 3 });          // sides may swap between votes
  assert.deepEqual(twoGroups([...fights, { for: [1, 2], against: [] }]), { a: [1, 2, 3], b: [7, 8, 9], votes: 3 });   // a one-sided vote says nothing
  assert.equal(twoGroups([...fights, { for: [1, 7], against: [2] }]), null);              // faction 7 crossed over
  assert.equal(twoGroups(fights.slice(0, 2)), null);                                      // two votes are too few
  assert.equal(twoGroups([...fights, { for: [20], against: [21] }]), null);               // a fight the others do not connect to
});

test('a cell keeps abstaining, not voting and no record apart', () => {
  const vote = { by_faction: [{ faction_id: 1, majority: 'for' }, { faction_id: 2, majority: 'abstain' }, { faction_id: 3, majority: 'none' },
    { faction_id: 4, majority: 'mixed' }], factions_without_records: [{ faction_id: 5 }] };
  assert.deepEqual([1, 2, 3, 4, 5, 6].map((id) => cell(vote, id)), ['for', 'abstain', 'none', 'mixed', 'no_record', null]);
});
