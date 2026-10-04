import { getTerms } from "@/lib/api";
import { getT } from "@/i18n/server";

/** Terms that fall in the loaded period (votes start in term 20). Plain GET form field: filters live in the URL. */
export async function TermSelect({ value, all = false }: { value?: string; all?: boolean }) {
  const t = await getT();
  const today = new Date().toISOString().slice(0, 10);
  const terms = (await getTerms()).data.filter((x) => x.number >= 20 && x.started_on <= today);
  return (
    <select name="term" defaultValue={value ?? ""} aria-label={t.d.common.termLabel}>
      {all && <option value="">{t.d.common.allTerms}</option>}
      {terms.map((x) => <option key={x.number} value={x.number}>{t.d.common.term(x.number)}</option>)}
    </select>
  );
}
