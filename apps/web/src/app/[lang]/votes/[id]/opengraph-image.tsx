import { ImageResponse } from "next/og";
import { getVote, NotFound } from "@/lib/api";
import { Frame, og, OG_SIZE, OG_TYPE, ogFonts, ogT, PlenumBar, Row, T, visual } from "@/lib/og";
import { verdict } from "@/lib/labels";

export const alt = "How the Knesset voted";
export const size = OG_SIZE;
export const contentType = OG_TYPE;

export default async function Image({ params }: { params: Promise<{ lang: string; id: string }> }) {
  const { lang, id } = await params;
  const t = ogT(lang);
  const L = t.locale;
  const vote = await getVote(Number(id)).then((r) => r.data, (e) => { if (e instanceof NotFound) return null; throw e; });
  const fonts = await ogFonts();
  if (!vote) {
    return new ImageResponse(<Frame locale={L} siteName={t.d.site.name}><div style={{ fontSize: 48 }}><T locale={L}>{t.d.vote.notFound}</T></div></Frame>, { ...size, fonts });
  }
  const rc = vote.roll_call;
  const cast = rc.for + rc.against + rc.abstain;
  const out = verdict(vote, t);
  const meta = [t.date(vote.occurred_on), vote.stage ? t.d.stage[vote.stage] : null].filter(Boolean).join(" · ");

  return new ImageResponse(
    (
      <Frame locale={L} siteName={t.d.site.name}>
        <div style={{ display: "flex", fontSize: 28, color: og.MUTED }}><T locale={L}>{meta}</T></div>
        {out && (
          <Row locale={L} style={{ alignItems: "center", gap: 18, fontSize: 60, fontWeight: 700, lineHeight: 1.1 }}>
            <div style={{ width: 26, height: 26, borderRadius: 13, background: out.accepted ? "#2a78d6" : "#e34948", flexShrink: 0 }} />
            <span><T locale={L}>{out.text}</T></span>
          </Row>
        )}
        {/* the Hebrew title, in visual order, right-aligned, clipped to two lines' height */}
        <div style={{ display: "flex", width: "100%", justifyContent: "flex-end", fontSize: 40, lineHeight: 1.25, color: og.INK2, maxHeight: 100, overflow: "hidden" }}>
          <span style={{ textAlign: "right" }}>{visual(vote.title_he, "rtl")}</span>
        </div>
        {cast > 0 && (
          <div style={{ display: "flex", flexDirection: "column", gap: 12, marginTop: "auto", width: "100%" }}>
            <PlenumBar c={rc} />
            <Row locale={L} style={{ justifyContent: "space-between", fontSize: 30, color: og.INK2 }}>
              <span><T locale={L}>{t.d.rc.line(rc.for, rc.against, rc.abstain)}</T></span>
              <span style={{ color: og.MUTED }}><T locale={L}>{t.d.rc.cast120(cast)}</T></span>
            </Row>
            {vote.blocs?.contested && (
              <Row locale={L} style={{ fontSize: 30, fontWeight: 700, color: og.INK2 }}><T locale={L}>{t.d.blocs.short(vote.blocs.coalition, vote.blocs.opposition)}</T></Row>
            )}
          </div>
        )}
      </Frame>
    ),
    { ...size, fonts },
  );
}
