import NextLink from "next/link";
import type { ComponentProps } from "react";
import { getLocale } from "@/i18n/server";
import { localize } from "@/i18n/config";

/** next/link with the current locale prefixed to internal paths ("/votes/1" -> "/en/votes/1"). */
export default async function Link({ href, ...rest }: Omit<ComponentProps<typeof NextLink>, "href"> & { href: string }) {
  return <NextLink href={localize(await getLocale(), href)} {...rest} />;
}
