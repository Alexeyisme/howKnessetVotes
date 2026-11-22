/** Knesset numbers as ranges: [18, 24, 25, 26] → "18, 24–26". A party that sat out some Knessets shows the gaps. */
export function termRanges(terms: number[]): string {
  const runs: [number, number][] = [];
  for (const n of [...new Set(terms)].sort((x, y) => x - y)) {
    const last = runs[runs.length - 1];
    if (last && n === last[1] + 1) last[1] = n;
    else runs.push([n, n]);
  }
  return runs.map(([from, to]) => (from === to ? `${from}` : `${from}–${to}`)).join(", ");
}
