# Graph Report - SyncAlly  (2026-11-08)

## Corpus Check
- 392 files · ~368,746 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 14 file(s) not represented in the graph (top: (none) 8, .example 2, .ini 1)

## Summary
- 6037 nodes · 19391 edges · 222 communities (159 shown, 63 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 2521 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `8580f8c4`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Conversations & Test Conversation Use
- AIContractError
- BaseModel
- application/deal_cases.py
- ConfiguredAIProvider
- schedule_deal_reminders
- repositories/negotiation.py
- PaymentNeedsAction
- GmailSMTPInvoiceNotifier
- api/agreements.py
- Test Conversation Routes (ConversationRouteTests)
- api/payments.py
- Test Agreement Routes (AgreementRouteTests)
- repositories/communications.py
- process_payment_intent
- AISuggestionProvider
- NegotiationTests
- Types & Client
- listOrganizations
- api/organizations.py
- OrganizationId
- Test Outbox Dispatcher & Outbox
- Simulate Deal Flow & Test
- Test Organization Invitations & Organizations
- CommunicationRepositoryTests
- package.json
- Organization
- Dealconversationreview & Dealconversationreview.Test
- Skill & Skill.Md
- identifiers.py
- App.test.tsx
- api/negotiation.py
- activities.py
- Aisuggestionreview & Suggestionpreview
- SyncAlly Implementation Plan Document
- PaymentProcessingTests
- application/deal_cases.py
- DealWorkflowNotification
- ApprovalRoutingTestCase
- Paymentstatuspanel & Paymentstatuspanel.Test
- PaymentIntentRepositoryTests
- services
- api/deals.py
- InvariantViolation
- OutboxEvent
- Test Dev Routes (DevRoutesTests)
- get_optional_actor
- DealWorkflow
- Test Organization Directory & Organizations
- create_deal
- SqlAlchemyDealRepository
- HealthRouteTests
- PaymentOutboxWorkerTests
- get_current_actor
- repositories/payment_processing.py
- AISuggestionProviderTests
- ._request
- _active_admin_membership
- CommercialDocumentDraftTests
- Test Migration Lock & Env
- Payment Processing & Test Payment
- 01 Commercial Domain Model &
- create_counterparty_invitation
- Test Deal Routes & Identity
- AIFallbackResilienceTests
- Compose.Yaml (volumes)
- Architectural & Implementation Plan: Step 08 Cancel Disputes (F8)
- apiRequest
- CommitAgreementCommand
- add_organization_member
- simulate_payment
- Money
- PersistentDemoSeedTests
- AgreementReview.tsx
- ProposedTerms
- SqlAlchemyReminderRepository
- repositories/agreements.py
- IdentityBoundaryTests
- Optional AI Specification
- Tsconfig (tsconfig.json)
- Test Paypal Webhooks (FakeWebhookVerifier)
- .add
- NormalizedRequirement
- OrganizationRepositoryTests
- SafeOperationsTests
- environment
- Main & Test Identity Boundary
- Deploying SyncAlly's Temporal workers on AWS
- Collections API and UI Specification F10b
- RefreshDealStateActivity
- OrganizationIndexPostgresMigrationTests
- Server-Enforced Capability Matrix
- Design Inspiration & Awwwards Research: SyncAlly
- NegotiationRouteTests
- DealWorkflowTests
- lock_demo_deal_creation
- PaymentNeedsAction
- DatabasePersistenceTests
- Master Execution Contract
- 0005 Conversation Party Unique (Enforce
- Main (Request)
- Safe Operations and Recovery Guide
- temporal-namespace
- api/reminders.py
- OrganizationContact
- review_constraint
- x-app-environment
- Test Payment Mode Migration (PaymentModeMigrationTests)
- environment
- RemindersPanel.tsx
- _connect_with_retry
- hash_password
- ApprovalRoutingRouteTests
- OpeningRequestNormalizationTests
- healthcheck
- Design Direction: SyncAlly (Trade Folio)
- NegotiationCommand
- AiContextSelectionTests
- Product Knowledge Brief: SyncAlly
- Final Gates and Truthful Completion Specification
- Skill (Repo Idea Thinker Skill)
- Vite Env.D (ImportMeta)
- temporal-schema
- PaymentReconciliationRepositoryTests
- Index (Frontend HTML Root Document)
- Pyproject (syncally)
- Customer journey: buyer and seller
- ConversationContractTests
- sqlalchemy
- scaling
- Deal
- SyncAlly deployment
- @playwright/test
- DealDetailPage.test.tsx
- ProposalComparison.tsx
- api/fulfillment.py
- application/reminders.py
- ConversationUseCaseTests
- volumes
- MASTER BOARD
- setup-temporal-postgres.sh
- FulfillmentMigrationTests
- DealsPage.tsx
- current_user
- record_paypal_webhook_event
- MigrationConfigTests
- CollectionSchemaMigrationTests
- create-temporal-namespace.sh
- postgres-init.sh
- amendment.py
- VerifiedProviderPaymentState
- WorkflowWorkerIntegrationTests
- application/conversations.py
- STATE LOG: developer
- Frontend Audit: SyncAlly Web Client
- platform.py
- User
- MilestonePaymentsMigrationTests
- STATE LOG: planner
- Code Review: Step 08 Cancel Disputes (F8) — Work Package RV1
- STATE LOG: reviewer
- CONTRACT: cancel-disputes-contract v1   status: FROZEN
- organization.py
- eslint.config.js
- api/documents.py
- NegotiationCommand
- Constraint
- scripts
- VerifiedProviderPaymentState
- hostless-start.sh
- vite.config.ts
- 0024_deal_display_name.py
- SqlAlchemyNegotiationRepository
- TEST_INFRA.md — E2E Testing Infrastructure & Specification
- SyncAlly: Confirmed Bugs and Feature Roadmap
- tokenize
- NegotiationMigrationTests
- create_database_engine
- database_health
- seed_demo_data
- AddMessageRequest
- TEST_READY.md — E2E Test Suite Readiness Declaration
- 0004_communication_sources_and_scope_indexes.py
- register_organization
- AIConfigurationError
- Frontend product review
- 0001_initial_schema.py
- .refresh_deal_state
- Proposal
- refresh_access_token
- deal_completion.py
- verify_password
- 0010_unique_provider_invoice_id.py
- 0012_message_idempotency.py
- 0025_system_admin.py
- OrganizationMemberDomainTests
- CommunicationMigrationTests
- OutboxDispatchMigrationTests

## God Nodes (most connected - your core abstractions)
1. `ActorContext` - 319 edges
2. `OrganizationId` - 241 edges
3. `InvariantViolation` - 150 edges
4. `UserId` - 139 edges
5. `Money` - 127 edges
6. `DealId` - 122 edges
7. `Deal` - 114 edges
8. `SqlAlchemyAgreementRepository` - 113 edges
9. `apiRequest()` - 88 edges
10. `TradeTerms` - 87 edges

## Surprising Connections (you probably didn't know these)
- `Tier 1: Feature Coverage (>=5 tests per feature)` --references--> `DealResponse`  [INFERRED]
  TEST_INFRA.md → backend/src/syncally/api/deals.py
- `Tier 1: Feature Coverage (>=5 per feature)` --references--> `DealResponse`  [INFERRED]
  TEST_READY.md → backend/src/syncally/api/deals.py
- `2. Oracles & Expected Output Derivation` --references--> `DemoAISuggestionProvider`  [INFERRED]
  TEST_INFRA.md → backend/src/syncally/infrastructure/ai/demo.py
- `1. Executive Summary & Change Stack Digest` --references--> `_resolve_deal_party_organization()`  [INFERRED]
  .orchestrator/reviews/RV1/review.md → backend/src/syncally/api/deals.py
- `5. Audit Checklist Verification` --references--> `_resolve_deal_party_organization()`  [INFERRED]
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

## Communities (222 total, 63 thin omitted)

### Community 0 - "Conversations & Test Conversation Use"
Cohesion: 0.07
Nodes (43): add_message_route(), AISuggestionRequest, clarify_fact_route(), confirm_fact_route(), ConstraintResponse, correct_fact_route(), CorrectFactRequest, create_fact_route() (+35 more)

### Community 1 - "AIContractError"
Cohesion: 0.11
Nodes (13): AIContractError, AIValidationClaim, _check_keys(), _decimal(), _required_string(), scope_extracted_facts(), ScopedFactCandidate, _validate_decimal() (+5 more)

### Community 2 - "BaseModel"
Cohesion: 0.09
Nodes (11): AcceptInvitationResponse, ApprovalRoutingPolicyRequest, ApprovalRoutingPolicyResponse, ContactPayload, ContactResponse, CounterpartyInvitationResponse, InvitationResponse, OrganizationDirectoryItem (+3 more)

### Community 3 - "application/deal_cases.py"
Cohesion: 0.14
Nodes (16): AddCaseEvidenceCommand, RaiseDealCaseCommand, RespondToDealCaseCommand, BilateralDecision, CaseError, CaseEvidence, CaseStatus, CaseType (+8 more)

### Community 4 - "ConfiguredAIProvider"
Cohesion: 0.09
Nodes (13): extract_facts_from_context(), ConfiguredAIProvider, AISuggestionProviderTests, respond(), respond(), respond(), respond(), respond() (+5 more)

### Community 5 - "schedule_deal_reminders"
Cohesion: 0.14
Nodes (8): dispatch_due_reminders(), _is_active_member(), schedule_deal_reminders(), AgreementRoutingDecision, Obligation, FulfillmentEvent, OrganizationApprovalRoutingPolicy, RemindersServiceTests

### Community 6 - "repositories/negotiation.py"
Cohesion: 0.08
Nodes (21): _create_fixture(), DemoIdentity, _password_for(), _seed_identities(), Approval, Base, Constraint, Conversation (+13 more)

### Community 7 - "PaymentNeedsAction"
Cohesion: 0.10
Nodes (8): PaymentOutcomeUnknown, _has_excess_currency_precision(), PayPalSandboxInvoiceProvider, _provider_error_code(), _provider_request_id(), _send_request(), PayPalSandboxAdapterTests, sender()

### Community 8 - "GmailSMTPInvoiceNotifier"
Cohesion: 0.12
Nodes (3): PaymentInvoiceNotice, _FakeSMTP, GmailSMTPInvoiceNotifierTests

### Community 9 - "api/agreements.py"
Cohesion: 0.05
Nodes (47): AgreementVersionResponse, AmendmentImpactResponse, ApprovalResponse, approve_agreement_route(), commit_agreement_route(), CommitAgreementRequest, compare_agreements_route(), create_agreement_draft_route() (+39 more)

### Community 10 - "Test Conversation Routes (ConversationRouteTests)"
Cohesion: 0.10
Nodes (3): ConversationRouteTests, respond(), send()

### Community 11 - "api/payments.py"
Cohesion: 0.04
Nodes (35): authorize_payment_route(), AuthorizePaymentRequest, AuthorizePaymentResponse, _check_milestone_delivery_confirmed(), get_payment_status_repository(), list_payment_milestones_route(), list_payment_statuses_route(), MilestoneAllocationResponse (+27 more)

### Community 13 - "repositories/communications.py"
Cohesion: 0.07
Nodes (13): can_view_message(), message_fingerprint(), NotificationKind, Conversation, Message, CommunicationScopeError, _conversation_to_domain(), _is_unique_violation() (+5 more)

### Community 14 - "process_payment_intent"
Cohesion: 0.08
Nodes (14): PaymentInvoiceNotifier, PaymentInvoiceProvider, PaymentProcessingRepository, process_payment_intent(), reconcile_payment_intent(), _request_id_retry_window_expired(), require_payment_provider(), claim_next_payment_event() (+6 more)

### Community 15 - "AISuggestionProvider"
Cohesion: 0.08
Nodes (22): AISuggestionProvider, draft_proposal(), draft_proposal_from_context(), extract_facts(), fact_suggestion_guidance(), FactExtractionResult, _list_all_constraints_for_owner(), missing_trade_fields() (+14 more)

### Community 16 - "NegotiationTests"
Cohesion: 0.20
Nodes (4): EvidenceReference, ProposalBase, negotiate_in_transaction(), NegotiationTests

### Community 17 - "Types & Client"
Cohesion: 0.04
Nodes (91): describeDetail(), getDealMessageExistence(), isAbortError(), isRecord(), listPlatformOrganizations(), readErrorDetail(), updatePlatformOrganizationStatus(), AddCaseEvidenceInput (+83 more)

### Community 18 - "listOrganizations"
Cohesion: 0.05
Nodes (72): dependencies, react@^19.3.0, react-dom@^19.3.0, three@^0.186.1, getCurrentUser(), listOrganizations(), login(), registerOrganization() (+64 more)

### Community 19 - "api/organizations.py"
Cohesion: 0.06
Nodes (24): _accept_invitation(), _active_admin_membership(), _case_insensitive_prefix(), _compute_effective_capabilities(), _create_invitation_token(), _deal_awaiting_counterparty(), delete_approval_routing_policy_route(), _escape_like() (+16 more)

### Community 20 - "OrganizationId"
Cohesion: 0.10
Nodes (12): PaymentMilestone, AgreementVersionId, DealId, OrganizationId, PaymentMilestoneId, _restore_domain_intent(), FakeAgreementRepository, MilestoneDomainValidationTests (+4 more)

### Community 21 - "Test Outbox Dispatcher & Outbox"
Cohesion: 0.09
Nodes (14): build_deal_workflow_id(), dispatch_outbox_event(), OutboxDispatchResult, PendingOutboxEvent, WorkflowStartTransientError, apply_dispatch_result(), claim_next_pending_event(), _claim_statement() (+6 more)

### Community 22 - "Simulate Deal Flow & Test"
Cohesion: 0.05
Nodes (15): _build_in_process_client(), dispatch_payment(), mark_fixture(), session_factory(), ci_deal_flow_hook(), DealFlowContext, DealFlowSimulator, _is_live_backend_healthy() (+7 more)

### Community 23 - "Test Organization Invitations & Organizations"
Cohesion: 0.15
Nodes (6): accept_invitation(), AcceptInvitationRequest, create_organization_invitation(), CreateInvitationRequest, _decode_invitation_token(), OrganizationInvitationTests

### Community 24 - "CommunicationRepositoryTests"
Cohesion: 0.12
Nodes (6): ConstraintId, ConversationId, MessageId, constraint(), message(), CommunicationRepositoryTests

### Community 25 - "package.json"
Cohesion: 0.10
Nodes (25): devDependencies, eslint@^10.13.0, happy-dom@^21.0.3, @testing-library/dom@^10.4.1, @testing-library/jest-dom@^7.0.1, @testing-library/react@^16.3.3, @types/react@^19.0.0, @types/react-dom@^19.0.0 (+17 more)

### Community 26 - "Organization"
Cohesion: 0.05
Nodes (48): addOrganizationMember(), deleteApprovalRoutingPolicy(), getApprovalRoutingPolicy(), getOrganizationProfile(), listOrganizationMembers(), putApprovalRoutingPolicy(), revokeOrganizationMember(), updateMemberPermissions() (+40 more)

### Community 27 - "Dealconversationreview & Dealconversationreview.Test"
Cohesion: 0.06
Nodes (48): createDealMessage(), importDealThread(), listDealFacts(), listDealMessages(), previewDealThreadImport(), reviewDealFact(), updateFactVisibility(), CreateDealPageProps (+40 more)

### Community 28 - "Skill & Skill.Md"
Cohesion: 0.04
Nodes (43): API and Database Engineer Skill, API Design and Contract Semantics, Data Integrity and Invariant Enforcement, Query Performance and Projection Optimization, Schema Migration and Backward Compatibility, Transaction Boundaries and Atomicity, Archify Diagrammer Skill, Archify CLI Global Tool (+35 more)

### Community 29 - "identifiers.py"
Cohesion: 0.06
Nodes (16): PaymentInvoiceLineItem, IdempotencyKeyReused, PaymentIntentCommandMismatch, PaymentMilestoneIneligible, PaymentMilestoneNotFound, PaymentStatusRecord, PaymentTriggerPolicyUnapproved, _decimal() (+8 more)

### Community 30 - "App.test.tsx"
Cohesion: 0.04
Nodes (54): ApiError, createOrganization(), getCommercialDocumentDraft(), getTradePack(), TradePackFormat, AgreementVersion, mockedApiRequest, mockedCreateCounterpartyInvitation (+46 more)

### Community 31 - "api/negotiation.py"
Cohesion: 0.13
Nodes (12): BaseRequest, CandidateRequest, EvidenceRequest, HistoryResponse, NegotiationRequest, NegotiationResponse, NegotiationResult, ProposalResponse (+4 more)

### Community 32 - "activities.py"
Cohesion: 0.08
Nodes (6): DealWorkflowState, load_deal_workflow_state(), parse_workflow_uuid(), WorkflowAgreementRepository, WorkflowDealNotFound, WorkflowDealRepository

### Community 33 - "Aisuggestionreview & Suggestionpreview"
Cohesion: 0.06
Nodes (61): correctDealFact(), createDealFact(), draftDealProposal(), getNegotiation(), negotiateDeal(), suggestDealFacts(), AIProvenance, DealFact (+53 more)

### Community 34 - "SyncAlly Implementation Plan Document"
Cohesion: 0.13
Nodes (16): SyncAlly Architecture Document, System Topology and Ownership Boundaries, Temporal Worker and Outbox Architecture, AI Provider Boundary Specification, AI Resilience and Retry Policy, AISuggestionProvider Contract, Acceptance Criteria Verification Matrix, SyncAlly Implementation Plan Document (+8 more)

### Community 35 - "PaymentProcessingTests"
Cohesion: 0.12
Nodes (6): payment_invoice_number(), FakeInvoiceProvider, FakeProcessingRepository, PaymentProcessingTests, _request(), _work_item()

### Community 36 - "application/deal_cases.py"
Cohesion: 0.13
Nodes (12): add_case_evidence(), assess_deal_case_blockers(), DealCaseRepository, DealNotFound, list_deal_cases(), raise_deal_case(), respond_to_deal_case(), CaseUnauthorizedError (+4 more)

### Community 37 - "DealWorkflowNotification"
Cohesion: 0.11
Nodes (7): DealWorkflowStarter, WorkflowStartError, WorkflowStartOutcome, WorkflowStartPermanentError, DealWorkflowNotification, TemporalDealWorkflowStarter, TemporalAdapterTests

### Community 38 - "ApprovalRoutingTestCase"
Cohesion: 0.15
Nodes (6): ApprovalRoutingMode, ApprovalRoutingPolicy, UserId, routing_policy_to_domain(), SqlAlchemyApprovalRoutingPolicyRepository, ApprovalRoutingTestCase

### Community 39 - "Paymentstatuspanel & Paymentstatuspanel.Test"
Cohesion: 0.09
Nodes (31): authorizeDealPayment(), listDealPaymentMilestones(), listPaymentStatuses(), previewDealPayment(), PaymentIntentStatus, formatCountdown(), parseTimestamp(), describeStatus() (+23 more)

### Community 40 - "PaymentIntentRepositoryTests"
Cohesion: 0.14
Nodes (3): queue_simulated_reconciliation(), authorize_payment_intent_in_transaction(), PaymentIntentRepositoryTests

### Community 41 - "services"
Cohesion: 0.09
Nodes (29): build, depends_on, restart, context, dockerfile, migrate, temporal-namespace, build (+21 more)

### Community 42 - "api/deals.py"
Cohesion: 0.12
Nodes (31): add_evidence_deals_route(), _add_evidence_impl(), add_evidence_v1_route(), AddEvidenceRequest, AnalyzeOpeningRequestRequest, CaseEvidenceResponse, CaseResponse, create_deal_route() (+23 more)

### Community 43 - "InvariantViolation"
Cohesion: 0.12
Nodes (5): _normalized_text(), _require_decimal(), InvariantViolation, bounded_decimal(), BoundedDecimalTests

### Community 44 - "OutboxEvent"
Cohesion: 0.10
Nodes (4): PaymentStatusResponse, OutboxEvent, dispatch(), PaymentStatusExtendedModelTests

### Community 47 - "DealWorkflow"
Cohesion: 0.17
Nodes (3): DealWorkflow, DealWorkflowUnitTests, run()

### Community 49 - "create_deal"
Cohesion: 0.17
Nodes (4): create_deal(), CreateDealCommand, DealUseCaseTests, FakeDealRepository

### Community 52 - "PaymentOutboxWorkerTests"
Cohesion: 0.09
Nodes (6): PaymentRetryableError, FakeRepository, NoCallProvider, PaymentOutboxWorkerTests, resolve(), _utc()

### Community 53 - "get_current_actor"
Cohesion: 0.13
Nodes (7): _decode_token(), _development_actor(), development_login(), get_current_actor(), _unauthorized(), _require_demo_admin(), resolve_actor()

### Community 54 - "repositories/payment_processing.py"
Cohesion: 0.13
Nodes (12): _connect_with_retry(), main(), run_forever(), main(), run_forever(), dispatch_pending_outbox_events(), is_permanent_rpc_error(), configure_logging() (+4 more)

### Community 55 - "AISuggestionProviderTests"
Cohesion: 0.15
Nodes (3): DeterministicFakeAIProvider, extract_facts(), FakeWebhookVerifier

### Community 56 - "._request"
Cohesion: 0.05
Nodes (6): BaseOpeningRequestE2ETest, _is_route_available(), TestOpeningRequestE2ETier1FeatureCoverage, TestOpeningRequestE2ETier2BoundaryAndCorners, TestOpeningRequestE2ETier3CrossFeatureCombinations, TestOpeningRequestE2ETier4RealWorldScenarios

### Community 57 - "_active_admin_membership"
Cohesion: 0.12
Nodes (15): close_marketplace_rfq(), create_marketplace_listing(), create_marketplace_rfq(), deactivate_marketplace_listing(), get_marketplace_listing(), get_marketplace_rfq(), MarketplaceListingRequest, MarketplaceListingResponse (+7 more)

### Community 58 - "CommercialDocumentDraftTests"
Cohesion: 0.15
Nodes (10): export_display_terms(), generate_trade_pack(), InvalidTradePack, _json_bytes(), _shape(), _trade_pack_html(), section(), TradePack (+2 more)

### Community 59 - "Test Migration Lock & Env"
Cohesion: 0.10
Nodes (9): run_migrations_offline(), run_migrations_online(), serialize_migrations(), _make_postgres_connection(), _make_sqlite_connection(), MigrationLockTests, simulated_migration(), PostgresRealAdvisoryLockTests (+1 more)

### Community 60 - "Payment Processing & Test Payment"
Cohesion: 0.13
Nodes (5): require_simulation_scope(), simulation_state(), SqlAlchemyPaymentProcessingRepository, transition(), transition()

### Community 61 - "01 Commercial Domain Model &"
Cohesion: 0.07
Nodes (19): AgreementVersion Aggregate, Append-Only AuditEvent Ledger, Commercial Constraint and Provenance, Deal Aggregate, Organization and Membership Entities, PaymentMilestone and Obligation, Proposal Aggregate and Terms Hash, Temporal Deal Workflow (+11 more)

### Community 62 - "create_counterparty_invitation"
Cohesion: 0.17
Nodes (5): create_counterparty_invitation(), CreateCounterpartyInvitationRequest, OnboardingConcurrencyCases, OnboardingPostgresConcurrencyTests, OnboardingSQLiteConcurrencyTests

### Community 63 - "Test Deal Routes & Identity"
Cohesion: 0.20
Nodes (3): ActorContext, DealAuthorizationTests, DealRouteTests

### Community 64 - "AIFallbackResilienceTests"
Cohesion: 0.06
Nodes (7): AIProvenance, AIRetryPolicy, call_with_bounded_retry(), OpeningRequestNormalizationService, AIFallbackResilienceTests, mock_fallback(), mock_fallback()

### Community 65 - "Compose.Yaml (volumes)"
Cohesion: 0.09
Nodes (22): POSTGRES_DB, POSTGRES_PASSWORD, POSTGRES_USER, interval, retries, test, timeout, environment (+14 more)

### Community 66 - "Architectural & Implementation Plan: Step 08 Cancel Disputes (F8)"
Cohesion: 0.12
Nodes (16): 2. Domain Entities & Value Objects, 3. Deal Aggregate Coordination, 4. Persistence Models & Alembic Migration 0025, 5. Application Layer: Use Cases & Operational Impact Assessment, 6. HTTP API Layer, 7. Frontend Integration, 9. Verification & Test Plan, Architectural & Implementation Plan: Step 08 Cancel Disputes (F8) (+8 more)

### Community 67 - "apiRequest"
Cohesion: 0.08
Nodes (41): acceptInvitation(), analyzeOpeningRequest(), apiBaseUrl(), apiRequest(), closeMarketplaceRFQ(), createAgreementFromReviewedTerms(), createCounterpartyInvitation(), createDeal() (+33 more)

### Community 68 - "CommitAgreementCommand"
Cohesion: 0.11
Nodes (6): CommitAgreementCommand, ProposeAmendmentCommand, RecordApprovalCommand, propose_amendment_in_transaction(), AgreementCommitTests, AmendmentTests

### Community 69 - "add_organization_member"
Cohesion: 0.17
Nodes (6): add_organization_member(), AddOrganizationMemberRequest, create_organization(), CreateOrganizationRequest, _is_duplicate_membership_error(), OrganizationOnboardingTests

### Community 70 - "simulate_payment"
Cohesion: 0.17
Nodes (8): _issue_tokens(), TokenResponse, DevResetResponse, DevRoleSwitchRequest, reset_demo(), simulate_payment(), SimulatePaymentRequest, switch_role()

### Community 71 - "Money"
Cohesion: 0.11
Nodes (16): build_trade_terms_from_request(), _money(), _parse_money(), PaymentObligationAllocation, PaymentTerm, ShipmentItemAllocation, ShipmentTerm, TradeLineItem (+8 more)

### Community 72 - "PersistentDemoSeedTests"
Cohesion: 0.11
Nodes (4): fixture_id(), initialize_offline_database(), main(), PersistentDemoSeedTests

### Community 73 - "AgreementReview.tsx"
Cohesion: 0.08
Nodes (43): API_REQUEST_TIMEOUT_MS, commitAgreementVersion(), compareAgreementVersions(), getAgreementHistory(), getAgreementVersion(), getAmendmentImpact(), previewAmendmentImpact(), proposeAmendment() (+35 more)

### Community 74 - "ProposedTerms"
Cohesion: 0.07
Nodes (23): AIPermanentError, AIProviderError, AITransientError, FactExtractionRequest, parse_extracted_facts(), parse_proposed_terms(), ProposalDraftRequest, AiContext (+15 more)

### Community 76 - "repositories/agreements.py"
Cohesion: 0.03
Nodes (70): AgreementAccessDenied, AgreementAlreadyCommitted, AgreementNotFound, AgreementRepository, AgreementVersionConflict, AmbiguousAgreementOrganization, assess_amendment_impact(), AuditEventDraft (+62 more)

### Community 77 - "IdentityBoundaryTests"
Cohesion: 0.11
Nodes (4): _is_loopback_temporal_address(), _is_weak_jwt_secret(), Settings, IdentityBoundaryTests

### Community 78 - "Optional AI Specification"
Cohesion: 0.29
Nodes (4): PayPal Sandbox Lifecycle Verification, Optional AI Specification, Human-Grounded AI Suggestion Evaluation, No AI Approval or Legal Authority Boundary

### Community 79 - "Tsconfig (tsconfig.json)"
Cohesion: 0.11
Nodes (17): compilerOptions, allowImportingTsExtensions, jsx, lib, module, moduleDetection, moduleResolution, noEmit (+9 more)

### Community 81 - ".add"
Cohesion: 0.43
Nodes (3): _is_idempotency_key_violation(), _is_one_active_per_milestone_violation(), _violated_constraint_name()

### Community 82 - "NormalizedRequirement"
Cohesion: 0.09
Nodes (9): analyze_opening_request_route(), AnalyzeOpeningRequestResponse, normalize_opening_request(), OpeningRequestNormalizationResult, SellerSuggestionItem, SellerSuggestionService, NormalizedRequirement, BaseSellerSuggestionTest (+1 more)

### Community 83 - "OrganizationRepositoryTests"
Cohesion: 0.17
Nodes (4): Organization, _organization_to_domain(), SqlAlchemyOrganizationRepository, OrganizationRepositoryTests

### Community 84 - "SafeOperationsTests"
Cohesion: 0.13
Nodes (6): OperationalFastAPI, OperationalRequestMiddleware, captured_output(), SafeOperationsTests, exercise(), failed_db()

### Community 85 - "environment"
Cohesion: 0.28
Nodes (28): environment, AI_PROVIDER, APP_ENV, DATABASE_URL, DEBUG, DEFAULT_NAMESPACE, GMAIL_APP_PASSWORD, GMAIL_FROM_EMAIL (+20 more)

### Community 87 - "Deploying SyncAlly's Temporal workers on AWS"
Cohesion: 0.09
Nodes (21): AWS layout, Build and deploy the worker services, Configure Temporal Cloud, Current deployment placement, Database and security boundaries, Deploying SyncAlly's Temporal workers on AWS, If Temporal itself must run in AWS, Provisioned so far (+13 more)

### Community 88 - "Collections API and UI Specification F10b"
Cohesion: 0.14
Nodes (12): Append-Only Fulfillment Observations and Confirmations, Canonical Hash and Legacy Export Preservation, Collection Schema Specification F10a, Versioned Item Shipment Payment Collections, Collections API and UI Specification F10b, Deterministic Version-Aware Export Downloads, Structured Collection Authoring and Review, Milestone Payment Intent State Machine (+4 more)

### Community 89 - "RefreshDealStateActivity"
Cohesion: 0.11
Nodes (8): RefreshDealStateActivity, DealWorkflowInput, _require_uuid(), new_workflow_input(), RefreshActivity, RefreshCall, RefreshDealStateActivityTests, factory()

### Community 90 - "OrganizationIndexPostgresMigrationTests"
Cohesion: 0.13
Nodes (4): ConversationPartyUniquenessMigrationTests, OrganizationIndexMigrationTests, OrganizationIndexPostgresMigrationTests, ProviderInvoiceUniqueMigrationTests

### Community 92 - "Design Inspiration & Awwwards Research: SyncAlly"
Cohesion: 0.13
Nodes (14): 1.1 Stripe Press / Stripe Dashboard (`stripe.com`), 1.2 Ramp (`ramp.com`), 1.3 Ironclad / Pactum AI (`ironcladapp.com` / `pactum.com`), 1. Category Peers (B2B Trade, LegalTech, FinTech), 2.1 Linear (`linear.app`), 2.2 Monolith Studio (`monolith.xyz`), 2.3 Resend (`resend.com`), 2. Emotional Peers (Calm Precision, Architectural Authority) (+6 more)

### Community 94 - "DealWorkflowTests"
Cohesion: 0.29
Nodes (3): DealWorkflowResult, DealWorkflowTests, new_notification()

### Community 95 - "lock_demo_deal_creation"
Cohesion: 0.19
Nodes (8): _acquire_lock(), _is_demo_deal(), lock_demo_deal_creation(), lock_demo_payment_processing(), lock_demo_reset(), lock_outbox_dispatch(), DemoLifecycleLockTests, _postgres_session()

### Community 96 - "PaymentNeedsAction"
Cohesion: 0.09
Nodes (11): get_paypal_webhook_configuration(), PaymentInvoiceLookup, PaymentInvoiceRequest, PaymentNeedsAction, PaymentWorkItem, main(), GmailSettings, PayPalSettings (+3 more)

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
Cohesion: 0.22
Nodes (10): get_deal_reminders(), ReminderResponse, _resolve_actor_deal_org(), suppress_reminder(), sync_reminders(), _to_response(), trigger_dispatch(), list_deal_reminders() (+2 more)

### Community 104 - "OrganizationContact"
Cohesion: 0.16
Nodes (6): _normalize_string(), OrganizationContact, OrganizationProfile, _contact_to_dict(), _profile_to_domain(), OrganizationContactDomainTests

### Community 105 - "review_constraint"
Cohesion: 0.09
Nodes (3): ConstraintRepository, review_constraint(), FakeCommunicationRepository

### Community 106 - "x-app-environment"
Cohesion: 0.09
Nodes (22): x-app-environment, AI_PROVIDER, APP_ENV, DATABASE_URL, DEBUG, GMAIL_APP_PASSWORD, GMAIL_FROM_EMAIL, GMAIL_SMTP_USERNAME (+14 more)

### Community 108 - "environment"
Cohesion: 0.12
Nodes (20): environment, BIND_ON_IP, DB, DB_PORT, DBNAME, POSTGRES_DB, POSTGRES_PASSWORD, POSTGRES_PWD (+12 more)

### Community 109 - "RemindersPanel.tsx"
Cohesion: 0.21
Nodes (14): listDealReminders(), suppressDealReminder(), syncDealReminders(), ReminderScope, ReminderStatus, formatUtc(), RemindersPanel(), scopeBadgeLabel() (+6 more)

### Community 110 - "_connect_with_retry"
Cohesion: 0.09
Nodes (11): _connect_with_retry(), create_worker(), _register_shutdown_handlers(), _remove_shutdown_handlers(), _request_shutdown(), run_worker(), workflow_activities(), ConnectWithRetryTests (+3 more)

### Community 111 - "hash_password"
Cohesion: 0.21
Nodes (6): bootstrap_system_admin(), CredentialsRequest, login(), hash_password(), fail(), scalar()

### Community 113 - "OpeningRequestNormalizationTests"
Cohesion: 0.05
Nodes (18): _extract_capabilities(), _extract_category(), _extract_delivery_date(), _extract_item_description(), extract_normalized_requirement(), _extract_payment_terms(), _resolve_country_code(), _contains_numeric_token() (+10 more)

### Community 114 - "healthcheck"
Cohesion: 0.16
Nodes (18): healthcheck, healthcheck, image, restart, volumes, temporal-schema, interval, retries (+10 more)

### Community 115 - "Design Direction: SyncAlly (Trade Folio)"
Cohesion: 0.17
Nodes (11): 1. Visual & Product Concept, 2. 3D Idea: The Consensus Core (Three.js WebGL), 3. Typographic System, 4. Colour Palette & Tokens, 5. Motion Language (Anime.js v4 + Three.js), 6.1 Unified Stage Header, 6.2 The Split-Desk Layout (Desktop), 6.3 Progressive Disclosure Sub-Tabs (+3 more)

### Community 116 - "NegotiationCommand"
Cohesion: 0.48
Nodes (3): negotiate(), NegotiationCommand, NegotiationRepository

### Community 118 - "Product Knowledge Brief: SyncAlly"
Cohesion: 0.20
Nodes (9): Audience, Brand and Voice, Content Inventory, Conversion, Identity, Product Knowledge Brief: SyncAlly, Technical Stack, Value (+1 more)

### Community 119 - "Final Gates and Truthful Completion Specification"
Cohesion: 0.20
Nodes (9): Evidence-Free Projection and Safety Bounds, F12 Trade Pack Handoff Document, Trade Pack Export Contract, Browser Verification Specification, ZIP HTML and Print Export Verification, Two-Party Isolated Browser Testing, Final Gates and Truthful Completion Specification, Full Gate Verification Suite (+1 more)

### Community 120 - "Skill (Repo Idea Thinker Skill)"
Cohesion: 0.50
Nodes (3): Repo Idea Thinker Skill, Repository-Grounded Ideation Discipline, Idea Quality Standards and Lightweight Validation

### Community 134 - "temporal-schema"
Cohesion: 0.15
Nodes (13): condition, db, command, depends_on, restart, migrate, temporal-schema, command (+5 more)

### Community 135 - "PaymentReconciliationRepositoryTests"
Cohesion: 0.19
Nodes (3): PaymentIntentStatus, VerifiedProviderPaymentStatus, PaymentReconciliationRepositoryTests

### Community 139 - "Customer journey: buyer and seller"
Cohesion: 0.29
Nodes (6): Customer contract, Customer journey: buyer and seller, Evidence and limits, Implementation constraints discovered during task mapping, Outcome, Task graph

### Community 140 - "ConversationContractTests"
Cohesion: 0.10
Nodes (5): ConcurrentConstraintUpdate, confirm_constraint(), ConstraintNotFound, ConversationContractTests, FakeConstraintRepository

### Community 141 - "sqlalchemy"
Cohesion: 0.03
Nodes (49): upgrade(), upgrade(), upgrade(), upgrade(), downgrade(), upgrade(), upgrade(), upgrade() (+41 more)

### Community 142 - "scaling"
Cohesion: 0.10
Nodes (20): build, build_context_directory, max_cpu, max_memory, min_cpu, min_memory, system, dockerfile_path (+12 more)

### Community 143 - "Deal"
Cohesion: 0.06
Nodes (17): Deal, DealStatus, _deal_to_domain(), _active_participation(), _to_domain(), FakeDealRepository, _domain_deal(), FakeDealRepository (+9 more)

### Community 144 - "SyncAlly deployment"
Cohesion: 0.20
Nodes (9): 1. Provision the VM and DNS, 2. Configure secrets, 3. Start the stack, Configure the Hostless App, Connect the Render frontend, Current $0 demo: Render + Hostless, OCI single-VM deployment, SyncAlly deployment (+1 more)

### Community 145 - "@playwright/test"
Cohesion: 0.11
Nodes (12): BUYER, SELLER, @playwright/test@^1.65.0, pngjs@^7.0.0, unzipper@^0.12.5, BUYER, SELLER, BUYER (+4 more)

### Community 146 - "DealDetailPage.test.tsx"
Cohesion: 0.04
Nodes (75): addCaseEvidence(), getCurrentAgreement(), getDeal(), getDealFulfillment(), listDealCases(), raiseDealCase(), recordDealFulfillment(), respondToDealCase() (+67 more)

### Community 147 - "ProposalComparison.tsx"
Cohesion: 0.19
Nodes (19): allocations(), Change, compareEntries(), comparisonChanges(), entries(), Entry, entrySignature(), Field (+11 more)

### Community 148 - "api/fulfillment.py"
Cohesion: 0.06
Nodes (30): _event_response(), FulfillmentEventResponse, FulfillmentSnapshotResponse, get_fulfillment_repository(), _raise_fulfillment_error(), read_fulfillment_route(), _record_fulfillment_event(), record_fulfillment_route() (+22 more)

### Community 149 - "application/reminders.py"
Cohesion: 0.09
Nodes (9): build_deduplication_key(), DealReminder, ensure_utc(), ReminderChannel, ReminderScope, ReminderStatus, SuppressionReason, _to_domain() (+1 more)

### Community 150 - "ConversationUseCaseTests"
Cohesion: 0.12
Nodes (9): AddMessageCommand, MessageIdempotencyPostgresTests, _find_conversation(), _find_keyed_message(), rendezvous(), send(), wait_for(), ConversationUseCaseTests (+1 more)

### Community 151 - "volumes"
Cohesion: 0.50
Nodes (4): volumes, caddy_config, caddy_data, postgres_data

### Community 152 - "MASTER BOARD"
Cohesion: 0.18
Nodes (10): ARBITRATION LOG, CAPABILITY MATRIX, CONSTRAINTS, CONTRACTS, DIRECTIVES, MASTER BOARD, OBJECTIVE, REQUIREMENTS (+2 more)

### Community 153 - "setup-temporal-postgres.sh"
Cohesion: 0.67
Nodes (3): PGPASSWORD, setup-temporal-postgres.sh script, update_database_schema()

### Community 155 - "DealsPage.tsx"
Cohesion: 0.17
Nodes (10): listDeals(), ViewerRole, DealsPage(), DealsPageProps, DealsState, describeError(), ROLE_LABELS, mockedGetOrganization (+2 more)

### Community 156 - "current_user"
Cohesion: 0.23
Nodes (4): current_user(), CurrentUserResponse, OrganizationRegistrationRequest, SystemAdminBootstrapRequest

### Community 157 - "record_paypal_webhook_event"
Cohesion: 0.20
Nodes (3): _persist_paypal_webhook_event(), receive_paypal_invoice_webhook(), record_paypal_webhook_event()

### Community 162 - "amendment.py"
Cohesion: 0.27
Nodes (4): compare_agreement_terms(), assess_amendment_impact(), FulfillmentObligationImpact, PaymentMilestoneImpact

### Community 163 - "VerifiedProviderPaymentState"
Cohesion: 0.35
Nodes (4): VerifiedProviderPaymentState, transition(), PaymentReconciliationTests, get_invoice_reconciliation()

### Community 165 - "application/conversations.py"
Cohesion: 0.08
Nodes (17): add_message(), can_view_constraint(), CommunicationRepository, correct_constraint(), create_manual_constraint(), deal_has_any_message(), import_thread(), list_visible_constraints() (+9 more)

### Community 166 - "STATE LOG: developer"
Cohesion: 0.25
Nodes (7): BLOCKERS & ESCALATIONS, CURRENT_STATE, ENVIRONMENT_SNAPSHOT (ENV), GOAL & ACCEPTANCE CRITERIA, IDENTITY & ROLE, IMPLEMENTATION_LEDGER, STATE LOG: developer

### Community 167 - "Frontend Audit: SyncAlly Web Client"
Cohesion: 0.40
Nodes (4): 1. Executive Summary, 2. Audit Table Against the 10 UI Principles, 3. Specific Bugs Identified, Frontend Audit: SyncAlly Web Client

### Community 168 - "platform.py"
Cohesion: 0.22
Nodes (4): list_platform_organizations(), _organization_summary(), OrganizationStatusUpdate, update_platform_organization_status()

### Community 169 - "User"
Cohesion: 0.06
Nodes (5): AgreementVersion, User, DealCasesTests, LocalWorkflowSmokeTests, commit_once()

### Community 171 - "STATE LOG: planner"
Cohesion: 0.25
Nodes (7): BLOCKERS & ESCALATIONS, CURRENT_STATE, ENVIRONMENT_SNAPSHOT (ENV), GOAL & ACCEPTANCE CRITERIA, IDENTITY & ROLE, IMPLEMENTATION_LEDGER, STATE LOG: planner

### Community 172 - "Code Review: Step 08 Cancel Disputes (F8) — Work Package RV1"
Cohesion: 0.22
Nodes (8): 1. Medium (P2) — Parallel Alembic Migration Heads Branching From 0024_amendments, 2. Reviewer's Guide, 3. Merge Gate, 4. Findings, 6. Empirical Verification Summary, 7. Review Verdict, Code Review: Step 08 Cancel Disputes (F8) — Work Package RV1, Control-flow diagram

### Community 173 - "STATE LOG: reviewer"
Cohesion: 0.25
Nodes (7): BLOCKERS & ESCALATIONS, CURRENT_STATE, ENVIRONMENT_SNAPSHOT (ENV), GOAL & ACCEPTANCE CRITERIA, IDENTITY & ROLE, IMPLEMENTATION_LEDGER, STATE LOG: reviewer

### Community 174 - "CONTRACT: cancel-disputes-contract v1   status: FROZEN"
Cohesion: 0.29
Nodes (6): Change rule, CONTRACT: cancel-disputes-contract v1   status: FROZEN, Domain / Models, Endpoints (under /api/v1/deals/{deal_id}/cases), Errors and edge cases, Interface

### Community 175 - "organization.py"
Cohesion: 0.16
Nodes (11): ContactVisibility, OrganizationCapability, OrganizationMember, OrganizationMemberRole, OrganizationMemberStatus, OrganizationStatus, OrganizationVerificationStatus, resolve_effective_capabilities() (+3 more)

### Community 176 - "eslint.config.js"
Cohesion: 0.18
Nodes (10): @eslint/js@^10.0.1, eslint-plugin-react-hooks@^7.1.1, eslint-plugin-react-refresh@^0.4.20, globals@^17.13.0, typescript-eslint@^8.71.2, @eslint/js, eslint-plugin-react-hooks, eslint-plugin-react-refresh (+2 more)

### Community 177 - "api/documents.py"
Cohesion: 0.14
Nodes (7): get_deal_repository(), CommercialDocumentDraftResponse, get_commercial_document_draft_route(), get_trade_pack_route(), AgreementNotCommitted, CommercialDocumentDraft, generate_commercial_document_draft()

### Community 178 - "NegotiationCommand"
Cohesion: 0.19
Nodes (5): NegotiationPostgresRaceTests, failing(), succeed(), create_legacy_draft(), replace_candidate()

### Community 179 - "Constraint"
Cohesion: 0.07
Nodes (10): CreateManualConstraintCommand, Constraint, ConstraintKind, ConstraintStatus, MessageSourceType, Visibility, _constraint_to_domain(), FakeCommunicationRepository (+2 more)

### Community 180 - "scripts"
Cohesion: 0.29
Nodes (7): scripts, build, dev, lint, lint:check, preview, test

### Community 181 - "VerifiedProviderPaymentState"
Cohesion: 0.23
Nodes (3): PaymentInvoiceReconciliation, FakePayPalInvoiceProvider, get_invoice_reconciliation()

### Community 183 - "vite.config.ts"
Cohesion: 0.33
Nodes (5): vite@^8.1.0, @vitejs/plugin-react@^6.1.2, API_PATH_PREFIXES, vite, @vitejs/plugin-react

### Community 185 - "0024_deal_display_name.py"
Cohesion: 0.36
Nodes (4): _deal_names_table(), downgrade(), _rollback_backup_table(), upgrade()

### Community 186 - "SqlAlchemyNegotiationRepository"
Cohesion: 0.19
Nodes (6): NegotiationConflict, NegotiationNotFound, NegotiationOrganizationRequired, ProposalId, SqlAlchemyNegotiationRepository, projection()

### Community 187 - "TEST_INFRA.md — E2E Testing Infrastructure & Specification"
Cohesion: 0.09
Nodes (21): 1.1 Backend Test Runner (`pytest`), 1.2 Frontend Test Runner (`vitest`), 1. Test Architecture & Runners, 2. Oracles & Expected Output Derivation, 3.1 Backend E2E Test Suite (`backend/tests/test_e2e_opening_request_analysis.py`), 3.2 Frontend E2E Test Suite (`frontend/src/deals/CreateDealPage.e2e.test.tsx`), 3. Test Suites & Coverage Inventory, 4.1 Running Backend E2E Tests (+13 more)

### Community 189 - "SyncAlly: Confirmed Bugs and Feature Roadmap"
Cohesion: 0.25
Nodes (7): Confirmed bugs, Core product capabilities, Feature roadmap, Hackathon-focused vertical slice, Scope and safeguards, Suggested sequencing, SyncAlly: Confirmed Bugs and Feature Roadmap

### Community 190 - "tokenize"
Cohesion: 0.29
Nodes (3): _normalize_token(), tokenize(), TestTokenizerAndWeights

### Community 192 - "create_database_engine"
Cohesion: 0.12
Nodes (4): create_database_engine(), CounterpartyOnboardingMigrationTests, DemoFixtureMigrationTests, NegotiationSqliteRaceTests

### Community 194 - "seed_demo_data"
Cohesion: 0.17
Nodes (7): _clear_fixture(), _delete_scoped(), DemoCollisionError, _normalized_index_predicate(), _preflight(), seed_demo_data(), DemoSeedTests

### Community 195 - "AddMessageRequest"
Cohesion: 0.19
Nodes (3): AddMessageRequest, CreateFactRequest, AddMessageRequestTests

### Community 196 - "TEST_READY.md — E2E Test Suite Readiness Declaration"
Cohesion: 0.14
Nodes (13): 1. Executive Summary, 2. Test Files Inventory, 3.1 Backend E2E Test Suite, 3.2 Frontend E2E Test Suite, 3.3 Full Combined E2E Verification, 3. Reproduction & Execution Commands, 4. Test Tier Breakdown, 5. Verification Results (+5 more)

### Community 197 - "0004_communication_sources_and_scope_indexes.py"
Cohesion: 0.60
Nodes (4): _create_scope_index(), downgrade(), _drop_scope_index(), upgrade()

### Community 198 - "register_organization"
Cohesion: 0.33
Nodes (3): _encode_access_token(), register_organization(), exercise_api()

### Community 200 - "Frontend product review"
Cohesion: 0.50
Nodes (3): Findings and fixes, Frontend product review, Walkthrough coverage

### Community 206 - "Proposal"
Cohesion: 0.12
Nodes (11): NegotiationSession, NegotiationSubmissionOutcome, Proposal, ProposalStatus, PaymentIntent, InvalidTransition, NegotiationSessionId, build_proposal() (+3 more)

### Community 208 - "refresh_access_token"
Cohesion: 0.19
Nodes (8): _as_utc(), create_refresh_token(), _hash_refresh_token(), refresh_access_token(), RefreshRequest, _replay_rotation(), _revoke_family(), RefreshToken

### Community 209 - "deal_completion.py"
Cohesion: 0.24
Nodes (6): delivery_obligation_fulfilled(), _event_total(), maybe_complete_deal(), payments_reconciled(), _scaled(), FulfillmentDomainTests

## Knowledge Gaps
- **48 isolated node(s):** `syncally`, `PGPASSWORD`, `F1a Curated Repeatable Demo Fixture`, `Editorial Dark Theme Design System`, `ZIP HTML and Print Export Verification` (+43 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1928 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **63 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ActorContext` connect `Test Deal Routes & Identity` to `Conversations & Test Conversation Use`, `ConfiguredAIProvider`, `api/agreements.py`, `Test Conversation Routes (ConversationRouteTests)`, `api/payments.py`, `ConversationContractTests`, `sqlalchemy`, `repositories/communications.py`, `AISuggestionProvider`, `Test Agreement Routes (AgreementRouteTests)`, `api/organizations.py`, `api/fulfillment.py`, `OrganizationId`, `ConversationUseCaseTests`, `Test Organization Invitations & Organizations`, `CommunicationRepositoryTests`, `Simulate Deal Flow & Test`, `current_user`, `identifiers.py`, `api/negotiation.py`, `application/conversations.py`, `platform.py`, `User`, `api/deals.py`, `PaymentIntentRepositoryTests`, `OutboxEvent`, `get_optional_actor`, `organization.py`, `Test Organization Directory & Organizations`, `api/documents.py`, `create_deal`, `get_current_actor`, `AISuggestionProviderTests`, `._request`, `_active_admin_membership`, `CommercialDocumentDraftTests`, `create_counterparty_invitation`, `CommitAgreementCommand`, `add_organization_member`, `simulate_payment`, `SqlAlchemyReminderRepository`, `repositories/agreements.py`, `IdentityBoundaryTests`, `NormalizedRequirement`, `.has_capability`, `NegotiationRouteTests`, `api/reminders.py`, `review_constraint`, `ApprovalRoutingRouteTests`, `AiContextSelectionTests`?**
  _High betweenness centrality (0.094) - this node is a cross-community bridge._
- **Are the 160 inferred relationships involving `ActorContext` (e.g. with `approve_agreement_route()` and `commit_agreement_route()`) actually correct?**
  _`ActorContext` has 160 INFERRED edges - model-reasoned connections that need verification._
- **What connects `syncally`, `PGPASSWORD`, `F1a Curated Repeatable Demo Fixture` to the rest of the system?**
  _48 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Conversations & Test Conversation Use` be split into smaller, more focused modules?**
  _Cohesion score 0.07006172839506172 - nodes in this community are weakly interconnected._
- **Why does `OrganizationId` connect `OrganizationId` to `AIContractError`, `application/deal_cases.py`, `ConfiguredAIProvider`, `schedule_deal_reminders`, `repositories/negotiation.py`, `api/agreements.py`, `Test Conversation Routes (ConversationRouteTests)`, `api/payments.py`, `Test Agreement Routes (AgreementRouteTests)`, `repositories/communications.py`, `sqlalchemy`, `AISuggestionProvider`, `Deal`, `ConversationContractTests`, `NegotiationTests`, `api/organizations.py`, `api/fulfillment.py`, `application/reminders.py`, `ConversationUseCaseTests`, `Test Outbox Dispatcher & Outbox`, `CommunicationRepositoryTests`, `identifiers.py`, `api/negotiation.py`, `VerifiedProviderPaymentState`, `application/deal_cases.py`, `application/conversations.py`, `ApprovalRoutingTestCase`, `PaymentIntentRepositoryTests`, `User`, `OutboxEvent`, `organization.py`, `create_deal`, `SqlAlchemyDealRepository`, `Constraint`, `AISuggestionProviderTests`, `SqlAlchemyNegotiationRepository`, `CommercialDocumentDraftTests`, `create_counterparty_invitation`, `NegotiationMigrationTests`, `CommitAgreementCommand`, `Money`, `ProposedTerms`, `repositories/agreements.py`, `Proposal`, `deal_completion.py`, `OrganizationRepositoryTests`, `OrganizationMemberDomainTests`, `.test_domain_capability_matrix_and_effective_capabilities`, `OrganizationContact`, `review_constraint`, `ApprovalRoutingRouteTests`, `AiContextSelectionTests`?**
  _High betweenness centrality (0.063) - this node is a cross-community bridge._
- **Are the 74 inferred relationships involving `OrganizationId` (e.g. with `build_trade_terms_from_request()` and `create_reviewed_agreement_draft_route()`) actually correct?**
  _`OrganizationId` has 74 INFERRED edges - model-reasoned connections that need verification._
- **Should `AIContractError` be split into smaller, more focused modules?**
  _Cohesion score 0.10909090909090909 - nodes in this community are weakly interconnected._