"use client";

// R8: search that answers while you type. Members, parties and topics come from /api/v1/search (same origin: Caddy in
// production, a rewrite in dev); Enter with nothing highlighted submits the form to /search for the full results
// (bills included). Keyboard: arrows, Enter, Escape.

import { useRouter } from "next/navigation";
import { useEffect, useId, useRef, useState } from "react";
import styles from "./SearchBox.module.css";

interface Hit { href: string; label: string; sub?: string }
interface Group { title: string; hits: Hit[] }

export interface SearchBoxLabels { placeholder: string; label: string; button?: string; members: string; parties: string; topics: string; all: string }

interface ApiResult {
  members: { id: number; name: string; name_he: string }[];
  factions: { id: number; term: number; name: string; short?: string | null; name_he: string }[];
  topics: { slug: string; label: string; label_he: string }[];
}

export function SearchBox({ locale, action, labels, large = false, autoFocus = false }:
  { locale: string; action: string; labels: SearchBoxLabels; large?: boolean; autoFocus?: boolean }) {
  const router = useRouter();
  const [q, setQ] = useState("");
  const [groups, setGroups] = useState<Group[]>([]);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const box = useRef<HTMLDivElement>(null);
  const listId = useId();

  useEffect(() => {
    const needle = q.trim();
    const ctl = new AbortController();
    const timer = setTimeout(async () => {
      if (needle.length < 2) { setGroups([]); setOpen(false); return; }
      try {
        const res = await fetch(`/api/v1/search?q=${encodeURIComponent(needle)}&lang=${locale}`, { signal: ctl.signal });
        if (!res.ok) return;
        const r = (await res.json()).data as ApiResult;
        // one row per party name: "Likud" once, not once per Knesset (the newest faction carries the link)
        const seen = new Set<string>();
        const parties: Hit[] = [];
        for (const f of r.factions) {
          const name = f.short ?? f.name ?? f.name_he;
          if (seen.has(name)) continue;
          seen.add(name);
          parties.push({ href: `/${locale}/factions/${f.id}`, label: name, sub: f.name_he !== name ? f.name_he : undefined });
        }
        const g: Group[] = [
          { title: labels.members, hits: r.members.slice(0, 5).map((m) => ({ href: `/${locale}/members/${m.id}`, label: m.name ?? m.name_he, sub: m.name !== m.name_he ? m.name_he : undefined })) },
          { title: labels.parties, hits: parties.slice(0, 4) },
          { title: labels.topics, hits: r.topics.slice(0, 4).map((x) => ({ href: `/${locale}/topics/${x.slug}`, label: x.label ?? x.label_he })) },
        ].filter((x) => x.hits.length > 0);
        setGroups(g); setOpen(true); setActive(-1);
      } catch { /* aborted or offline: the form still works */ }
    }, 180);
    return () => { clearTimeout(timer); ctl.abort(); };
  }, [q, locale, labels.members, labels.parties, labels.topics]);

  useEffect(() => {
    const close = (e: MouseEvent) => { if (!box.current?.contains(e.target as Node)) setOpen(false); };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);

  const flat = groups.flatMap((g) => g.hits);
  // position of each group's first hit in the flat list, for keyboard highlighting
  const starts = groups.reduce<number[]>((acc, g, i) => [...acc, (acc[i - 1] ?? 0) + (groups[i - 1]?.hits.length ?? 0)], []);

  function onKey(e: React.KeyboardEvent<HTMLInputElement>) {
    if (!open || flat.length === 0) return;
    if (e.key === "ArrowDown") { e.preventDefault(); setActive((a) => (a + 1) % flat.length); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setActive((a) => (a <= 0 ? flat.length - 1 : a - 1)); }
    else if (e.key === "Escape") { setOpen(false); }
    else if (e.key === "Enter" && active >= 0) { e.preventDefault(); setOpen(false); router.push(flat[active].href); }
  }

  return (
    <div ref={box} className={`${styles.box} ${large ? styles.large : ""}`}>
      <form action={action} role="search" className={styles.form} onSubmit={() => setOpen(false)}>
        <input name="q" value={q} onChange={(e) => setQ(e.target.value)} onFocus={() => flat.length > 0 && setOpen(true)} onKeyDown={onKey}
               placeholder={labels.placeholder} aria-label={labels.label} dir="auto" autoComplete="off" autoFocus={autoFocus}
               role="combobox" aria-autocomplete="list" aria-expanded={open} aria-controls={listId} />
        {labels.button && <button type="submit">{labels.button}</button>}
      </form>
      {open && flat.length > 0 && (
        <div id={listId} role="listbox" className={styles.list}>
          {groups.map((g, gi) => (
            <div key={g.title} className={styles.group}>
              <div className={styles.groupTitle}>{g.title}</div>
              {g.hits.map((h, hi) => {
                const i = starts[gi] + hi;
                return (
                  <a key={h.href} href={h.href} role="option" aria-selected={i === active} className={`${styles.hit} ${i === active ? styles.active : ""}`}
                     onMouseEnter={() => setActive(i)} onClick={() => setOpen(false)}>
                    <span>{h.label}</span>{h.sub && <span className={styles.sub} dir="rtl">{h.sub}</span>}
                  </a>
                );
              })}
            </div>
          ))}
          <a href={`${action}?q=${encodeURIComponent(q.trim())}`} className={`${styles.hit} ${styles.all}`} onClick={() => setOpen(false)}>{labels.all} →</a>
        </div>
      )}
    </div>
  );
}
