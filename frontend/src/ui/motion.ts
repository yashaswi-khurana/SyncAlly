import { animate, createScope, createSpring, stagger, splitText } from "animejs";

/**
 * Motion system — Anime.js v4.
 * Tokens mirror design/direction.md (140 / 320 / 680ms, 30ms stagger) and the
 * --dur-* custom properties in src/styles/tokens.css.
 */
export const motion = {
  ease: {
    out: "outExpo",
    inOut: "inOutQuad",
    spring: () => createSpring({ stiffness: 220, damping: 18 }),
  },
  dur: { micro: 140, ui: 320, reveal: 680 },
  stagger: 30,
};

/** Shared plain state: DOM animations write it, the WebGL scene reads it each frame. */
export const sceneState = { consensus: 0, focus: 0 };

/**
 * Pointer and scroll, sampled once by src/ui/fx.ts and read every frame by the
 * WebGL scenes. Viewport pixels; `active` is false until a pointer moves, and
 * `pressedAt` is the time of the last press on empty space (not on a control).
 * Scroll velocity is in pixels per second.
 */
export const pointerState = { x: -9999, y: -9999, active: false, pressedAt: 0 };
export const scrollState = { y: 0, velocity: 0 };

export const prefersReduced = () =>
  typeof window !== "undefined" &&
  typeof window.matchMedia === "function" &&
  window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/** Decorative motion never runs in tests (they assert DOM text, not frames). */
export const isTestMode = () => import.meta.env.MODE === "test";

/** True when entrance and pointer motion may run: a browser, not a test, no reduced-motion preference. */
export const motionEnabled = () =>
  typeof window !== "undefined" && !isTestMode() && !prefersReduced();

/** Reduced-motion end-state: everything visible, no transforms left behind. */
export function applyEndState(root: ParentNode): void {
  root.querySelectorAll<HTMLElement>("[data-motion]").forEach((el) => {
    el.style.opacity = "1";
    el.style.transform = "none";
  });
}

/**
 * Drive the shared scene consensus (direction §2): approval progress in the DOM
 * tweens this value and the Three.js seal/orbit react to it. Under reduced
 * motion or in tests the value is set immediately (no tween).
 */
export function setSceneConsensus(target: number, immediate = false): void {
  const clamped = Math.max(0, Math.min(1, target));
  if (immediate || import.meta.env.MODE === "test" || prefersReduced()) {
    sceneState.consensus = clamped;
    return;
  }
  try {
    animate(sceneState, {
      consensus: clamped,
      duration: motion.dur.reveal,
      ease: motion.ease.out,
    });
  } catch {
    sceneState.consensus = clamped;
  }
}

type MotionHandle = { destroy: () => void };
const noopHandle: MotionHandle = { destroy: () => {} };

/**
 * Initialise entrance motion inside `root`. Content is visible by default;
 * the animation applies its own start state, so a failure always falls back
 * to the static end-state. Safe no-op in the test environment.
 */
export function initMotion(root: ParentNode | null | undefined): MotionHandle {
  if (!root) return noopHandle;
  // Motion is visual-only: tests assert DOM text, never animation frames.
  if (import.meta.env.MODE === "test") return noopHandle;
  if (prefersReduced()) {
    applyEndState(root);
    return noopHandle;
  }

  try {
    // anime's selector types are narrower than ParentNode; runtime accepts any root
    const scope = createScope({ root: root as unknown as HTMLElement }).add(() => {
      // Split-text only on the hero h1 (ai-slop-blacklist rule).
      const headline = root.querySelector<HTMLElement>("[data-motion-title]");
      if (headline) {
        try {
          const { words } = splitText(headline, { words: true, accessible: true });
          animate(words, {
            translateY: ["110%", "0%"],
            opacity: [0, 1],
            duration: motion.dur.reveal,
            ease: motion.ease.out,
            delay: stagger(motion.stagger),
            autoplay: true,
          });
        } catch {
          animate(headline, {
            translateY: [16, 0],
            opacity: [0, 1],
            duration: motion.dur.reveal,
            ease: motion.ease.out,
            autoplay: true,
          });
        }
      }

      // Generic rise-in blocks (direction: staggered entrances).
      const rising = root.querySelectorAll<HTMLElement>("[data-motion='rise']");
      rising.forEach((el, index) => {
        animate(el, {
          translateY: [18, 0],
          opacity: [0, 1],
          duration: motion.dur.ui,
          ease: motion.ease.out,
          delay: index * motion.stagger,
          autoplay: true,
        });
      });

      // Stage-bar fill on the deal overview (direction §6.1).
      const stepperItems = root.querySelectorAll(".stage-stepper__item");
      if (stepperItems.length > 0) {
        animate(stepperItems, {
          translateY: [10, 0],
          opacity: [0, 1],
          duration: motion.dur.ui,
          ease: motion.ease.out,
          delay: stagger(motion.stagger),
          autoplay: true,
        });
      }
    });
    return { destroy: () => scope.revert() };
  } catch {
    applyEndState(root);
    return noopHandle;
  }
}
