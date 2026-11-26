// A new Knesset before its government, read as one page (components/TermNow): its votes by day with runs of
// look-alike votes as one entry, a table of factions by votes, and whether the factions fell into the same two groups
// every time. No coalition exists yet, so nothing here is called one: the groups are what the votes show.

type Dated = { id: number; occurred_on: string };

/** Each vote's number in the order they were held (1 = the first vote of the term): the day list and the table's
 *  columns name a vote by it. */
export function numbered(votes: Dated[]): Map<number, number> {
  const sorted = [...votes].sort((a, b) => a.occurred_on.localeCompare(b.occurred_on) || a.id - b.id);
  return new Map(sorted.map((v, i) => [v.id, i + 1]));
}

/** Days, newest first; in a day the votes in the order given, consecutive votes with the same key as one entry.
 *  A null key never joins a run. */
export function byDay<V extends Dated>(votes: V[], keyOf: (v: V) => string | null): { on: string; entries: V[][] }[] {
  const days: { on: string; entries: V[][] }[] = [];
  let lastKey: string | null = null;
  for (const v of votes) {
    let day = days[days.length - 1];
    if (!day || day.on !== v.occurred_on) {
      day = { on: v.occurred_on, entries: [] };
      days.push(day);
      lastKey = null;
    }
    const key = keyOf(v);
    if (key !== null && key === lastKey) day.entries[day.entries.length - 1].push(v);
    else day.entries.push([v]);
    lastKey = key;
  }
  return days;
}

/** The key of look-alike votes: the same kind of vote (or the same bill), the same outcome and the same factions on
 *  each side. Four special committees set up one after another by the same six factions against the same four are
 *  one entry; a fifth with another line-up is its own. */
export function likeKey(what: string | null, accepted: boolean | null, forIds: number[], againstIds: number[]): string | null {
  if (!what) return null;
  const ids = (xs: number[]) => [...xs].sort((a, b) => a - b).join(",");
  return `${what}|${accepted}|${ids(forIds)}|${ids(againstIds)}`;
}

/** Did the factions fall into the same two groups in every vote where they were on opposite sides? Factions on one
 *  side of a vote must be in one group and the two sides in different groups; which group is "for" may change from
 *  vote to vote. Returns the two groups (the one holding the first vote's "for" side first) and the number of votes
 *  it rests on, or null: fewer than three such votes, a faction that crossed over, or factions the votes do not tie
 *  to either group. */
export function twoGroups(votes: { for: number[]; against: number[] }[]): { a: number[]; b: number[]; votes: number } | null {
  const opposed = votes.filter((v) => v.for.length > 0 && v.against.length > 0);
  if (opposed.length < 3) return null;
  // union-find with parity: parity[x] = whether x is in the other group than its root
  const parent = new Map<number, number>(), parity = new Map<number, number>();
  const find = (x: number): [number, number] => {
    if (!parent.has(x)) { parent.set(x, x); parity.set(x, 0); }
    const p = parent.get(x)!;
    if (p === x) return [x, 0];
    const [root, up] = find(p);
    parent.set(x, root);
    parity.set(x, parity.get(x)! ^ up);
    return [root, parity.get(x)!];
  };
  const join = (x: number, y: number, differ: number): boolean => {
    const [rx, px] = find(x), [ry, py] = find(y);
    if (rx === ry) return (px ^ py) === differ;
    parent.set(rx, ry);
    parity.set(rx, px ^ py ^ differ);
    return true;
  };
  for (const v of opposed) {
    for (const x of v.for) if (!join(x, v.for[0], 0)) return null;
    for (const x of v.against) if (!join(x, v.against[0], 0)) return null;
    if (!join(v.for[0], v.against[0], 1)) return null;
  }
  const first = find(opposed[0].for[0]);
  const a: number[] = [], b: number[] = [];
  for (const x of parent.keys()) {
    const [root, p] = find(x);
    if (root !== first[0]) return null;   // two unrelated fights: not one division
    (p === first[1] ? a : b).push(x);
  }
  return { a: a.sort((x, y) => x - y), b: b.sort((x, y) => x - y), votes: opposed.length };
}

export type Cell = "for" | "against" | "abstain" | "mixed" | "none" | "no_record";

/** A faction's cell for one vote: how the majority of its members who voted went; "none" when it has records but no
 *  vote cast (present, not voting); "no_record" when the vote lists it among the factions with no record at all. Null
 *  when the vote does not know the faction (it did not sit that day). Abstaining, not voting and no record stay apart. */
export function cell(vote: { by_faction: { faction_id: number; majority: string }[]; factions_without_records?: { faction_id: number }[] },
                     factionId: number): Cell | null {
  const row = vote.by_faction.find((f) => f.faction_id === factionId);
  if (row) return (["for", "against", "abstain", "mixed"].includes(row.majority) ? row.majority : "none") as Cell;
  return vote.factions_without_records?.some((f) => f.faction_id === factionId) ? "no_record" : null;
}
