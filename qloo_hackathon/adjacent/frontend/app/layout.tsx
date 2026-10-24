import type { Metadata } from "next";
import "./globals.css";
import { Nav } from "@/components/nf/Nav";
import { Footer } from "@/components/nf/Footer";

export const metadata: Metadata = {
  title: "Adjacent Cinema — Every film belongs to more than one world",
  description:
    "Cultural intelligence for independent filmmakers. Investigate a film's cultural relationships, examine the evidence, and develop a positioning hypothesis worth testing.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-ink text-paper">
        <a
          href="#main"
          className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-[80] focus:bg-paper focus:px-4 focus:py-2 focus:text-ink"
        >
          Skip to content
        </a>
        <Nav />
        <main id="main">{children}</main>
        <Footer />
      </body>
    </html>
  );
}
