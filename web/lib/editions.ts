// Typed access to the generated daily-paper data. Mirrors lib/library.ts:
// editions.generated.ts is rebuilt from editions/ before every dev/build.

import { EDITIONS as RAW } from "./editions.generated";

export type EditionSource = {
  url: string;
  title?: string;
  domain?: string;
  reliability_tier?: string;
};

export type EditionItem = {
  headline: string;
  body: string;
  so_what?: string;
  sources?: EditionSource[];
  related_slug?: string;
};

export type EditionSection = {
  id: string;
  title: string;
  items: EditionItem[];
};

export type Edition = {
  date: string;
  headline: string;
  overview?: string;
  sections: EditionSection[];
  refresh_recommendations?: string[];
};

export const EDITIONS = RAW as unknown as Edition[];

export function latestEdition(): Edition | null {
  return EDITIONS.length > 0 ? EDITIONS[0] : null;
}

export function getEdition(date: string): Edition | null {
  return EDITIONS.find((e) => e.date === date) ?? null;
}
