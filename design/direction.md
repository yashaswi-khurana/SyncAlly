# Design Direction: SyncAlly

This note describes the interface as it is built in `frontend/`. It replaces the earlier
"warm paper and ink" direction; `audit.md`, `inspiration.md` and `product-brief.md` are kept as the
research that led here.

## 1. Concept

> **Bring your trade agreements together.**

SyncAlly turns a buyer and seller conversation into one record that both sides approve. The
interface makes that literal: separate things travel toward one point and settle there.

The look is light, precise and type-led: a cool off-white canvas, midnight ink, one cobalt accent,
oversized tight headlines and small mono labels. Midnight panels are kept for the moments that carry
weight: the deal room header, the recommended next step, an order total.

The reference for craft is Davide Carusio's portfolio (`davidecarusio.it`): rigid-body physics the
visitor can touch, per-letter headlines, a floating navigation pill and a wordmark that fills the
footer. SyncAlly borrows those techniques, not the look. Palette, copy and density stay those of a
trade tool that people work in all day.

---

## 2. Physics and 3D

Physics is simulated with **cannon-es**. The WebGL scenes are rendered with **Three.js**; the footer
wordmark moves real DOM letters. Headline motion uses **Anime.js v4**.

| Scene | Where | Behaviour |
|---|---|---|
| **Convergence** `src/ui/ConvergenceScene.tsx` | Sign-in and organization sign-up hero | 12 to 34 spheres (by stage area) in a zero-gravity world. Each is steered toward a gathering point: it cruises in, eases out and stops without swinging past. The point is the centre of an empty box (`.auth-stage__well`) that CSS places at each breakpoint, and the cluster is scaled to fit that box. Bodies start on a ring around the point, turned away from directions whose straight path would cross the headline or lede. The pointer pushes them, a press on empty space bursts them apart, and scrolling shoves the cluster with inertia. |
| **Physics wordmark** `src/ui/PhysicsWordmark.tsx` | Footer of every page | Each letter of "SyncAlly" is a body tied to its place by a spring. Letters are let go one after another when the footer scrolls into view, collide, can be knocked by the pointer and always settle back into the word. The simulation stops when nothing moves. |
| **Trade flow** `src/deals/TradeFlowScene.tsx` | Deal room header, "How it works" on the landing page | A buyer sphere (cobalt) and a seller sphere (teal) sit either side of a paper record while pulses travel the routes between them. The scene tilts with the pointer (at most 8°) and yaws with scroll. As `sceneState.consensus` moves from 0 to 1 the two sides draw closer, the record squares up and its seal turns brass. |
| **Ambient field** `src/ui/AmbientField.tsx` | Behind signed-in pages | A grid of ledger dots rolling like a slow swell and lifting where the pointer passes. One draw call. |

Sphere materials are the palette as matter: porcelain, midnight with a clear coat, cobalt, mist blue
and a little brass.

Rules every scene follows:

- Decorative only: `aria-hidden`, never captures the pointer, never holds content.
- The convergence scene and the ambient field create their canvas inside the effect, so every
  mount owns a fresh WebGL context that is released on unmount.
- Three.js and cannon-es are loaded with `import()` so they stay out of the first bundle.
- The loop pauses when the scene is off screen or the tab is hidden.
- Forces are applied in cannon's `preStep` hook, so motion is the same at any frame rate.
- `prefers-reduced-motion`: one still, settled frame. No WebGL: nothing is drawn (the trade flow
  scene shows its drawn SVG instead). Tests: the new components render plain markup.

---

## 3. Type

All three families are variable fonts, self-hosted through `@fontsource-variable` and imported in
`src/main.tsx`.

| Role | Family | Rules |
|---|---|---|
| **Display** | Inter Tight Variable | Page headlines: tracking `-0.042em`, word spacing `0.06em`, line height `0.96`, up to `6.25rem`. Card and section titles: `-0.03em` to `-0.04em`. |
| **Body and controls** | Geist Variable | `0.9375rem` base, line height 1.5 to 1.6. |
| **Labels and data** | Geist Mono Variable | Uppercase eyebrows at `0.6875rem` with `0.14em` tracking; deal references, hashes, timestamps, table headers. |

The type scale is `--text-xs` to `--text-mega` in `src/styles/tokens.css`.

---

## 4. Colour and tokens

Defined once in `src/styles/tokens.css`. Older variable names (`--bg-*`, `--border-*`, `--radius-*`,
`--shadow-sm/md/lg`, `--accent-buyer`, …) are aliased there so existing components keep working.

```css
:root {
  /* canvas and surfaces */
  --canvas: #f3f5f9;
  --surface: #ffffff;
  --surface-2: #f6f8fb;
  --surface-3: #eceff5;
  --surface-glass: rgba(255, 255, 255, 0.74);

  /* ink */
  --ink: #0a1326;
  --ink-2: #36435c;
  --ink-3: #5b6781;
  --ink-4: #8a94a9;

  /* brand */
  --navy: #0a1326;
  --accent: #1f4fe0;          /* cobalt: primary accent, links, focus */
  --accent-strong: #173cb4;
  --accent-bright: #5b8cff;   /* on midnight */

  /* party identity */
  --buyer: #1f4fe0;           /* cobalt */
  --seller: #0b8272;          /* teal */
  --gold: #b98a2f;            /* brass: consensus, committed */

  /* semantic */
  --success: #0e7a4f;
  --warning: #8f5a06;
  --danger: #c2302b;

  /* lines */
  --line: rgba(10, 19, 38, 0.09);
  --line-strong: rgba(10, 19, 38, 0.17);
  --line-control: rgba(10, 19, 38, 0.24);

  /* radii and shadows */
  --r-sm: 10px;  --r-md: 14px;  --r-lg: 20px;  --r-xl: 28px;  --r-pill: 999px;
  --shadow-1: 0 1px 2px rgba(10, 19, 38, 0.05);
  --shadow-2: 0 10px 28px -10px rgba(10, 19, 38, 0.16), 0 2px 6px rgba(10, 19, 38, 0.04);
  --shadow-3: 0 34px 70px -24px rgba(10, 19, 38, 0.3), 0 14px 28px -14px rgba(10, 19, 38, 0.14);
}
```

Surfaces: cards are white with a hairline border and a 20px radius; the navigation and the sign-in
card are glass (`backdrop-filter`); feature panels are midnight with a cobalt glow.

---

## 5. Motion language

DOM and WebGL share one vocabulary (`src/styles/tokens.css`, `src/ui/motion.ts`).

- **Easings:** `--ease-out: cubic-bezier(0.16, 1, 0.3, 1)` for entrances, `--spring` for controls
  that overshoot slightly, `--ease-in-out` for loops.
- **Durations:** micro `140ms` (hover, toggle), UI `320ms` (panel, drawer), reveal `680ms`.
- **Headlines** (`src/ui/SplitText.tsx`): letters rise out of a mask once, when the headline enters
  the viewport. The landing statement fills in letter by letter as the reader scrolls.
- **Page heroes** arrive in order: label, then the headline letters, then lede and actions.
- **Scroll reveals** (`src/ui/fx.ts`): cards and list rows rise 22px as they enter the viewport,
  staggered in document order, once.
- **Buttons:** pills. The fill grows from the point where the pointer entered; primary controls
  lean a few pixels toward the pointer; `:active` scales to `0.97`.
- **Cards:** a soft spotlight follows the pointer.
- **Navigation:** the active pill slides between items; a hairline shows scroll progress; a short
  flash marks a route change.
- **Scene state:** the deal status sets `sceneState.consensus` (0 draft, 0.5 pending approvals,
  1 agreed). The value is tweened, and the trade flow scene reads it every frame.

Constraints:

- Never leave a `transform`, `translate`, `filter` or a forwards-filled animation on a card or page
  wrapper: they contain `position: fixed` dialogs, which would be trapped inside.
- Effects write `data-*` attributes and custom properties only, never classes or text, so React's
  rendering is not disturbed.
- `prefers-reduced-motion` switches all of it off: no reveals, no letter effects, instant
  transitions, still scenes.

---

## 6. Layout and page narrative

### 6.1 Shell
- A floating glass navigation pill, sticky at the top. At 940px and below it becomes a menu button
  that opens a drawer; the page recedes behind a veil while the drawer is open.
- Page width is capped at 1360px (1560px in the deal room).
- Every page ends with the full-width wordmark.

### 6.2 Public landing
Masthead; the stage (pitch on the left, sign-in card on the right, the convergence scene between
and behind them); a ticker of the trade stages; the one-line statement; "How it works" on midnight
with the trade flow scene; three benefits; footer. Organization sign-up reuses the same stage.

### 6.3 Deal room
- **Header:** midnight panel with the deal title, the trade flow scene and a strip of references.
- **Pipeline:** `01 Negotiation → 02 Term verification → 03 Bilateral approval → 04 Committed trade
  → 05 Settlement`, with the current stage and the next action.
- **Desk:** four views in a sticky pill: Trade Desk, Obligations & Delivery, Invoices & Payments,
  Audit & Legal.
- **Trade Desk** at 1280px and wider: the working stream beside a pinned agreement ledger
  (`clamp(370px, 30%, 450px)`) that scrolls in its own frame. Inside the stream, at 900px and wider,
  the conversation sits beside fact review; the copilot and proposals take the full width.
- A new deal opens with a "next steps" guide above the header.

### 6.4 Forms and boards
- A workspace card that holds one long form (new deal) is two columns from 900px: what the form is
  for on the left, the fields on the right.
- Marketplace: search, then publishing tools side by side, then requests and listings side by side
  from 1080px.
- Sourcing hub: a segmented mode switch, candidate cards with the match tier first, and a
  comparison table that scrolls sideways in its own frame on a phone.

### 6.5 Small screens
- One column. Buttons and fields are 44px or taller; the compact button (34px) is kept for
  secondary actions inside dense cards.
- The desk view switch becomes a thumb bar fixed to the bottom at 768px and below; the footer ends
  above it.
- Wide tables scroll inside their own frame; the page itself must not scroll sideways.
