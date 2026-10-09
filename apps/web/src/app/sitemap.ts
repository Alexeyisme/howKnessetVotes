import type { MetadataRoute } from "next";
import { listMembers, listParties, listTopics } from "@/lib/api";
import { LOCALES, localize } from "@/i18n/config";

const SITE_URL = process.env.SITE_URL ?? "https://knessetvotes.org";

const SECTIONS = ["/", "/votes", "/members", "/parties", "/topics", "/bills", "/match", "/compare", "/about/glossary", "/about/methodology"];

/** One entry per page with its four language versions. */
function entry(path: string): MetadataRoute.Sitemap[number] {
  const languages = Object.fromEntries(LOCALES.map((l) => [l, `${SITE_URL}${localize(l, path)}`]));
  return { url: `${SITE_URL}${localize("ru", path)}`, alternates: { languages } };
}

// The hubs a visitor starts from: sections, members, parties and their factions, topics. Votes and bills (tens of
// thousands) are reached through their links; listing them would mean hundreds of API pages per sitemap build.
export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const [members, parties, topics] = await Promise.all([listMembers({}), listParties(), listTopics()]);
  return [
    ...SECTIONS.map(entry),
    ...members.data.map((m) => entry(`/members/${m.id}`)),
    ...parties.data.map((p) => entry(`/parties/${p.slug}`)),
    ...parties.data.flatMap((p) => p.factions.map((f) => entry(`/factions/${f.id}`))),
    ...topics.data.map((x) => entry(`/topics/${x.slug}`)),
  ];
}
