import { getStatus, getTerms } from "@/lib/api";
import { getT } from "@/i18n/server";

/** A Knesset that has been sworn in but has not voted yet: say that its MKs, factions and votes appear as the Knesset
 *  publishes them (hkv update loads them; names and photos from the Knesset website). Gone after the first vote.
 *  `fallback`: the term a list shows instead because the new one has no MKs in the source yet. */
export async function NewTermNotice({ fallback }: { fallback?: string }) {
  const t = await getT();
  const today = new Date().toISOString().slice(0, 10);
  const [terms, status] = await Promise.all([getTerms().then((r) => r.data, () => []), getStatus().then((r) => r.data, () => null)]);
  const term = terms.find((x) => x.number > 0 && x.started_on <= today);
  if (!term || !status || status.coverage.last_vote_on >= term.started_on) return null;
  const d = t.d.newTerm;
  return (
    <p className="note">
      {d.notice(term.number, t.date(term.started_on))}
      {fallback && fallback !== String(term.number) && <> {d.fallback(Number(fallback))}</>}
    </p>
  );
}
