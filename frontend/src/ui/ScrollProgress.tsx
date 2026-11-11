import { useEffect, useRef } from "react";

import { isTestMode } from "./motion";

/** A hairline along the top edge showing how far down the page the reader is. */
export default function ScrollProgress() {
  const barRef = useRef<HTMLSpanElement>(null);
  const plain = isTestMode();

  useEffect(() => {
    const bar = barRef.current;
    if (!bar || plain) return;
    let frame = 0;
    const render = () => {
      frame = 0;
      const scrollable = document.documentElement.scrollHeight - window.innerHeight;
      const progress = scrollable > 4 ? Math.max(0, Math.min(1, window.scrollY / scrollable)) : 0;
      bar.style.transform = `scaleX(${progress.toFixed(4)})`;
    };
    const request = () => {
      if (!frame) frame = window.requestAnimationFrame(render);
    };
    const resizeObserver = typeof ResizeObserver === "undefined" ? null : new ResizeObserver(request);
    resizeObserver?.observe(document.body);
    window.addEventListener("scroll", request, { passive: true });
    window.addEventListener("resize", request);
    request();
    return () => {
      if (frame) window.cancelAnimationFrame(frame);
      resizeObserver?.disconnect();
      window.removeEventListener("scroll", request);
      window.removeEventListener("resize", request);
    };
  }, [plain]);

  if (plain) return null;
  return (
    <span className="scroll-progress" aria-hidden="true">
      <span ref={barRef} className="scroll-progress__bar" />
    </span>
  );
}
