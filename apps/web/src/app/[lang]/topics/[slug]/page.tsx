import type { Metadata } from "next";
import { notFound } from "next/navigation";
import Link from "@/components/Link";
import { Title } from "@/components/Title";
import { VoteFeed } from "@/components/VoteFeed";
import { He } from "@/components/ui";
import { getTopic, NotFound } from "@/lib/api";
import { getT } from "@/i18n/server";

async function load(slug: string) {
  try {
    return (await getTopic(slug)).data;
  } catch (e) {
    if (e instanceof NotFound) notFound();
    throw e;
  }
}

export async function generateMetadata({ params }: PageProps<"/[lang]/topics/[slug]">): Promise<Metadata> {
  return { title: (await getT()).topic(await load((await params).slug)) };
}

export default async function TopicPage({ params, searchParams }: PageProps<"/[lang]/topics/[slug]">) {
  const { slug } = await params;
  const sp = await searchParams;
  const x = await load(slug);
  const t = await getT();
  const d = t.d.topic;
  const label = t.topic(x);
  const aliases = (t.locale === "he" ? [] : x[`aliases_${t.locale}`] ?? []).filter((a) => a.toLowerCase() !== label.toLowerCase());

  return (
    <div className="stack">
      <header className="page-head">
        <p className="small muted">{d.kicker}{t.locale !== "he" && <> · <He>{x.label_he}</He></>}</p>
        <h1>{label}</h1>
        {aliases.length > 0 && <p className="small muted">{d.aliases} {aliases.join(", ")}</p>}
      </header>

      {/* where the parties fought over the topic first; a topic with no contested final vote opens on its final votes */}
      <section>
        <h2 className="section-title">{d.votesTitle}</h2>
        <VoteFeed base={`/topics/${slug}`} sp={sp} filter={{ topic: slug }} defaultView="contested" fallback="final" />
      </section>

      <section>
        <h2 className="section-title">{d.bills(x.bills)}</h2>
        <ul className="card" style={{ listStyle: "none" }}>
          {x.recent_bills.map((b) => (
            <li key={b.id} style={{ padding: "8px 16px", borderBottom: "1px solid var(--hairline)" }}>
              <Link href={`/bills/${b.id}`} style={{ display: "block", fontWeight: 600, color: "var(--ink)" }}><Title he={b.title_he} t={b} compact /></Link>
              <span className="small muted">{t.d.common.term(b.term)}{b.last_vote_on && d.lastVote(t.date(b.last_vote_on))}{b.passed_third_reading && ` · ${t.d.common.passed}`}
                {b.sides?.speakers || b.sides?.reservations ? ` · ${t.d.sides.counts(b.sides.speakers, b.sides.reservations)}` : null}</span>
            </li>
          ))}
        </ul>
        <p style={{ marginTop: 8 }}><Link href={`/bills?topic=${slug}`}>{d.allBills}</Link></p>
      </section>
    </div>
  );
}
