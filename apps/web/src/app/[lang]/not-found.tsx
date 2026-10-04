import Link from "@/components/Link";
import { getT } from "@/i18n/server";

export default async function NotFound() {
  const d = (await getT()).d.notFound;
  return (
    <div className="card">
      <h1 className="section-title">{d.title}</h1>
      <p className="muted">{d.text} <Link href="/">{d.home}</Link></p>
    </div>
  );
}
