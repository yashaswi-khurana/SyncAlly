# Frontend Audit: SyncAlly Web Client

**Target:** `https://syncally-frontend.onrender.com/`  
**API:** `https://syncally-api.onrender.com/`  
**Audited Accounts:**
- Buyer: `shivanshgaur2p+buyer@gmail.com`
- Seller: `shivanshgaur2p+seller@gmail.com`

---

## 1. Executive Summary

While the backend architecture and domain modeling of SyncAlly are exceptionally rigorous (featuring cryptographic bilateral consensus, transactional outbox relays, and Temporal workflows), the frontend interface currently presents significant visual, ergonomic, accessibility, and functional regressions. 

Key diagnostic findings:
1. **Critical Mobile Horizontal Overflow:** At standard mobile viewports (360px and 390px), the page content expands to 430px wide (`scrollWidth: 430px`), forcing awkward horizontal scrolling and breaking container bounds.
2. **Infinite Vertical Card Sprawl (Cognitive Overload):** The Deal Detail page stacks 9 separate heavy cards vertically, featuring **7 separate manual refresh buttons**, creating severe fatigue and obscuring the trade stage.
3. **Severe Accessibility & Contrast Failures:** Dark grey input fields on dark green background on the Sign-in card fail WCAG AA contrast, and micro-typography (as small as `0.55rem` / 8.8px) is deployed across multiple components.
4. **AI-Slop Blacklist Violations:** Default blacklisted font stack (`Space Grotesk` + `Inter`), continuous full-bleed graph paper grid, raw unformatted UUIDs displayed to end-users, and a detached 3D canvas that does not react to deal state transitions.
5. **Session & Routing Inconsistencies:** Switching between Buyer and Seller preserves stale URL hash paths (`#/organizations`), stranding users in unexpected settings panels upon sign-in.
6. **Literal Code Typos & Misalignments:** `↓↓` (double down arrow) typo in proposal line-item reordering (`NegotiationReview.tsx:645`), raw browser fieldset borders, and misaligned message visibility radio buttons.

---

## 2. Audit Table Against the 10 UI Principles

| # | Principle | Finding & Evidence | Severity | Recommended Fix |
|---|---|---|---|---|
| **P1** | **Simplicity** | **9 Stacked Panels & 7 Refresh Buttons:** The Deal Room forces the user to scroll through Overview, Conversation, Fact review, Suggestion review, Proposals, Agreement, Delivery, Payment, Cases, and Reminders all at once. There are 7 distinct "Refresh" buttons (`Refresh room`, `Refresh proposals`, `Reload agreement`, 2x `Refresh status`, `Raise Case`, `Sync Reminders`). | **High** | Refactor into a **Split-View / Tabbed Command Room**: Left pane for Negotiation & Timeline; Right pane for Live Agreement & Terms Ledger. Condense refresh actions into a single global status poller / refresh action. |
| **P1** | **Simplicity** | **Marketplace Creation Form Clutter:** The Marketplace page forces BOTH a full Seller product listing creation form AND a Buyer RFQ creation form above the actual listings, pushing available deals below the fold. | **Medium** | Move "Publish listing" and "Request quote" into clean modal drawers or dedicated action tabs, allowing users to immediately browse active trades. |
| **P1** | **Simplicity** | **Duplicate "New deal" CTA:** On the Workspace page, "New deal" appears in the global navbar and directly inside the hero card banner right below it. | **Low** | Keep "New deal" as the primary header action; replace the card button with active filter chips (e.g. "Drafts", "Pending Approval", "Committed"). |
| **P2** | **Consistency** | **Fragmented Button Design System:** At least 6 diverging button classes are used (`.button`, `.button.secondary`, `.button.ghost`, `.button.deal-room__refresh`, `.button--compact`, `.button--secondary`). Some are pill-shaped, some rounded-rect, some outline, some filled. | **High** | Establish unified button tokens (`variant: primary \| secondary \| ghost \| danger`, `size: sm \| md \| lg`). Remove ad-hoc overrides in `styles.css`. |
| **P2** | **Consistency** | **Typo in Button Label:** `NegotiationReview.tsx:645` renders `<button>↓↓</button>` with two down arrows for reordering items down, while up is `↑`. | **Medium** | Replace with standard SVG arrow icons (`ArrowUpIcon`, `ArrowDownIcon`) and standardize touch padding. |
| **P2** | **Consistency** | **Mismatched Icon Usage (`↗`):** The external link glyph `↗` is affixed to internal action buttons like `Enter workspace ↗` (form submit) and `Refresh room ↗` (internal state reload), violating universal web conventions. | **Medium** | Reserve `↗` strictly for outbound external links. Use a spinner for loading/submit and a circular arrow `↻` for refresh actions. |
| **P3** | **Visual Hierarchy** | **Raw UUIDs Dominating Trade Record:** The Deal Room hero header prominently displays full and truncated UUIDs (`da41adfc-2893-...`, `53b600cc-...`, `d5f824e4-...`) in a large 4-column ledger, while crucial trade information (total amount, payment terms, delivery date) is buried. | **High** | Replace raw UUIDs with legal entity badges, counterparty verified avatars, commercial total values, and trade reference tags (e.g. `#TRD-2026-0811`). Hide technical UUIDs behind an expandable "Developer / Audit Metadata" accordion. |
| **P3** | **Visual Hierarchy** | **3D Canvas Shows Raw Hashes:** Floating labels in `DealConstellation.tsx` render raw hex fragments `53b600cc` and `d5f824e4` above the buyer and seller nodes. | **Medium** | Render actual trading partner legal names (e.g., "Buyer Co." / "Seller Co.") with status pips. |
| **P3** | **Visual Hierarchy** | **"Deal overview" Is a Raw Debug Paragraph:** Instead of a visual progress tracker, Deal Overview renders unformatted text: *"Current stage: Draft Next action: Buyer: share your requirements... Checking agreement status..."*. | **High** | Replace with an interactive **Trade Pipeline Stepper** (`Negotiation → Term Consensus → Bilateral Approval → Committed → Settlement`). |
| **P4** | **Feedback & Responsiveness** | **WebGL Performance Stall:** Browser console reports repeated GPU stalls: `GL Driver Message: GPU stall due to ReadPixels`. | **High** | Eliminate any synchronous readback or framebuffer reads; simplify geometries and cap pixel ratio at 1.5. Lazy-load scene with `IntersectionObserver` and pause when tab is inactive. |
| **P4** | **Feedback & Responsiveness** | **Stale "Loading..." Flashes on Initial Render:** Deal room renders 9 disjointed `Loading...` strings (`Loading saved agreement...`, `Loading conversation...`, `Checking agreement status...`) without skeletons. | **Medium** | Implement an unified skeleton layout and coordinated promise resolution to eliminate layout shifts (CLS). |
| **P5** | **Accessibility** | **Severe Low Contrast on Sign-in Inputs:** In `SignInPage.tsx`, input fields inside `.auth-card` use dark grey text on dark green inputs (`#1d2c25`), failing WCAG AA 4.5:1 ratio. | **Critical** | Use high-contrast inputs with clean borders (`rgba(255, 255, 255, 0.18)`), crisp white text (`#FFFFFF`), and distinct focus-visible rings (`#CF4F32`). |
| **P5** | **Accessibility** | **Micro-Typography Violation (<12px):** `styles.css` uses `0.55rem` (8.8px) and `0.59rem` (9.4px) in `.auth-masthead__note`, `.brand__type small`, and `.site-footer__row`. | **High** | Enforce a minimum font size of `0.75rem` (12px) for secondary metadata and `0.875rem` (14px) for body text. |
| **P5** | **Accessibility** | **Radio Button Misalignment & Tiny Touch Targets:** Message visibility radios (`Shareable` vs `Private`) in `DealConversationReview.tsx` have awkward line wraps and touch heights < 30px. | **Medium** | Convert into segmented toggle chips with minimum 44px height and explicit keyboard focus indicators. |
| **P6** | **Clarity** | **Brand Text Concatenation:** Logo markup renders `SyncAllyTRADE FOLIO` without a separator or space in the accessible DOM tree. | **Low** | Separate into `<span className="brand-name">SyncAlly</span><span className="brand-badge">Trade Folio</span>`. |
| **P6** | **Clarity** | **Developer Jargon Exposed to Commercial Users:** Terms like "Idempotency key", "Terms hash", "Transactional outbox", "Reload token", and "Durable schedule" are visible across headings and hints. | **Medium** | Rephrase into business-friendly language: "Guaranteed Submission Key", "Security Fingerprint", "Audit Log", "Commercial Milestones". |
| **P6** | **Clarity** | **Intrusive "Import thread" Box:** A large "Import thread" paste box is displayed permanently inside the conversation card directly below the message composer. | **Medium** | Move thread import into a collapsible secondary action ("Import from Email / Chat") so it doesn't compete with active messaging. |
| **P7** | **User Control** | **Session Route Leak Across Roles:** Signing out from `#/organizations` and signing into a different account leaves the hash at `#/organizations`, redirecting the new user into settings instead of workspace. | **High** | Upon authentication or sign-out, reset active hash route to `#/deals` unless an explicit deep-link redirect is specified. |
| **P7** | **User Control** | **Inability to Filter or Collapse Deal Sections:** Users cannot collapse or filter inactive sections (e.g. Fulfillment & Payment while still in Draft). | **Medium** | Introduce dynamic stage disclosure: progressively reveal Fulfillment and Payments only once the agreement is Committed. |
| **P8** | **Error Prevention** | **Spurious 404 Console Errors on Draft Deals:** Fetching `/deals/{id}/agreements/current` on draft deals triggers 4 red 404 errors in the console. | **Medium** | Update client/API contract so draft status is known prior to querying `/current`, or handle gracefully without polluting network error telemetry. |
| **P8** | **Error Prevention** | **Hardcoded Country Code in Marketplace:** Marketplace search has `IN` hardcoded in a plain text input without validation or dropdown. | **Low** | Provide a searchable ISO country select dropdown with flag indicators. |
| **P9** | **Aesthetics & Appeal** | **AI-Slop Blacklist Hit — Default Fonts:** Uses `Space Grotesk` + `Inter` as the primary typographic stack. | **High** | Upgrade to an editorial, authoritative pairing: **Cabinet Grotesk / Syne** for display and **Plus Jakarta Sans / Geist** for data/UI. |
| **P9** | **Aesthetics & Appeal** | **Repetitive Graph-Paper Grid Background:** The entire viewport is covered in a relentless faint graph-paper grid pattern. | **Medium** | Replace with subtle, layered architectural surfaces, refined borders, and purposeful whitespace. |
| **P9** | **Aesthetics & Appeal** | **Monolithic 4,877-line `styles.css`:** Stylesheet contains multiple legacy overrides, duplicate selectors, and conflicting media queries. | **High** | Clean up styles into modular CSS variables and scoped component styles. |
| **P10** | **Scalability & Mobile** | **Mobile Horizontal Overflow Bug (360px & 390px):** `scrollWidth` reaches 430px due to uncollapsed `.site-nav` grid and fixed-width ledger elements. | **Critical** | Implement responsive navigation drawer / hamburger menu on mobile (`< 768px`) and ensure all containers have `max-width: 100%; overflow-x: clip`. |
| **P10** | **Scalability & Mobile** | **Mobile Touch Targets < 44px:** Buttons such as `↑`, `↓↓`, `Remove`, and compact refresh buttons fail 44x44px minimum touch target size. | **High** | Enforce `min-height: 44px; min-width: 44px` on all interactive touch elements. |

---

## 3. Specific Bugs Identified

1. **Typo in Proposal Reorder Down Button:** `frontend/src/deals/NegotiationReview.tsx:645` contains `↓↓` instead of `↓`.
2. **Horizontal Viewport Breach on Mobile:** In `frontend/src/styles.css`, `.site-nav` at line 2697 does not collapse its navigation items or brand logo, forcing a minimum width of 430px on 360px/390px mobile viewports.
3. **Session Hash Route Bug:** `useSession.ts` / `App.tsx` fails to normalize the hash route on sign-in, carrying over previous routes (such as `#/organizations`) to newly authenticated sessions.
4. **WebGL ReadPixels GPU Stall:** `TradeFlowScene.tsx` initiates animation loops that trigger GPU driver warnings and CPU stalls in Chromium.
5. **Form Submit / Action Glyph Misuse:** `Enter workspace` on `SignInPage.tsx` and `Refresh room` on `DealDetailPage.tsx` both render external link arrows `↗`.
6. **Formset Border Bleed:** In `CreateDealPage.tsx`, `<fieldset>` elements use default user-agent styling resulting in an unstyled 2px groove border.
7. **Redundant Duplicate CTA:** On `DealsPage.tsx`, "New deal" button is present both in the sticky navigation header and in the body card header directly adjacent to it.
8. **Spurious 404 Logging:** `DealDetailPage.tsx` and `AgreementReview.tsx` issue requests to `/agreements/current` even when `deal.version === 0`, causing repeated 404 network failure logs.
