"use client";

import { useEffect, useRef, useState } from "react";

type Turnstile = {
  render: (el: HTMLElement, opts: Record<string, unknown>) => string;
  reset: (id?: string) => void;
  remove: (id: string) => void;
};
declare global { interface Window { turnstile?: Turnstile } }

const TURNSTILE_JS = "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit";

/** Cloudflare's script, loaded once per page when the form first needs it. */
function loadTurnstile(): Promise<Turnstile> {
  return new Promise((resolve, reject) => {
    if (window.turnstile) return resolve(window.turnstile);
    let s = document.querySelector<HTMLScriptElement>(`script[src="${TURNSTILE_JS}"]`);
    if (!s) {
      s = document.createElement("script");
      s.src = TURNSTILE_JS;
      s.async = true;
      document.head.appendChild(s);
    }
    s.addEventListener("load", () => (window.turnstile ? resolve(window.turnstile) : reject()));
    s.addEventListener("error", () => reject());
  });
}

const FIELD = { font: "inherit", padding: 8, border: "1px solid var(--border)", borderRadius: 8, background: "var(--surface)", color: "var(--ink)" };

/** Posts a correction or a message to the author to /api/v1/suggestions (same origin). A correction has the source
 *  hash and the note; a message has neither and is free text. The hidden `website` field is a honeypot for bots; with a
 *  `siteKey`, Cloudflare Turnstile (usually invisible) gives a token the API verifies. */
export function SuggestForm({ sha, lang, text, page, siteKey, labels }:
  { sha: string | null; lang: string; text: string; page: string | null; siteKey: string | null;
    labels: { textLabel: string; noteLabel: string; contactLabel: string; send: string; thanks: string; error: string } }) {
  const [value, setValue] = useState(text);
  const [note, setNote] = useState("");
  const [contact, setContact] = useState("");
  const [token, setToken] = useState("");
  const box = useRef<HTMLDivElement>(null);
  const widget = useRef<string | null>(null);

  useEffect(() => {
    if (!siteKey || !box.current) return;
    let gone = false;
    loadTurnstile().then((ts) => {
      if (gone || !box.current) return;
      widget.current = ts.render(box.current, {
        sitekey: siteKey, language: lang, appearance: "interaction-only",
        callback: (t: string) => setToken(t), "expired-callback": () => setToken(""), "error-callback": () => setToken(""),
      });
    }).catch(() => {});
    return () => { gone = true; if (widget.current) window.turnstile?.remove(widget.current); widget.current = null; };
  }, [siteKey, lang]);
  const [state, setState] = useState<"idle" | "sending" | "done" | "error">("idle");

  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const hp = (e.currentTarget.elements.namedItem("website") as HTMLInputElement | null)?.value ?? "";
    setState("sending");
    try {
      const res = await fetch("/api/v1/suggestions", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source_sha256: sha, language: lang, suggested_text: value.trim(), note: note.trim() || null,
                              contact: contact.trim() || null, page, website: hp, turnstile_token: token || null }),
      });
      setState(res.ok ? "done" : "error");
      if (!res.ok && widget.current) { window.turnstile?.reset(widget.current); setToken(""); }
    } catch { setState("error"); }
  }

  if (state === "done") return <p className="note">{labels.thanks}</p>;
  return (
    <form onSubmit={submit} className="stack">
      <label className="small" style={{ display: "grid", gap: 4 }}>
        {labels.textLabel}
        <textarea name="text" value={value} onChange={(e) => setValue(e.target.value)} required maxLength={2000} rows={sha ? 3 : 5} dir="auto" style={FIELD} />
      </label>
      {sha && (
        <label className="small" style={{ display: "grid", gap: 4 }}>
          {labels.noteLabel}
          <textarea name="note" value={note} onChange={(e) => setNote(e.target.value)} maxLength={2000} rows={2} dir="auto" style={FIELD} />
        </label>
      )}
      <label className="small" style={{ display: "grid", gap: 4 }}>
        {labels.contactLabel}
        <input type="text" name="contact" value={contact} onChange={(e) => setContact(e.target.value)} maxLength={200} dir="auto" style={FIELD} />
      </label>
      <input type="text" name="website" tabIndex={-1} autoComplete="off" aria-hidden style={{ position: "absolute", left: -9999 }} />
      {siteKey && <div ref={box} />}
      {state === "error" && <p className="note">{labels.error}</p>}
      <p><button type="submit" disabled={state === "sending" || !value.trim() || (!!siteKey && !token)}
                 style={{ font: "inherit", padding: "8px 16px", borderRadius: 10, border: "1px solid var(--accent)", background: "var(--accent)", color: "#fff", cursor: "pointer" }}>
        {labels.send}
      </button></p>
    </form>
  );
}
