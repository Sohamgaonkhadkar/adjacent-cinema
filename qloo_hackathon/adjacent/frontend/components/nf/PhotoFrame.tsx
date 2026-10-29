"use client";

import { useState } from "react";
import type { Photo } from "@/lib/photos";
import { cn } from "@/lib/cn";

type Props = {
  photo: Photo;
  className?: string;
  imgClassName?: string;
  credit?: boolean;
  /**
   * Render the credit's source as a link. Off when the frame already sits inside
   * a link: `<a>` cannot contain `<a>`, and the browser's parser hoists the inner
   * anchor, which desynchronises hydration on the whole page.
   */
  creditLink?: boolean;
  gate?: boolean;
  priority?: boolean;
  /** Cover the parent box instead of taking part in its flow. */
  fill?: boolean;
};

/**
 * Ported from the source ZIP (src/components/PhotoFrame.tsx).
 * A failed photograph keeps the layout and says so instead of showing a
 * broken image or a substitute picture.
 *
 * `fill` is the only supported way to layer a photograph behind copy. It is
 * applied as an inline style *and* as classes because the position utilities are
 * not order-independent: the compiled stylesheet emits `.absolute` before
 * `.relative`, so a hard-coded `relative` on this element silently beat a
 * caller's `absolute inset-0`. The figure then stayed in flow with an
 * indefinite height, `.img-frame`'s `height: 100%` resolved against `auto`, and
 * the frame collapsed to its `min-height` — a ~10rem strip of photograph at the
 * top of a full-height dark column. Every stage photo that asked to "absolutely
 * fill" its container was rendering that strip.
 */
export function PhotoFrame({
  photo,
  className,
  imgClassName,
  credit = true,
  creditLink = true,
  gate = false,
  priority = false,
  fill = false,
}: Props) {
  const [failed, setFailed] = useState(false);

  return (
    <figure
      className={cn(fill && "absolute inset-0 h-full w-full", className)}
      style={fill ? { position: "absolute", inset: 0 } : undefined}
    >
      <div className={cn("img-frame h-full w-full min-h-[10rem]", gate && "film-gate")}>
        {failed ? (
          <div className="flex h-full min-h-[12rem] w-full items-end bg-ink-3 p-4">
            <p className="caption">Image unavailable · layout preserved</p>
          </div>
        ) : (
          // Remote atmospheric photography is intentionally a plain <img>: the
          // source design crops it with CSS and no optimiser configuration.
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={photo.src}
            alt={photo.alt}
            className={imgClassName}
            loading={priority ? "eager" : "lazy"}
            decoding="async"
            onError={() => setFailed(true)}
          />
        )}
      </div>
      {credit && (
        <figcaption className="caption mt-2 flex flex-wrap items-baseline justify-between gap-2">
          <span>Photo · {photo.credit}</span>
          {creditLink ? (
            <a href={photo.source} target="_blank" rel="noreferrer" className="hover:text-amber">
              Pexels
            </a>
          ) : (
            <span className="text-dim">Pexels</span>
          )}
        </figcaption>
      )}
    </figure>
  );
}
