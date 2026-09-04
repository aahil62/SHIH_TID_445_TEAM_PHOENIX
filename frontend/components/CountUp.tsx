"use client";

import { useEffect, useRef, useState } from "react";

/** Animates a numeric readout from 0 to `value` once it enters view.
 * Purely cosmetic (the real number is server-fetched and correct the
 * instant the animation finishes) — never used for a number the user
 * needs to read accurately mid-animation. */
export default function CountUp({
  value,
  decimals = 0,
  duration = 900,
  suffix = "",
  prefix = "",
}: {
  value: number;
  decimals?: number;
  duration?: number;
  suffix?: string;
  prefix?: string;
}) {
  const ref = useRef<HTMLSpanElement>(null);
  const [display, setDisplay] = useState(() =>
    typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches ? value : 0,
  );

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const el = ref.current;
    if (!el) return;

    let rafId: number;
    // Belt-and-suspenders: some browsers fully pause requestAnimationFrame
    // (not just throttle it) while the tab/pane is backgrounded, which can
    // freeze the animation mid-count instead of just slowing it down. This
    // timer force-completes to the real value once `duration` has surely
    // passed, regardless of whether rAF ever resumed.
    let fallbackTimer: ReturnType<typeof setTimeout>;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (!entry.isIntersecting) return;
        observer.disconnect();
        const start = performance.now();
        function tick(now: number) {
          const t = Math.min(1, (now - start) / duration);
          const eased = 1 - Math.pow(1 - t, 3);
          setDisplay(value * eased);
          if (t < 1) rafId = requestAnimationFrame(tick);
        }
        rafId = requestAnimationFrame(tick);
        fallbackTimer = setTimeout(() => setDisplay(value), duration + 300);
      },
      { threshold: 0.4 },
    );
    observer.observe(el);
    return () => {
      observer.disconnect();
      cancelAnimationFrame(rafId);
      clearTimeout(fallbackTimer);
    };
  }, [value, duration]);

  return (
    <span ref={ref}>
      {prefix}
      {display.toLocaleString(undefined, {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals,
      })}
      {suffix}
    </span>
  );
}
