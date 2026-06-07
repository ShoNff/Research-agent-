# Research Agent — POC Launcher

A small, password-gated Next.js app: log in with one password, then access the
POCs you keep behind the research agent (decks, reports, demos) from a launcher
page. Built to deploy on Vercel.

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

## Add or edit a POC

The launcher is data-driven. Edit **`lib/pocs.ts`** and append an entry:

```ts
{
  id: "deck",
  title: "Research Deck",
  description: "The presentation deck built with the research agent.",
  href: "https://your-link-here",   // Google Slides, hosted PDF, deployed app…
  status: "live",                    // "live" shows an Open ↗ button
  emoji: "📊",
}
```

- A card stays disabled ("Coming soon") while `status` is `"coming-soon"` or
  `href` is still `"#"`.
- Live cards open in a new tab.

Commit and push — Vercel redeploys automatically.

## How auth works

The password is only ever read on the server. `app/api/login/route.ts` compares
the submitted password to `APP_PASSWORD` and, on success, sets an httpOnly
cookie holding a SHA-256 token derived from the password. `middleware.ts`
verifies that cookie on every request and redirects to `/login` if it's missing
or wrong. The password is never included in the browser bundle.

> This is a lightweight single-password gate for low-stakes POCs — not a
> multi-user auth system.
