import type { Metadata } from "next";
import Link from "@/components/Link";
import { listTopics } from "@/lib/api";
import { getT } from "@/i18n/server";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getT()).d.topics.title };
}

export default async function TopicsPage() {
  const t = await getT();
  const { data } = await listTopics();
  return (
    <div className="stack">
      <header className="page-head"><h1>{t.d.topics.title}</h1></header>
      <p className="note">{t.d.topics.note}</p>
      <ul className="card" style={{ listStyle: "none", columns: "2 280px", columnGap: 32 }}>
        {data.map((x) => (
          <li key={x.slug} style={{ padding: "6px 0", breakInside: "avoid" }}>
            <Link href={`/topics/${x.slug}`}>{t.topic(x)}</Link>{" "}
            <span className="small muted">
              {t.locale !== "he" && <>· <span className="he" lang="he" dir="rtl">{x.label_he}</span> </>}· {t.d.common.billsCount(x.bills)}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
