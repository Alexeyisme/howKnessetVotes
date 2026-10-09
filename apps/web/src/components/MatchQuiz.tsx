"use client";

// R6: one vote per card, For / Against / Skip, then the parties ranked by how often their majority chose what the
// visitor chose. Answers live only in the URL (?q=vote ids&a=fas…, one letter per question), so a result is shareable and
// nothing is stored anywhere.

import { useEffect, useMemo, useState } from "react";
import styles from "./MatchQuiz.module.css";

/** One side's most-made argument in the plenum debate (L7), as display strings; `he`: the text is the Hebrew original. */
export interface MatchSide { text: string; he: boolean; made: string }
export interface MatchVote {
  id: number; date: string; title_he: string; title: string | null; outcome: string; line: string; stands: Record<number, "for" | "against">;
  sides: { for: MatchSide; against: MatchSide } | null;
}
export interface MatchParty { id: number; name: string; alignment: string | null }
/** Plain strings only (functions cannot cross into a client component): progress[i] for question i+1, agree[m][n]
 *  for "n of m". Both are bounded by the number of questions, so the server precomputes them. */
export interface MatchLabels {
  question: string; yes: string; no: string; skip: string; progress: string[]; resultTitle: string;
  agree: string[][]; noAnswers: string; again: string; share: string; copied: string; yours: string; passed: string;
  alignment: Record<string, string>; choice: Record<string, string>; sidesFor: string; sidesAgainst: string; sidesNote: string;
}

type Answer = "f" | "a" | "s";

export function MatchQuiz({ votes, parties, initial, locale, labels }:
  { votes: MatchVote[]; parties: MatchParty[]; initial: string; locale: string; labels: MatchLabels }) {
  const valid = /^[fas]*$/.test(initial) ? (initial.slice(0, votes.length).split("") as Answer[]) : [];
  const [answers, setAnswers] = useState<Answer[]>(valid.length === votes.length ? valid : []);
  const [copied, setCopied] = useState(false);
  const done = answers.length >= votes.length;
  const current = votes[answers.length];

  useEffect(() => {
    // keep the URL in sync so the back button and sharing work; no navigation, no history spam
    const url = new URL(window.location.href);
    if (done) {
      url.searchParams.set("q", votes.map((v) => v.id).join(","));
      url.searchParams.set("a", answers.join(""));
    } else {
      url.searchParams.delete("q");
      url.searchParams.delete("a");
    }
    window.history.replaceState(null, "", url);
  }, [answers, done, votes]);

  const ranking = useMemo(() => {
    if (!done) return [];
    return parties.map((p) => {
      let agree = 0, comparable = 0;
      votes.forEach((v, i) => {
        const stand = v.stands[p.id];
        const mine = answers[i];
        if (!stand || mine === "s") return;
        comparable += 1;
        if ((mine === "f" && stand === "for") || (mine === "a" && stand === "against")) agree += 1;
      });
      return { ...p, agree, comparable, share: comparable ? agree / comparable : -1 };
    }).filter((p) => p.comparable > 0).sort((x, y) => y.share - x.share || y.comparable - x.comparable);
  }, [done, answers, parties, votes]);

  async function share() {
    const url = window.location.href;
    try {
      if (navigator.share) await navigator.share({ url });
      else { await navigator.clipboard.writeText(url); setCopied(true); setTimeout(() => setCopied(false), 2000); }
    } catch { /* cancelled */ }
  }

  if (!done && current) {
    const i = answers.length;
    return (
      <section className={styles.card} aria-live="polite">
        <p className="small muted">{labels.progress[i]} · {current.date}</p>
        <div className={styles.progress} aria-hidden><span style={{ width: `${(100 * i) / votes.length}%` }} /></div>
        <h2 className={styles.question}>{labels.question}</h2>
        <p className={`he ${styles.title}`} lang="he" dir="rtl">{current.title_he}</p>
        {current.title && <p className={styles.translation} dir="auto">{current.title}</p>}
        {/* both sides' main argument, so the answer can rest on more than the title */}
        {current.sides && (
          <div className={styles.sides}>
            {(["for", "against"] as const).map((k) => {
              const x = current.sides![k];
              return (
                <div key={k} className={`${styles.side} ${k === "for" ? styles.sideFor : styles.sideAgainst}`}>
                  <span className={styles.sideHead}>{k === "for" ? labels.sidesFor : labels.sidesAgainst}<span className={styles.tag} title={labels.sidesNote}>auto</span></span>
                  <span lang={x.he ? "he" : undefined} dir={x.he ? "rtl" : "auto"}>{x.text}</span>
                  <span className={styles.made}>{x.made}</span>
                </div>
              );
            })}
          </div>
        )}
        <div className={styles.buttons}>
          <button type="button" className={styles.yes} onClick={() => setAnswers([...answers, "f"])}>{labels.yes}</button>
          <button type="button" className={styles.no} onClick={() => setAnswers([...answers, "a"])}>{labels.no}</button>
          <button type="button" className={styles.skip} onClick={() => setAnswers([...answers, "s"])}>{labels.skip}</button>
        </div>
      </section>
    );
  }

  const answered = answers.filter((x) => x !== "s").length;
  return (
    <section className={styles.result}>
      <h2 className="section-title">{labels.resultTitle}</h2>
      {answered === 0 ? <p className="muted">{labels.noAnswers}</p> : (
        <ol className={styles.ranking}>
          {ranking.map((p) => (
            <li key={p.id}>
              <a href={`/${locale}/factions/${p.id}`} className={styles.party}>
                <span className={styles.name}>{p.name}{p.alignment && p.alignment !== "unknown" && <span className={styles.align}> · {labels.alignment[p.alignment]}</span>}</span>
                <span className={styles.bar} aria-hidden><span style={{ width: `${100 * p.share}%` }} /></span>
                <span className={`small num ${styles.agree}`}>{labels.agree[p.comparable][p.agree]}</span>
              </a>
            </li>
          ))}
        </ol>
      )}
      <div className={styles.actions}>
        <button type="button" onClick={share}>{copied ? labels.copied : labels.share}</button>
        <button type="button" className={styles.skip} onClick={() => setAnswers([])}>{labels.again}</button>
      </div>
      <details className={styles.review}>
        <summary className="small">{labels.yours}</summary>
        <ol className={styles.answers}>
          {votes.map((v, i) => (
            <li key={v.id}>
              <a href={`/${locale}/votes/${v.id}`} className="he" lang="he" dir="rtl">{v.title_he}</a>
              {v.title && <span className={`${styles.answerTr} small`} dir="auto">{v.title}</span>}
              <span className="small muted"> · {labels.yours}: {answers[i] === "f" ? labels.choice.for : answers[i] === "a" ? labels.choice.against : "—"} · {labels.passed}: {v.outcome} ({v.line})</span>
            </li>
          ))}
        </ol>
      </details>
    </section>
  );
}
