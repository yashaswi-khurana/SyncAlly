# Graph Report - SyncAlly  (2026-11-08)

## Corpus Check
- 374 files · ~344,812 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 14 file(s) not represented in the graph (top: (none) 8, .example 2, .ini 1)

## Summary
- 5680 nodes · 18621 edges · 205 communities (146 shown, 59 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 2462 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `5b3e0a4c`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Conversations & Test Conversation Use
- AIContractError
- BaseModel
- repositories/agreements.py
- AISuggestionProviderTests
- schedule_deal_reminders
- repositories/agreements.py
- PaymentNeedsAction
- PaymentProviderResolver
- api/agreements.py
- Test Conversation Routes (ConversationRouteTests)
- OutboxEvent
- Test Agreement Routes (AgreementRouteTests)
- Message
- process_payment_intent
- draft_proposal_from_context
- NegotiationTests
- Types & Client
- listOrganizations
- OrganizationPermissionsTests
- AgreementVersionId
- Test Outbox Dispatcher & Outbox
- Simulate Deal Flow & Test
- Test Organization Invitations & Organizations
- DealId
- package.json
- Organization
- Dealconversationreview & Dealconversationreview.Test
- Skill & Skill.Md
- api/payments.py
- repositories/payment_processing.py
- repositories/negotiation.py
- workflow_state.py
- Aisuggestionreview & Suggestionpreview
- SyncAlly Implementation Plan Document
- PaymentProcessingTests
- application/deal_cases.py
- worker.py
- ApprovalRoutingTestCase
- Paymentstatuspanel & Paymentstatuspanel.Test
- PaymentIntentRepositoryTests
- services
- api/deals.py
- InvariantViolation
- build_terms
- Test Dev Routes (DevRoutesTests)
- add_organization_member
- DealWorkflowTests
- Test Organization Directory & Organizations
- create_deal
- SqlAlchemyDealRepository
- auth.py
- PaymentOutboxWorkerTests
- api/payments.py
- repositories/agreements.py
- NegotiationReview.tsx
- RemindersPanel.tsx
- _active_admin_membership
- CommercialDocumentDraftTests
- Test Migration Lock & Env
- Payment Processing & Test Payment
- 01 Commercial Domain Model &
- create_counterparty_invitation
- Test Deal Routes & Identity
- api/negotiation.py
- Compose.Yaml (volumes)
- Architectural & Implementation Plan: Step 08 Cancel Disputes (F8)
- CreateDealPage.tsx
- CommitAgreementCommand
- PaymentWorkItem
- simulate_payment
- TradeTerms
- PersistentDemoSeedTests
- AgreementReview.tsx
- refresh_access_token
- SqlAlchemyReminderRepository
- repositories/agreements.py
- IdentityBoundaryTests
- Optional AI Specification
- Tsconfig (tsconfig.json)
- Test Paypal Webhooks (FakeWebhookVerifier)
- NegotiationPostgresRaceTests
- authorize_payment_intent
- uuid
- SafeOperationsTests
- environment
- Main & Test Identity Boundary
- Deploying SyncAlly's Temporal workers on AWS
- Collections API and UI Specification F10b
- ApiError
- Test Organization Index Migration (OrganizationIndexPostgresMigrationTests)
- Server-Enforced Capability Matrix
- maybe_complete_deal
- NegotiationRouteTests
- InvalidTransition
- lock_demo_deal_creation
- application/conversations.py
- DatabasePersistenceTests
- Master Execution Contract
- 0005 Conversation Party Unique (Enforce
- Main (Request)
- Safe Operations and Recovery Guide
- temporal-namespace
- api/reminders.py
- ProposedTerms
- .test_generates_draft_from_schema_2_committed_terms
- x-app-environment
- Test Payment Mode Migration (PaymentModeMigrationTests)
- environment
- Test Communication Migration (ConversationPartyUniquenessMigrationTests)
- create_worker
- OnboardingWizard.tsx
- ApprovalRoutingRouteTests
- NegotiationCommand
- healthcheck
- queue_simulated_reconciliation
- DealWorkflowInput
- AiContextSelectionTests
- canonical_decimal
- Final Gates and Truthful Completion Specification
- Skill (Repo Idea Thinker Skill)
- SqlAlchemyPaymentIntentRepository
- Vite Env.D (ImportMeta)
- temporal-schema
- PaymentReconciliationRepositoryTests
- Index (Frontend HTML Root Document)
- Pyproject (syncally)
- Customer journey: buyer and seller
- devDependencies
- sqlalchemy
- scaling
- Deal
- SyncAlly deployment
- comprehensive_verification.mjs
- DealDetailPage.test.tsx
- ProposalComparison.tsx
- api/fulfillment.py
- DealReminder
- build_terms
- volumes
- MASTER BOARD
- setup-temporal-postgres.sh
- FulfillmentMigrationTests
- ProviderInvoiceUniqueMigrationTests
- simulate_deal_flow.py
- current_user
- MigrationConfigTests
- CollectionSchemaMigrationTests
- create-temporal-namespace.sh
- postgres-init.sh
- amendment.py
- ConversationUseCaseTests
- repositories/reminders.py
- DealWorkflowInput
- STATE LOG: developer
- AuthorizePaymentIntentCommand
- 0004_communication_sources_and_scope_indexes.py
- DealCasesTests
- MilestonePaymentsMigrationTests
- STATE LOG: planner
- NegotiationMigrationTests
- STATE LOG: reviewer
- CONTRACT: cancel-disputes-contract v1   status: FROZEN
- organization.py
- eslint.config.js
- _register_shutdown_handlers
- get_commercial_document_draft_route
- Constraint
- scripts
- FakePayPalInvoiceProvider
- hostless-start.sh
- vite.config.ts
- VerifiedProviderPaymentState
- login
- .__call__
- main.py
- SyncAlly: Confirmed Bugs and Feature Roadmap
- Code Review: Step 08 Cancel Disputes (F8) — Work Package RV1
- check_milestone_trigger_eligibility
- _is_one_active_per_milestone_violation
- ._seed
- env.py
- get_optional_actor
- _is_duplicate_membership_error
- Frontend product review
- DealWorkflowNotification
- HealthRouteTests

## God Nodes (most connected - your core abstractions)
1. `ActorContext` - 313 edges
2. `OrganizationId` - 241 edges
3. `InvariantViolation` - 150 edges
4. `UserId` - 139 edges
5. `Money` - 127 edges
6. `DealId` - 122 edges
7. `Deal` - 114 edges
8. `SqlAlchemyAgreementRepository` - 113 edges
9. `AISuggestionProviderTests` - 87 edges
10. `TradeTerms` - 87 edges

## Surprising Connections (you probably didn't know these)
- `5. Audit Checklist Verification` --references--> `AuditEvent`  [INFERRED]
  .orchestrator/reviews/RV1/review.md → backend/src/syncally/infrastructure/models/operations.py
- `Existing Codebase Behavior` --references--> `InvalidTransition`  [INFERRED]
  .orchestrator/plans/cancel_disputes_plan.md → backend/src/syncally/domain/shared/errors.py
- `5. Audit Checklist Verification` --references--> `OutboxEvent`  [INFERRED]
  .orchestrator/reviews/RV1/review.md → backend/src/syncally/infrastructure/models/operations.py
- `AST Metrics Table` --references--> `_raise_case_impl()`  [INFERRED]
  .orchestrator/reviews/RV1/review.md → backend/src/syncally/api/deals.py
- `AST Metrics Table` --references--> `_respond_case_impl()`  [INFERRED]
  .orchestrator/reviews/RV1/review.md → backend/src/syncally/api/deals.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Deal Governance and Exception Lifecycle** — docs_remaining_tasks_07_amendments_amendments_contract, docs_remaining_tasks_08_cancel_disputes_cancel_disputes_contract, docs_remaining_tasks_09_approval_routing_approval_routing_contract, docs_remaining_tasks_10_reminders_reminders_contract [EXTRACTED 1.00]
- **Mandatory System-Level Verification Gates** — docs_remaining_tasks_11_judge_demo_judge_demo_contract, docs_remaining_tasks_12_browser_verification_browser_verification_contract, docs_remaining_tasks_13_postgres_temporal_postgres_temporal_contract, docs_remaining_tasks_16_final_gates_final_gates_contract [EXTRACTED 1.00]
- **Core Commercial Step Execution Chain** — docs_remaining_tasks_01_profiles_profiles_contract, docs_remaining_tasks_02_permissions_permissions_contract, docs_remaining_tasks_03_fulfillment_fulfillment_contract, docs_remaining_tasks_04_collection_schema_collection_schema_contract, docs_remaining_tasks_05_collections_api_ui_docs_collections_api_ui_contract, docs_remaining_tasks_06_milestone_payments_milestone_payments_contract [EXTRACTED 1.00]
- **Repository Architecture, Visualization, and Ideation Framework** — github_skills_repo_architect_skill, github_skills_archify_diagrammer_skill, github_skills_repo_idea_thinker_skill, github_skills_api_database_skill [INFERRED 0.85]
- **Code Implementation, Review, Debugging, and QA Loop** — github_skills_senior_engineer_skill, github_skills_code_reviewer_skill, github_skills_debugger_skill, github_skills_testing_qa_skill [INFERRED 0.85]
- **Multi-Tenant Privacy and Context Boundary Enforcement** — docs_architecture_06_ai_provider_boundary_ai_egress_and_privacy_filtering, backend_readme_message_idempotency, docs_f12_trade_pack_handoff_evidence_free_projection_and_safety_bounds [INFERRED 0.85]
- **Production Readiness and Quality Gate Lifecycle** — github_skills_devops_production_skill, github_skills_performance_reliability_skill, github_skills_security_analyst_skill, github_skills_testing_qa_skill [INFERRED 0.85]
- **Asynchronous Outbox Worker and Reconciliation Topology** — architecture_transactional_outbox_pattern, architecture_temporal_worker_and_outbox, architecture_paypal_sandbox_invoicing_flow, docs_operations_outbox_recovery_and_workflow_replay [INFERRED 0.95]
- **Bilateral Agreement Approval and Commitment Flow** — docs_architecture_01_commercial_domain_model_atomic_bilateral_approval, docs_architecture_01_commercial_domain_model_agreement_version, docs_architecture_05_domain_layer_agreement_commitment_flow [INFERRED 0.95]
- **Bilateral Agreement Consensus and Execution Pipeline** — architecture_bilateral_consensus_lifecycle, readme_core_trade_lifecycle, backend_readme_f6_agreement_history_and_comparison, docs_f12_trade_pack_handoff_trade_pack_export_contract [INFERRED 0.95]
- **PayPal Payment Intent and Reconciliation Lifecycle** — docs_architecture_03_paypal_payment_intent_lifecycle_payment_intent, docs_architecture_03_paypal_payment_intent_lifecycle_create_unknown_state, docs_architecture_03_paypal_payment_intent_lifecycle_payment_reconciliation [INFERRED 0.95]
- **Temporal Outbox Relay and Workflow Orchestration** — docs_architecture_02_temporal_deal_workflow_contract_deal_workflow, docs_architecture_02_temporal_deal_workflow_contract_outbox_workflow_start, docs_architecture_02_temporal_deal_workflow_contract_refresh_deal_state, infra_readme_restart_smoke_test [INFERRED 0.95]

## Communities (205 total, 59 thin omitted)

### Community 0 - "Conversations & Test Conversation Use"
Cohesion: 0.06
Nodes (45): add_message_route(), AddMessageRequest, AISuggestionRequest, clarify_fact_route(), confirm_fact_route(), ConstraintResponse, correct_fact_route(), CorrectFactRequest (+37 more)

### Community 1 - "AIContractError"
Cohesion: 0.07
Nodes (25): AIContractError, AIValidationClaim, _check_keys(), _contains_numeric_token(), _contains_token(), _date_value_is_present(), _decimal(), _fact_value_is_supported_by_quote() (+17 more)

### Community 2 - "BaseModel"
Cohesion: 0.09
Nodes (11): AcceptInvitationResponse, ApprovalRoutingPolicyRequest, ApprovalRoutingPolicyResponse, ContactPayload, ContactResponse, CounterpartyInvitationResponse, InvitationResponse, OrganizationDirectoryItem (+3 more)

### Community 3 - "repositories/agreements.py"
Cohesion: 0.07
Nodes (23): AgreementAccessDenied, AgreementAlreadyCommitted, AgreementNotFound, AgreementVersionConflict, create_agreement_draft(), CreateAgreementDraftCommand, ProposalNotFound, StaleAgreementVersion (+15 more)

### Community 4 - "AISuggestionProviderTests"
Cohesion: 0.07
Nodes (15): get_ai_suggestion_provider(), extract_facts_from_context(), ConfiguredAIProvider, AISuggestionProviderTests, respond(), respond(), respond(), respond() (+7 more)

### Community 5 - "schedule_deal_reminders"
Cohesion: 0.18
Nodes (3): dispatch_due_reminders(), schedule_deal_reminders(), RemindersServiceTests

### Community 6 - "repositories/agreements.py"
Cohesion: 0.06
Nodes (33): _is_active_member(), NotificationKind, _create_fixture(), DemoIdentity, _password_for(), _seed_identities(), AgreementRoutingDecision, AgreementVersion (+25 more)

### Community 7 - "PaymentNeedsAction"
Cohesion: 0.09
Nodes (11): get_paypal_webhook_configuration(), receive_paypal_invoice_webhook(), PaymentNeedsAction, PaymentOutcomeUnknown, PaymentRetryableError, PayPalSandboxInvoiceProvider, _provider_request_id(), _send_request() (+3 more)

### Community 8 - "PaymentProviderResolver"
Cohesion: 0.10
Nodes (8): PaymentInvoiceNotice, main(), GmailSettings, PayPalSettings, GmailSMTPInvoiceNotifier, PaymentProviderResolver, _FakeSMTP, GmailSMTPInvoiceNotifierTests

### Community 9 - "api/agreements.py"
Cohesion: 0.05
Nodes (46): AgreementVersionResponse, AmendmentImpactResponse, ApprovalResponse, approve_agreement_route(), commit_agreement_route(), CommitAgreementRequest, compare_agreements_route(), create_agreement_draft_route() (+38 more)

### Community 10 - "Test Conversation Routes (ConversationRouteTests)"
Cohesion: 0.10
Nodes (3): ConversationRouteTests, respond(), send()

### Community 11 - "OutboxEvent"
Cohesion: 0.12
Nodes (3): PaymentStatusResponse, OutboxEvent, PaymentStatusExtendedModelTests

### Community 13 - "Message"
Cohesion: 0.07
Nodes (19): ConcurrentConstraintUpdate, message_fingerprint(), MessageIdempotencyConflict, ConstraintKind, ConstraintStatus, Conversation, Message, MessageSourceType (+11 more)

### Community 14 - "process_payment_intent"
Cohesion: 0.07
Nodes (15): payment_invoice_number(), PaymentInvoiceNotifier, PaymentInvoiceProvider, PaymentProcessingRepository, reconcile_payment_intent(), _request_id_retry_window_expired(), require_payment_provider(), claim_next_payment_event() (+7 more)

### Community 15 - "draft_proposal_from_context"
Cohesion: 0.07
Nodes (25): AIProvenance, AIRetryPolicy, AISuggestionProvider, call_with_bounded_retry(), draft_proposal(), draft_proposal_from_context(), extract_facts(), fact_suggestion_guidance() (+17 more)

### Community 16 - "NegotiationTests"
Cohesion: 0.20
Nodes (4): EvidenceReference, ProposalBase, negotiate_in_transaction(), NegotiationTests

### Community 17 - "Types & Client"
Cohesion: 0.04
Nodes (98): closeMarketplaceRFQ(), createMarketplaceListing(), createMarketplaceRFQ(), deactivateMarketplaceListing(), describeDetail(), getDealMessageExistence(), isAbortError(), isRecord() (+90 more)

### Community 18 - "listOrganizations"
Cohesion: 0.05
Nodes (67): dependencies, react@^19.3.0, react-dom@^19.3.0, three@^0.186.1, getCurrentUser(), listOrganizations(), login(), registerOrganization() (+59 more)

### Community 19 - "OrganizationPermissionsTests"
Cohesion: 0.07
Nodes (18): _active_admin_membership(), _compute_effective_capabilities(), _deal_awaiting_counterparty(), delete_approval_routing_policy_route(), get_approval_routing_policy_route(), get_organization_profile_route(), get_organization_route(), list_my_organizations() (+10 more)

### Community 20 - "AgreementVersionId"
Cohesion: 0.14
Nodes (7): PaymentMilestone, AgreementVersionId, PaymentMilestoneId, _restore_domain_intent(), MilestoneDomainValidationTests, DealDomainTests, make_deal()

### Community 21 - "Test Outbox Dispatcher & Outbox"
Cohesion: 0.09
Nodes (14): build_deal_workflow_id(), dispatch_outbox_event(), OutboxDispatchResult, PendingOutboxEvent, WorkflowStartTransientError, apply_dispatch_result(), claim_next_pending_event(), _claim_statement() (+6 more)

### Community 22 - "Simulate Deal Flow & Test"
Cohesion: 0.05
Nodes (14): _build_in_process_client(), dispatch_payment(), mark_fixture(), session_factory(), ci_deal_flow_hook(), DealFlowContext, DealFlowSimulator, run_simulation() (+6 more)

### Community 23 - "Test Organization Invitations & Organizations"
Cohesion: 0.16
Nodes (5): accept_invitation(), AcceptInvitationRequest, create_organization_invitation(), CreateInvitationRequest, OrganizationInvitationTests

### Community 24 - "DealId"
Cohesion: 0.06
Nodes (11): confirm_constraint(), ConstraintNotFound, ConstraintId, ConversationId, DealId, MessageId, constraint(), message() (+3 more)

### Community 25 - "package.json"
Cohesion: 0.15
Nodes (12): happy-dom@^21.0.3, @testing-library/dom@^10.4.1, @testing-library/jest-dom@^7.0.1, engines, node, name, private, type (+4 more)

### Community 26 - "Organization"
Cohesion: 0.04
Nodes (58): API_REQUEST_TIMEOUT_MS, deleteApprovalRoutingPolicy(), getApprovalRoutingPolicy(), getCommercialDocumentDraft(), listOrganizationMembers(), putApprovalRoutingPolicy(), revokeOrganizationMember(), CREATED_MESSAGE (+50 more)

### Community 27 - "Dealconversationreview & Dealconversationreview.Test"
Cohesion: 0.07
Nodes (47): createDealMessage(), importDealThread(), listDealFacts(), listDealMessages(), previewDealThreadImport(), reviewDealFact(), updateFactVisibility(), Visibility (+39 more)

### Community 28 - "Skill & Skill.Md"
Cohesion: 0.04
Nodes (43): API and Database Engineer Skill, API Design and Contract Semantics, Data Integrity and Invariant Enforcement, Query Performance and Projection Optimization, Schema Migration and Backward Compatibility, Transaction Boundaries and Atomicity, Archify Diagrammer Skill, Archify CLI Global Tool (+35 more)

### Community 30 - "repositories/payment_processing.py"
Cohesion: 0.06
Nodes (8): _persist_paypal_webhook_event(), PaymentInvoiceLineItem, PaymentIntentCommandMismatch, PaymentMilestoneNotFound, PaymentIntentId, _has_excess_currency_precision(), _provider_error_code(), record_paypal_webhook_event()

### Community 31 - "repositories/negotiation.py"
Cohesion: 0.19
Nodes (6): NegotiationConflict, NegotiationNotFound, NegotiationOrganizationRequired, ProposalId, SqlAlchemyNegotiationRepository, projection()

### Community 32 - "workflow_state.py"
Cohesion: 0.11
Nodes (9): DealWorkflowState, load_deal_workflow_state(), parse_workflow_uuid(), WorkflowAgreementRepository, WorkflowDealNotFound, WorkflowDealRepository, _FakeAgreementRepository, _FakeDealRepository (+1 more)

### Community 33 - "Aisuggestionreview & Suggestionpreview"
Cohesion: 0.09
Nodes (38): correctDealFact(), createDealFact(), draftDealProposal(), getNegotiation(), suggestDealFacts(), AIProvenance, DealFact, FactReviewAction (+30 more)

### Community 34 - "SyncAlly Implementation Plan Document"
Cohesion: 0.13
Nodes (16): SyncAlly Architecture Document, System Topology and Ownership Boundaries, Temporal Worker and Outbox Architecture, AI Provider Boundary Specification, AI Resilience and Retry Policy, AISuggestionProvider Contract, Acceptance Criteria Verification Matrix, SyncAlly Implementation Plan Document (+8 more)

### Community 35 - "PaymentProcessingTests"
Cohesion: 0.15
Nodes (6): process_payment_intent(), FakeInvoiceProvider, FakeProcessingRepository, PaymentProcessingTests, _request(), _work_item()

### Community 36 - "application/deal_cases.py"
Cohesion: 0.09
Nodes (29): add_case_evidence(), AddCaseEvidenceCommand, assess_deal_case_blockers(), DealCaseNotFound, DealCaseRepository, DealNotFound, list_deal_cases(), raise_deal_case() (+21 more)

### Community 37 - "worker.py"
Cohesion: 0.09
Nodes (16): _connect_with_retry(), main(), run_forever(), main(), run_forever(), is_permanent_rpc_error(), configure_logging(), log_operation() (+8 more)

### Community 38 - "ApprovalRoutingTestCase"
Cohesion: 0.09
Nodes (10): ApprovalRoutingPolicy, OrganizationId, UserId, routing_policy_to_domain(), SqlAlchemyApprovalRoutingPolicyRepository, ApprovalRoutingTestCase, FakeDealRepository, OrganizationDomainTests (+2 more)

### Community 39 - "Paymentstatuspanel & Paymentstatuspanel.Test"
Cohesion: 0.09
Nodes (31): authorizeDealPayment(), listDealPaymentMilestones(), listPaymentStatuses(), previewDealPayment(), PaymentIntentStatus, formatCountdown(), parseTimestamp(), describeStatus() (+23 more)

### Community 41 - "services"
Cohesion: 0.09
Nodes (29): build, depends_on, restart, context, dockerfile, migrate, temporal-namespace, build (+21 more)

### Community 42 - "api/deals.py"
Cohesion: 0.13
Nodes (31): add_evidence_deals_route(), _add_evidence_impl(), add_evidence_v1_route(), AddEvidenceRequest, CaseEvidenceResponse, CaseResponse, create_deal_route(), CreateDealRequest (+23 more)

### Community 43 - "InvariantViolation"
Cohesion: 0.11
Nodes (5): _normalized_text(), _require_decimal(), InvariantViolation, bounded_decimal(), BoundedDecimalTests

### Community 44 - "build_terms"
Cohesion: 0.19
Nodes (14): build_trade_terms_from_request(), PaymentObligationAllocation, PaymentTerm, ShipmentItemAllocation, ShipmentTerm, TradeLineItem, ProposedTerms, Money (+6 more)

### Community 46 - "add_organization_member"
Cohesion: 0.22
Nodes (5): add_organization_member(), AddOrganizationMemberRequest, create_organization(), CreateOrganizationRequest, OrganizationOnboardingTests

### Community 47 - "DealWorkflowTests"
Cohesion: 0.13
Nodes (5): DealWorkflow, DealWorkflowResult, DealWorkflowTests, DealWorkflowUnitTests, new_notification()

### Community 48 - "Test Organization Directory & Organizations"
Cohesion: 0.13
Nodes (4): _case_insensitive_prefix(), _escape_like(), value(), OrganizationDirectoryTests

### Community 49 - "create_deal"
Cohesion: 0.16
Nodes (5): _both_organizations_active(), create_deal(), CreateDealCommand, DealUseCaseTests, FakeDealRepository

### Community 50 - "SqlAlchemyDealRepository"
Cohesion: 0.18
Nodes (3): _active_participation(), SqlAlchemyDealRepository, DealRepositoryTests

### Community 51 - "auth.py"
Cohesion: 0.13
Nodes (15): _as_utc(), create_refresh_token(), current_user(), CurrentUserResponse, _decode_token(), _development_actor(), development_login(), _encode_access_token() (+7 more)

### Community 52 - "PaymentOutboxWorkerTests"
Cohesion: 0.10
Nodes (5): FakeRepository, NoCallProvider, PaymentOutboxWorkerTests, resolve(), _utc()

### Community 53 - "api/payments.py"
Cohesion: 0.09
Nodes (21): authorize_payment_route(), AuthorizePaymentRequest, AuthorizePaymentResponse, _check_milestone_delivery_confirmed(), get_payment_status_repository(), list_payment_milestones_route(), list_payment_statuses_route(), MilestoneAllocationResponse (+13 more)

### Community 54 - "repositories/agreements.py"
Cohesion: 0.07
Nodes (21): DuplicateApproval, NotEligibleApprover, OutOfSequenceApproval, record_routing_decision(), RecordRoutingDecisionCommand, RoutingDecisionOutcome, ApprovalDecision, ApprovalRoutingMode (+13 more)

### Community 55 - "NegotiationReview.tsx"
Cohesion: 0.05
Nodes (49): getDeal(), getOrganization(), negotiateDeal(), Deal, NegotiationView, AgreementReviewProps, DealCasesPanelProps, DealConstellation() (+41 more)

### Community 56 - "RemindersPanel.tsx"
Cohesion: 0.21
Nodes (14): listDealReminders(), suppressDealReminder(), syncDealReminders(), ReminderScope, ReminderStatus, formatUtc(), RemindersPanel(), scopeBadgeLabel() (+6 more)

### Community 57 - "_active_admin_membership"
Cohesion: 0.14
Nodes (14): close_marketplace_rfq(), create_marketplace_listing(), create_marketplace_rfq(), deactivate_marketplace_listing(), get_marketplace_listing(), get_marketplace_rfq(), MarketplaceListingRequest, MarketplaceListingResponse (+6 more)

### Community 58 - "CommercialDocumentDraftTests"
Cohesion: 0.14
Nodes (11): export_display_terms(), generate_commercial_document_draft(), generate_trade_pack(), InvalidTradePack, _json_bytes(), _shape(), _trade_pack_html(), section() (+3 more)

### Community 59 - "Test Migration Lock & Env"
Cohesion: 0.12
Nodes (8): run_migrations_online(), serialize_migrations(), _make_postgres_connection(), _make_sqlite_connection(), MigrationLockTests, simulated_migration(), PostgresRealAdvisoryLockTests, worker()

### Community 61 - "01 Commercial Domain Model &"
Cohesion: 0.07
Nodes (19): AgreementVersion Aggregate, Append-Only AuditEvent Ledger, Commercial Constraint and Provenance, Deal Aggregate, Organization and Membership Entities, PaymentMilestone and Obligation, Proposal Aggregate and Terms Hash, Temporal Deal Workflow (+11 more)

### Community 62 - "create_counterparty_invitation"
Cohesion: 0.12
Nodes (7): create_counterparty_invitation(), _create_invitation_token(), CreateCounterpartyInvitationRequest, _decode_invitation_token(), OnboardingConcurrencyCases, OnboardingPostgresConcurrencyTests, OnboardingSQLiteConcurrencyTests

### Community 63 - "Test Deal Routes & Identity"
Cohesion: 0.20
Nodes (3): require_system_admin(), ActorContext, DealRouteTests

### Community 64 - "api/negotiation.py"
Cohesion: 0.13
Nodes (12): BaseRequest, CandidateRequest, EvidenceRequest, HistoryResponse, NegotiationRequest, NegotiationResponse, NegotiationResult, ProposalResponse (+4 more)

### Community 65 - "Compose.Yaml (volumes)"
Cohesion: 0.09
Nodes (22): POSTGRES_DB, POSTGRES_PASSWORD, POSTGRES_USER, interval, retries, test, timeout, environment (+14 more)

### Community 66 - "Architectural & Implementation Plan: Step 08 Cancel Disputes (F8)"
Cohesion: 0.10
Nodes (19): 1. Executive Summary & Existing vs. Required Behavior, 2. Domain Entities & Value Objects, 3. Deal Aggregate Coordination, 4. Persistence Models & Alembic Migration 0025, 5. Application Layer: Use Cases & Operational Impact Assessment, 6. HTTP API Layer, 7. Frontend Integration, 9. Verification & Test Plan (+11 more)

### Community 67 - "CreateDealPage.tsx"
Cohesion: 0.07
Nodes (29): createCounterpartyInvitation(), createDeal(), getMarketplaceListing(), getMarketplaceRFQ(), listDeals(), ViewerRole, counterpartyInvitePreview(), counterpartyInviteUrl() (+21 more)

### Community 68 - "CommitAgreementCommand"
Cohesion: 0.07
Nodes (11): CommitAgreementCommand, propose_amendment(), ProposeAmendmentCommand, RecordApprovalCommand, commit_agreement_in_transaction(), propose_amendment_in_transaction(), record_approval_in_transaction(), AgreementCommitTests (+3 more)

### Community 69 - "PaymentWorkItem"
Cohesion: 0.14
Nodes (4): PaymentInvoiceLookup, PaymentInvoiceRequest, PaymentWorkItem, OfflineDemoInvoiceProvider

### Community 70 - "simulate_payment"
Cohesion: 0.15
Nodes (7): DevResetResponse, DevRoleSwitchRequest, _require_demo_admin(), reset_demo(), simulate_payment(), SimulatePaymentRequest, switch_role()

### Community 71 - "TradeTerms"
Cohesion: 0.12
Nodes (5): compare_agreement_terms(), _money(), _parse_money(), TradeTerms, with_timing()

### Community 72 - "PersistentDemoSeedTests"
Cohesion: 0.10
Nodes (7): fixture_id(), initialize_offline_database(), main(), PersistentDemoSeedTests, exercise_api(), start_deal_workflow(), dispatch()

### Community 73 - "AgreementReview.tsx"
Cohesion: 0.07
Nodes (54): acceptInvitation(), apiBaseUrl(), ApiError, apiRequest(), commitAgreementVersion(), compareAgreementVersions(), createAgreementFromReviewedTerms(), getAgreementHistory() (+46 more)

### Community 74 - "refresh_access_token"
Cohesion: 0.08
Nodes (5): _hash_refresh_token(), refresh_access_token(), RefreshRequest, RefreshToken, User

### Community 75 - "SqlAlchemyReminderRepository"
Cohesion: 0.16
Nodes (3): DealReminderModel, SqlAlchemyReminderRepository, RemindersRoutesTests

### Community 76 - "repositories/agreements.py"
Cohesion: 0.07
Nodes (19): AgreementRepository, assess_amendment_impact(), AuditEventDraft, AuditRepository, commit_agreement(), create_reviewed_agreement_draft(), CreateReviewedAgreementDraftCommand, get_current_agreement() (+11 more)

### Community 77 - "IdentityBoundaryTests"
Cohesion: 0.11
Nodes (4): _is_loopback_temporal_address(), _is_weak_jwt_secret(), Settings, IdentityBoundaryTests

### Community 78 - "Optional AI Specification"
Cohesion: 0.29
Nodes (4): PayPal Sandbox Lifecycle Verification, Optional AI Specification, Human-Grounded AI Suggestion Evaluation, No AI Approval or Legal Authority Boundary

### Community 79 - "Tsconfig (tsconfig.json)"
Cohesion: 0.11
Nodes (17): compilerOptions, allowImportingTsExtensions, jsx, lib, module, moduleDetection, moduleResolution, noEmit (+9 more)

### Community 81 - "NegotiationPostgresRaceTests"
Cohesion: 0.08
Nodes (8): create_database_engine(), CounterpartyOnboardingMigrationTests, DemoFixtureMigrationTests, NegotiationPostgresRaceTests, run(), failing(), succeed(), NegotiationSqliteRaceTests

### Community 82 - "authorize_payment_intent"
Cohesion: 0.19
Nodes (4): authorize_payment_intent(), PaymentIntentRepository, SellerMembershipRepository, UnauthorizedPaymentAuthorization

### Community 83 - "uuid"
Cohesion: 0.08
Nodes (7): CommunicationMigrationTests, MessageIdempotencyMigrationTests, FulfillmentShippingMigrationTests, InvitingPartyMigrationTests, OrganizationIndexMigrationTests, OutboxDispatchMigrationTests, PaymentCreateStartedMigrationTests

### Community 84 - "SafeOperationsTests"
Cohesion: 0.15
Nodes (6): WorkflowStartError, WorkflowStartPermanentError, captured_output(), SafeOperationsTests, exercise(), failed_db()

### Community 85 - "environment"
Cohesion: 0.28
Nodes (28): environment, AI_PROVIDER, APP_ENV, DATABASE_URL, DEBUG, DEFAULT_NAMESPACE, GMAIL_APP_PASSWORD, GMAIL_FROM_EMAIL (+20 more)

### Community 87 - "Deploying SyncAlly's Temporal workers on AWS"
Cohesion: 0.09
Nodes (21): AWS layout, Build and deploy the worker services, Configure Temporal Cloud, Current deployment placement, Database and security boundaries, Deploying SyncAlly's Temporal workers on AWS, If Temporal itself must run in AWS, Provisioned so far (+13 more)

### Community 88 - "Collections API and UI Specification F10b"
Cohesion: 0.14
Nodes (12): Append-Only Fulfillment Observations and Confirmations, Canonical Hash and Legacy Export Preservation, Collection Schema Specification F10a, Versioned Item Shipment Payment Collections, Collections API and UI Specification F10b, Deterministic Version-Aware Export Downloads, Structured Collection Authoring and Review, Milestone Payment Intent State Machine (+4 more)

### Community 89 - "ApiError"
Cohesion: 0.09
Nodes (20): addOrganizationMember(), getOrganizationProfile(), updateOrganizationProfile(), ContactVisibility, Organization, OrganizationContact, MarketplacePageProps, Props (+12 more)

### Community 92 - "maybe_complete_deal"
Cohesion: 0.33
Nodes (4): delivery_obligation_fulfilled(), _event_total(), maybe_complete_deal(), payments_reconciled()

### Community 94 - "InvalidTransition"
Cohesion: 0.17
Nodes (3): Proposal, PaymentIntent, InvalidTransition

### Community 95 - "lock_demo_deal_creation"
Cohesion: 0.19
Nodes (8): _acquire_lock(), _is_demo_deal(), lock_demo_deal_creation(), lock_demo_payment_processing(), lock_demo_reset(), lock_outbox_dispatch(), DemoLifecycleLockTests, _postgres_session()

### Community 96 - "application/conversations.py"
Cohesion: 0.05
Nodes (25): add_message(), AddMessageCommand, can_view_constraint(), can_view_message(), CommunicationRepository, ConstraintRepository, correct_constraint(), create_manual_constraint() (+17 more)

### Community 98 - "Master Execution Contract"
Cohesion: 0.11
Nodes (30): Execution Acceptance Gates, Master Execution Contract, Safe Windows PowerShell Runner, Four-Dimension Profile Collections, Private Contact Channels, Profiles Specification F14, Fresh Authorization Enforcement, Permissions Specification F15a (+22 more)

### Community 99 - "0005 Conversation Party Unique (Enforce"
Cohesion: 0.36
Nodes (5): _create_party_unique_constraint(), _deduplicate_conversations(), downgrade(), _drop_party_unique_constraint(), upgrade()

### Community 101 - "Safe Operations and Recovery Guide"
Cohesion: 0.18
Nodes (16): PayPal Sandbox Invoicing and Reconciliation Flow, Backend README Document, F11a Explicit Payment Modes, F12 Committed Trade Packs, F1a Curated Repeatable Demo Fixture, F2 AI Configuration and Provider Boundary, F4 Invitations and Private Pending Deals, F5 Persisted Human Negotiation (+8 more)

### Community 102 - "temporal-namespace"
Cohesion: 0.09
Nodes (22): condition, aliases, api, temporal, APP_DOMAIN, TEMPORAL_DOMAIN, default, temporal-namespace (+14 more)

### Community 103 - "api/reminders.py"
Cohesion: 0.21
Nodes (9): get_deal_reminders(), ReminderResponse, _resolve_actor_deal_org(), suppress_reminder(), sync_reminders(), _to_response(), trigger_dispatch(), list_deal_reminders() (+1 more)

### Community 104 - "ProposedTerms"
Cohesion: 0.07
Nodes (20): AIConfigurationError, AIPermanentError, AIProviderError, AITransientError, FactExtractionRequest, parse_extracted_facts(), parse_proposed_terms(), ProposalDraftRequest (+12 more)

### Community 106 - "x-app-environment"
Cohesion: 0.09
Nodes (22): x-app-environment, AI_PROVIDER, APP_ENV, DATABASE_URL, DEBUG, GMAIL_APP_PASSWORD, GMAIL_FROM_EMAIL, GMAIL_SMTP_USERNAME (+14 more)

### Community 108 - "environment"
Cohesion: 0.12
Nodes (20): environment, BIND_ON_IP, DB, DB_PORT, DBNAME, POSTGRES_DB, POSTGRES_PASSWORD, POSTGRES_PWD (+12 more)

### Community 110 - "create_worker"
Cohesion: 0.20
Nodes (3): create_worker(), workflow_activities(), WorkflowWorkerTests

### Community 111 - "OnboardingWizard.tsx"
Cohesion: 0.15
Nodes (14): createOrganization(), COUNTRY_NAMES, CountryOption, describeError(), isAmbiguousCreateFailure(), OnboardingWizard(), findExistingOrganization(), handleSubmit() (+6 more)

### Community 113 - "NegotiationCommand"
Cohesion: 0.42
Nodes (3): negotiate(), NegotiationCommand, NegotiationRepository

### Community 114 - "healthcheck"
Cohesion: 0.16
Nodes (18): healthcheck, healthcheck, image, restart, volumes, temporal-schema, interval, retries (+10 more)

### Community 116 - "DealWorkflowInput"
Cohesion: 0.13
Nodes (4): RefreshDealStateActivity, _workflow_input_value(), RefreshDealStateActivityTests, factory()

### Community 118 - "canonical_decimal"
Cohesion: 0.18
Nodes (4): _display(), _render(), _decimal(), canonical_decimal()

### Community 119 - "Final Gates and Truthful Completion Specification"
Cohesion: 0.20
Nodes (9): Evidence-Free Projection and Safety Bounds, F12 Trade Pack Handoff Document, Trade Pack Export Contract, Browser Verification Specification, ZIP HTML and Print Export Verification, Two-Party Isolated Browser Testing, Final Gates and Truthful Completion Specification, Full Gate Verification Suite (+1 more)

### Community 120 - "Skill (Repo Idea Thinker Skill)"
Cohesion: 0.50
Nodes (3): Repo Idea Thinker Skill, Repository-Grounded Ideation Discipline, Idea Quality Standards and Lightweight Validation

### Community 122 - "SqlAlchemyPaymentIntentRepository"
Cohesion: 0.10
Nodes (8): DuplicateActivePaymentIntent, IdempotencyKeyReused, PaymentIntentAuthorizationOutcome, PaymentModeChanged, PaymentStatusRecord, ExtendedPaymentStatusRecord, SqlAlchemyPaymentIntentRepository, _utc_timestamp()

### Community 134 - "temporal-schema"
Cohesion: 0.15
Nodes (13): condition, db, command, depends_on, restart, migrate, temporal-schema, command (+5 more)

### Community 139 - "Customer journey: buyer and seller"
Cohesion: 0.29
Nodes (6): Customer contract, Customer journey: buyer and seller, Evidence and limits, Implementation constraints discovered during task mapping, Outcome, Task graph

### Community 140 - "devDependencies"
Cohesion: 0.15
Nodes (13): devDependencies, eslint@^10.13.0, @testing-library/react@^16.3.3, @types/react@^19.0.0, @types/react-dom@^19.0.0, @types/three@^0.186.0, typescript@^6.0.0, vitest@^5.0.5 (+5 more)

### Community 141 - "sqlalchemy"
Cohesion: 0.03
Nodes (50): upgrade(), uuid_column(), upgrade(), upgrade(), upgrade(), upgrade(), downgrade(), upgrade() (+42 more)

### Community 142 - "scaling"
Cohesion: 0.10
Nodes (20): build, build_context_directory, max_cpu, max_memory, min_cpu, min_memory, system, dockerfile_path (+12 more)

### Community 143 - "Deal"
Cohesion: 0.08
Nodes (9): Deal, DealStatus, _to_domain(), DealAuthorizationTests, _domain_deal(), FakeDealRepository, _domain_deal(), 1. Executive Summary & Change Stack Digest (+1 more)

### Community 144 - "SyncAlly deployment"
Cohesion: 0.20
Nodes (9): 1. Provision the VM and DNS, 2. Configure secrets, 3. Start the stack, Configure the Hostless App, Connect the Render frontend, Current $0 demo: Render + Hostless, OCI single-VM deployment, SyncAlly deployment (+1 more)

### Community 145 - "comprehensive_verification.mjs"
Cohesion: 0.23
Nodes (6): @playwright/test@^1.65.0, pngjs@^7.0.0, unzipper@^0.12.5, @playwright/test, pngjs, unzipper

### Community 146 - "DealDetailPage.test.tsx"
Cohesion: 0.05
Nodes (51): addCaseEvidence(), getDealFulfillment(), listDealCases(), raiseDealCase(), recordDealFulfillment(), respondToDealCase(), BilateralDecision, CaseStatus (+43 more)

### Community 147 - "ProposalComparison.tsx"
Cohesion: 0.19
Nodes (19): allocations(), Change, compareEntries(), comparisonChanges(), entries(), Entry, entrySignature(), Field (+11 more)

### Community 148 - "api/fulfillment.py"
Cohesion: 0.05
Nodes (32): _event_response(), FulfillmentEventResponse, FulfillmentSnapshotResponse, get_fulfillment_repository(), _raise_fulfillment_error(), read_fulfillment_route(), _record_fulfillment_event(), record_fulfillment_route() (+24 more)

### Community 149 - "DealReminder"
Cohesion: 0.17
Nodes (3): DealReminder, ensure_utc(), ReminderDomainTests

### Community 150 - "build_terms"
Cohesion: 0.24
Nodes (7): NegotiationSession, NegotiationSubmissionOutcome, ProposalStatus, NegotiationSessionId, build_proposal(), HumanNegotiationTests, NegotiationTests

### Community 151 - "volumes"
Cohesion: 0.50
Nodes (4): volumes, caddy_config, caddy_data, postgres_data

### Community 152 - "MASTER BOARD"
Cohesion: 0.18
Nodes (10): ARBITRATION LOG, CAPABILITY MATRIX, CONSTRAINTS, CONTRACTS, DIRECTIVES, MASTER BOARD, OBJECTIVE, REQUIREMENTS (+2 more)

### Community 153 - "setup-temporal-postgres.sh"
Cohesion: 0.67
Nodes (3): PGPASSWORD, setup-temporal-postgres.sh script, update_database_schema()

### Community 156 - "simulate_deal_flow.py"
Cohesion: 0.11
Nodes (9): _clear_fixture(), _delete_scoped(), DemoCollisionError, _normalized_index_predicate(), _preflight(), seed_demo_data(), _is_live_backend_healthy(), main() (+1 more)

### Community 162 - "amendment.py"
Cohesion: 0.13
Nodes (10): AmendmentAlreadyCommitted, AmendmentConflict, AmendmentError, AmendmentImpact, AmendmentImpactBlocked, assess_amendment_impact(), FulfillmentObligationImpact, PaymentMilestoneImpact (+2 more)

### Community 163 - "ConversationUseCaseTests"
Cohesion: 0.20
Nodes (5): MessageIdempotencyPostgresTests, _find_conversation(), _find_keyed_message(), rendezvous(), wait_for()

### Community 164 - "repositories/reminders.py"
Cohesion: 0.20
Nodes (6): build_deduplication_key(), ReminderChannel, ReminderScope, ReminderStatus, SuppressionReason, _to_domain()

### Community 165 - "DealWorkflowInput"
Cohesion: 0.12
Nodes (7): DealWorkflowInput, DealWorkflowStatus, _require_uuid(), new_workflow_input(), RefreshActivity, RefreshCall, WorkflowWorkerIntegrationTests

### Community 166 - "STATE LOG: developer"
Cohesion: 0.25
Nodes (7): BLOCKERS & ESCALATIONS, CURRENT_STATE, ENVIRONMENT_SNAPSHOT (ENV), GOAL & ACCEPTANCE CRITERIA, IDENTITY & ROLE, IMPLEMENTATION_LEDGER, STATE LOG: developer

### Community 168 - "0004_communication_sources_and_scope_indexes.py"
Cohesion: 0.60
Nodes (4): _create_scope_index(), downgrade(), _drop_scope_index(), upgrade()

### Community 171 - "STATE LOG: planner"
Cohesion: 0.25
Nodes (7): BLOCKERS & ESCALATIONS, CURRENT_STATE, ENVIRONMENT_SNAPSHOT (ENV), GOAL & ACCEPTANCE CRITERIA, IDENTITY & ROLE, IMPLEMENTATION_LEDGER, STATE LOG: planner

### Community 173 - "STATE LOG: reviewer"
Cohesion: 0.25
Nodes (7): BLOCKERS & ESCALATIONS, CURRENT_STATE, ENVIRONMENT_SNAPSHOT (ENV), GOAL & ACCEPTANCE CRITERIA, IDENTITY & ROLE, IMPLEMENTATION_LEDGER, STATE LOG: reviewer

### Community 174 - "CONTRACT: cancel-disputes-contract v1   status: FROZEN"
Cohesion: 0.29
Nodes (6): Change rule, CONTRACT: cancel-disputes-contract v1   status: FROZEN, Domain / Models, Endpoints (under /api/v1/deals/{deal_id}/cases), Errors and edge cases, Interface

### Community 175 - "organization.py"
Cohesion: 0.06
Nodes (23): ContactVisibility, _normalize_string(), Organization, OrganizationCapability, OrganizationContact, OrganizationMember, OrganizationMemberRole, OrganizationMemberStatus (+15 more)

### Community 176 - "eslint.config.js"
Cohesion: 0.18
Nodes (10): @eslint/js@^10.0.1, eslint-plugin-react-hooks@^7.1.1, eslint-plugin-react-refresh@^0.4.20, globals@^17.13.0, typescript-eslint@^8.71.2, @eslint/js, eslint-plugin-react-hooks, eslint-plugin-react-refresh (+2 more)

### Community 177 - "_register_shutdown_handlers"
Cohesion: 0.27
Nodes (4): _register_shutdown_handlers(), _remove_shutdown_handlers(), _request_shutdown(), WorkerShutdownSignalTests

### Community 178 - "get_commercial_document_draft_route"
Cohesion: 0.24
Nodes (3): CommercialDocumentDraftResponse, get_commercial_document_draft_route(), get_trade_pack_route()

### Community 179 - "Constraint"
Cohesion: 0.07
Nodes (4): Constraint, FakeCommunicationRepository, FakeCommunicationRepository, FakeCommunicationRepository

### Community 180 - "scripts"
Cohesion: 0.29
Nodes (7): scripts, build, dev, lint, lint:check, preview, test

### Community 181 - "FakePayPalInvoiceProvider"
Cohesion: 0.21
Nodes (4): PaymentInvoiceReconciliation, FakePayPalInvoiceProvider, get_invoice_reconciliation(), get_invoice_reconciliation()

### Community 183 - "vite.config.ts"
Cohesion: 0.33
Nodes (5): vite@^8.1.0, @vitejs/plugin-react@^6.1.2, API_PATH_PREFIXES, vite, @vitejs/plugin-react

### Community 184 - "VerifiedProviderPaymentState"
Cohesion: 0.40
Nodes (3): VerifiedProviderPaymentState, transition(), PaymentReconciliationTests

### Community 186 - "login"
Cohesion: 0.14
Nodes (8): bootstrap_system_admin(), CredentialsRequest, login(), _accept_invitation(), hash_password(), verify_password(), fail(), scalar()

### Community 188 - "main.py"
Cohesion: 0.05
Nodes (11): _require_dev_environment(), database_health(), health(), OperationalFastAPI, list_platform_organizations(), _organization_summary(), OrganizationStatusUpdate, update_platform_organization_status() (+3 more)

### Community 189 - "SyncAlly: Confirmed Bugs and Feature Roadmap"
Cohesion: 0.25
Nodes (7): Confirmed bugs, Core product capabilities, Feature roadmap, Hackathon-focused vertical slice, Scope and safeguards, Suggested sequencing, SyncAlly: Confirmed Bugs and Feature Roadmap

### Community 190 - "Code Review: Step 08 Cancel Disputes (F8) — Work Package RV1"
Cohesion: 0.22
Nodes (8): 1. Medium (P2) — Parallel Alembic Migration Heads Branching From 0024_amendments, 2. Reviewer's Guide, 3. Merge Gate, 4. Findings, 6. Empirical Verification Summary, 7. Review Verdict, Code Review: Step 08 Cancel Disputes (F8) — Work Package RV1, Control-flow diagram

### Community 193 - "_is_one_active_per_milestone_violation"
Cohesion: 0.43
Nodes (3): _is_idempotency_key_violation(), _is_one_active_per_milestone_violation(), _violated_constraint_name()

### Community 200 - "Frontend product review"
Cohesion: 0.50
Nodes (3): Findings and fixes, Frontend product review, Walkthrough coverage

### Community 202 - "DealWorkflowNotification"
Cohesion: 0.14
Nodes (5): DealWorkflowStarter, WorkflowStartOutcome, DealWorkflowNotification, TemporalDealWorkflowStarter, TemporalAdapterTests

## Knowledge Gaps
- **48 isolated node(s):** `syncally`, `PGPASSWORD`, `F1a Curated Repeatable Demo Fixture`, `Editorial Dark Theme Design System`, `ZIP HTML and Print Export Verification` (+43 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1767 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **59 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ActorContext` connect `Test Deal Routes & Identity` to `Conversations & Test Conversation Use`, `AISuggestionProviderTests`, `repositories/agreements.py`, `api/agreements.py`, `Test Conversation Routes (ConversationRouteTests)`, `OutboxEvent`, `Test Agreement Routes (AgreementRouteTests)`, `draft_proposal_from_context`, `Deal`, `OrganizationPermissionsTests`, `api/fulfillment.py`, `Simulate Deal Flow & Test`, `Test Organization Invitations & Organizations`, `DealId`, `api/payments.py`, `repositories/payment_processing.py`, `ConversationUseCaseTests`, `ApprovalRoutingTestCase`, `PaymentIntentRepositoryTests`, `DealCasesTests`, `api/deals.py`, `add_organization_member`, `organization.py`, `Test Organization Directory & Organizations`, `create_deal`, `get_commercial_document_draft_route`, `auth.py`, `api/payments.py`, `_active_admin_membership`, `login`, `CommercialDocumentDraftTests`, `main.py`, `create_counterparty_invitation`, `api/negotiation.py`, `._seed`, `CommitAgreementCommand`, `simulate_payment`, `get_optional_actor`, `SqlAlchemyReminderRepository`, `repositories/agreements.py`, `IdentityBoundaryTests`, `NegotiationRouteTests`, `application/conversations.py`, `api/reminders.py`, `.test_generates_draft_from_schema_2_committed_terms`, `ApprovalRoutingRouteTests`, `queue_simulated_reconciliation`, `AiContextSelectionTests`?**
  _High betweenness centrality (0.087) - this node is a cross-community bridge._
- **Are the 157 inferred relationships involving `ActorContext` (e.g. with `approve_agreement_route()` and `commit_agreement_route()`) actually correct?**
  _`ActorContext` has 157 INFERRED edges - model-reasoned connections that need verification._
- **What connects `syncally`, `PGPASSWORD`, `F1a Curated Repeatable Demo Fixture` to the rest of the system?**
  _48 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Conversations & Test Conversation Use` be split into smaller, more focused modules?**
  _Cohesion score 0.05750350631136045 - nodes in this community are weakly interconnected._
- **Why does `OrganizationId` connect `ApprovalRoutingTestCase` to `AIContractError`, `repositories/agreements.py`, `AISuggestionProviderTests`, `schedule_deal_reminders`, `repositories/agreements.py`, `api/agreements.py`, `Test Conversation Routes (ConversationRouteTests)`, `OutboxEvent`, `Test Agreement Routes (AgreementRouteTests)`, `Message`, `draft_proposal_from_context`, `Deal`, `NegotiationTests`, `OrganizationPermissionsTests`, `AgreementVersionId`, `DealReminder`, `build_terms`, `api/fulfillment.py`, `DealId`, `Test Outbox Dispatcher & Outbox`, `api/payments.py`, `repositories/payment_processing.py`, `repositories/negotiation.py`, `application/deal_cases.py`, `repositories/reminders.py`, `PaymentIntentRepositoryTests`, `DealCasesTests`, `build_terms`, `NegotiationMigrationTests`, `organization.py`, `create_deal`, `SqlAlchemyDealRepository`, `Constraint`, `repositories/agreements.py`, `VerifiedProviderPaymentState`, `CommercialDocumentDraftTests`, `create_counterparty_invitation`, `api/negotiation.py`, `._seed`, `CommitAgreementCommand`, `TradeTerms`, `repositories/agreements.py`, `NegotiationPostgresRaceTests`, `maybe_complete_deal`, `InvalidTransition`, `application/conversations.py`, `.test_generates_draft_from_schema_2_committed_terms`, `ApprovalRoutingRouteTests`, `AiContextSelectionTests`, `SqlAlchemyPaymentIntentRepository`?**
  _High betweenness centrality (0.063) - this node is a cross-community bridge._
- **Are the 74 inferred relationships involving `OrganizationId` (e.g. with `build_trade_terms_from_request()` and `create_reviewed_agreement_draft_route()`) actually correct?**
  _`OrganizationId` has 74 INFERRED edges - model-reasoned connections that need verification._
- **Should `AIContractError` be split into smaller, more focused modules?**
  _Cohesion score 0.07287784679089027 - nodes in this community are weakly interconnected._