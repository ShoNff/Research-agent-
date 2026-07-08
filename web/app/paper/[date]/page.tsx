import Link from "next/link";
import { notFound } from "next/navigation";

import EditionView from "@/components/EditionView";
import LogoutButton from "@/components/LogoutButton";
import { EDITIONS, getEdition } from "@/lib/editions";

export function generateStaticParams() {
  return EDITIONS.map((e) => ({ date: e.date }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ date: string }>;
}) {
  const { date } = await params;
  const edition = getEdition(date);
  return { title: edition ? `The Daily Brief — ${date}` : "Edition not found" };
}

export default async function EditionPage({
  params,
}: {
  params: Promise<{ date: string }>;
}) {
  const { date } = await params;
  const edition = getEdition(date);
  if (!edition) notFound();

  return (
    <main className="shell">
      <header className="topbar">
        <div className="lead">
          <Link href="/paper" className="back">
            ← All editions
          </Link>
          <h1>The Daily Brief</h1>
        </div>
        <LogoutButton />
      </header>

      <EditionView edition={edition} />

      <footer className="footer">Research Agent · private</footer>
    </main>
  );
}
