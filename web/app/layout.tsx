import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Research Agent — Launcher",
  description: "Password-gated launcher for research agent POCs.",
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
