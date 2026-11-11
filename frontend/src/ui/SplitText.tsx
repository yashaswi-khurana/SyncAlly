import { Fragment, useEffect, useLayoutEffect, useRef } from "react";
import { animate, stagger } from "animejs";

import { isTestMode, motion, prefersReduced } from "./motion";

interface SplitTextProps {
  /** Plain text. A newline forces a line break. */
  text: string;
  /**
   * "rise": letters rise out of a mask once, when the text enters the viewport.
   * "scrub": letters fill in with scroll progress, like ink following the reader.
   */
  effect?: "rise" | "scrub";
  /** Milliseconds before a "rise" starts. */
  delay?: number;
  /** Words (exact match, punctuation included) drawn in the accent colour. */
  accent?: string | string[];
  className?: string;
}

/**
 * Per-letter headline animation driven by Anime.js.
 *
 * React renders the letter spans itself, so the text can change (a deal title
 * arriving from the API) without anything mutating React-owned nodes. Assistive
 * technology reads one visually hidden copy; the animated letters are
 * aria-hidden. In tests, and whenever motion is unavailable, it renders the
 * plain string.
 */
export default function SplitText({ text, effect = "rise", delay = 0, accent, className }: SplitTextProps) {
  const rootRef = useRef<HTMLSpanElement>(null);
  const plain = isTestMode();

  // hide the letters before the first paint; without JS they simply stay visible
  useLayoutEffect(() => {
    const root = rootRef.current;
    if (!root || plain || prefersReduced()) return;
    root.dataset.state = "idle";
  }, [plain, text, effect]);

  useEffect(() => {
    const root = rootRef.current;
    if (!root || plain || prefersReduced()) return;
    const letters = Array.from(root.querySelectorAll<HTMLElement>(".split__char"));
    if (letters.length === 0) {
      root.dataset.state = "in";
      return;
    }

    if (effect === "scrub") {
      let frame = 0;
      let current = 0;
      let active = false;
      let timeline: ReturnType<typeof animate> | null = null;
      try {
        timeline = animate(letters, {
          opacity: [0.13, 1],
          duration: 420,
          delay: stagger(46),
          ease: "linear",
          autoplay: false,
        });
      } catch {
        root.dataset.state = "in";
        return;
      }
      const measure = () => {
        const rect = root.getBoundingClientRect();
        const viewport = window.innerHeight || 1;
        const from = viewport * 0.9;
        const to = viewport * 0.42;
        return Math.max(0, Math.min(1, (from - rect.top) / (from - to + rect.height)));
      };
      const render = () => {
        frame = 0;
        const target = measure();
        current += (target - current) * 0.16;
        if (Math.abs(target - current) < 0.0015) current = target;
        timeline?.seek(current * timeline.duration);
        if (active && current !== target) frame = window.requestAnimationFrame(render);
      };
      const request = () => {
        if (!frame) frame = window.requestAnimationFrame(render);
      };
      const observer =
        typeof IntersectionObserver === "undefined"
          ? null
          : new IntersectionObserver(
              (entries) => {
                active = entries.some((entry) => entry.isIntersecting);
                if (active) request();
              },
              { rootMargin: "20% 0px 20% 0px" },
            );
      if (observer) observer.observe(root);
      else active = true;
      window.addEventListener("scroll", request, { passive: true });
      window.addEventListener("resize", request);
      request();
      return () => {
        if (frame) window.cancelAnimationFrame(frame);
        observer?.disconnect();
        window.removeEventListener("scroll", request);
        window.removeEventListener("resize", request);
        timeline?.revert();
      };
    }

    let animation: ReturnType<typeof animate> | null = null;
    let failsafe = 0;
    const finish = () => {
      root.dataset.state = "in";
    };
    const play = () => {
      try {
        animation = animate(letters, {
          translateY: ["112%", "0%"],
          rotate: [7, 0],
          opacity: [0, 1],
          duration: 1000,
          delay: stagger(Math.max(10, Math.min(26, 520 / letters.length)), { start: delay }),
          ease: motion.ease.out,
          onComplete: finish,
        });
        failsafe = window.setTimeout(finish, 3200 + delay);
      } catch {
        finish();
      }
    };
    const observer =
      typeof IntersectionObserver === "undefined"
        ? null
        : new IntersectionObserver(
            (entries) => {
              if (entries.some((entry) => entry.isIntersecting)) {
                observer?.disconnect();
                play();
              }
            },
            { threshold: 0.05 },
          );
    if (observer) observer.observe(root);
    else play();

    return () => {
      observer?.disconnect();
      window.clearTimeout(failsafe);
      animation?.revert();
    };
  }, [plain, text, effect, delay]);

  if (plain) return <>{text.replace(/\s*\n\s*/g, " ")}</>;

  const accents = accent === undefined ? [] : Array.isArray(accent) ? accent : [accent];
  const lines = text.split("\n");

  return (
    <span ref={rootRef} className={`split split--${effect}${className ? ` ${className}` : ""}`}>
      <span className="visually-hidden">{text.replace(/\s*\n\s*/g, " ")}</span>
      <span className="split__visual" aria-hidden="true">
        {lines.map((line, lineIndex) => {
          const words = line.split(" ").filter(Boolean);
          return (
            <Fragment key={`${lineIndex}:${line}`}>
              {lineIndex > 0 ? <br /> : null}
              {words.map((word, wordIndex) => (
                <Fragment key={`${wordIndex}:${word}`}>
                  <span className={`split__word${accents.includes(word) ? " split__word--accent" : ""}`}>
                    {Array.from(word).map((letter, letterIndex) => (
                      <span key={`${letterIndex}:${letter}`} className="split__char">
                        {letter}
                      </span>
                    ))}
                  </span>
                  {wordIndex < words.length - 1 ? " " : null}
                </Fragment>
              ))}
            </Fragment>
          );
        })}
      </span>
    </span>
  );
}
