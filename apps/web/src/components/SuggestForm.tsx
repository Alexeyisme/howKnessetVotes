"use client";

import { useState } from "react";

/** Posts a correction to /api/v1/suggestions (same origin). The hidden `website` field is a honeypot for bots. */
export function SuggestForm({ sha, lang, text, page, labels }:
  { sha: string | null; lang: string; text: string; page: string | null; labels: { textLabel: string; noteLabel: string; send: string; thanks: string; error: string } }) {
  const [value, setValue] = useState(text);
  const [note, setNote] = useState("");
  const [state, setState] = useState<"idle" | "sending" | "done" | "error">("idle");

  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const hp = (e.currentTarget.elements.namedItem("website") as HTMLInputElement | null)?.value ?? "";
    setState("sending");
    try {
      const res = await fetch("/api/v1/suggestions", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source_sha256: sha, language: lang, suggested_text: value.trim(), note: note.trim() || null, page, website: hp }),
      });
      setState(res.ok ? "done" : "error");
    } catch { setState("error"); }
  }

  if (state === "done") return <p className="note">{labels.thanks}</p>;
  return (
    <form onSubmit={submit} className="stack">
      <label className="small" style={{ display: "grid", gap: 4 }}>
        {labels.textLabel}
        <textarea name="text" value={value} onChange={(e) => setValue(e.target.value)} required maxLength={2000} rows={3} dir="auto"
                  style={{ font: "inherit", padding: 8, border: "1px solid var(--border)", borderRadius: 8, background: "var(--surface)", color: "var(--ink)" }} />
      </label>
      <label className="small" style={{ display: "grid", gap: 4 }}>
        {labels.noteLabel}
        <textarea name="note" value={note} onChange={(e) => setNote(e.target.value)} maxLength={2000} rows={2} dir="auto"
                  style={{ font: "inherit", padding: 8, border: "1px solid var(--border)", borderRadius: 8, background: "var(--surface)", color: "var(--ink)" }} />
      </label>
      <input type="text" name="website" tabIndex={-1} autoComplete="off" aria-hidden style={{ position: "absolute", left: -9999 }} />
      {state === "error" && <p className="note">{labels.error}</p>}
      <p><button type="submit" disabled={state === "sending" || !value.trim()}
                 style={{ font: "inherit", padding: "8px 16px", borderRadius: 10, border: "1px solid var(--accent)", background: "var(--accent)", color: "#fff", cursor: "pointer" }}>
        {labels.send}
      </button></p>
    </form>
  );
}
