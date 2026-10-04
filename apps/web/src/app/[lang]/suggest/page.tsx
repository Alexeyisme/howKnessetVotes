import type { Metadata } from "next";
import { SuggestForm } from "@/components/SuggestForm";
import { He } from "@/components/ui";
import { getT } from "@/i18n/server";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getT()).d.suggest.title };
}

// R4: a visitor's correction to a machine translation. Everything the form needs is in the URL (the hash of the
// Hebrew source, the language, the current text); the form posts to /api/v1/suggestions and an editor decides.
export default async function SuggestPage({ searchParams }: PageProps<"/[lang]/suggest">) {
  const t = await getT();
  const d = t.d.suggest;
  const sp = await searchParams;
  const str = (k: string) => (typeof sp[k] === "string" ? (sp[k] as string) : "");
  const sha = /^[0-9a-f]{64}$/.test(str("sha")) ? str("sha") : null;
  const lang = ["en", "ru", "ar", "he"].includes(str("lang")) ? str("lang") : t.locale;

  return (
    <div className="stack" style={{ maxWidth: 640 }}>
      <header className="page-head"><h1>{d.title}</h1></header>
      <p className="muted">{d.lead}</p>
      {str("he") && <p><span className="small muted">{d.original}:</span> <He>{str("he")}</He></p>}
      <SuggestForm sha={sha} lang={lang} text={str("text")} page={str("page") || null}
                   labels={{ textLabel: d.textLabel, noteLabel: d.noteLabel, send: d.send, thanks: d.thanks, error: d.error }} />
    </div>
  );
}
