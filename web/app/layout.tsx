import type { Metadata, Viewport } from "next";
import "./globals.css";

// Icons + manifest are emitted automatically from the app/ file conventions
// (icon.svg, apple-icon.png, favicon.ico, manifest.ts) — no need to list them
// here, which would duplicate the <link> tags.
export const metadata: Metadata = {
  title: "Research Library",
  description: "Every topic researched, published automatically.",
  applicationName: "Research Library",
  appleWebApp: {
    capable: true,
    title: "Research",
    statusBarStyle: "black-translucent",
  },
};

export const viewport: Viewport = {
  themeColor: "#0a0f1f",
  colorScheme: "dark", // emit <meta name="color-scheme"> so mobile UAs render dark
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover", // honour env(safe-area-inset-*) on notched phones
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <div className="bg-orbs" aria-hidden />
        {children}
      </body>
    </html>
  );
}
