import { useEffect, useRef, useState } from "react";

import { isTestMode } from "./motion";

const INTERACTIVE = "a, button, summary, select, label, [role='tab'], [role='option'], [data-cursor]";
const TEXT_ENTRY = "input:not([type='checkbox']):not([type='radio']), textarea";

/**
 * A ring that trails the pointer and reacts to what is under it: it opens up
 * over anything clickable and narrows to a caret over text fields. The native
 * cursor stays visible, so nothing about pointing or clicking changes.
 * Disabled for touch, reduced motion and tests.
 */
export default function CustomCursor() {
  const ringRef = useRef<HTMLDivElement>(null);
  const [enabled] = useState(() => {
    if (isTestMode() || typeof window === "undefined" || typeof window.matchMedia !== "function") {
      return false;
    }
    const fine = window.matchMedia("(hover: hover) and (pointer: fine)").matches;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    return fine && !reduced;
  });

  useEffect(() => {
    const ring = ringRef.current;
    if (!enabled || !ring) return;

    let frame = 0;
    let shown = false;
    const pointer = { x: window.innerWidth / 2, y: window.innerHeight / 2 };
    const position = { x: pointer.x, y: pointer.y };

    const render = () => {
      position.x += (pointer.x - position.x) * 0.2;
      position.y += (pointer.y - position.y) * 0.2;
      ring.style.transform = `translate3d(${position.x.toFixed(1)}px, ${position.y.toFixed(1)}px, 0)`;
      const settled = Math.abs(pointer.x - position.x) < 0.1 && Math.abs(pointer.y - position.y) < 0.1;
      frame = settled ? 0 : window.requestAnimationFrame(render);
    };

    const onMove = (event: PointerEvent) => {
      if (event.pointerType !== "mouse") return;
      pointer.x = event.clientX;
      pointer.y = event.clientY;
      if (!shown) {
        shown = true;
        position.x = pointer.x;
        position.y = pointer.y;
        ring.dataset.visible = "true";
      }
      if (!frame) frame = window.requestAnimationFrame(render);
    };
    const onOver = (event: PointerEvent) => {
      const target = event.target instanceof Element ? event.target : null;
      ring.dataset.mode = target?.closest(TEXT_ENTRY) ? "text" : target?.closest(INTERACTIVE) ? "action" : "idle";
    };
    const onDown = () => {
      ring.dataset.pressed = "true";
    };
    const onUp = () => {
      delete ring.dataset.pressed;
    };
    const onLeave = () => {
      shown = false;
      delete ring.dataset.visible;
    };

    window.addEventListener("pointermove", onMove, { passive: true });
    window.addEventListener("pointerover", onOver, { passive: true });
    window.addEventListener("pointerdown", onDown, { passive: true });
    window.addEventListener("pointerup", onUp, { passive: true });
    document.documentElement.addEventListener("pointerleave", onLeave);

    return () => {
      if (frame) window.cancelAnimationFrame(frame);
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerover", onOver);
      window.removeEventListener("pointerdown", onDown);
      window.removeEventListener("pointerup", onUp);
      document.documentElement.removeEventListener("pointerleave", onLeave);
    };
  }, [enabled]);

  if (!enabled) return null;
  return (
    <div ref={ringRef} className="cursor-ring" aria-hidden="true">
      <span className="cursor-ring__shape" />
    </div>
  );
}
