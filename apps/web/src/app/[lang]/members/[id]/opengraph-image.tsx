import { ImageResponse } from "next/og";
import { getMember, NotFound } from "@/lib/api";
import { Frame, og, OG_SIZE, OG_TYPE, ogFonts, ogT, Row, T } from "@/lib/og";

export const alt = "Member of Knesset";
export const size = OG_SIZE;
export const contentType = OG_TYPE;

export default async function Image({ params }: { params: Promise<{ lang: string; id: string }> }) {
  const { lang, id } = await params;
  const t = ogT(lang);
  const L = t.locale;
  const rtl = L === "he" || L === "ar";
  const fonts = await ogFonts();
  const m = await getMember(Number(id)).then((r) => r.data, (e) => { if (e instanceof NotFound) return null; throw e; });
  if (!m) {
    return new ImageResponse(<Frame locale={L} siteName={t.d.site.name}><div style={{ fontSize: 48 }}><T locale={L}>{t.d.notFound.title}</T></div></Frame>, { ...size, fonts });
  }
  const s = m.stats;
  const stat = (value: string, label: string) => (
    <div style={{ display: "flex", flexDirection: "column", maxWidth: 330, alignItems: rtl ? "flex-end" : "flex-start" }}>
      <span style={{ fontSize: 60, fontWeight: 700, color: og.INK }}>{value}</span>
      <span style={{ fontSize: 26, lineHeight: 1.2 }}><T locale={L}>{label}</T></span>
    </div>
  );

  return new ImageResponse(
    (
      <Frame locale={L} siteName={t.d.site.name}>
        <div style={{ display: "flex", fontSize: 28, color: og.MUTED }}><T locale={L}>{t.d.member.kicker(m.terms.join(", "))}</T></div>
        <div style={{ display: "flex", fontSize: 80, fontWeight: 700, lineHeight: 1.05 }}><T locale={L}>{t.person(m)}</T></div>
        {m.last_faction && <div style={{ display: "flex", fontSize: 38, color: og.INK2 }}><T locale={L}>{t.faction(m.last_faction)}</T></div>}
        <Row locale={L} style={{ gap: 44, marginTop: "auto", color: og.INK2 }}>
          {stat(t.pct(s.with_coalition), t.d.member.withCoalition)}
          {stat(String(s.deviation_from_faction.numerator), t.d.member.deviation)}
          {stat(t.pct(s.participation), t.d.member.participation)}
        </Row>
      </Frame>
    ),
    { ...size, fonts },
  );
}
