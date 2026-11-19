import type { Metadata } from "next";

// Self-hosted fonts (no runtime font CDN), as required by the design tokens.
import "@fontsource-variable/plus-jakarta-sans";
import "@fontsource-variable/source-serif-4";
import "@fontsource/ibm-plex-mono/400.css";

import { AuthProvider } from "@/lib/auth";

import "./tokens.css";
import "./globals.css";

export const metadata: Metadata = {
  title: "AITMS",
  description: "AI Training Management System",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
