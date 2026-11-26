import type { Metadata } from "next";
import Link from "@/components/Link";
import { TermNow } from "@/components/TermNow";
import { FILTERS, ViewChips, VoteFeed } from "@/components/VoteFeed";
import { termBeforeGovernment } from "@/lib/api";
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
  if (on) {
    return (
      <>
        <h1 className={styles.h1}>{t.d.votes.onDay(t.date(on))}</h1>
        <p className="small" style={{ marginBottom: 12 }}><Link href="/votes">{t.d.votes.title}</Link></p>
        <VoteFeed base="/votes" sp={sp} filter={{ date_from: on, date_to: on }} keep={{ on }} defaultView="all" />
      </>
    );
  }
  // A new Knesset before its government: the page opens on that Knesset (all its votes by day and a table of factions
  // by votes), because the usual default, votes on bills, hid ten of its first twelve votes. The feed's views are one
  // chip away, and the page is the ordinary feed again once the government is sworn in.
  const now = await termBeforeGovernment();
  const picked = typeof sp.view === "string" && FILTERS.some((f) => f.key === sp.view);
  if (now && !picked) {
    return (
      <>
        <h1 className={styles.h1}>{t.d.votes.now.all(now.term)}</h1>
        <ViewChips current="" href={(key) => `/votes?view=${key}`} primary={["main", "all"]} lead={{ label: t.d.common.knessetOf(now.term), href: "/votes" }} />
        <TermNow term={now.term} startedOn={now.started_on} />
      </>
    );
  }
  return (
    <>
      <h1 className={styles.h1}>{t.d.votes.title}</h1>
      <VoteFeed base="/votes" sp={sp} lead={now ? { label: t.d.common.knessetOf(now.term), href: "/votes" } : undefined} />
    </>
  );
}
