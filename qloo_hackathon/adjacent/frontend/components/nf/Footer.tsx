import Link from "next/link";
import { ApertureMark } from "./Wordmark";

/** Footer ported from the source ZIP (src/components/Footer.tsx). */
export function Footer() {
  return (
    <footer className="border-t border-line bg-ink">
      <div className="mx-auto grid max-w-[1440px] gap-10 px-4 py-16 md:grid-cols-12 md:px-8">
        <div className="md:col-span-5">
          <div className="flex items-center gap-3 text-amber">
            <ApertureMark />
            <span className="font-display text-3xl text-paper">Adjacent</span>
          </div>
          <p className="mt-6 max-w-sm text-sm leading-relaxed text-mute">
            Cultural intelligence for independent filmmakers and cinema programmers. Evidence, or an
            honest unknown. Never an invented audience.
          </p>
        </div>
        <div className="md:col-span-3">
          <p className="type-kicker">Rooms</p>
          <ul className="mt-4 space-y-2 text-sm">
            {[
              ["/", "Index"],
              ["/creator", "Creator Studio"],
              ["/cinema", "Cinema Mode"],
              ["/creator/sponsor", "FilmSponsor"],
            ].map(([href, label]) => (
              <li key={href}>
                <Link className="text-paper-2 hover:text-amber" href={href}>
                  {label}
                </Link>
              </li>
            ))}
          </ul>
        </div>
        <div className="md:col-span-4">
          <p className="type-kicker">Principle</p>
          <p className="mt-4 font-display text-2xl leading-snug text-paper">
            Qloo affinity is a cultural-similarity signal. It is not a forecast.
          </p>
        </div>
      </div>
      <div className="border-t border-line">
        <div className="mx-auto flex max-w-[1440px] flex-wrap items-center justify-between gap-3 px-4 py-4 md:px-8">
          <p className="caption">Issue 01 · Adjacent · The Culture Room</p>
          <p className="caption">No fabricated Qloo results · Missing stays missing</p>
        </div>
      </div>
    </footer>
  );
}
