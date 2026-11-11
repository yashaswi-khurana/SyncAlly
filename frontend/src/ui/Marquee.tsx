import { useEffect, useRef } from "react";
import type { ReactNode } from "react";

import { isTestMode, prefersReduced, scrollState } from "./motion";

interface MarqueeProps {
  children: ReactNode;
  /** Seconds for one full pass; slower is larger. */
  speed?: number;
  reverse?: boolean;
  className?: string;
}

/**
 * Seamless horizontal ticker. Children are duplicated so the track can loop
 * without a visible jump, and the pass speeds up while the page is scrolling.
 * Purely decorative (hidden from assistive technology), so it is not rendered
 * in tests.
 */
export default function Marquee({ children, speed = 28, reverse = false, className }: MarqueeProps) {
  const trackRef = useRef<HTMLDivElement>(null);
  const plain = isTestMode();

  useEffect(() => {
    const track = trackRef.current;
    if (!track || plain || prefersReduced() || typeof track.getAnimations !== "function") return;
    let frame = 0;
    let rate = 1;
    const tick = () => {
      const target = 1 + Math.min(5, Math.abs(scrollState.velocity) / 420);
      rate += (target - rate) * 0.08;
      for (const animation of track.getAnimations()) animation.playbackRate = rate;
      frame = window.requestAnimationFrame(tick);
    };
    frame = window.requestAnimationFrame(tick);
    return () => window.cancelAnimationFrame(frame);
  }, [plain]);

  if (plain) return null;
  return (
    <div className={`marquee${className ? ` ${className}` : ""}`} role="presentation" aria-hidden="true">
      <div
        ref={trackRef}
        className={`marquee__track${reverse ? " marquee__track--reverse" : ""}`}
        style={{ animationDuration: `${speed}s` }}
      >
        <div className="marquee__group">{children}</div>
        <div className="marquee__group">{children}</div>
      </div>
    </div>
  );
}
