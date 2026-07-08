import Link from "next/link";

import EditionView from "@/components/EditionView";
import LogoutButton from "@/components/LogoutButton";
import LibraryBrowser, { ExtraCard, ProjectCard } from "@/components/LibraryBrowser";
import { EDITIONS, latestEdition } from "@/lib/editions";
import { PROJECTS, allTags } from "@/lib/library";
import { POCS, isLive } from "@/lib/pocs";

export default function LauncherPage() {
  const projects: ProjectCard[] = PROJECTS.map((p) => ({
    slug: p.slug,
    title: p.title,
    summary: p.summary,
    tags: p.tags,
    updated: p.updated,
    version: p.version,
    artifactCount: p.artifacts.length,
  }));

  // Manually-curated POCs (e.g. standalone decks) live alongside the auto-built
  // research library so nothing previously added disappears.
  const extras: ExtraCard[] = POCS.filter(isLive).map((p) => ({
    id: p.id,
    title: p.title,
    description: p.description,
    href: p.href,
    emoji: p.emoji,
  }));

  const edition = latestEdition();

  return (
    <main className="shell">
      <header className="topbar">
        <div className="lead">
          <h1>Research Library</h1>
          <p>Every topic researched, published here automatically.</p>
        </div>
        <LogoutButton />
      </header>

      {edition && (
        <>
          <EditionView edition={edition} />
          {EDITIONS.length > 1 && (
            <div className="editionArchiveLink">
              <Link href="/paper">Past editions ({EDITIONS.length}) →</Link>
            </div>
          )}
        </>
      )}

      <LibraryBrowser projects={projects} tags={allTags()} extras={extras} />

      <footer className="footer">Research Agent · private</footer>
    </main>
  );
}
