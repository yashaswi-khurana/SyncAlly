# Customer journey: buyer and seller

## Outcome

Enable a buyer and seller to start a trade, agree on the same terms, follow payment and delivery, and return knowing what needs their attention. This is a product objective, not a claim that customer research or production readiness has been completed.

## Customer contract

1. A customer can understand how to access the product and whether an environment is a demo. An invitation must say how it is delivered; do not imply that a link was emailed when it was only generated. Production onboarding requires verified recipient ownership before granting access.
2. Either party can initiate a deal in its correct role, find or invite the other organization, and recognize the deal later by human-readable trade and party information. Pending invitations and unavailable information must be represented honestly without exposing private organization data.
3. A deal provides a role-aware overview: what is being traded, current stage, what the customer can do next, and what is waiting on the other party. Show an action only when current authoritative state and permissions support it; if they cannot be determined, say so rather than guessing.
4. Customers can discuss terms privately or with both parties, understand who can see each item, review suggestions and enter terms manually. A message, extracted suggestion, confirmed fact, proposal, one-party approval and committed agreement are distinct states. AI must not approve or commit a trade.
5. Both organizations review and approve the same current agreement version. Show changes, decisions and any remaining commit step clearly. A changed version cannot inherit stale approvals; committed terms and their evidence remain immutable.
6. After commitment, show payment and delivery as separate tracks with role-appropriate actions. A request, provider send, provider-confirmed payment, simulated payment, shipment and buyer confirmation are distinct. Never treat a redirect or an uncertain provider result as payment confirmation.
7. Customers returning later can find their deals, identify pending actions and understand waiting or error states. Notifications must not be claimed delivered without delivery evidence and must respect private information.
8. Customer-facing flows remain accessible on desktop and mobile, with keyboard access, clear error recovery and no technical identifiers as the primary way to identify a deal.

## Task graph

- **A. Journey baseline and safety:** map actual buyer/seller flows, current capabilities and protected boundaries; preserve existing local work. This specification records the baseline and must be revised when behavior or product decisions change.
- **B. Invitation handoff:** after A, make manual delivery, recipient, expiry and recovery clear for existing invite paths. Depends on existing invitation behavior; does not introduce unverified email delivery.
- **C. Deal discovery:** after A, identify counterparties and pending invitations from authorized data; provide clear fallbacks. Do not infer a next action from a generic status. A meaningful trade title requires an authorized server-owned source and must not leak private facts.
- **D. Role-correct initiation:** after A, extend buyer/seller creation and counterparty invitations end to end, including authorization, pending shell ownership and invitation acceptance. Add buyer/seller and cross-tenant tests. A frontend-only role switch is insufficient.
- **E. Role-aware deal overview:** after C and the relevant state/permission contracts, project verified stage, actor and next actions; retain an explicit unknown state and privacy boundaries.
- **F. Terms and agreement flow:** after E, make discussion, suggestions, proposed versions, approvals and final commitment distinct and navigable; preserve exact-version concurrency and human bilateral authorization.
- **G. Execution and return:** after F, present separate payment and delivery tracks, trustworthy provider states and actionable exceptions. Reliable notifications, verified identity and long-lived infrastructure are dependencies where needed, not promises implied by UI.
- **H. End-to-end validation:** after B-G, exercise a real two-party journey on desktop and mobile, including invitations, permissions, changed terms, payment/delivery exceptions and accessibility. Record actual environments and provider limitations. Independent review and the required project checks must pass before declaring completion.

## Evidence and limits

The deployed static frontend was reachable during the November 6 review, but its backend was not connected. A separate local SQLite demo allowed navigation as each party; it did not establish production, PostgreSQL/Temporal or real PayPal behavior. Existing roadmap issue #78 is broader than this task graph, and closed issue #77 is historical evidence, not proof of this specification. Do not invent RICE reach, impact, confidence, effort or retention results in the absence of customer data.
