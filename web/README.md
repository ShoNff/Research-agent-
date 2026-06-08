# Research Agent — Research Library

A password-gated Next.js app: log in with one password, then browse every topic
the research agent has produced. The home page is the **research library** — one
card per project, with search and tag filters — and each project has a detail
page rendering its report, deck, diagrams, sources, and history. Built to deploy
on Vercel.

## How the library is built

The library is **not** hand-curated. `scripts/build-library.mjs` runs before
every `dev` and `build` and reads the repo's `projects/<slug>/manifest.json`
folders (written by the research agent's publish step). For each project it:

- copies web-servable artifacts (decks, diagrams) into `public/library/<slug>/`,
- renders `report.md` to HTML, and
- emits `lib/library.generated.ts`, which the app imports.

So the rule holds end to end: research a topic → it publishes a project → the
project appears here automatically on the next deploy. Nothing to wire up by
hand. The generated outputs (`public/library/`, and the regenerated
`library.generated.ts`) are derived from `projects/` — that folder is the source
of truth.

## Run locally

```bash
cd web
npm install
npm run dev          # http://localhost:3000
```

You'll be redirected to `/login`. The default password is **`Lithium3`**
(override it with the `APP_PASSWORD` env var). After logging in you land on the
launcher.

To check a production build before deploying:

```bash
npm run build
```

## Deploy on Vercel

1. Import this GitHub repo in Vercel.
2. Set **Root Directory** = `web` (Vercel auto-detects Next.js).
3. (Optional but recommended) Add an env var **`APP_PASSWORD`** = your password.
   If unset, it falls back to `Lithium3`.
4. Deploy.

## Adding research projects

You don't add them here — run the research agent. Each run publishes a
`projects/<slug>/` folder with a `manifest.json`, and the next deploy picks it up
automatically. Commit the project folder and push; Vercel rebuilds and the card
appears.

## Standalone decks & demos (manual)

For one-off things that aren't research projects (e.g. a hand-built deck), the
launcher still shows a secondary **Decks & demos** section sourced from
**`lib/pocs.ts`**. Append an entry:

```ts
{
  id: "deck",
  title: "Research Deck",
  description: "A standalone presentation deck.",
  href: "/decks/foo.html",   // in-repo asset under public/, or an external URL
  status: "live",            // "live" shows an Open ↗ button
  emoji: "📊",
}
```

Commit and push — Vercel redeploys automatically.

## How auth works

The password is only ever read on the server. `app/api/login/route.ts` compares
the submitted password to `APP_PASSWORD` and, on success, sets an httpOnly
cookie holding a SHA-256 token derived from the password. `middleware.ts`
verifies that cookie on every request and redirects to `/login` if it's missing
or wrong. The password is never included in the browser bundle.

> This is a lightweight single-password gate for low-stakes POCs — not a
> multi-user auth system.
