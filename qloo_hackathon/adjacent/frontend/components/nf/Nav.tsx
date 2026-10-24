"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { Menu, X } from "lucide-react";
import { Wordmark } from "./Wordmark";
import { cn } from "@/lib/cn";

const LINKS = [
  { href: "/", label: "Index" },
  { href: "/creator", label: "Creator Studio" },
  { href: "/cinema", label: "Cinema Mode" },
  { href: "/creator/sponsor", label: "FilmSponsor" },
] as const;

/**
 * Navigation ported from the source ZIP (src/components/Nav.tsx): a sticky
 * wordmark bar that is transparent over the home hero and solid after scroll.
 */
export function Nav() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const overlay = pathname === "/";

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  return (
    <header
      className={cn(
        "sticky top-0 z-50 transition-colors duration-300",
        overlay && !scrolled && !open
          ? "bg-transparent"
          : "bg-ink/92 backdrop-blur-md border-b border-line",
      )}
    >
      <div className="mx-auto flex max-w-[1440px] items-center justify-between gap-4 px-4 py-3 md:px-8">
        <Wordmark />

        <nav className="hidden items-center gap-8 lg:flex" aria-label="Primary">
          {LINKS.map((link) => {
            const current = pathname === link.href;
            return (
              <Link
                key={link.href}
                href={link.href}
                aria-current={current ? "page" : undefined}
                className={cn(
                  "font-mono text-[0.68rem] uppercase tracking-[0.16em] transition-colors",
                  current ? "text-paper" : "text-mute hover:text-paper",
                )}
              >
                {link.label}
                {current && <span className="ml-2 inline-block h-px w-4 bg-amber align-middle" />}
              </Link>
            );
          })}
        </nav>

        <div className="hidden items-center gap-4 lg:flex">
          <span className="type-meta text-[0.58rem]">Vol. 01 · The Culture Room</span>
        </div>

        <button
          type="button"
          className="inline-flex h-11 w-11 items-center justify-center border border-line-strong text-paper lg:hidden"
          aria-expanded={open}
          aria-controls="mobile-nav"
          aria-label={open ? "Close menu" : "Open menu"}
          onClick={() => setOpen((v) => !v)}
        >
          {open ? <X size={18} /> : <Menu size={18} />}
        </button>
      </div>

      {open && (
        <div id="mobile-nav" className="border-t border-line bg-ink px-4 py-4 lg:hidden">
          <nav className="flex flex-col" aria-label="Mobile">
            {LINKS.map((link, index) => {
              const current = pathname === link.href;
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  aria-current={current ? "page" : undefined}
                  className={cn(
                    "flex h-12 items-center justify-between border-b border-line text-left font-mono text-xs uppercase tracking-[0.16em]",
                    current ? "text-amber" : "text-paper",
                  )}
                >
                  {link.label}
                  <span className="text-dim">0{index + 1}</span>
                </Link>
              );
            })}
          </nav>
        </div>
      )}
    </header>
  );
}
