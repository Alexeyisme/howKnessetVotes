import { ImageResponse } from "next/og";
import { getFaction, getParty, NotFound } from "@/lib/api";
import { Frame, og, OG_SIZE, OG_TYPE, ogFonts, ogT, Row, T, visual } from "@/lib/og";

export const alt = "Party in the Knesset";
export const size = OG_SIZE;
export const contentType = OG_TYPE;

export default async function Image({ params }: { params: Promise<{ lang: string; slug: string }> }) {
  const { lang, slug } = await params;
  const t = ogT(lang);
  const L = t.locale;
  const fonts = await ogFonts();
  const party = await getParty(slug).then((r) => r.data, (e) => { if (e instanceof NotFound) return null; throw e; });
  if (!party) {
    return new ImageResponse(<Frame locale={L} siteName={t.d.site.name}><div style={{ fontSize: 48 }}><T locale={L}>{t.d.notFound.title}</T></div></Frame>, { ...size, fonts });
  }
  const latest = party.factions[party.factions.length - 1];
  const faction = latest ? await getFaction(latest.id).then((r) => r.data) : null;
  const members = faction ? faction.members.filter((m) => !m.valid_to).length : 0;
  const stat = (value: string, label: string) => (
    <div style={{ display: "flex", flexDirection: "column", alignItems: L === "he" || L === "ar" ? "flex-end" : "flex-start" }}>
      <span style={{ fontSize: 64, fontWeight: 700, color: og.INK }}>{value}</span>
      <span><T locale={L}>{label}</T></span>
    </div>
  );

  return new ImageResponse(
    (
      <Frame locale={L} siteName={t.d.site.name}>
        <div style={{ display: "flex", fontSize: 28, color: og.MUTED }}><T locale={L}>{t.d.parties.kicker}</T></div>
        <Row locale={L} style={{ alignItems: "center", gap: 20, fontSize: 84, fontWeight: 700, lineHeight: 1.05 }}>
          <span><T locale={L}>{t.party(party)}</T></span>
          {latest?.alignment_last && latest.alignment_last !== "unknown" && (
            <span style={{ fontSize: 30, fontWeight: 700, padding: "6px 20px", borderRadius: 999, border: `3px solid ${og.INK2}`, color: og.INK2 }}>
              <T locale={L}>{t.d.alignment[latest.alignment_last]}</T>
            </span>
          )}
        </Row>
        {L !== "he" && <div style={{ display: "flex", fontSize: 40, color: og.INK2 }}>{visual(party.name_he, "rtl")}</div>}
        {latest && faction && (
          <Row locale={L} style={{ gap: 48, marginTop: "auto", fontSize: 30, color: og.INK2 }}>
            {stat(String(members), `${t.d.parties.members} · ${t.d.common.term(latest.term)}`)}
            {stat(t.pct(faction.stats.cohesion), t.d.faction.cohesion)}
          </Row>
        )}
      </Frame>
    ),
    { ...size, fonts },
  );
}
