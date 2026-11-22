import { notFound } from "next/navigation";

// An address under a language that no page matches: without this route Next.js answers with its bare 404, outside
// the site layout. Calling notFound() here renders [lang]/not-found.tsx with the header and the footer.
export default function UnknownPage() {
  notFound();
}
