import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { TermSelect } from "@/components/TermSelect";
import { TopicFactions } from "@/components/TopicFactions";
import { He } from "@/components/ui";
import { getTopic, NotFound } from "@/lib/api";
import { formatDate } from "@/lib/labels";

async function load(slug: string, term?: string) {
  try {
    return (await getTopic(slug, { term })).data;
  } catch (e) {
    if (e instanceof NotFound) notFound();
    throw e;
  }
}

export async function generateMetadata({ params }: PageProps<"/topics/[slug]">): Promise<Metadata> {
  return { title: (await load((await params).slug)).label_ru };
}

export default async function TopicPage({ params, searchParams }: PageProps<"/topics/[slug]">) {
  const { slug } = await params;
  const sp = await searchParams;
  const term = typeof sp.term === "string" && sp.term ? sp.term : undefined;
  const t = await load(slug, term);

  return (
    <div className="stack">
      <header className="page-head">
        <p className="small muted">Тема · <He>{t.label_he}</He></p>
        <h1>{t.label_ru}</h1>
        <p className="small muted">Также ищется по словам: {t.aliases_ru.filter((a) => a !== t.label_ru).join(", ")}</p>
      </header>

      <section className="card">
        <h2 className="section-title">Как фракции голосовали по законопроектам темы — {t.term}-й созыв</h2>
        <form className="search" action={`/topics/${slug}`}>
          <TermSelect value={String(t.term)} />
          <button type="submit">Показать</button>
        </form>
        <p className="small muted" style={{ marginBottom: 12 }}>
          Считаются голосования в третьем чтении за законопроект в целом. Для каждой фракции — в скольких из них большинство её голосовавших членов было за или против.
          Законопроекты, отклонённые на ранних стадиях, сюда не попадают.
        </p>
        {t.factions.length > 0 ? <TopicFactions rows={t.factions} /> : <p className="muted">В этом созыве нет таких голосований.</p>}
      </section>

      <section>
        <h2 className="section-title">Законопроекты темы ({t.bills})</h2>
        <ul className="card" style={{ listStyle: "none" }}>
          {t.recent_bills.map((b) => (
            <li key={b.id} style={{ padding: "8px 16px", borderBottom: "1px solid var(--hairline)" }}>
              <Link href={`/bills/${b.id}`} style={{ display: "block", textAlign: "right", fontWeight: 600, color: "var(--ink)" }}><He>{b.title_he}</He></Link>
              <span className="small muted">{b.term}-й созыв{b.last_vote_on && ` · последнее голосование ${formatDate(b.last_vote_on)}`}{b.passed_third_reading && " · принят"}</span>
            </li>
          ))}
        </ul>
        <p style={{ marginTop: 8 }}><Link href={`/bills?topic=${slug}`}>Все законопроекты темы →</Link></p>
      </section>
    </div>
  );
}
