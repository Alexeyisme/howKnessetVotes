import Link from "next/link";

export default function NotFound() {
  return (
    <div className="card">
      <h1 className="section-title">Голосование не найдено</h1>
      <p className="muted">Возможно, оно ещё не загружено. <Link href="/">К списку голосований</Link></p>
    </div>
  );
}
