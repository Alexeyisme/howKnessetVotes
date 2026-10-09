"use client";

import { useEffect } from "react";
import { LOCALE_COOKIE } from "@/i18n/config";

/** Remembers the language of the page being read, for the redirect of unprefixed links (proxy.ts). Set here and not
 *  by the server, so that HTML responses carry no Set-Cookie and can be cached for everyone. */
export function LangCookie({ locale }: { locale: string }) {
  useEffect(() => {
    if (!document.cookie.split("; ").includes(`${LOCALE_COOKIE}=${locale}`)) {
      document.cookie = `${LOCALE_COOKIE}=${locale}; path=/; max-age=${60 * 60 * 24 * 365}; samesite=lax`;
    }
  }, [locale]);
  return null;
}
