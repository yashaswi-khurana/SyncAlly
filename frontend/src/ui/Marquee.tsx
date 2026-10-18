import type { ReactNode } from "react";

interface MarqueeProps {
  children: ReactNode;
  /** Seconds for one full pass; slower is larger. */
  speed?: number;
  reverse?: boolean;
  className?: string;
}

/**
 * Seamless horizontal marquee. Children are duplicated so the track can loop
 * without a visible jump.
 */
export default function Marquee({ children, speed = 28, reverse = false, className }: MarqueeProps) {
  return (
    <div className={`marquee${className ? ` ${className}` : ""}`} role="presentation">
      <div
        className={`marquee__track${reverse ? " marquee__track--reverse" : ""}`}
        style={{ animationDuration: `${speed}s` }}
      >
        <div className="marquee__group" aria-hidden="true">
          {children}
        </div>
        <div className="marquee__group" aria-hidden="true">
          {children}
        </div>
      </div>
    </div>
  );
}
