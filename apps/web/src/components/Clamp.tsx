"use client";

import { useState } from "react";
import styles from "./Clamp.module.css";

/** A long page title on a phone: four lines and a button for the rest (the Hebrew original folds away with it), so
 *  the outcome is on the first screen; a title took twelve lines there. Wider screens show everything, no button. */
export function Clamp({ children, more, less }: { children: React.ReactNode; more: string; less: string }) {
  const [open, setOpen] = useState(false);
  return (
    <div className={styles.clamp} data-open={open ? "" : undefined}>
      {children}
      <button type="button" className={styles.toggle} aria-expanded={open} onClick={() => setOpen(!open)}>{open ? less : more}</button>
    </div>
  );
}
