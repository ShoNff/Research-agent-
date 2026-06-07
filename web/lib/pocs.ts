// The launcher is data-driven: every card on the home page comes from this list.
//
// To add a POC, append an entry below and (for live ones) set `href` to its URL.
// Cards left as "coming-soon" (or with href "#") render disabled until you add a
// real link. Commit + push and Vercel redeploys automatically.
//
// Two kinds of href work:
//   - An external URL (https://…) — opens that site.
//   - An in-repo path (/decks/foo.html) — a static file served from web/public.
//     Drop a self-contained deck/page into web/public/<path> and link to it here;
//     it's served by the same Vercel app and stays behind the password gate.

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
    id: "azure-workspaces",
    title: "Azure Workspaces",
    description: "Animated concept presentation on Azure workspaces.",
    href: "/decks/azure-workspaces.html", // served from web/public/decks
    status: "live",
    emoji: "🔷",
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
