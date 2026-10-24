"use client";

import { useState } from "react";
import type { Photo } from "@/lib/nightfallPhotos";
import { cn } from "@/components/u";

type Props = {
  photo: Photo;
  className?: string;
  imgClassName?: string;
  credit?: boolean;
  gate?: boolean;
  priority?: boolean;
};

export default function NightfallPhotoFrame({
  photo,
  className,
  imgClassName,
  credit = true,
  gate = false,
  priority = false,
}: Props) {
  const [failed, setFailed] = useState(false);

  return (
    <figure className={cn("relative", className)}>
      <div className={cn("img-frame h-full w-full min-h-[10rem]", gate && "film-gate")}>
        {failed ? (
          <div className="flex h-full min-h-[12rem] w-full items-end bg-ink-3 p-4">
            <p className="caption">Image unavailable · layout preserved</p>
          </div>
        ) : (
          // Remote editorial photography matches the archive; no photo asset was bundled in it.
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
          <a href={photo.source} target="_blank" rel="noreferrer" className="hover:text-amber">
            Pexels
          </a>
        </figcaption>
      )}
    </figure>
  );
}
