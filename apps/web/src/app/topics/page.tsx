import type { Metadata } from "next";
import Link from "next/link";
import { listTopics } from "@/lib/api";

export const metadata: Metadata = { title: "Темы" };

export default async function TopicsPage() {
  const { data } = await listTopics();
  return (
    <div className="stack">
      <header className="page-head"><h1>Темы</h1></header>
      <p className="note">
        Темы назначены автоматически по словам в названии законопроекта и ещё не проверены редактором; один законопроект может относиться к нескольким темам.
        Это редакционная классификация сайта, а не официальная классификация Кнессета.
      </p>
      <ul className="card" style={{ listStyle: "none", columns: "2 280px", columnGap: 32 }}>
        {data.map((t) => (
          <li key={t.slug} style={{ padding: "6px 0", breakInside: "avoid" }}>
            <Link href={`/topics/${t.slug}`}>{t.label_ru}</Link>{" "}
            <span className="small muted">· <span className="he" lang="he" dir="rtl">{t.label_he}</span> · {t.bills} законопр.</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
