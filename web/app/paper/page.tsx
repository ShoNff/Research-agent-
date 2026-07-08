import Link from "next/link";

import LogoutButton from "@/components/LogoutButton";
import { EDITIONS } from "@/lib/editions";

export const metadata = { title: "The Daily Brief — archive" };

export default function PaperArchivePage() {
  return (
    <main className="shell">
      <header className="topbar">
        <div className="lead">
          <Link href="/" className="back">
            ← Library
          </Link>
          <h1>The Daily Brief</h1>
          <p>Every edition, archived.</p>
        </div>
        <LogoutButton />
      </header>

      {EDITIONS.length === 0 && <p>No editions yet — the first paper lands soon.</p>}

      <ul className="editionList">
        {EDITIONS.map((e) => (
          <li key={e.date}>
            <Link href={`/paper/${e.date}`} className="editionListItem">
              <span className="editionListDate">{e.date}</span>
              <span className="editionListHeadline">{e.headline}</span>
            </Link>
          </li>
        ))}
      </ul>

      <footer className="footer">Research Agent · private</footer>
    </main>
  );
}
