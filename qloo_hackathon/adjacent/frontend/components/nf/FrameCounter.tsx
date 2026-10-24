"use client";

import { useEffect, useState } from "react";

function pad(n: number, w = 2) {
  return String(n).padStart(w, "0");
}

/** Decorative timecode ported from the source ZIP (src/components/FrameCounter.tsx). */
export function FrameCounter() {
  const [t, setT] = useState(112);

  useEffect(() => {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce) return;
    const id = window.setInterval(() => setT((v) => (v + 1) % 24), 80);
    return () => window.clearInterval(id);
  }, []);

  const seconds = Math.floor(t / 24);
  const frames = t % 24;

  return (
    <span className="font-mono text-[0.65rem] tracking-[0.18em] text-amber tabular-nums">
      {pad(0)}:{pad(0)}:{pad(seconds)}:{pad(frames)}
    </span>
  );
}
