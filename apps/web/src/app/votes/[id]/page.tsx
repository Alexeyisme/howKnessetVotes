import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { FactionBreakdown, Legend } from "@/components/FactionBreakdown";
import { getBallots, getVote, NotFound, type Counts } from "@/lib/api";
import { ballotLabel, formatDate, formatTime, METHOD, missingRollCallText, MOTION, MOTION_HINT, plural, STAGE } from "@/lib/labels";
import styles from "./vote.module.css";

const BILL_URL = (id: number) => `https://main.knesset.gov.il/APPS/legislation/main/bills/${id}`;

async function load(idParam: string) {
  const id = Number(idParam);
  if (!Number.isInteger(id) || id <= 0) notFound();
  try {
    const [vote, ballots] = await Promise.all([getVote(id), getBallots(id)]);
    return { vote: vote.data, ballots: ballots.data };
  } catch (e) {
    if (e instanceof NotFound) notFound();
    throw e;
  }
}

export async function generateMetadata({ params }: PageProps<"/votes/[id]">): Promise<Metadata> {
  const { vote } = await load((await params).id);
  return { title: `${vote.title_he} — ${formatDate(vote.occurred_on)}` };
}

function Tally({ c }: { c: Counts }) {
  const tiles = [
    { label: "За", n: c.for, cls: styles.for },
    { label: "Против", n: c.against, cls: styles.against },
    { label: "Воздержались", n: c.abstain, cls: styles.abstain },
    { label: "Присутствовали, не голосовали", n: c.present_not_voting, cls: "" },
  ];
  return (
    <dl className={styles.tally}>
      {tiles.map((t) => (
        <div key={t.label} className={styles.tile}>
          <dt className="small muted"><span className={`${styles.dot} ${t.cls}`} aria-hidden />{t.label}</dt>
          <dd className={styles.big}>{t.n}</dd>
        </div>
      ))}
    </dl>
  );
}

export default async function VotePage({ params }: PageProps<"/votes/[id]">) {
  const { vote, ballots } = await load((await params).id);
  const time = formatTime(vote.occurred_at);
  const hint = vote.motion_type ? MOTION_HINT[vote.motion_type] : undefined;
  const rc = vote.roll_call;
  const hasRollCall = rc.total_records > 0;

  return (
    <article>
      <header className={styles.head}>
        <p className="small muted">
          {formatDate(vote.occurred_on)}{time ? `, ${time}` : ""} · Кнессет {vote.term}-го созыва · голосование № {vote.id}
        </p>
        <div className={styles.badges}>
          {vote.stage && <span className="badge">{STAGE[vote.stage]}</span>}
          {vote.motion_type && <span className="badge">{MOTION[vote.motion_type]}</span>}
          <span className="badge">голосование {METHOD[vote.method] ?? vote.method}</span>
          {vote.status !== "valid" && <span className="badge">статус: {vote.status}</span>}
        </div>
        <h1 className={`${styles.title} he`} lang="he" dir="rtl">{vote.title_he}</h1>
        {vote.subject_he && <p className={`${styles.subject} he`} lang="he" dir="rtl">{vote.subject_he}</p>}
      </header>

      <section className="card" aria-labelledby="q">
        <h2 id="q" className="section-title">Что ставилось на голосование</h2>
        {vote.question_he && (
          <p className={`${styles.question} he`} lang="he" dir="rtl">«{vote.question_he}»</p>
        )}
        {hint && <p className="note" style={{ marginTop: 10 }}>{hint}</p>}
        {vote.bills.length > 0 && (
          <p className="small" style={{ marginTop: 10 }}>
            Законопроект:{" "}
            {vote.bills.map((b) => (
              <a key={b.id} href={BILL_URL(b.id)} className="he" lang="he" dir="rtl" rel="noopener" target="_blank">{b.title_he}</a>
            ))}
          </p>
        )}
      </section>

      <section className="card" aria-labelledby="res">
        <h2 id="res" className="section-title">Результат по поимённым записям</h2>
        {hasRollCall ? <Tally c={rc} /> : (
          <p className="note">Нет поимённых записей: {missingRollCallText(vote.method)}.</p>
        )}
        {vote.official_totals && (
          <p className="small" style={{ marginTop: 12 }}>
            Официальный итог: {vote.official_totals.for} за, {vote.official_totals.against} против, {vote.official_totals.abstain} воздержались
            {vote.official_totals.is_accepted != null && (vote.official_totals.is_accepted ? " — принято." : " — отклонено.")}
            {vote.excluded_from_official_total > 0 &&
              ` По данным источника ${vote.excluded_from_official_total} ${plural(vote.excluded_from_official_total, "запись", "записи", "записей")} поимённого списка не ${vote.excluded_from_official_total === 1 ? "вошла" : "вошли"} в официальный итог (голос заявлен или исправлен после голосования).`}
            {vote.totals_match === true && " С учётом этого поимённый список совпадает с официальным итогом."}
            {vote.totals_match === false && " Поимённый список расходится с официальным итогом — расхождение зарегистрировано для проверки."}
          </p>
        )}
        <p className="small muted" style={{ marginTop: 12 }}>
          Учтены только депутаты, по которым есть запись. Отсутствие записи не означает, что депутат отсутствовал.
          {!vote.official_totals && " Официальный итог для голосований после июля 2021 года в открытых данных не публикуется."}
        </p>
      </section>

      {hasRollCall && (
        <section className="card" aria-labelledby="fx">
          <h2 id="fx" className="section-title">По фракциям на дату голосования</h2>
          <Legend />
          <FactionBreakdown rows={vote.by_faction} ballots={ballots} />
          {vote.unresolved_faction_records > 0 && (
            <p className="note" style={{ marginTop: 10 }}>У {vote.unresolved_faction_records} записей фракция на эту дату не установлена.</p>
          )}
        </section>
      )}

      {hasRollCall && (
        <section className="card">
          <details>
            <summary className={styles.tableToggle}>Поимённый список — таблица ({ballots.length})</summary>
            <div className="table-scroll" style={{ marginTop: 12 }}>
              <table>
                <thead><tr><th>Депутат</th><th>Фракция тогда</th><th>Голос</th><th>Код источника</th></tr></thead>
                <tbody>
                  {ballots.map((b) => (
                    <tr key={b.person_id}>
                      <td className="he" lang="he" dir="rtl">{b.name_he}</td>
                      <td className="he" lang="he" dir="rtl">{b.faction_name_he ?? "—"}{b.faction_ambiguous ? " *" : ""}</td>
                      <td>
                        {ballotLabel(b.choice, b.participation)}
                        {b.counted_in_official_total === false && <span className="muted small"> · не вошёл в офиц. итог</span>}
                      </td>
                      <td className="num muted">{b.source === "knesset_votes_legacy" ? `Votes.svc ${b.source_result_code}` : b.source_result_code}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </details>
        </section>
      )}

      <p className="small muted" style={{ marginTop: 16 }}>
        Источник: <a href={vote.source_url} target="_blank" rel="noopener">карточка голосования на сайте Кнессета ↗</a>
      </p>
    </article>
  );
}
