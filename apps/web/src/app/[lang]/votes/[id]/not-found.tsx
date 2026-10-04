import Link from "@/components/Link";
import { getT } from "@/i18n/server";

export default async function NotFound() {
  const d = (await getT()).d.vote;
  return (
    <div className="card">
      <h1 className="section-title">{d.notFound}</h1>
      <p className="muted">{d.notFoundText} <Link href="/votes">{d.backToList}</Link></p>
    </div>
  );
}
