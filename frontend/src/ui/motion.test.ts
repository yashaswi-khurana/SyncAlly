import { afterEach, describe, expect, it, vi } from "vitest";
import { splitText } from "animejs";
import {
  applyEndState,
  initMotion,
  motion,
  sceneState,
  setSceneConsensus,
} from "./motion";

afterEach(() => {
  document.body.innerHTML = "";
  sceneState.consensus = 0;
  sceneState.focus = 0;
  vi.restoreAllMocks();
});

describe("motion tokens (direction.md §5)", () => {
  it("uses the approved durations and stagger", () => {
    expect(motion.dur).toEqual({ micro: 140, ui: 320, reveal: 680 });
    expect(motion.stagger).toBe(30);
  });
});

describe("sceneState", () => {
  it("starts at zero consensus", () => {
    expect(sceneState).toEqual({ consensus: 0, focus: 0 });
  });

  it("setSceneConsensus clamps and applies immediately under test", () => {
    setSceneConsensus(0.5);
    expect(sceneState.consensus).toBe(0.5);
    setSceneConsensus(7);
    expect(sceneState.consensus).toBe(1);
    setSceneConsensus(-3);
    expect(sceneState.consensus).toBe(0);
  });
});

describe("initMotion", () => {
  it("is a safe no-op in the test environment and returns a destroy handle", () => {
    document.body.innerHTML = `<div data-motion="rise" style="opacity: 0.3">Hi</div>`;
    const handle = initMotion(document.body);
    expect(typeof handle.destroy).toBe("function");
    // test-mode guard must not touch styles
    expect(document.body.querySelector("div")!.style.opacity).toBe("0.3");
    handle.destroy();
  });

  it("accepts a missing root without throwing", () => {
    expect(() => initMotion(null).destroy()).not.toThrow();
  });
});

describe("applyEndState (reduced-motion path)", () => {
  it("forces tagged elements back to their visible end-state", () => {
    document.body.innerHTML = `
      <div data-motion="rise" style="opacity: 0; transform: translateY(20px)">A</div>
      <span data-motion title>B</span>`;
    applyEndState(document.body);
    const first = document.body.querySelector<HTMLElement>("div")!;
    expect(first.style.opacity).toBe("1");
    expect(first.style.transform).toBe("none");
  });
});

describe("splitText on the hero headline markup", () => {
  it("keeps the accessible heading text intact", () => {
    // happy-dom has no FontFaceSet; anime reads document.fonts.status
    Object.defineProperty(document, "fonts", {
      value: { status: "loaded", ready: Promise.resolve() },
      configurable: true,
    });
    const h1 = document.createElement("h1");
    h1.innerHTML = "Bring your trade<br /><span>agreements together.</span>";
    document.body.appendChild(h1);
    const { words } = splitText(h1, { words: true, accessible: true });
    expect(words.length).toBeGreaterThan(2);
    // accessible:true keeps a visually-hidden copy of the original markup
    expect(h1.textContent).toContain("Bring your trade");
    expect(h1.textContent).toContain("agreements together.");
    const hidden = Array.from(h1.querySelectorAll("span")).find((span) =>
      span.style.clipPath.includes("inset"),
    );
    expect(hidden).toBeTruthy();
    // the visually-hidden copy keeps the original markup (incl. <br>), which is
    // what accessible-name computation reads after the split
    expect(hidden!.innerHTML).toContain("Bring your trade");
    expect(hidden!.innerHTML).toContain("<br");
    expect(hidden!.innerHTML).toContain("agreements together.");
  });
});
