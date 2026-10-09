"use client";

import NextLink from "next/link";
import { usePathname } from "next/navigation";

/** The footer's "report a mistake" link, carrying the page it was clicked on (the layout cannot know the path, and
 *  document.referrer does not follow client-side navigation). */
export function ReportLink({ locale, label }: { locale: string; label: string }) {
  const path = usePathname().replace(/^\/(he|en|ru|ar)(?=\/|$)/, "") || "/";
  const page = path.startsWith("/suggest") ? "" : `?page=${encodeURIComponent(path)}`;
  return <NextLink href={`/${locale}/suggest${page}`} prefetch={false} rel="nofollow">{label}</NextLink>;
}
