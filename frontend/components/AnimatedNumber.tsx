"use client";

import { useEffect, useRef, useState } from "react";

function prefersReducedMotion(): boolean {
  return typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/** Counts up to a real, already-computed value on mount — decorative
 * motion only, never alters or estimates the number itself. Respects
 * prefers-reduced-motion (skips straight to the final value via lazy
 * initial state, rather than animating then snapping). */
export default function AnimatedNumber({
  value,
  durationMs = 700,
}: {
  value: number;
  durationMs?: number;
}) {
  const [display, setDisplay] = useState(() => (prefersReducedMotion() ? value : 0));
  const startRef = useRef<number | null>(null);

  useEffect(() => {
    if (prefersReducedMotion()) return;

    let raf = 0;
    startRef.current = null;
    function tick(ts: number) {
      if (startRef.current === null) startRef.current = ts;
      const progress = Math.min((ts - startRef.current) / durationMs, 1);
      setDisplay(Math.round(progress * value));
      if (progress < 1) raf = requestAnimationFrame(tick);
    }
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [value, durationMs]);

  return <>{display}</>;
}
