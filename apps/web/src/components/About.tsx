import Link from "./Link";
import type { BillAbout } from "@/lib/api";
import { getT } from "@/i18n/server";
import styles from "./Title.module.css";

/** The start of a long text: whole sentences up to `max` characters; a first sentence far longer than that is cut
 *  at a word. */
function lead(text: string, locale: string, max: number): string {
  let out = "";
  for (const { segment } of new Intl.Segmenter(locale, { granularity: "sentence" }).segment(text)) {
    if (!out && segment.length > max * 1.5) return segment.slice(0, segment.lastIndexOf(" ", max)).trimEnd() + " …";
    if (out && out.length + segment.length > max) return out.trimEnd() + " …";
    out += segment;
  }
  return out.trimEnd();
}

/** What a law does, on cards and quiz questions: the start of the Knesset's official summary, or where there is none
 *  of our description of the sponsors' notes, labelled as on the bill page. A title like "Basic Law: The Government
 *  (Amendment No. 11)" says nothing on its own. `compact` (inside a card that is itself a link) drops the link to the
 *  full text and marks machine text with the small "auto" tag, its explanation on hover. */
export async function About({ about, bill, max = 360, compact = false }: { about: BillAbout; bill: number; max?: number; compact?: boolean }) {
  const t = await getT();
  const d = t.d.bill;
  const official = !!about.summary_he;
  const he = official ? about.summary_he : about.explanation_he;
  if (!he) return null;
  const tr = t.locale !== "he" ? (official ? about.summary : about.explanation) ?? null : null;
  const machine = !!tr && (official ? about.summary_origin : about.explanation_origin) === "machine";
  // the sponsors' notes are retold by a model in every language, Hebrew included; the official summary only translated
  const note = !official ? d.explanationNote : machine ? t.d.common.machine : null;
  const text = <span lang={tr ? undefined : "he"} dir={tr ? "auto" : "rtl"}>{lead(tr ?? he, tr ? t.locale : "he", max)}</span>;
  if (compact) return (
    <>
      <span className="small muted">{official ? d.summaryTitle : d.explanationTitle}{note && <span className={styles.tag} title={note}>auto</span>}</span>
      {text}
    </>
  );
  return (
    <>
      <span className="small muted">{official ? d.summaryTitle : d.explanationTitle}</span>
      {text}
      <span className={styles.marker}>{note}{note && " · "}<Link href={`/bills/${bill}`} target="_blank">{t.d.match.aboutMore}</Link></span>
    </>
  );
}
