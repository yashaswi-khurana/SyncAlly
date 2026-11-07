# Frontend product review

Reviewed: 2026-11-06

## Findings and fixes

| Priority | Finding | Change |
| --- | --- | --- |
| High | An expired session could leave the workspace shell visible and make protected retries fail repeatedly with an invalid token. | A protected API 401 now clears the local session and returns the app to sign-in. Other tabs follow session removal from local storage. |
| Medium | Primary buttons changed from the orange product accent to blue on hover. | Hover now uses a darker orange and the existing accent glow. |
| Medium | Deals without a custom title were hard to distinguish; duplicate custom titles were also ambiguous. | Deal rows append a short stable reference to every title, and untitled deals use the buyer/seller names where available. |
| Medium | The deal-room title had poor contrast against the page background. | The heading now uses a high-contrast foreground color. |
| Medium | The deal-room ledger and agreement approval list could show organization IDs instead of legal names. | Deal details now look up and pass legal names into the ledger and approval list, with a short organization reference as fallback. |
| Medium | A pending-counterparty deal repeated the “Awaiting counterparty” empty-state banner above an overview that already explained the invitation state. | Removed the redundant banner. |
| Low | Organization settings used technical wording (“Organization IDs”) and the member action implied that it created a new account. | Renamed the section “Your organizations” and clarified the action as “Add an existing member.” |
| Medium | A committed agreement could be described with copy that implied the agreement still needed to be committed. | The committed-state explanation now says both organizations approved the version and that payment and delivery are tracked separately. |
| Medium | The counterparty invitation success state showed a long bearer link as a raw full-width field. | The state presents the recipient, a masked link preview, a copy action, an expandable manual-copy field, and expiry in a responsive card. Local invite links use the running app path in development. |

## Walkthrough coverage

The local demo session was restored with the repository's documented demo account. I reviewed the deal register, new-deal form, organization settings, pending-counterparty state, draft deal as buyer and seller, negotiation editor, agreement review, delivery, and payment status. No proposal, message, invitation, agreement decision, payment, or delivery action was submitted. The buyer/seller role switch changed the displayed role without changing deal data.

The review exposed one remaining data-backed display gap: the existing demo deals' party-name lookups did not resolve in the live browser. Rows still show deal names and unique references; the redundant “Name unavailable” subtitle is now omitted when no legal name is available, and the detail ledger shows short organization references. Verify the organization lookup response/seed data before claiming legal names appear for every existing deal.

The committed trade pack still labels the generated document “DRAFT – FOR REVIEW ONLY.” This may describe the document export rather than agreement state, so it needs product confirmation before changing. Payment status accurately indicates no confirmed payment; no external invoice or payment provider was opened.

No business data was created or changed during this review. The only session-side change was switching the local demo role back to Buyer.
