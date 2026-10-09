import type { DebateSides, ProseText } from "@/lib/api";
import { getT } from "@/i18n/server";
import { He } from "./ui";
import styles from "./Sides.module.css";

type Argument = ProseText & { speakers: number };

/** L7 "two sides": the argument each side made most often in the plenum debate, and how many speakers made it. The
 *  API sends both arguments or neither, so a card never shows one side alone. Each side carries a visible "AI summary"
 *  tag, so a cropped screenshot of one side still says who wrote it. Spans only: it sits inside card links. */
export async function Sides({ sides }: { sides: DebateSides }) {
  const t = await getT();
  const d = t.d.sides;
  if (!sides.argument_for || !sides.argument_against) return null;
  const side = (a: Argument, kind: "for" | "against", head: string) => (
    <span className={`${styles.side} ${styles[kind]}`}>
      <span className={styles.head}>{head}<span className={styles.tag} title={d.note}>{t.d.common.aiSummary}</span></span>
      {t.locale !== "he" && a.text ? <span dir="auto">{a.text}</span> : <He>{a.text_he}</He>}
      <span className={styles.made}>{d.made(a.speakers)}</span>
    </span>
  );
  return (
    <span className={styles.sides}>
      {side(sides.argument_for, "for", d.for)}
      {side(sides.argument_against, "against", d.against)}
    </span>
  );
}
