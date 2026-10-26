import Link from "next/link";

/** Aperture mark + wordmark ported from the source ZIP (src/components/Wordmark.tsx). */
export function ApertureMark({ className = "h-7 w-7" }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={className} aria-hidden="true">
      <circle cx="16" cy="16" r="14.5" fill="none" stroke="currentColor" strokeWidth="1" />
      <circle cx="16" cy="16" r="5" fill="none" stroke="currentColor" strokeWidth="1" />
      <path
        d="M16 2.5 L19.2 11.2 L16 16 L12.8 11.2 Z M29.5 16 L20.8 12.8 L16 16 L20.8 19.2 Z M16 29.5 L12.8 20.8 L16 16 L19.2 20.8 Z M2.5 16 L11.2 19.2 L16 16 L11.2 12.8 Z"
        fill="currentColor"
        opacity="0.85"
      />
    </svg>
  );
}

export function Wordmark({ compact = false }: { compact?: boolean }) {
  return (
    <Link href="/" className="group flex items-center gap-3 text-left" aria-label="Adjacent Cinema, home">
      <span className="text-amber">
        <ApertureMark className={compact ? "h-6 w-6" : "h-7 w-7"} />
      </span>
      <span className="flex flex-col leading-none">
        <span className="font-display text-[1.35rem] tracking-tight text-paper">Adjacent</span>
        {!compact && (
          <span className="type-meta mt-1 text-[0.58rem] tracking-[0.22em] text-mute">Cinema</span>
        )}
      </span>
    </Link>
  );
}
