"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

const LINKS = [
  { href: "/", label: "Index", number: "01" },
  { href: "/creator", label: "Creator Studio", number: "02" },
  { href: "/cinema", label: "Cinema Mode", number: "03" },
  { href: "/creator/sponsor", label: "FilmSponsor", number: "04" },
  { href: "/#multiverse", label: "Multiverse", number: "05" },
];

export default function NightfallNavigation() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  if (pathname === "/cinema") return null; // Cinema retains its five-chapter navigation.

  return (
    <header className={`nightfall-site-header${open ? " is-open" : ""}`}>
      <div className="nightfall-site-header-inner">
        <Link className="nightfall-wordmark" href="/" onClick={() => setOpen(false)} aria-label="Adjacent home">
          ADJACENT<span>cultural intelligence</span>
        </Link>
        <nav className="nightfall-site-nav" aria-label="Primary navigation">
          {LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              aria-current={pathname === link.href ? "page" : undefined}
              className={pathname === link.href ? "is-current" : undefined}
              onClick={() => setOpen(false)}
            >
              <small>{link.number}</small>{link.label}
            </Link>
          ))}
        </nav>
        <button
          className="nightfall-menu-toggle"
          type="button"
          aria-expanded={open}
          aria-controls="nightfall-mobile-navigation"
          aria-label={open ? "Close navigation" : "Open navigation"}
          onClick={() => setOpen((value) => !value)}
        >
          <span />
          <span />
        </button>
      </div>
      {open && (
        <nav id="nightfall-mobile-navigation" className="nightfall-mobile-nav" aria-label="Mobile navigation">
          {LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              aria-current={pathname === link.href ? "page" : undefined}
              onClick={() => setOpen(false)}
            >
              <span>{link.number}</span>{link.label}<span aria-hidden="true">↗</span>
            </Link>
          ))}
        </nav>
      )}
    </header>
  );
}
