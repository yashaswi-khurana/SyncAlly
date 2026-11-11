import { isTestMode, pointerState, prefersReduced, scrollState } from "./motion";

/**
 * Page-wide presentation effects, started once from main.tsx:
 *
 *  - scroll reveals: content blocks rise in as they enter the viewport
 *  - pointer fill: buttons fill from the point where the pointer entered
 *  - magnetic pull: primary controls lean a few pixels toward the pointer
 *  - card spotlight: a soft highlight follows the pointer across a card
 *  - shared pointer / scroll state for the WebGL scenes
 *
 * Everything here is decorative. It only writes data-* attributes and CSS
 * custom properties (never classes or text), so React's rendering is not
 * disturbed, and it is a no-op in tests and under prefers-reduced-motion.
 */

/** Blocks that rise into view. Order within a batch follows the document. */
const REVEAL_SELECTOR = [
  ".card",
  ".panel",
  ".hero__lede",
  ".hero > .actions",
  ".deal-list > li",
  ".message-list > li",
  ".fact-list > li",
  ".review-metric",
  ".deal-room__ledger-item",
  ".deal-onboarding-step",
  ".negotiation-review",
  ".agreement-terms__item",
  ".terms-readiness__item",
  ".payment-status__item",
  ".deal-case-item",
  ".reminders-panel__item",
  ".member-list > li",
  ".org-switcher__item",
  ".org-detail",
  ".candidate-card",
  ".gap-item",
  ".marketplace-page__listing",
  ".auth-benefits li",
  "tbody > tr",
  "[data-reveal-auto]",
].join(",");

/** Never animate inside dialogs (they have their own entrance) or opted-out trees. */
const REVEAL_SKIP = "[data-no-reveal], [role='dialog'], .manual-fact-modal-backdrop, .conversation-modal";

const MAGNETIC_SELECTOR = ".button:not(.button--compact), .nav-link, [data-magnetic]";
const FILL_SELECTOR = ".button";
const SPOTLIGHT_SELECTOR = ".card, .panel, [data-spotlight]";
/** A press on one of these is a real interaction, not a press on the backdrop. */
const CONTROL_SELECTOR =
  "a, button, input, select, textarea, label, summary, [role='tab'], [role='option'], [role='dialog'], [contenteditable='true']";

const STAGGER_MS = 70;
const MAX_STAGGER_STEPS = 7;

let started = false;

function setupReveal(): () => void {
  if (typeof IntersectionObserver === "undefined" || typeof MutationObserver === "undefined") {
    return () => {};
  }
  const root = document.documentElement;
  const seen = new WeakSet<Element>();
  const pending = new Set<HTMLElement>();

  const show = (el: HTMLElement, step: number) => {
    pending.delete(el);
    el.style.setProperty("--reveal-delay", `${Math.min(step, MAX_STAGGER_STEPS) * STAGGER_MS}ms`);
    el.setAttribute("data-inview", "");
  };

  const observer = new IntersectionObserver(
    (entries) => {
      let step = 0;
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        observer.unobserve(entry.target);
        show(entry.target as HTMLElement, step);
        step += 1;
      }
    },
    { rootMargin: "0px 0px -5% 0px", threshold: 0 },
  );

  const register = (el: Element) => {
    if (seen.has(el) || !(el instanceof HTMLElement) || el.closest(REVEAL_SKIP)) return;
    seen.add(el);
    el.setAttribute("data-reveal", "");
    pending.add(el);
    observer.observe(el);
  };

  const scan = (node: Node) => {
    if (!(node instanceof Element)) return;
    if (node.matches(REVEAL_SELECTOR)) register(node);
    node.querySelectorAll(REVEAL_SELECTOR).forEach(register);
  };

  const mutations = new MutationObserver((records) => {
    for (const record of records) record.addedNodes.forEach(scan);
  });

  // Once the entrance has played, drop the markers so nothing replays later
  // (for example when a hidden tab panel is shown again).
  const onAnimationEnd = (event: AnimationEvent) => {
    if (event.animationName !== "reveal-rise") return;
    const el = event.target;
    if (!(el instanceof HTMLElement) || !el.hasAttribute("data-inview")) return;
    el.removeAttribute("data-reveal");
    el.removeAttribute("data-inview");
    el.style.removeProperty("--reveal-delay");
  };

  // Safety net: nothing that is on screen may stay hidden.
  const sweep = window.setInterval(() => {
    const height = window.innerHeight;
    let step = 0;
    for (const el of pending) {
      if (!el.isConnected) {
        pending.delete(el);
        continue;
      }
      const rect = el.getBoundingClientRect();
      if (rect.width > 0 && rect.height > 0 && rect.top < height && rect.bottom > 0) {
        observer.unobserve(el);
        show(el, step);
        step += 1;
      }
    }
  }, 1200);

  root.classList.add("motion-ready");
  scan(document.body);
  mutations.observe(document.body, { childList: true, subtree: true });
  document.addEventListener("animationend", onAnimationEnd);

  return () => {
    window.clearInterval(sweep);
    mutations.disconnect();
    observer.disconnect();
    document.removeEventListener("animationend", onAnimationEnd);
    root.classList.remove("motion-ready");
    document.querySelectorAll("[data-reveal]").forEach((el) => {
      el.removeAttribute("data-reveal");
      el.removeAttribute("data-inview");
    });
  };
}

function setupPointer(animated: boolean): () => void {
  let magnet: HTMLElement | null = null;
  let frame = 0;
  let lastEvent: PointerEvent | null = null;

  const releaseMagnet = () => {
    if (!magnet) return;
    magnet.style.removeProperty("--mag-x");
    magnet.style.removeProperty("--mag-y");
    magnet = null;
  };

  const setFillOrigin = (event: PointerEvent) => {
    const target = event.target instanceof Element ? event.target.closest<HTMLElement>(FILL_SELECTOR) : null;
    if (!target) return;
    const rect = target.getBoundingClientRect();
    target.style.setProperty("--px", `${event.clientX - rect.left}px`);
    target.style.setProperty("--py", `${event.clientY - rect.top}px`);
  };

  const apply = () => {
    frame = 0;
    const event = lastEvent;
    if (!event) return;
    const element = event.target instanceof Element ? event.target : null;

    const spot = element?.closest<HTMLElement>(SPOTLIGHT_SELECTOR) ?? null;
    if (spot) {
      const rect = spot.getBoundingClientRect();
      spot.style.setProperty("--sx", `${event.clientX - rect.left}px`);
      spot.style.setProperty("--sy", `${event.clientY - rect.top}px`);
    }

    if (!animated) return;
    const nextMagnet = element?.closest<HTMLElement>(MAGNETIC_SELECTOR) ?? null;
    if (nextMagnet !== magnet) releaseMagnet();
    if (nextMagnet && !(nextMagnet as HTMLButtonElement).disabled) {
      const rect = nextMagnet.getBoundingClientRect();
      const dx = event.clientX - (rect.left + rect.width / 2);
      const dy = event.clientY - (rect.top + rect.height / 2);
      const limit = 7;
      nextMagnet.style.setProperty("--mag-x", `${Math.max(-limit, Math.min(limit, dx * 0.22)).toFixed(2)}px`);
      nextMagnet.style.setProperty("--mag-y", `${Math.max(-limit, Math.min(limit, dy * 0.3)).toFixed(2)}px`);
      magnet = nextMagnet;
    }
  };

  const onMove = (event: PointerEvent) => {
    pointerState.x = event.clientX;
    pointerState.y = event.clientY;
    pointerState.active = true;
    if (event.pointerType !== "mouse") return;
    lastEvent = event;
    if (!frame) frame = window.requestAnimationFrame(apply);
  };

  const onOver = (event: PointerEvent) => {
    if (event.pointerType === "mouse") setFillOrigin(event);
  };

  const onDown = (event: PointerEvent) => {
    pointerState.x = event.clientX;
    pointerState.y = event.clientY;
    pointerState.active = true;
    // only presses on empty space reach the scenes (they answer with a burst)
    const target = event.target instanceof Element ? event.target : null;
    if (!target?.closest(CONTROL_SELECTOR)) pointerState.pressedAt = performance.now();
  };

  const onLeave = () => {
    pointerState.active = false;
    lastEvent = null;
    releaseMagnet();
  };

  const onTouchEnd = (event: PointerEvent) => {
    if (event.pointerType !== "mouse") pointerState.active = false;
  };

  window.addEventListener("pointermove", onMove, { passive: true });
  window.addEventListener("pointerdown", onDown, { passive: true });
  window.addEventListener("pointerup", onTouchEnd, { passive: true });
  window.addEventListener("pointercancel", onTouchEnd, { passive: true });
  document.addEventListener("pointerover", onOver, { passive: true });
  document.documentElement.addEventListener("pointerleave", onLeave);
  window.addEventListener("blur", onLeave);

  return () => {
    if (frame) window.cancelAnimationFrame(frame);
    window.removeEventListener("pointermove", onMove);
    window.removeEventListener("pointerdown", onDown);
    window.removeEventListener("pointerup", onTouchEnd);
    window.removeEventListener("pointercancel", onTouchEnd);
    document.removeEventListener("pointerover", onOver);
    document.documentElement.removeEventListener("pointerleave", onLeave);
    window.removeEventListener("blur", onLeave);
    releaseMagnet();
  };
}

function setupScroll(): () => void {
  let lastY = window.scrollY;
  let lastTime = performance.now();
  let frame = 0;

  const sample = () => {
    frame = 0;
    const now = performance.now();
    const y = window.scrollY;
    const dt = Math.max(1, now - lastTime);
    // pixels per second, lightly smoothed so one wheel tick does not spike
    const instant = ((y - lastY) / dt) * 1000;
    scrollState.velocity += (instant - scrollState.velocity) * 0.35;
    scrollState.y = y;
    lastY = y;
    lastTime = now;
  };

  const onScroll = () => {
    if (!frame) frame = window.requestAnimationFrame(sample);
  };

  // velocity decays back to rest when scrolling stops
  const decay = window.setInterval(() => {
    if (performance.now() - lastTime > 90) scrollState.velocity *= 0.6;
    if (Math.abs(scrollState.velocity) < 1) scrollState.velocity = 0;
  }, 60);

  scrollState.y = lastY;
  window.addEventListener("scroll", onScroll, { passive: true });
  return () => {
    if (frame) window.cancelAnimationFrame(frame);
    window.clearInterval(decay);
    window.removeEventListener("scroll", onScroll);
  };
}

/** Start the global effects. Returns a cleanup function; safe to call twice. */
export function startGlobalFx(): () => void {
  if (started || typeof window === "undefined" || typeof document === "undefined" || isTestMode()) {
    return () => {};
  }
  started = true;
  const animated = !prefersReduced();
  const cleanups = [setupPointer(animated), setupScroll()];
  if (animated) cleanups.push(setupReveal());
  return () => {
    cleanups.forEach((cleanup) => cleanup());
    started = false;
  };
}
