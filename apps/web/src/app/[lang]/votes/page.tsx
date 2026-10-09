import type { Metadata } from "next";
import { VoteFeed } from "@/components/VoteFeed";
import { getT } from "@/i18n/server";
import styles from "./list.module.css";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getT()).d.votes.title };
}

export default async function VotesPage({ searchParams }: PageProps<"/[lang]/votes">) {
  const t = await getT();
  return (
    <>
      <h1 className={styles.h1}>{t.d.votes.title}</h1>
      <VoteFeed base="/votes" sp={await searchParams} />
    </>
  );
}
