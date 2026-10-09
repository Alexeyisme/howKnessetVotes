import type { Metadata } from "next";
import { SuggestForm } from "@/components/SuggestForm";
import { He } from "@/components/ui";
import { getT } from "@/i18n/server";

export async function generateMetadata({ searchParams }: PageProps<"/[lang]/suggest">): Promise<Metadata> {
  const d = (await getT()).d.suggest;
  // one URL per translated title and per page: a form, not content for search engines
  return { title: typeof (await searchParams).sha === "string" ? d.title : d.reportTitle, robots: { index: false, follow: false } };
}

// R4: a visitor's correction to a machine translation. Everything the form needs is in the URL (the hash of the
// Hebrew source, the language, the current text); the form posts to /api/v1/suggestions and an editor decides.
// Without a source hash it is a free-text mistake report about a page (the footer and the machine-written notes).
export default async function SuggestPage({ searchParams }: PageProps<"/[lang]/suggest">) {
  const t = await getT();
  const d = t.d.suggest;
  const sp = await searchParams;
  const str = (k: string) => (typeof sp[k] === "string" ? (sp[k] as string) : "");
  const sha = /^[0-9a-f]{64}$/.test(str("sha")) ? str("sha") : null;
  const lang = ["en", "ru", "ar", "he"].includes(str("lang")) ? str("lang") : t.locale;

  return (
    <div className="stack" style={{ maxWidth: 640 }}>
      <header className="page-head"><h1>{sha ? d.title : d.reportTitle}</h1></header>
      <p className="muted">{sha ? d.lead : d.reportLead}</p>
      {str("he") && <p><span className="small muted">{d.original}:</span> <He>{str("he")}</He></p>}
      {/* the Turnstile site key is read at request time (runtime env of the web container), so no rebuild is needed */}
      <SuggestForm sha={sha} lang={lang} text={str("text")} page={str("page") || null} siteKey={process.env.TURNSTILE_SITE_KEY || null}
                   labels={{ textLabel: sha ? d.textLabel : d.reportTextLabel, noteLabel: d.noteLabel, contactLabel: d.contactLabel,
                           send: d.send, thanks: sha ? d.thanks : d.reportThanks, error: d.error }} />
    </div>
  );
}
