import { useEffect, useRef, useState } from "react";

/**
 * A soft pointer follower in the spirit of the reference portfolio: a small
 * filled dot that tracks precisely plus a larger ring that trails behind.
 * Disabled for coarse pointers and reduced-motion users.
 */
export default function CustomCursor() {
  const dotRef = useRef<HTMLDivElement>(null);
  const ringRef = useRef<HTMLDivElement>(null);
  const [enabled] = useState(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
      return false;
    }
    const fine = window.matchMedia("(pointer: fine)").matches;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    return fine && !reduced;
  });
  const [active, setActive] = useState(false);

  useEffect(() => {
    if (!enabled) {
      return;
    }
    let frame = 0;
    const pointer = { x: window.innerWidth / 2, y: window.innerHeight / 2 };
    const ring = { x: pointer.x, y: pointer.y };

    const onMove = (event: PointerEvent) => {
      pointer.x = event.clientX;
      pointer.y = event.clientY;
    };
    const onOver = (event: PointerEvent) => {
      const target = event.target as HTMLElement | null;
      setActive(Boolean(target?.closest("a, button, input, select, [data-cursor]")));
    };

    const render = () => {
      ring.x += (pointer.x - ring.x) * 0.16;
      ring.y += (pointer.y - ring.y) * 0.16;
      if (dotRef.current) {
        dotRef.current.style.transform = `translate3d(${pointer.x}px, ${pointer.y}px, 0)`;
      }
      if (ringRef.current) {
        ringRef.current.style.transform = `translate3d(${ring.x}px, ${ring.y}px, 0)`;
      }
      frame = window.requestAnimationFrame(render);
    };

    window.addEventListener("pointermove", onMove, { passive: true });
    window.addEventListener("pointerover", onOver, { passive: true });
    frame = window.requestAnimationFrame(render);
    document.documentElement.classList.add("has-custom-cursor");

    return () => {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerover", onOver);
      window.cancelAnimationFrame(frame);
      document.documentElement.classList.remove("has-custom-cursor");
    };
  }, [enabled]);

  if (!enabled) {
    return null;
  }

  return (
    <>
      <div ref={dotRef} className={`cursor-dot${active ? " is-active" : ""}`} aria-hidden="true" />
      <div ref={ringRef} className={`cursor-ring${active ? " is-active" : ""}`} aria-hidden="true" />
    </>
  );
}
