import Link from "next/link";

import type { Edition } from "@/lib/editions";
import { getProject } from "@/lib/library";

const TIER_CLASS: Record<string, string> = {
  established: "tier-established",
  reputable: "tier-reputable",
  emerging: "tier-emerging",
  opinion: "tier-opinion",
  unknown: "tier-unknown",
};

function dateHuman(iso: string): string {
  const d = new Date(iso + "T12:00:00Z");
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
  });
}

export default function EditionView({
  edition,
  compact = false,
}: {
  edition: Edition;
  compact?: boolean;
}) {
  return (
    <section className={compact ? "edition editionCompact" : "edition"}>
      <div className="editionMast">
        <div className="editionKicker">
          The Daily Brief · {dateHuman(edition.date)}
        </div>
        <h2 className="editionHeadline">{edition.headline}</h2>
        {edition.overview && <p className="editionOverview">{edition.overview}</p>}
      </div>

      <div className="editionGrid">
        {edition.sections
          .filter((s) => s.items.length > 0)
          .map((section) => (
            <div
              key={section.id}
              className={`editionSection editionSection-${section.id}`}
            >
              <div className="editionSectionTitle">{section.title}</div>
              {section.items.map((item, idx) => {
                const related = item.related_slug ? getProject(item.related_slug) : null;
                return (
                  <article key={idx} className="editionItem">
                    <h3>{item.headline}</h3>
                    <p>{item.body}</p>
                    {item.so_what && (
                      <p className="soWhat">
                        <strong>So what:</strong> {item.so_what}
                      </p>
                    )}
                    <div className="editionMeta">
                      {(item.sources ?? []).slice(0, 3).map((s, si) => (
                        <a
                          key={si}
                          href={s.url}
                          target="_blank"
                          rel="noreferrer"
                          className="editionSource"
                        >
                          {s.reliability_tier && (
                            <span
                              className={`tierdot ${TIER_CLASS[s.reliability_tier] ?? "tier-unknown"}`}
                            />
                          )}
                          {s.title || s.domain || s.url}
                        </a>
                      ))}
                      {related && (
                        <Link href={`/projects/${related.slug}`} className="editionRelated">
                          in your library: {related.title} →
                        </Link>
                      )}
                    </div>
                  </article>
                );
              })}
            </div>
          ))}
      </div>
    </section>
  );
}
