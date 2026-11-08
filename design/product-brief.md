# Product Knowledge Brief: SyncAlly

## Identity
- **Product name:** SyncAlly (Trade Folio)
- **One-sentence description (plain words):** A collaborative B2B trade management platform that turns unstructured commercial negotiations between buyers and sellers into legally vetted terms, bilaterally approved agreements, automated commercial document drafts, and verified PayPal invoice payments.
- **Category / industry:** B2B Trade Infrastructure / LegalTech / FinTech & Procurement
- **Stage (idea, beta, live, enterprise):** Live Beta / Vertical Slice (Deployed on Render: frontend at `https://syncally-frontend.onrender.com/`, API at `https://syncally-api.onrender.com/`)

## Audience
- **Primary users:** 
  1. **B2B Buyers / Procurement Managers:** Initiating RFQs, proposing delivery deadlines and specifications, verifying seller compliance, reviewing terms, and settling milestone invoices.
  2. **B2B Sellers / Suppliers / Exporters:** Listing products, offering price quotes, negotiating quantity and payment terms, drafting binding commercial proposals, and requesting milestone payouts.
- **Secondary audiences:**
  - Organization administrators (managing team members, approval routing, invitation workflows).
  - Legal & compliance officers (auditing SHA-256 agreement terms hashes and cryptographic trade packs).
- **What they are trying to get done:**
  - Move away from fragmented, messy WhatsApp/email threads into a single verifiable trade record.
  - Automatically extract commercial facts from unstructured messages without manual data re-entry.
  - Reach cryptographic bilateral consensus on exact agreement wording before money moves.
  - Automate post-agreement fulfillment tracking and PayPal Sandbox/Live milestone invoicing.

## Value
- **Core jobs-to-be-done (max 3):**
  1. **Turn messy negotiations into verified facts:** Ingest unstructured buyer/seller conversation messages, run AI-assisted term extraction (item, quantity, unit price, delivery date, port), and allow human operators to review and confirm them.
  2. **Establish cryptographic bilateral agreement consensus:** Invalidate stale approvals whenever terms change, require independent SHA-256 agreement approval from both parties, and commit atomically into an immutable trade pack.
  3. **Bridge agreements to fulfillment & payment:** Transition committed terms into obligation milestones, legal trade pack archives (`.zip` / `.html`), and automated PayPal invoicing with webhook reconciliation.
- **Real features, using the product's own names:**
  - **Shared Deal Room:** Unified deal timeline with dual-visibility messages (`SHAREABLE` visible to both parties, `PRIVATE` scoped strictly to authoring organization).
  - **Fact Review Buffer & Suggestion Review:** Human-in-the-loop review interface for AI-extracted commercial facts (Item Description, Quantity, Unit, Unit Price, Delivery Destination, Delivery Date).
  - **Bilateral Agreement Consensus:** Versioned candidate agreement engine with cryptographic `terms_hash` (SHA-256) and independent dual-party approval gates.
  - **Atomic Agreement Commitment:** Single PostgreSQL transaction transitioning deals to `COMMITTED`, locking terms, creating immutable obligations, and generating audit logs.
  - **Commercial Document Trade Pack:** Downloadable tamper-evident trade packs (`trade-pack.html`, `canonical-terms.json`, `manifest.json`) in encrypted ZIP format.
  - **PayPal Milestone Invoicing:** Asynchronous invoice creation, dispatch, and webhook-driven reconciliation marking obligations `PAID`.
  - **Trade Marketplace:** Directory for publishing product listings, broadcasting RFQs, and initiating one-click bilateral deals.
  - **Dev Role Switcher:** Instant tenant simulation tool for switching between Buyer, Seller, and Admin roles without manual credential juggling.
- **Differentiators vs alternatives (Email/WhatsApp, DocuSign, SAP Ariba):**
  - **vs. WhatsApp/Email:** Eliminates "he said, she said" disputes by enforcing structured cryptographic consensus on every line item and terms hash.
  - **vs. DocuSign/PandaDoc:** Moves beyond static PDF signing by turning contract terms into active database obligations and direct invoice triggers.
  - **vs. SAP Ariba:** Low-friction, lightweight web interface without enterprise bloat, suitable for agile cross-border SME trading partners.
- **Proof that exists:**
  - Live bilateral trade engine running on Render with FastAPI, PostgreSQL 16, Temporal durable workflows, and React 19 client.
  - Comprehensive Playwright test suite verifying pixel-perfect Three.js rendering, canvas motion, bilateral dual-party approval, and trade pack ZIP downloads.

## Conversion
- **Primary action:** "Enter workspace" (Sign In) → "Create deal" / "Open deal" → "Approve agreement" → "Commit agreement".
- **Secondary action:** "Publish a product listing" / "Request a supplier quote" on Marketplace; "Invite team member".
- **Pricing model:** Public pricing not currently gated; vertical slice operates with seeded organizational tiers.

## Brand and Voice
- **Existing logo & assets:** Cube icon SVG, paper graph grid pattern background (`#e9e5db`).
- **Brand colours:**
  - Background: Cream/Paper `#e9e5db`, `#dfd9cc`, Surface `#f7f4ec`
  - Accent / Primary: Burnt Terracotta / Rust `#cf4f32` / `#e36c48`
  - Secondary / Accent Soft: Deep Forest Ink `#182722` / `#20332c`
  - Counterparty Jade: `#a8d6b3` / `#64876a`
- **Fonts currently loaded:** Google Fonts `Space Grotesk` (headings) + `Inter` (body/UI) — *Note: Flagged for replacement under AI-slop guidelines*.
- **Tone of voice:** Authoritative, disciplined, legally precise, transparent, calm.
  - *Example copy:* "Each deal has one shared reference. Every reviewed term stays tied to its source."
- **Words and claims to avoid:** "Supercharge your workflow", "AI magic", "Next-gen revolution", "Effortless contract generation".
- **Visual no-gos:** Generic purple/blue neon glows, glassmorphism on white, ungrounded floating 3D spheres, unformatted raw UUID hashes.

## Content Inventory
- **Screens / flows:**
  1. `/` or `#/signin` - Authentication & Organization Onboarding
  2. `#/deals` - Workspace / Deal Register (shared deals list)
  3. `#/deals/new` - Create a draft deal wizard (role selection, counterparty picker)
  4. `#/deals/:id` - Deal Room (Overview, Conversation, Fact Review, Proposals, Agreement, Fulfillment, Payment, Cases, Reminders)
  5. `#/marketplace` - Trade Marketplace (Listings, RFQs, Quote requests)
  6. `#/organizations` - Organization Profile, Team Members, Approval Routing
- **Available assets:** Procedural Three.js WebGL scenes (`TradeFlowScene.tsx`, `DealConstellation.tsx`), custom SVG icon set.
- **Legal copy:** "AI suggestions are unreviewed. AI never approves or commits an agreement. Both parties independently approve the identical terms hash."

## Technical Stack
- **Client:** React 19.3, TypeScript 6, Vite 8.1, Three.js 0.186, Hash-based client router (`useHashRoute.ts`).
- **Styling:** CSS variables in `frontend/src/styles.css` (4,877 lines, needs refactoring).
- **Backend API:** FastAPI (Python 3.12+), PostgreSQL 16, SQLAlchemy 2, Alembic, Uvicorn on Render (`syncally-api.onrender.com`).
- **Orchestration & Workers:** Temporal Python SDK, Transactional Outbox workers for PayPal Sandbox payments.

## Visual Metaphor Candidates
- **Core truth in one line:** "Two independent parties weaving unstructured conversation into a single, unshakeable cryptographic trade ledger."
- **3 Candidate 3D / visual metaphors:**
  1. **The Bilateral Loom / Consensus Ring:** Two opposing orbital particles (Buyer terracotta, Seller jade) that weave continuous golden threads into a central hexagonal cryptographic tablet. As terms are accepted, the tablet engraves and locks with an embossed seal.
  2. **The Dynamic Ledger Vault:** A low-poly tactile ledger where verified fact blocks physically snap into alignment like precision brass gears, completing a secure trade vault latch.
  3. **The Lighted Trade Pipeline:** A physical topological map of international trade where negotiation pulses travel between two corporate headquarters, lighting up clearance checkpoints (Terms → Consensus → Commitment → Payment).
