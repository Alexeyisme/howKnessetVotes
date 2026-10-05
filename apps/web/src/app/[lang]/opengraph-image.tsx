import { ImageResponse } from "next/og";
import { getStatus } from "@/lib/api";
import { Frame, og, OG_SIZE, OG_TYPE, ogFonts, ogT, Row, T } from "@/lib/og";

export const alt = "How the Knesset Votes";
export const size = OG_SIZE;
export const contentType = OG_TYPE;

/** Default share image for every page without its own: the site in one line and its size in numbers. */
export default async function Image({ params }: { params: Promise<{ lang: string }> }) {
  const { lang } = await params;
  const t = ogT(lang);
  const L = t.locale;
  const rtl = L === "he" || L === "ar";
  const [fonts, status] = await Promise.all([ogFonts(), getStatus().then((r) => r.data, () => null)]);
  const stat = (value: string, label: string) => (
    <div style={{ display: "flex", flexDirection: "column", alignItems: rtl ? "flex-end" : "flex-start" }}>
      <span style={{ fontSize: 64, fontWeight: 700, color: og.INK }}>{value}</span><span><T locale={L}>{label}</T></span>
    </div>
  );
  return new ImageResponse(
    (
      <Frame locale={L} siteName={t.d.site.name}>
        <div style={{ display: "flex", fontSize: 84, fontWeight: 700, lineHeight: 1.05 }}><T locale={L}>{t.d.site.name}</T></div>
        <div style={{ display: "flex", fontSize: 36, color: og.INK2, lineHeight: 1.3, maxWidth: 1000, maxHeight: 150, overflow: "hidden" }}>
          <T locale={L}>{t.d.home.lead}</T>
        </div>
        {status && (
          <Row locale={L} style={{ gap: 48, marginTop: "auto", color: og.INK2, fontSize: 30 }}>
            {stat(t.num(status.coverage.votes), t.d.nav.votes)}
            {stat(t.num(status.coverage.ballots), `${t.d.ballots.member} × ${t.d.ballots.vote}`)}
          </Row>
        )}
      </Frame>
    ),
    { ...size, fonts },
  );
}
