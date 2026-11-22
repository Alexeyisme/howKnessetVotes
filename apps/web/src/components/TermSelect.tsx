import { getStatus, getTerms } from "@/lib/api";
import { getT } from "@/i18n/server";

/** Terms that fall in the loaded period: from the Knesset of the first loaded vote (the 16th) to the newest one that
 *  has started. Plain GET form field: filters live in the URL. */
export async function TermSelect({ value, all = false }: { value?: string; all?: boolean }) {
  const t = await getT();
  const today = new Date().toISOString().slice(0, 10);
  const [all_, status] = await Promise.all([getTerms(), getStatus().then((r) => r.data, () => null)]);
  const first = status?.coverage.first_vote_on;
  const terms = all_.data.filter((x) => x.started_on <= today && (!first || !x.ended_on || x.ended_on > first));
  return (
    <select name="term" defaultValue={value ?? ""} aria-label={t.d.common.termLabel}>
      {all && <option value="">{t.d.common.allTerms}</option>}
      {terms.map((x) => <option key={x.number} value={x.number}>{t.d.common.term(x.number)}</option>)}
    </select>
  );
}
