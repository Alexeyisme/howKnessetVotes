import { getTerms } from "@/lib/api";

/** Terms that fall in the loaded period (votes start in term 20). Plain GET form field: filters live in the URL. */
export async function TermSelect({ value, allLabel }: { value?: string; allLabel?: string }) {
  const today = new Date().toISOString().slice(0, 10);
  const terms = (await getTerms()).data.filter((t) => t.number >= 20 && t.started_on <= today);
  return (
    <select name="term" defaultValue={value ?? ""} aria-label="Созыв">
      {allLabel && <option value="">{allLabel}</option>}
      {terms.map((t) => <option key={t.number} value={t.number}>{t.number}-й созыв</option>)}
    </select>
  );
}
