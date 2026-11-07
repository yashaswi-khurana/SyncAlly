# MASTER BOARD
<!-- owner: orchestrator. Workers read only. Status columns are mirrors of worker logs; logs are the truth for agent state. -->
- updated: 2026-11-07T07:15:00Z
- stale_after_minutes: 15

## OBJECTIVE
Implement Step 08 Cancel Disputes (F8): Scoped auditable cancellation and dispute cases with bilateral decisions, privacy-aware evidence, conflict serialization, actual-head migration, UI case history, and empirical test gates.

## REQUIREMENTS
| id | requirement | acceptance | covered_by | status | evidence |
|---|---|---|---|---|---|
| R1 | Persist scoped cancellation and dispute case requests with type, reason, agreement version/hash, obligation references, actor, timestamp, evidence visibility, and atomic audit/outbox events. | Domain model, database tables, and repository persist cases with audit and outbox integration. | WP1, WP2 | PASS | `test_deal_cases.py` (case creation, audit & outbox records) |
| R2 | Preserve existing pre-commit cancellation behavior without regression. | Pre-commit deals in DRAFT/NEGOTIATING cancel directly via existing cancel route/use-case; tests pass. | WP1, WP2 | PASS | `test_precommit_cancellation_preserved_without_cases` |
| R3 | Distinguish case creation from effective cancellation, liability, refund, or settlement; surface operational impact blockers for paid or in-flight consequences. | Case creation does not modify payment status or delivery obligations; blockers remain visible. | WP1, WP2 | PASS | `test_operational_blockers_on_paid_milestones_and_fulfilled_shipments` |
| R4 | Enforce authorized bilateral decisions for mutual cancellation on matching agreement version/hash with zero AI authority. | POST /cases/{id}/respond enforces bilateral counterparty authorization and version hash consistency. | WP1, WP2 | PASS | `test_bilateral_consent_mutual_cancellation` |
| R5 | Serialize concurrent conflicts with payments, amendments, and fulfillment using optimistic checks and no network calls inside DB locks. | Concurrent cases and stale versions return HTTP 409 Conflict; no network inside DB transactions. | WP1, WP2 | PASS | `test_stale_terms_hash_fails_closed_with_409` |
| R6 | Support private and scoped evidence states with strict tenant boundary checks. | Counterparty-restricted or private evidence is filtered out for unauthorized tenants. | WP1, WP2 | PASS | `test_evidence_visibility_filtering_for_counterparty_and_private` |
| R7 | Actual-head additive database migration 0025 with downgrade preservation and history-loss block. | Alembic migration 0025_cancel_disputes applies cleanly on top of actual head 0025_system_admin; downgrade blocks history loss. | WP2 | PASS | `test_alembic_migration_0025_and_downgrade_block` |
| R8 | Frontend UI case history and bilateral decision controls in DealDetailPage. | DealDetailPage renders case history, dispute/cancellation requests, evidence visibility, and bilateral actions; frontend tests pass. | WP2 | PASS | `DealDetailPage.test.tsx` (37 passed) |
| R9 | Independent review verification, focused test gates, full static/test gates green, and progress report updated. | Reviewer verifies diff, focused test discovery script passes, DealDetailPage.test.tsx passes, lint/build green, progress.md and 08-cancel-disputes.md updated. | WP9, RV1 | PASS | Reviewer VERDICT: PASS; 424 frontend tests passed; lint/build clean |

## CONSTRAINTS
<!-- hard project rules found in recon: fixed roles, limits, approval gates. Quote the source file. -->
| rule | source | effect on plan |
|---|---|---|
| Exactly three specialized role agents: PLANNER read-only; DEVELOPER one planned task; REVIEWER independent; repair max 3 | User prompt / docs/remaining-tasks/08-cancel-disputes.md | Fixed role topology: planner (WP1) -> developer (WP2) -> reviewer (RV1), max 3 repairs |
| Missing coordination BLOCKED; ask before manual substitution, never self-approve/pretend review | User prompt / docs/remaining-tasks/08-cancel-disputes.md | Strict subagent dispatch and verification; no self-approval |
| Conservative choices approved, not policy expansion/client roles/backfills/refunds/legal claims/private egress | User prompt / docs/remaining-tasks/08-cancel-disputes.md | Purely scoped cases and authorized bilateral decisions; no automated money movement |
| Atomic durable outbox/no network inside DB locks; finite bounded Decimal BEFORE formatting/calculation | User prompt / docs/remaining-tasks/08-cancel-disputes.md | Transactions commit DB state and outbox atomically without external calls inside locks |
| Preserve all dirty tracked/untracked/user changes, reread before apply_patch; no cleanup/branch/commit/push/reset | User prompt / docs/remaining-tasks/08-cancel-disputes.md | Keep git worktree clean, do not clobber user or graphify files |
| Actual-head migration never fixed 0018; upgrade preservation/history-loss downgrade block | User prompt / docs/remaining-tasks/08-cancel-disputes.md | 0025_cancel_disputes follows 0025_system_admin with downgrade check |
| Python 3.12+ configured venv, no implicit installs/services | User prompt / docs/remaining-tasks/08-cancel-disputes.md | Rely only on existing packages in backend/.venv |

## CAPABILITY MATRIX
| WP | needed capability | assigned skill/agent | fit (OK / ADHOC / GAP) | reason if generic over specialist |
|---|---|---|---|---|
| WP0 | Contract definition | project-orchestrator | OK | Core orchestrator function |
| WP1 | Architecture planning & read-only analysis | planner (lazy-senior-engineer) | OK | Read-only analysis and inspection |
| WP2 | Full-stack backend/frontend implementation | developer (lazy-senior-engineer) | OK | Proven minimal, resilient engineering across stack |
| RV1 | Independent adversarial review | reviewer (precision-code-reviewer) | OK | High-precision adversarial review |
| WP9 | Integration & test gate verification | orchestrator (project-orchestrator) | OK | Verification, documentation and gate closing |

## WAVES AND WORK PACKAGES
| wave | WP | agent-id | depends_on | write_scope | state (mirror) | synced |
|---|---|---|---|---|---|---|
| 0 | WP0 | orchestrator | [] | .orchestrator/contracts/** | ACCEPTED | 2026-11-07T06:01:00Z |
| 1 | WP1 | planner | ["WP0"] | .orchestrator/plans/** | ACCEPTED | 2026-11-07T06:08:00Z |
| 2 | WP2 | developer | ["WP1"] | backend/**, frontend/**, docs/** | ACCEPTED | 2026-11-07T06:47:00Z |
| 3 | RV1 | reviewer | ["WP2"] | .orchestrator/reviews/RV1/** | ACCEPTED | 2026-11-07T06:56:00Z |
| 4 | WP9 | orchestrator | ["RV1"] | .orchestrator/master-board.md, docs/remaining-tasks/** | COMPLETED | 2026-11-07T07:15:00Z |

## CONTRACTS
| name | version | path | status (DRAFT / FROZEN) |
|---|---|---|---|
| cancel-disputes-contract | 1 | .orchestrator/contracts/cancel-disputes-contract.md | FROZEN |

## RESOURCE REGISTRY
| resource (port, db, env key) | value or name | owner |
|---|---|---|
| Migration revision | 0025_cancel_disputes | developer |
| Contract API prefix | /api/v1/deals/{deal_id}/cases | developer |
| Database table | deal_cases, deal_case_evidence | developer |

## DIRECTIVES
| id | target agent | directive (HALT / RESUME / CHANGE) | detail | issued |
|---|---|---|---|---|

## ARBITRATION LOG
<!-- append-only -->
