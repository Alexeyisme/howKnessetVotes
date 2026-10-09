"use client";

// R6: one vote per card, For / Against / Skip, then the parties ranked by how often their majority chose what the
// visitor chose (lib/match.ts). Answers live only in the URL (?q=vote ids&a=fas…, one letter per question, &step= while
// editing), so a result is shareable, progress survives a reload or a language switch, and nothing is stored anywhere.

import { useEffect, useMemo, useRef, useState } from "react";
import { parseAnswers, scoreParties, type Answer, type MatchParty, type MatchVote, type Stand } from "@/lib/match";
import styles from "./MatchQuiz.module.css";

/** Plain strings only (functions cannot cross into a client component): progress[i] for question i+1, agree[m][n]
 *  for "n of m", coverage[n] for "n of all questions". All are bounded by the number of questions, so the server
 *  precomputes them. */
export interface MatchLabels {
  question: string; yes: string; no: string; skip: string; progress: string[]; resultTitle: string; agree: string[][];
  again: string; share: string; copied: string; yours: string; passed: string; back: string; edit: string; finish: string;
  insufficient: string; unranked: string; tied: string; coverage: string[];
  agreed: string; differed: string; excluded: string; noItems: string; partyChoice: string; review: string;
  stand: Record<Stand, string>; choice: Record<string, string>; sidesFor: string; sidesAgainst: string; sidesNote: string;
}

export function MatchQuiz({ votes, parties, initial, initialStep, locale, labels }:
  { votes: MatchVote[]; parties: MatchParty[]; initial: string; initialStep: string; locale: string; labels: MatchLabels }) {
  const [answers, setAnswers] = useState<Answer[]>(() => parseAnswers(initial, votes.length));
  const [index, setIndex] = useState(() => {
    const length = parseAnswers(initial, votes.length).length;
    return /^\d+$/.test(initialStep) && Number(initialStep) <= length ? Number(initialStep) : length;
  });
  // editing one answer of a finished quiz returns to the results instead of walking through the rest
  const [editing, setEditing] = useState(() => parseAnswers(initial, votes.length).length === votes.length &&
    /^\d+$/.test(initialStep) && Number(initialStep) < votes.length);
  const [copied, setCopied] = useState(false);
  const heading = useRef<HTMLHeadingElement>(null);
  const mounted = useRef(false);
  const done = index === votes.length;
  const current = votes[index];

  useEffect(() => {
    // keep the URL in sync so reloads, language switches and sharing work; no navigation, no history spam
    const url = new URL(window.location.href);
    if (answers.length) {
      url.searchParams.set("q", votes.map((v) => v.id).join(","));
      url.searchParams.set("a", answers.join(""));
      if (index < answers.length) url.searchParams.set("step", String(index));
      else url.searchParams.delete("step");
    } else {
      for (const key of ["q", "a", "step"]) url.searchParams.delete(key);
    }
    window.history.replaceState(null, "", url);
  }, [answers, index, votes]);

  useEffect(() => {
    // move focus with the card so keyboard and screen-reader users start at the new question
    if (mounted.current) {
      heading.current?.focus({ preventScroll: true });
      heading.current?.scrollIntoView({ block: "start" });
    }
    mounted.current = true;
  }, [index]);

  const scores = useMemo(() => scoreParties(votes, parties, answers), [votes, parties, answers]);
  const ranked = scores.filter((p) => p.eligible);
  const unranked = scores.filter((p) => !p.eligible).sort((a, b) => a.name.localeCompare(b.name, locale));
  const mine = (i: number) => answers[i] === "f" ? labels.choice.for : answers[i] === "a" ? labels.choice.against : labels.skip;
  const choose = (answer: Answer) => {
    const next = [...answers]; next[index] = answer;
    setAnswers(next); setIndex(editing ? votes.length : index + 1); setEditing(false);
  };

  async function share() {
    try {
      if (navigator.share) await navigator.share({ url: window.location.href });
      else { await navigator.clipboard.writeText(window.location.href); setCopied(true); setTimeout(() => setCopied(false), 2000); }
    } catch { /* cancelled */ }
  }

  if (!done && current) return (
    <section className={styles.card}>
      <p className="small muted" aria-live="polite">{labels.progress[index]} · {current.date}</p>
      <progress className={styles.progress} max={votes.length} value={index} aria-label={labels.progress[index]} />
      <h2 ref={heading} tabIndex={-1} className={styles.question}>{labels.question}</h2>
      <p className={`he ${styles.title}`} lang="he" dir="rtl">{current.title_he}</p>
      {current.title && <p className={styles.translation} dir="auto">{current.title}</p>}
      {current.about && <div className={styles.about}>{current.about}</div>}
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
      <div className={styles.controls}>
        <div className={styles.buttons}>
          <button type="button" className={styles.yes} aria-pressed={answers[index] === "f"} onClick={() => choose("f")}>{labels.yes}</button>
          <button type="button" className={styles.no} aria-pressed={answers[index] === "a"} onClick={() => choose("a")}>{labels.no}</button>
          <button type="button" className={styles.skip} aria-pressed={answers[index] === "s"} onClick={() => choose("s")}>{labels.skip}</button>
        </div>
        <div className={styles.actions}>
          <button type="button" disabled={index === 0} onClick={() => { setIndex(index - 1); setEditing(false); }}>{labels.back}</button>
          {answers.length === votes.length && <button type="button" onClick={() => { setIndex(votes.length); setEditing(false); }}>{labels.finish}</button>}
        </div>
      </div>
    </section>
  );

  function breakdown(p: typeof scores[number]) {
    return <details className={styles.breakdown}><summary>{labels.review}</summary>
      {([[labels.agreed, p.agreed], [labels.differed, p.differed], [labels.excluded, p.excluded]] as const).map(([label, indices]) => (
        <section key={label}><h3>{label} ({indices.length})</h3>
          {indices.length === 0 ? <p className="small muted">{labels.noItems}</p> : <ul className={styles.answers}>
            {indices.map((i) => <li key={votes[i].id}>
              <a href={`/${locale}/votes/${votes[i].id}`} dir="auto">{votes[i].title ?? votes[i].title_he} · {votes[i].date}</a>
              <p className="small">{labels.yours}: {mine(i)} · {labels.partyChoice}: {labels.stand[votes[i].stands[p.id] ?? "missing"]}</p>
            </li>)}
          </ul>}
        </section>
      ))}
    </details>;
  }

  return <section className={styles.result}>
    <h2 ref={heading} tabIndex={-1} className="section-title">{labels.resultTitle}</h2>
    {!ranked.length && <p role="status" className="note">{labels.insufficient}</p>}
    <ol className={styles.ranking}>
      {ranked.map((p) => <li key={p.id} className={styles.party}>
        <div className={styles.partyHead}>
          <strong><span className="num">{p.rank}. </span><a href={`/${locale}/factions/${p.id}`}>{p.name}</a> {p.tied && <span className="badge">{labels.tied}</span>}</strong>
          <span className="num">{labels.agree[p.comparable][p.agreed.length]}</span>
        </div>
        <div className={styles.bar} aria-hidden><span style={{ width: `${100 * p.share}%` }} /></div>
        <p className="small muted">{labels.coverage[p.comparable]}</p>
        {breakdown(p)}
      </li>)}
    </ol>
    {unranked.length > 0 && <details><summary>{labels.unranked} ({unranked.length})</summary>
      <p className="small muted">{labels.insufficient}</p>
      <ul className={styles.ranking}>{unranked.map((p) => <li key={p.id} className={styles.party}>
        <a href={`/${locale}/factions/${p.id}`}>{p.name}</a>
        <p className="small">{labels.coverage[p.comparable]}</p>
        {breakdown(p)}
      </li>)}</ul>
    </details>}
    <div className={styles.actions}>
      {ranked.length > 0 && <button type="button" onClick={share}>{copied ? labels.copied : labels.share}</button>}
      <button type="button" onClick={() => { setAnswers([]); setIndex(0); setEditing(false); }}>{labels.again}</button>
    </div>
    <section className={styles.review}>
      <h3>{labels.yours}</h3>
      <ol className={styles.answers}>
        {votes.map((v, i) => <li key={v.id}>
          <a href={`/${locale}/votes/${v.id}`} className="he" lang="he" dir="rtl">{v.title_he}</a>
          {v.title && <span className={`${styles.answerTr} small`} dir="auto">{v.title}</span>}
          <p className="small muted">{labels.yours}: {mine(i)} · {labels.passed}: {v.outcome} ({v.line})</p>
          <button type="button" onClick={() => { setIndex(i); setEditing(true); }}>{labels.edit} · {labels.progress[i]}</button>
        </li>)}
      </ol>
    </section>
  </section>;
}
