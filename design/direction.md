# Design Direction: SyncAlly (Trade Folio)

## 1. Visual & Product Concept

> **"The Bilateral Trade Loom: Turning unstructured human negotiation into an unbreakable cryptographic trade ledger."**

SyncAlly replaces the chaos of fragmented WhatsApp/email deals with the tactile authority of a physical customs house and the cryptographic certainty of a distributed ledger. The aesthetic is **warm architectural paper & ink**, precision typography, and tangible state transitions.

---

## 2. 3D Idea: The Consensus Core (Three.js WebGL)

- **What it is:** An interactive, dual-orbital "Consensus Core". Two glowing nodal rings (Buyer: Terracotta `#D95232`; Seller: Jade `#2E7D5B`) orbit a central floating cryptographic agreement tablet (`#FAF8F5`). 
- **What it expresses:** 
  - **In Draft State:** The two nodes orbit loosely, sending luminous bezier pulse particles back and forth representing chat messages and fact proposals.
  - **In Pending Approval State:** The orbits tighten, and the central agreement tablet glows with an active holographic wireframe showing the version number.
  - **In Committed State:** The two nodes snap into a locked bilateral ring, stamping an embossed golden SHA-256 seal onto the tablet with a subtle radial wave burst.
- **Interaction & Ergonomics:**
  - **Pointer-reactive:** Gentle parallax tilt (max 8 degrees) following cursor position with damped spring physics.
  - **Scroll-linked:** Rotates smoothly as user scrolls through deal stages.
  - **Accessibility & Reduced Motion:** Automatically pauses loop, hides particles, and renders a single static crisp SVG geometric seal when `prefers-reduced-motion` is enabled or WebGL is unsupported.
  - **Performance Guardrails:** Capped at `devicePixelRatio: 1.5`, zero synchronous `readPixels`, lazy-mounted via `IntersectionObserver`, and completely disposed on unmount.

---

## 3. Typographic System

Eliminate the blacklisted `Space Grotesk` + `Inter` combination. Introduce an authoritative, high-craft editorial stack:

| Role | Font Family | Weights | Usage & Rules |
|---|---|---|---|
| **Display / Headings** | **Cabinet Grotesk** (or **Syne**) | 600, 700, 800 | Architectural character, tight tracking (`-0.035em`), uppercase eyebrows (`letter-spacing: 0.12em`). Display-to-body ratio 3:1 on heroes. |
| **Body & UI Text** | **Plus Jakarta Sans** (or **Geist**) | 400, 500, 600 | High legibility at small sizes, open counters, tall x-height, line-height 1.55-1.65. |
| **Data, Hashes & Code** | **JetBrains Mono** | 400, 500 | Tabular numbers (`font-variant-numeric: tabular-nums`), deal references, SHA-256 hashes, timestamps, currency amounts. |

---

## 4. Colour Palette & Tokens

Derived from tactile paper archives, customs stamps, and raw ink:

```css
:root {
  /* Surfaces */
  --bg-canvas: #F4F1EA;       /* Warm architectural bone paper */
  --bg-surface: #FCFAF7;      /* Clean card surface */
  --bg-elevated: #FFFFFF;     /* Elevated modal & dropdown surface */
  --bg-subtle: #ECE8E0;       /* Secondary neutral fill */
  
  /* Ink & Typography */
  --ink-primary: #14201A;     /* Deep forest black (WCAG AAA contrast 14.8:1) */
  --ink-secondary: #4A5750;   /* Muted body text (WCAG AA contrast 6.2:1) */
  --ink-tertiary: #75837B;    /* Micro captions, timestamps (WCAG AA 4.6:1) */
  
  /* Brand Accents */
  --accent-buyer: #D95232;    /* Terracotta Rust (Buyer actions, primary CTA) */
  --accent-buyer-soft: rgba(217, 82, 50, 0.12);
  --accent-seller: #2E7D5B;   /* Deep Verdant Jade (Seller actions, approval) */
  --accent-seller-soft: rgba(46, 125, 91, 0.12);
  --accent-gold: #C28B38;     /* Consensus Seal / Committed badge */
  
  /* Architectural Lines */
  --border-subtle: rgba(20, 32, 26, 0.08);
  --border-medium: rgba(20, 32, 26, 0.16);
  --border-strong: rgba(20, 32, 26, 0.32);
  
  /* Radius & Shadows */
  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 16px;
  --shadow-sm: 0 1px 3px rgba(20, 32, 26, 0.04);
  --shadow-md: 0 4px 16px rgba(20, 32, 26, 0.08);
  --shadow-lg: 0 12px 36px rgba(20, 32, 26, 0.12);
}
```

---

## 5. Motion Language (Anime.js v4 + Three.js)

A unified physical motion vocabulary shared by DOM UI and WebGL canvas:

- **Shared Easings:**
  - `reveal`: `cubic-bezier(0.16, 1, 0.3, 1)` (snappy entry with gentle deceleration)
  - `spring`: `spring(1, 90, 14, 0)` (tactile button presses, card lifts)
  - `pulse`: `cubic-bezier(0.4, 0, 0.6, 1)` (beacon indicators, live synchronization)
- **Standard Durations:**
  - Micro-action (hover, toggle): `140ms`
  - UI Reveal (panel switch, drawer open): `320ms`
  - Stage Transition (consensus lock, commitment): `680ms`
- **Choreography Rules:**
  - Headlines and lists enter using Anime.js v4 `stagger(30)` reveals.
  - Buttons feature tactile `:active` spring depression (`scale(0.97)`).
  - Synchronized `sceneState`: When a user switches tabs or approves a version in the DOM, Anime.js tweens `sceneState.consensusProgress` from `0` to `1`, which the Three.js render loop immediately reads to morph the 3D scene in real-time.

---

## 6. Information Architecture & Page Narrative

### 6.1 Unified Stage Header
Replace the unformatted "Deal overview" paragraph with an **Interactive Commercial Pipeline**:
`[1. Negotiation] ────> [2. Term Verification] ────> [3. Bilateral Approval] ────> [4. Committed Trade] ────> [5. Settlement]`
- Highlights the current active stage.
- Shows exactly whose turn it is to act with a clear indicator (e.g. `Waiting on Buyer approval`).

### 6.2 The Split-Desk Layout (Desktop)
Replace the 9-panel endless vertical scroll with a high-efficiency **Split-Desk Workspace**:
- **Left Column (58% width): The Negotiation Stream**
  - Unified timeline containing shareable and private messages, proposal cards, and counter-offers in chronological sequence.
  - Single, intuitive composer with a clean toggle for `Shareable (Both Parties)` vs `Private (My Org)`.
  - Secondary drawer for "Import thread from WhatsApp / Email" (collapsed by default).
- **Right Column (42% width): The Live Agreement & Fact Ledger**
  - Sticky side panel displaying the active Agreement Candidate.
  - One-click version diff toggle (`Compare with v1`).
  - Clear **Bilateral Consensus Ring**: shows Buyer status (`Approved ✓`), Seller status (`Pending ⏳`), and the verified SHA-256 hash.
  - Primary Action Button: `Approve Version 1` (or `Commit Agreement` when bilateral consensus is met).

### 6.3 Progressive Disclosure Sub-Tabs
Keep secondary post-commitment flows tucked into intuitive stage tabs:
- `[Trade Desk]` (Timeline + Agreement)
- `[Obligations & Delivery]` (Milestones, tracking, fulfillment proofs)
- `[Invoices & Payments]` (PayPal invoice generation, payment receipts)
- `[Audit & Legal Pack]` (SHA-256 verification, downloadable ZIP trade pack)

### 6.4 Mobile Optimization
- Navbar collapses into an accessible slide-out mobile drawer on screens `< 768px`.
- Split-desk switches into an ergonomic bottom tab switcher (`[Timeline] | [Agreement] | [Details]`).
- All touch targets strictly `>= 44px`.
- `scrollWidth` guaranteed to match `100vw` without horizontal scroll bleeding.
