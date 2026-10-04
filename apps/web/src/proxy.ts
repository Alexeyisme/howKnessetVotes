// Locale routing (docs/roadmap.md L3). Every page lives under /ru, /en or /he. A path without a locale (old links,
// the bare domain) redirects to the visitor's language: the last one they picked (cookie), else the browser's
// Accept-Language, else Russian. Locale paths pass through with the locale remembered and the unprefixed path in a
// request header for the language switcher and hreflang links.

import { NextResponse, type NextRequest } from "next/server";
import { DEFAULT_LOCALE, fromAcceptLanguage, isLocale, LOCALE_COOKIE, PATH_HEADER } from "@/i18n/config";

export function proxy(request: NextRequest) {
  const { pathname, search } = request.nextUrl;
  const first = pathname.split("/")[1];

  if (isLocale(first)) {
    const headers = new Headers(request.headers);
    headers.set(PATH_HEADER, (pathname.slice(first.length + 1) || "/") + search);
    const res = NextResponse.next({ request: { headers } });
    if (request.cookies.get(LOCALE_COOKIE)?.value !== first) {
      res.cookies.set(LOCALE_COOKIE, first, { path: "/", maxAge: 60 * 60 * 24 * 365, sameSite: "lax" });
    }
    return res;
  }

  const cookie = request.cookies.get(LOCALE_COOKIE)?.value;
  const locale = isLocale(cookie) ? cookie : fromAcceptLanguage(request.headers.get("accept-language")) ?? DEFAULT_LOCALE;
  const url = request.nextUrl.clone();
  url.pathname = pathname === "/" ? `/${locale}` : `/${locale}${pathname}`;
  const res = NextResponse.redirect(url);
  res.headers.set("Vary", "Accept-Language, Cookie");
  return res;
}

export const config = {
  // API paths (routed to the API by Caddy), Next internals and files are not localized
  matcher: ["/((?!_next/|api/|docs|openapi\\.json|.*\\.[a-z0-9]+$).*)"],
};
