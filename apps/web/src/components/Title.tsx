import { createHash } from "node:crypto";
import Link from "./Link";
import { He } from "./ui";
import type { Titled } from "@/lib/api";
import { getT } from "@/i18n/server";
import styles from "./Title.module.css";

/** R4: a law or vote title. The translation in the UI language first, marked "AI translation" (with "suggest a
 *  correction") until an editor has reviewed it; under it, smaller, the Hebrew original, which stays on every page
 *  as the official text. The order was the other way round until 2026-11-26: a reader of the Russian or English site
 *  met a line they could not read before the one they could. In the Hebrew UI, or when there is no translation yet,
 *  only the Hebrew line shows. `compact` keeps the marker to a small tag for lists, in the same words. */
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
    <Tag className={`${styles.title} ${compact ? "" : styles.full} ${className}`}>
      <span className={styles.tr} dir="auto">
        {text}
        {machine && (
          compact
            ? <span className={styles.tag} title={t.d.common.machine}>{t.d.common.machine}</span>
            : <span className={styles.marker}> · {t.d.common.machine} · <Link href={suggest} prefetch={false} rel="nofollow">{t.d.common.suggest}</Link></span>
        )}
      </span>
      <He className={styles.he}>{he}</He>
    </Tag>
  );
}

/** L7: the official bill summary. A paragraph, so unlike a title the translation leads and the Hebrew original is
 *  folded away. The correction link carries only the hash: the text itself would not fit in a URL. */
export async function Summary({ he, text, origin, page }: { he: string; text?: string | null; origin?: string | null; page?: string }) {
  const t = await getT();
  if (!text || t.locale === "he") return <He as="p">{he}</He>;
  const sha = createHash("sha256").update(he, "utf8").digest("hex");
  const suggest = `/suggest?${new URLSearchParams({ sha, lang: t.locale, ...(page ? { page } : {}) })}`;
  return (
    <>
      <p dir="auto">{text}</p>
      {origin === "machine" && <p className={styles.marker}>{t.d.common.machine} · <Link href={suggest} prefetch={false} rel="nofollow">{t.d.common.suggest}</Link></p>}
      <details className={styles.original}>
        <summary className="small muted">{t.d.common.hebrewOriginal}</summary>
        <He as="p">{he}</He>
      </details>
    </>
  );
}

/** The best title for a page's <title> and share text: the translation when there is one. */
export function titleText(he: string, tr?: Titled | null, locale?: string): string {
  return (locale !== "he" && tr?.title) || he;
}
