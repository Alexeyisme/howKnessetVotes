import type { Metadata } from "next";
import Link from "@/components/Link";
import { VoteFeed } from "@/components/VoteFeed";
import { getT } from "@/i18n/server";
import styles from "./list.module.css";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getT()).d.votes.title };
}

export default async function VotesPage({ searchParams }: PageProps<"/[lang]/votes">) {
  const t = await getT();
  const sp = await searchParams;
  // ?on=2026-11-24: every vote of that day (a vote page links here: "all votes on 24 November")
  const on = typeof sp.on === "string" && /^\d{4}-\d{2}-\d{2}$/.test(sp.on) ? sp.on : null;
  return (
    <>
      <h1 className={styles.h1}>{on ? t.d.votes.onDay(t.date(on)) : t.d.votes.title}</h1>
      {on && <p className="small" style={{ marginBottom: 12 }}><Link href="/votes">{t.d.votes.title}</Link></p>}
      {on
        ? <VoteFeed base="/votes" sp={sp} filter={{ date_from: on, date_to: on }} keep={{ on }} defaultView="all" />
        : <VoteFeed base="/votes" sp={sp} />}
    </>
  );
}
