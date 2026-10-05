import { createHash } from "node:crypto";
import Link from "./Link";
import { He } from "./ui";
import type { Titled } from "@/lib/api";
import { getT } from "@/i18n/server";
import styles from "./Title.module.css";

/** R4: a law or vote title. The Hebrew original first; under it the translation in the UI language, marked
 *  "automatic translation" (with "suggest a correction") until an editor has reviewed it. In the Hebrew UI, or when
 *  there is no translation yet, only the Hebrew line shows. `compact` keeps the marker to a small tag for lists. */
export async function Title({ he, t: tr, as = "span", compact = false, className = "", page }:
  { he: string; t?: Titled | null; as?: "span" | "h1" | "p"; compact?: boolean; className?: string; page?: string }) {
  const t = await getT();
  const text = tr?.title;
  const machine = tr?.title_origin === "machine";
  const Tag = as;
  if (!text || t.locale === "he") return <He as={as} className={className}>{he}</He>;
  const sha = createHash("sha256").update(he, "utf8").digest("hex");
  const suggest = `/suggest?${new URLSearchParams({ sha, lang: t.locale, text, he, ...(page ? { page } : {}) })}`;
  return (
    <Tag className={`${styles.title} ${className}`}>
      <He className={styles.he}>{he}</He>
      <span className={styles.tr} dir="auto">
        {text}
        {machine && (
          compact
            ? <span className={styles.tag} title={t.d.common.machine}>auto</span>
            : <span className={styles.marker}> · {t.d.common.machine} · <Link href={suggest}>{t.d.common.suggest}</Link></span>
        )}
      </span>
    </Tag>
  );
}

/** The best title for a page's <title> and share text: the translation when there is one. */
export function titleText(he: string, tr?: Titled | null, locale?: string): string {
  return (locale !== "he" && tr?.title) || he;
}
