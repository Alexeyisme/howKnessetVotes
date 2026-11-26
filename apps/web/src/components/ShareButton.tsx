"use client";

import { useState } from "react";

/** Share this page: the phone's own share sheet where there is one, else the link is copied. Links to a vote travel
 *  through messengers (84% of visits arrive with no referrer), so the page offers the next hop itself. */
export function ShareButton({ label, copied, title, className }: { label: string; copied: string; title: string; className?: string }) {
  const [done, setDone] = useState(false);
  async function share() {
    const url = window.location.href;
    try {
      if (navigator.share) await navigator.share({ title, url });
      else {
        await navigator.clipboard.writeText(url);
        setDone(true);
        setTimeout(() => setDone(false), 2500);
      }
    } catch { /* cancelled */ }
  }
  return <button type="button" className={className} onClick={share} aria-live="polite">{done ? copied : label}</button>;
}
