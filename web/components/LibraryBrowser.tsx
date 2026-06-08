"use client";

import { useMemo, useState } from "react";
import Link from "next/link";

export type ProjectCard = {
  slug: string;
  title: string;
  summary: string;
  tags: string[];
  updated: string;
  version: number;
  artifactCount: number;
};

export type ExtraCard = {
  id: string;
  title: string;
  description: string;
  href: string;
  emoji?: string;
};

export default function LibraryBrowser({
  projects,
  tags,
  extras,
}: {
  projects: ProjectCard[];
  tags: string[];
  extras: ExtraCard[];
}) {
  const [query, setQuery] = useState("");
  const [activeTag, setActiveTag] = useState<string | null>(null);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return projects.filter((p) => {
      if (activeTag && !p.tags.includes(activeTag)) return false;
      if (!q) return true;
      return (
        p.title.toLowerCase().includes(q) ||
        p.summary.toLowerCase().includes(q) ||
        p.tags.some((t) => t.toLowerCase().includes(q))
      );
    });
  }, [projects, query, activeTag]);

  const hasProjects = projects.length > 0;

  return (
    <>
      {hasProjects && (
        <div className="controls">
          <input
            className="search"
            type="search"
            placeholder="Search projects…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            aria-label="Search projects"
          />
          {tags.length > 0 && (
            <div className="tagbar">
              <button
                className={`chip ${activeTag === null ? "on" : ""}`}
                onClick={() => setActiveTag(null)}
              >
                All
              </button>
              {tags.map((tag) => (
                <button
                  key={tag}
                  className={`chip ${activeTag === tag ? "on" : ""}`}
                  onClick={() => setActiveTag(activeTag === tag ? null : tag)}
                >
                  {tag}
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {!hasProjects ? (
        <div className="empty">
          No research projects yet. Run the research agent — each run publishes a
          project here automatically.
        </div>
      ) : filtered.length === 0 ? (
        <div className="empty">No projects match your search.</div>
      ) : (
        <section className="grid">
          {filtered.map((p) => (
            <Link key={p.slug} href={`/projects/${p.slug}`} className="card live">
              <div className="badge">📄</div>
              <h3>{p.title}</h3>
              <p>{p.summary || "Research project."}</p>
              <div className="cardmeta">
                {p.tags.slice(0, 3).map((t) => (
                  <span key={t} className="tagdot">
                    {t}
                  </span>
                ))}
              </div>
              <span className="pill live">Open →</span>
            </Link>
          ))}
        </section>
      )}

      {extras.length > 0 && (
        <>
          <h2 className="sectionhead">Decks &amp; demos</h2>
          <section className="grid">
            {extras.map((x) => (
              <a
                key={x.id}
                className="card live"
                href={x.href}
                target="_blank"
                rel="noreferrer"
              >
                <div className="badge">{x.emoji ?? "🚀"}</div>
                <h3>{x.title}</h3>
                <p>{x.description}</p>
                <span className="pill live">Open ↗</span>
              </a>
            ))}
          </section>
        </>
      )}
    </>
  );
}
