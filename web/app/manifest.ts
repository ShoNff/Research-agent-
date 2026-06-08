import type { MetadataRoute } from "next";

// Served at /manifest.webmanifest. Lets the app install to a phone home screen
// with a proper name + icon instead of a screenshot thumbnail.
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Research Library",
    short_name: "Research",
    description: "Every topic researched, published automatically.",
    start_url: "/",
    display: "standalone",
    background_color: "#0a0f1f",
    theme_color: "#0a0f1f",
    icons: [
      {
        src: "/icon-192.png",
        sizes: "192x192",
        type: "image/png",
        purpose: "any",
      },
      {
        src: "/icon-512.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "any",
      },
      {
        src: "/icon-512.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "maskable",
      },
    ],
  };
}
