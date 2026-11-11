import { useEffect, useRef } from "react";
import { animate, createSpring, utils } from "animejs";

import { isTestMode, prefersReduced } from "./motion";

interface NavIndicatorProps {
  /** Changes whenever the active link or the nav layout may have changed. */
  layoutKey: string;
}

type Box = { x: number; y: number; width: number; height: number };

const boxOf = (element: HTMLElement): Box => ({
  x: element.offsetLeft,
  y: element.offsetTop,
  width: element.offsetWidth,
  height: element.offsetHeight,
});

/**
 * The sliding pills behind the primary navigation: a solid one marks the
 * active section and springs to the next one on navigation; a soft one follows
 * the pointer. Must be rendered inside the positioned nav container, next to
 * `.nav-link` buttons. Renders nothing in tests.
 */
export default function NavIndicator({ layoutKey }: NavIndicatorProps) {
  const activeRef = useRef<HTMLSpanElement>(null);
  const hoverRef = useRef<HTMLSpanElement>(null);
  const placed = useRef(false);
  const plain = isTestMode();

  useEffect(() => {
    const pill = activeRef.current;
    const nav = pill?.parentElement;
    if (!pill || !nav || plain) return;

    const place = (animated: boolean) => {
      const link = nav.querySelector<HTMLElement>(".nav-link.is-active");
      if (!link) {
        pill.style.opacity = "0";
        placed.current = false;
        return;
      }
      const box = boxOf(link);
      pill.style.opacity = "1";
      if (!animated || !placed.current || prefersReduced()) {
        utils.set(pill, box);
      } else {
        animate(pill, { ...box, ease: createSpring({ stiffness: 260, damping: 24 }) });
      }
      placed.current = true;
    };

    place(true);
    const settle = () => place(false);
    const resizeObserver = typeof ResizeObserver === "undefined" ? null : new ResizeObserver(settle);
    resizeObserver?.observe(nav);
    window.addEventListener("resize", settle);
    void document.fonts?.ready.then(settle).catch(() => {});
    return () => {
      resizeObserver?.disconnect();
      window.removeEventListener("resize", settle);
    };
  }, [layoutKey, plain]);

  useEffect(() => {
    const pill = hoverRef.current;
    const nav = pill?.parentElement;
    if (!pill || !nav || plain || prefersReduced()) return;
    let visible = false;

    const onOver = (event: PointerEvent) => {
      if (event.pointerType !== "mouse") return;
      const link = event.target instanceof Element ? event.target.closest<HTMLElement>(".nav-link") : null;
      if (!link || !nav.contains(link)) return;
      const box = boxOf(link);
      if (!visible) {
        utils.set(pill, box);
        visible = true;
      } else {
        animate(pill, { ...box, ease: createSpring({ stiffness: 320, damping: 26 }) });
      }
      pill.style.opacity = "1";
    };
    const onLeave = () => {
      visible = false;
      pill.style.opacity = "0";
    };

    nav.addEventListener("pointerover", onOver);
    nav.addEventListener("pointerleave", onLeave);
    return () => {
      nav.removeEventListener("pointerover", onOver);
      nav.removeEventListener("pointerleave", onLeave);
    };
  }, [plain]);

  if (plain) return null;
  return (
    <>
      <span ref={hoverRef} className="nav-pill nav-pill--hover" aria-hidden="true" />
      <span ref={activeRef} className="nav-pill nav-pill--active" aria-hidden="true" />
    </>
  );
}
