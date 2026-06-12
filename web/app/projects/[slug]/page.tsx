import Link from "next/link";
import { notFound } from "next/navigation";

import LogoutButton from "@/components/LogoutButton";
import { PROJECTS, getProject } from "@/lib/library";

export function generateStaticParams() {
  return PROJECTS.map((p) => ({ slug: p.slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const project = getProject(slug);
  return { title: project ? project.title : "Project not found" };
}

export default async function ProjectPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const project = getProject(slug);
  if (!project) notFound();

  const decks = project.artifacts.filter((a) => a.type === "deck" || a.type === "document");
  const images = project.artifacts.filter((a) => a.type === "image");

  return (
    <main className="shell">
      <header className="topbar">
        <div className="lead">
          <Link href="/" className="back">
            ← Library
          </Link>
          <h1>{project.title}</h1>
          <p>
            {project.summary ||
              (project.topic ? `Research on ${project.topic}.` : "Research project.")}
          </p>
        </div>
        <LogoutButton />
      </header>

      <div className="metarow">
        {project.tags.map((t) => (
          <span key={t} className="tagdot">
            {t}
          </span>
        ))}
        <span className="metaitem">v{project.version}</span>
        {project.updated && <span className="metaitem">updated {project.updated}</span>}
      </div>

      {decks.length > 0 && (
        <section className="artifacts">
          {decks.map((a) => (
            <div key={a.url} className="artifactrow">
              <a className="artifact" href={a.url} target="_blank" rel="noreferrer">
                {a.type === "deck" ? "🖥️" : "📄"} {a.name} ↗
              </a>
              {/* Decks are self-contained HTML — download to run standalone offline. */}
              <a className="artifact download" href={a.url} download={a.name}>
                ⬇ Download
              </a>
            </div>
          ))}
        </section>
      )}

      {project.hasReport && (
        <article
          className="prose"
          dangerouslySetInnerHTML={{ __html: project.reportHtml }}
        />
      )}

      {images.length > 0 && (
        <section className="figures">
          <h2 className="sectionhead">Diagrams</h2>
          {images.map((a) => (
            // eslint-disable-next-line @next/next/no-img-element
            <img key={a.url} src={a.url} alt={a.name} className="figure" />
          ))}
        </section>
      )}

      {project.sources.length > 0 && (
        <section className="sources">
          <h2 className="sectionhead">Sources ({project.sources.length})</h2>
          <ul className="sourcelist">
            {project.sources.map((s, idx) => (
              <li key={(s.url || "") + idx} className="source">
                {s.reliability_tier && (
                  <span className={`tier tier-${s.reliability_tier}`}>{s.reliability_tier}</span>
                )}
                {s.url ? (
                  <a href={s.url} target="_blank" rel="noreferrer">
                    {s.title || s.url}
                  </a>
                ) : (
                  <span>{s.title || "Untitled source"}</span>
                )}
                {s.domain && <span className="domain">{s.domain}</span>}
              </li>
            ))}
          </ul>
        </section>
      )}

      {project.changelog.length > 0 && (
        <section className="changelog">
          <h2 className="sectionhead">History</h2>
          <ul className="changelist">
            {[...project.changelog].reverse().map((c) => (
              <li key={c.version}>
                <span className="metaitem">v{c.version}</span>
                <span className="changedate">{c.date}</span>
                <span>{c.note}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {project.related.length > 0 && (
        <section className="related">
          <h2 className="sectionhead">Related</h2>
          <div className="relatedlinks">
            {project.related.map((slug) => {
              const rel = getProject(slug);
              return (
                <Link key={slug} href={`/projects/${slug}`} className="chip">
                  {rel ? rel.title : slug}
                </Link>
              );
            })}
          </div>
        </section>
      )}

      <footer className="footer">Research Agent · private</footer>
    </main>
  );
}
