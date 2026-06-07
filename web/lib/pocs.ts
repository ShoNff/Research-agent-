// The launcher is data-driven: every card on the home page comes from this list.
//
// To add a POC, append an entry below and (for live ones) set `href` to its URL.
// Cards left as "coming-soon" (or with href "#") render disabled until you add a
// real link. Commit + push and Vercel redeploys automatically.

export type Poc = {
  id: string;
  title: string;
  description: string;
  href: string; // external URL or hosted asset; "#" until filled in
  status?: "live" | "coming-soon";
  emoji?: string; // simple per-card glyph
};

export const POCS: Poc[] = [
  {
    id: "deck",
    title: "Research Deck",
    description: "The presentation deck built with the research agent.",
    href: "#", // <- paste the real link here (Google Slides, hosted PDF, etc.)
    status: "coming-soon",
    emoji: "📊",
  },
  // Add more POCs by appending entries here, e.g.:
  // {
  //   id: "report",
  //   title: "Latest Report",
  //   description: "Full markdown/HTML research report.",
  //   href: "https://example.com/report",
  //   status: "live",
  //   emoji: "📄",
  // },
];

/** A POC is openable only if it's live and has a real destination. */
export function isLive(poc: Poc): boolean {
  return poc.status !== "coming-soon" && poc.href.trim() !== "" && poc.href !== "#";
}
