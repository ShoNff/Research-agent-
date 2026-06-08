// Typed access to the research library.
//
// The data comes from lib/library.generated.ts, which scripts/build-library.mjs
// rebuilds from the repo's projects/ folder before every dev/build. Treat this
// module as the single read path for project data in the app.

import { LIBRARY } from "./library.generated";

export type Artifact = {
  type: string; // deck | image | document | file
  name: string;
  url: string;
};

export type Source = {
  url?: string;
  title?: string;
  domain?: string;
  reliability_tier?: string;
  confidence_score?: number;
};

export type ChangelogEntry = {
  version: number;
  date: string;
  note: string;
};

export type Project = {
  slug: string;
  title: string;
  topic: string;
  summary: string;
  tags: string[];
  created: string;
  updated: string;
  version: number;
  sources: Source[];
  related: string[];
  changelog: ChangelogEntry[];
  artifacts: Artifact[];
  hasReport: boolean;
  reportHtml: string;
};

export const PROJECTS: Project[] = LIBRARY as unknown as Project[];

export function getProject(slug: string): Project | null {
  return PROJECTS.find((p) => p.slug === slug) ?? null;
}

/** All distinct tags across the library, sorted by frequency then name. */
export function allTags(): string[] {
  const counts = new Map<string, number>();
  for (const p of PROJECTS) {
    for (const tag of p.tags) {
      counts.set(tag, (counts.get(tag) ?? 0) + 1);
    }
  }
  return [...counts.entries()]
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
    .map(([tag]) => tag);
}
