# Graph Report - SyncAlly  (2026-11-08)

## Corpus Check
- 392 files · ~367,840 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 14 file(s) not represented in the graph (top: (none) 8, .example 2, .ini 1)

## Summary
- 6031 nodes · 19374 edges · 206 communities (150 shown, 56 thin omitted)
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
- repositories/agreements.py
- ConfiguredAIProvider
- schedule_deal_reminders
- repositories/agreements.py
- PaymentNeedsAction
- GmailSMTPInvoiceNotifier
- api/agreements.py
- Test Conversation Routes (ConversationRouteTests)
- InvalidTransition
- Test Agreement Routes (AgreementRouteTests)
- repositories/communications.py
- process_payment_intent
- AISuggestionProvider
- NegotiationTests
- Types & Client
- listOrganizations
- OrganizationPermissionsTests
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
- workflow_state.py
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
- Agreement
- Test Dev Routes (DevRoutesTests)
- api/organizations.py
- DealWorkflow
- Test Organization Directory & Organizations
- create_deal
- SqlAlchemyDealRepository
- typing
- PaymentOutboxWorkerTests
- api/payments.py
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
- authorize_payment_route
- SafeOperationsTests
- environment
- Main & Test Identity Boundary
- Deploying SyncAlly's Temporal workers on AWS
- Collections API and UI Specification F10b
- RefreshDealStateActivity
- Test Organization Index Migration (OrganizationIndexPostgresMigrationTests)
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
- ai.py
- review_constraint
- x-app-environment
- Test Payment Mode Migration (PaymentModeMigrationTests)
- environment
- Test Communication Migration (ConversationPartyUniquenessMigrationTests)
- _connect_with_retry
- OnboardingWizard.tsx
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
- DealReminder
- MessageIdempotencyPostgresTests
- volumes
- MASTER BOARD
- setup-temporal-postgres.sh
- FulfillmentMigrationTests
- ProviderInvoiceUniqueMigrationTests
- read_deal_route
- record_paypal_webhook_event
- MigrationConfigTests
- CollectionSchemaMigrationTests
- create-temporal-namespace.sh
- postgres-init.sh
- amendment.py
- ConversationUseCaseTests
- repositories/reminders.py
- application/conversations.py
- STATE LOG: developer
- Frontend Audit: SyncAlly Web Client
- platform.py
- DealCasesTests
- MilestonePaymentsMigrationTests
- STATE LOG: planner
- STATE LOG: reviewer
- CONTRACT: cancel-disputes-contract v1   status: FROZEN
- organization.py
- eslint.config.js
- get_commercial_document_draft_route
- NegotiationCommand
- Constraint
- scripts
- VerifiedProviderPaymentState
- hostless-start.sh
- vite.config.ts
- MarketplaceRFQRequest
- 0024_deal_display_name.py
- SqlAlchemyNegotiationRepository
- TEST_INFRA.md — E2E Testing Infrastructure & Specification
- .__call__
- SyncAlly: Confirmed Bugs and Feature Roadmap
- tokenize
- NegotiationMigrationTests
- create_database_engine
- database_health
- DemoSeedTests
- AddMessageRequest
- TEST_READY.md — E2E Test Suite Readiness Declaration
- 0004_communication_sources_and_scope_indexes.py
- require_system_admin
- DealParticipation
- Frontend product review
- .setUp
- Proposal
- auth.py
- maybe_complete_deal

## God Nodes (most connected - your core abstractions)
1. `ActorContext` - 319 edges
2. `OrganizationId` - 241 edges
3. `InvariantViolation` - 150 edges
4. `UserId` - 139 edges
5. `Money` - 127 edges
6. `DealId` - 122 edges
7. `Deal` - 114 edges
8. `SqlAlchemyAgreementRepository` - 113 edges
9. `TradeTerms` - 87 edges
10. `AISuggestionProviderTests` - 87 edges

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

## Communities (206 total, 56 thin omitted)

### Community 0 - "Conversations & Test Conversation Use"
Cohesion: 0.06
Nodes (49): add_message_route(), AISuggestionRequest, clarify_fact_route(), confirm_fact_route(), ConstraintResponse, correct_fact_route(), CorrectFactRequest, create_fact_route() (+41 more)

### Community 1 - "AIContractError"
Cohesion: 0.11
Nodes (16): AIContractError, AIValidationClaim, _check_keys(), _decimal(), FactField, _required_string(), scope_extracted_facts(), ScopedFactCandidate (+8 more)

### Community 3 - "repositories/agreements.py"
Cohesion: 0.08
Nodes (17): AgreementAccessDenied, AgreementAlreadyCommitted, AgreementNotFound, AgreementVersionConflict, DuplicateApproval, ProposalNotFound, StaleAgreementVersion, UnauthorizedApproval (+9 more)

### Community 4 - "ConfiguredAIProvider"
Cohesion: 0.08
Nodes (13): extract_facts_from_context(), ConfiguredAIProvider, AISuggestionProviderTests, respond(), respond(), respond(), respond(), respond() (+5 more)

### Community 6 - "repositories/agreements.py"
Cohesion: 0.05
Nodes (43): dispatch_due_reminders(), _is_active_member(), NotificationKind, _clear_fixture(), _create_fixture(), _delete_scoped(), DemoCollisionError, DemoIdentity (+35 more)

### Community 7 - "PaymentNeedsAction"
Cohesion: 0.09
Nodes (10): PaymentOutcomeUnknown, PaymentRetryableError, VerifiedProviderPaymentStatus, _has_excess_currency_precision(), PayPalSandboxInvoiceProvider, _provider_error_code(), _provider_request_id(), _send_request() (+2 more)

### Community 8 - "GmailSMTPInvoiceNotifier"
Cohesion: 0.08
Nodes (5): PaymentInvoiceNotice, main(), GmailSMTPInvoiceNotifier, _FakeSMTP, GmailSMTPInvoiceNotifierTests

### Community 9 - "api/agreements.py"
Cohesion: 0.05
Nodes (45): AgreementVersionResponse, AmendmentImpactResponse, ApprovalResponse, approve_agreement_route(), commit_agreement_route(), CommitAgreementRequest, compare_agreements_route(), create_agreement_draft_route() (+37 more)

### Community 10 - "Test Conversation Routes (ConversationRouteTests)"
Cohesion: 0.10
Nodes (3): ConversationRouteTests, respond(), send()

### Community 11 - "InvalidTransition"
Cohesion: 0.05
Nodes (15): PaymentStatusResponse, AuthorizePaymentIntentCommand, DuplicateActivePaymentIntent, PaymentIntentAuthorizationOutcome, PaymentStatusRecord, PaymentIntent, InvalidTransition, ExtendedPaymentStatusRecord (+7 more)

### Community 13 - "repositories/communications.py"
Cohesion: 0.07
Nodes (12): CreateManualConstraintCommand, ConstraintKind, ConstraintStatus, Visibility, CommunicationScopeError, _constraint_to_domain(), _conversation_to_domain(), _is_unique_violation() (+4 more)

### Community 14 - "process_payment_intent"
Cohesion: 0.08
Nodes (15): payment_invoice_number(), PaymentInvoiceNotifier, PaymentInvoiceProvider, PaymentProcessingRepository, reconcile_payment_intent(), _request_id_retry_window_expired(), require_payment_provider(), PaymentProviderResolver (+7 more)

### Community 15 - "AISuggestionProvider"
Cohesion: 0.08
Nodes (18): AISuggestionProvider, draft_proposal(), draft_proposal_from_context(), extract_facts(), fact_suggestion_guidance(), FactExtractionResult, missing_trade_fields(), ProposalDraftResult (+10 more)

### Community 16 - "NegotiationTests"
Cohesion: 0.19
Nodes (5): EvidenceReference, ProposalBase, negotiate_in_transaction(), replace_candidate(), NegotiationTests

### Community 17 - "Types & Client"
Cohesion: 0.03
Nodes (100): describeDetail(), getDealMessageExistence(), isAbortError(), isRecord(), listDealReminders(), listPlatformOrganizations(), readErrorDetail(), suppressDealReminder() (+92 more)

### Community 18 - "listOrganizations"
Cohesion: 0.05
Nodes (67): dependencies, react@^19.3.0, react-dom@^19.3.0, three@^0.186.1, getCurrentUser(), login(), registerOrganization(), clearAccessToken() (+59 more)

### Community 19 - "OrganizationPermissionsTests"
Cohesion: 0.13
Nodes (5): _compute_effective_capabilities(), revoke_organization_member(), update_member_permissions(), UpdateMemberPermissionsRequest, OrganizationPermissionsTests

### Community 20 - "OrganizationId"
Cohesion: 0.09
Nodes (13): PaymentMilestone, AgreementVersionId, DealId, OrganizationId, PaymentIntentId, PaymentMilestoneId, _restore_domain_intent(), PaymentReconciliationTests (+5 more)

### Community 21 - "Test Outbox Dispatcher & Outbox"
Cohesion: 0.08
Nodes (15): build_deal_workflow_id(), DealWorkflowStarter, dispatch_outbox_event(), OutboxDispatchResult, PendingOutboxEvent, WorkflowStartTransientError, apply_dispatch_result(), claim_next_pending_event() (+7 more)

### Community 22 - "Simulate Deal Flow & Test"
Cohesion: 0.06
Nodes (13): _build_in_process_client(), dispatch_payment(), mark_fixture(), session_factory(), ci_deal_flow_hook(), DealFlowContext, DealFlowSimulator, run_simulation() (+5 more)

### Community 23 - "Test Organization Invitations & Organizations"
Cohesion: 0.13
Nodes (10): accept_invitation(), AcceptInvitationRequest, create_counterparty_invitation(), create_organization_invitation(), CreateCounterpartyInvitationRequest, CreateInvitationRequest, _decode_invitation_token(), ActorContext (+2 more)

### Community 25 - "package.json"
Cohesion: 0.10
Nodes (25): devDependencies, eslint@^10.13.0, happy-dom@^21.0.3, @testing-library/dom@^10.4.1, @testing-library/jest-dom@^7.0.1, @testing-library/react@^16.3.3, @types/react@^19.0.0, @types/react-dom@^19.0.0 (+17 more)

### Community 26 - "Organization"
Cohesion: 0.05
Nodes (49): addOrganizationMember(), deleteApprovalRoutingPolicy(), getApprovalRoutingPolicy(), getOrganizationProfile(), listOrganizationMembers(), putApprovalRoutingPolicy(), revokeOrganizationMember(), updateMemberPermissions() (+41 more)

### Community 27 - "Dealconversationreview & Dealconversationreview.Test"
Cohesion: 0.07
Nodes (45): createDealMessage(), importDealThread(), listDealFacts(), listDealMessages(), previewDealThreadImport(), reviewDealFact(), updateFactVisibility(), Visibility (+37 more)

### Community 28 - "Skill & Skill.Md"
Cohesion: 0.04
Nodes (43): API and Database Engineer Skill, API Design and Contract Semantics, Data Integrity and Invariant Enforcement, Query Performance and Projection Optimization, Schema Migration and Backward Compatibility, Transaction Boundaries and Atomicity, Archify Diagrammer Skill, Archify CLI Global Tool (+35 more)

### Community 29 - "identifiers.py"
Cohesion: 0.06
Nodes (4): CommercialDocumentDraft, _quantity(), _request_hash(), DomainDependencyTests

### Community 30 - "App.test.tsx"
Cohesion: 0.04
Nodes (53): ApiError, getCommercialDocumentDraft(), getTradePack(), listDeals(), TradePackFormat, AgreementVersion, ViewerRole, mockedApiRequest (+45 more)

### Community 31 - "api/negotiation.py"
Cohesion: 0.13
Nodes (12): BaseRequest, CandidateRequest, EvidenceRequest, HistoryResponse, NegotiationRequest, NegotiationResponse, NegotiationResult, ProposalResponse (+4 more)

### Community 32 - "workflow_state.py"
Cohesion: 0.10
Nodes (10): DealWorkflowState, load_deal_workflow_state(), parse_workflow_uuid(), WorkflowAgreementRepository, WorkflowDealNotFound, WorkflowDealRepository, _domain_deal(), _FakeAgreementRepository (+2 more)

### Community 33 - "Aisuggestionreview & Suggestionpreview"
Cohesion: 0.05
Nodes (67): correctDealFact(), createDealFact(), draftDealProposal(), getNegotiation(), negotiateDeal(), suggestDealFacts(), AIProvenance, Deal (+59 more)

### Community 34 - "SyncAlly Implementation Plan Document"
Cohesion: 0.13
Nodes (16): SyncAlly Architecture Document, System Topology and Ownership Boundaries, Temporal Worker and Outbox Architecture, AI Provider Boundary Specification, AI Resilience and Retry Policy, AISuggestionProvider Contract, Acceptance Criteria Verification Matrix, SyncAlly Implementation Plan Document (+8 more)

### Community 35 - "PaymentProcessingTests"
Cohesion: 0.13
Nodes (6): process_payment_intent(), FakeInvoiceProvider, FakeProcessingRepository, PaymentProcessingTests, _request(), _work_item()

### Community 36 - "application/deal_cases.py"
Cohesion: 0.09
Nodes (27): add_case_evidence(), AddCaseEvidenceCommand, assess_deal_case_blockers(), DealCaseRepository, DealNotFound, list_deal_cases(), raise_deal_case(), RaiseDealCaseCommand (+19 more)

### Community 37 - "DealWorkflowNotification"
Cohesion: 0.13
Nodes (6): WorkflowStartError, WorkflowStartOutcome, WorkflowStartPermanentError, DealWorkflowNotification, TemporalDealWorkflowStarter, TemporalAdapterTests

### Community 38 - "ApprovalRoutingTestCase"
Cohesion: 0.08
Nodes (17): NotEligibleApprover, OutOfSequenceApproval, ApprovalDecision, ApprovalRoutingMode, ApprovalRoutingPolicy, can_act(), evaluate_routing(), RoutingApproverSlot (+9 more)

### Community 39 - "Paymentstatuspanel & Paymentstatuspanel.Test"
Cohesion: 0.08
Nodes (36): API_REQUEST_TIMEOUT_MS, authorizeDealPayment(), listDealPaymentMilestones(), listPaymentStatuses(), previewDealPayment(), CREATED_MESSAGE, fetchMock, lastRequest() (+28 more)

### Community 41 - "services"
Cohesion: 0.09
Nodes (29): build, depends_on, restart, context, dockerfile, migrate, temporal-namespace, build (+21 more)

### Community 42 - "api/deals.py"
Cohesion: 0.19
Nodes (24): add_evidence_deals_route(), _add_evidence_impl(), add_evidence_v1_route(), AddEvidenceRequest, AnalyzeOpeningRequestRequest, CaseEvidenceResponse, CaseResponse, CreateDealRequest (+16 more)

### Community 43 - "InvariantViolation"
Cohesion: 0.11
Nodes (7): _normalized_text(), _require_decimal(), InvariantViolation, bounded_decimal(), currency_precision(), has_excess_currency_precision(), BoundedDecimalTests

### Community 44 - "Agreement"
Cohesion: 0.20
Nodes (6): Agreement, Approval, AgreementId, _agreement_to_domain(), FakeAgreementRepository, FakeDealRepository

### Community 46 - "api/organizations.py"
Cohesion: 0.07
Nodes (25): AcceptInvitationResponse, ApprovalRoutingPolicyRequest, ApprovalRoutingPolicyResponse, _case_insensitive_prefix(), ContactResponse, CounterpartyInvitationResponse, _create_invitation_token(), _deal_awaiting_counterparty() (+17 more)

### Community 47 - "DealWorkflow"
Cohesion: 0.09
Nodes (8): DealWorkflow, DealWorkflowInput, _require_uuid(), DealWorkflowUnitTests, new_workflow_input(), RefreshActivity, RefreshCall, WorkflowWorkerIntegrationTests

### Community 49 - "create_deal"
Cohesion: 0.14
Nodes (7): create_deal_route(), _both_organizations_active(), create_deal(), CreateDealCommand, DealNotFound, DealUseCaseTests, FakeDealRepository

### Community 50 - "SqlAlchemyDealRepository"
Cohesion: 0.16
Nodes (4): get_deal_repository(), _active_participation(), SqlAlchemyDealRepository, DealRepositoryTests

### Community 51 - "typing"
Cohesion: 0.04
Nodes (7): _require_dev_environment(), OperationalFastAPI, _is_live_backend_healthy(), main(), get_db(), HealthRouteTests, OutboxDispatchMigrationTests

### Community 52 - "PaymentOutboxWorkerTests"
Cohesion: 0.10
Nodes (5): FakeRepository, NoCallProvider, PaymentOutboxWorkerTests, resolve(), _utc()

### Community 53 - "api/payments.py"
Cohesion: 0.07
Nodes (18): PaymentOutboxStatus, OutboxEventDraft, authorize_payment_intent(), IdempotencyKeyReused, PaymentIntentCommandMismatch, PaymentIntentRepository, PaymentMilestoneNotFound, PaymentModeChanged (+10 more)

### Community 54 - "repositories/payment_processing.py"
Cohesion: 0.11
Nodes (15): _connect_with_retry(), main(), run_forever(), main(), run_forever(), is_permanent_rpc_error(), configure_logging(), log_operation() (+7 more)

### Community 56 - "._request"
Cohesion: 0.05
Nodes (6): BaseOpeningRequestE2ETest, _is_route_available(), TestOpeningRequestE2ETier1FeatureCoverage, TestOpeningRequestE2ETier2BoundaryAndCorners, TestOpeningRequestE2ETier3CrossFeatureCombinations, TestOpeningRequestE2ETier4RealWorldScenarios

### Community 57 - "_active_admin_membership"
Cohesion: 0.17
Nodes (12): close_marketplace_rfq(), create_marketplace_listing(), create_marketplace_rfq(), deactivate_marketplace_listing(), get_marketplace_listing(), get_marketplace_rfq(), _response(), _rfq_response() (+4 more)

### Community 58 - "CommercialDocumentDraftTests"
Cohesion: 0.13
Nodes (12): AgreementNotCommitted, export_display_terms(), generate_commercial_document_draft(), generate_trade_pack(), InvalidTradePack, _json_bytes(), _shape(), _trade_pack_html() (+4 more)

### Community 59 - "Test Migration Lock & Env"
Cohesion: 0.10
Nodes (9): run_migrations_offline(), run_migrations_online(), serialize_migrations(), _make_postgres_connection(), _make_sqlite_connection(), MigrationLockTests, simulated_migration(), PostgresRealAdvisoryLockTests (+1 more)

### Community 60 - "Payment Processing & Test Payment"
Cohesion: 0.18
Nodes (3): PaymentInvoiceLineItem, SqlAlchemyPaymentProcessingRepository, transition()

### Community 61 - "01 Commercial Domain Model &"
Cohesion: 0.07
Nodes (19): AgreementVersion Aggregate, Append-Only AuditEvent Ledger, Commercial Constraint and Provenance, Deal Aggregate, Organization and Membership Entities, PaymentMilestone and Obligation, Proposal Aggregate and Terms Hash, Temporal Deal Workflow (+11 more)

### Community 62 - "create_counterparty_invitation"
Cohesion: 0.19
Nodes (3): OnboardingConcurrencyCases, OnboardingPostgresConcurrencyTests, OnboardingSQLiteConcurrencyTests

### Community 64 - "AIFallbackResilienceTests"
Cohesion: 0.05
Nodes (9): get_ai_suggestion_provider(), AIConfigurationError, AIProvenance, AIRetryPolicy, call_with_bounded_retry(), OpeningRequestNormalizationService, AIFallbackResilienceTests, mock_fallback() (+1 more)

### Community 65 - "Compose.Yaml (volumes)"
Cohesion: 0.09
Nodes (22): POSTGRES_DB, POSTGRES_PASSWORD, POSTGRES_USER, interval, retries, test, timeout, environment (+14 more)

### Community 66 - "Architectural & Implementation Plan: Step 08 Cancel Disputes (F8)"
Cohesion: 0.12
Nodes (16): 2. Domain Entities & Value Objects, 3. Deal Aggregate Coordination, 4. Persistence Models & Alembic Migration 0025, 5. Application Layer: Use Cases & Operational Impact Assessment, 6. HTTP API Layer, 7. Frontend Integration, 9. Verification & Test Plan, Architectural & Implementation Plan: Step 08 Cancel Disputes (F8) (+8 more)

### Community 67 - "apiRequest"
Cohesion: 0.07
Nodes (45): acceptInvitation(), apiBaseUrl(), apiRequest(), closeMarketplaceRFQ(), createAgreementFromReviewedTerms(), createCounterpartyInvitation(), createDeal(), createMarketplaceListing() (+37 more)

### Community 68 - "CommitAgreementCommand"
Cohesion: 0.07
Nodes (11): AuthorizePaymentRequest, CommitAgreementCommand, ProposeAmendmentCommand, RecordApprovalCommand, commit_agreement_in_transaction(), propose_amendment_in_transaction(), record_approval_in_transaction(), AgreementCommitTests (+3 more)

### Community 69 - "add_organization_member"
Cohesion: 0.17
Nodes (6): add_organization_member(), AddOrganizationMemberRequest, create_organization(), CreateOrganizationRequest, _is_duplicate_membership_error(), OrganizationOnboardingTests

### Community 70 - "simulate_payment"
Cohesion: 0.15
Nodes (6): DevResetResponse, DevRoleSwitchRequest, _require_demo_admin(), reset_demo(), SimulatePaymentRequest, switch_role()

### Community 71 - "Money"
Cohesion: 0.10
Nodes (21): build_trade_terms_from_request(), build_obligations(), build_payment_milestones(), PaymentMilestoneDraft, _money(), _parse_money(), PaymentObligationAllocation, PaymentTerm (+13 more)

### Community 72 - "PersistentDemoSeedTests"
Cohesion: 0.09
Nodes (7): fixture_id(), initialize_offline_database(), main(), PersistentDemoSeedTests, exercise_api(), start_deal_workflow(), dispatch()

### Community 73 - "AgreementReview.tsx"
Cohesion: 0.10
Nodes (38): commitAgreementVersion(), compareAgreementVersions(), getAgreementHistory(), getAgreementVersion(), getAmendmentImpact(), previewAmendmentImpact(), proposeAmendment(), recordAgreementDecision() (+30 more)

### Community 74 - "ProposedTerms"
Cohesion: 0.08
Nodes (19): AIPermanentError, AIProviderError, AITransientError, FactExtractionRequest, parse_extracted_facts(), parse_proposed_terms(), ProposalDraftRequest, _provider_context() (+11 more)

### Community 75 - "SqlAlchemyReminderRepository"
Cohesion: 0.18
Nodes (3): DealReminderModel, SqlAlchemyReminderRepository, RemindersRoutesTests

### Community 76 - "repositories/agreements.py"
Cohesion: 0.04
Nodes (30): AgreementRepository, assess_amendment_impact(), AuditEventDraft, AuditRepository, commit_agreement(), create_agreement_draft(), create_reviewed_agreement_draft(), CreateAgreementDraftCommand (+22 more)

### Community 77 - "IdentityBoundaryTests"
Cohesion: 0.04
Nodes (6): _is_loopback_temporal_address(), _is_weak_jwt_secret(), Settings, IdentityBoundaryTests, fail(), scalar()

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
Cohesion: 0.10
Nodes (9): analyze_opening_request_route(), AnalyzeOpeningRequestResponse, normalize_opening_request(), OpeningRequestNormalizationResult, SellerSuggestionItem, SellerSuggestionService, NormalizedRequirement, BaseSellerSuggestionTest (+1 more)

### Community 83 - "authorize_payment_route"
Cohesion: 0.11
Nodes (13): authorize_payment_route(), AuthorizePaymentResponse, _check_milestone_delivery_confirmed(), get_payment_status_repository(), list_payment_milestones_route(), list_payment_statuses_route(), MilestoneAllocationResponse, MilestonePaymentSummaryResponse (+5 more)

### Community 84 - "SafeOperationsTests"
Cohesion: 0.24
Nodes (4): captured_output(), SafeOperationsTests, exercise(), failed_db()

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
Cohesion: 0.13
Nodes (4): RefreshDealStateActivity, _workflow_input_value(), RefreshDealStateActivityTests, factory()

### Community 92 - "Design Inspiration & Awwwards Research: SyncAlly"
Cohesion: 0.13
Nodes (14): 1.1 Stripe Press / Stripe Dashboard (`stripe.com`), 1.2 Ramp (`ramp.com`), 1.3 Ironclad / Pactum AI (`ironcladapp.com` / `pactum.com`), 1. Category Peers (B2B Trade, LegalTech, FinTech), 2.1 Linear (`linear.app`), 2.2 Monolith Studio (`monolith.xyz`), 2.3 Resend (`resend.com`), 2. Emotional Peers (Calm Precision, Architectural Authority) (+6 more)

### Community 94 - "DealWorkflowTests"
Cohesion: 0.22
Nodes (4): DealWorkflowResult, DealWorkflowStatus, DealWorkflowTests, new_notification()

### Community 95 - "lock_demo_deal_creation"
Cohesion: 0.19
Nodes (8): _acquire_lock(), _is_demo_deal(), lock_demo_deal_creation(), lock_demo_payment_processing(), lock_demo_reset(), lock_outbox_dispatch(), DemoLifecycleLockTests, _postgres_session()

### Community 96 - "PaymentNeedsAction"
Cohesion: 0.08
Nodes (13): simulate_payment(), get_paypal_webhook_configuration(), PaymentInvoiceLookup, PaymentInvoiceRequest, PaymentNeedsAction, PaymentWorkItem, GmailSettings, PayPalSettings (+5 more)

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

### Community 104 - "ai.py"
Cohesion: 0.10
Nodes (17): _extract_capabilities(), _extract_category(), _extract_delivery_date(), _extract_item_description(), _list_all_constraints_for_owner(), persist_fact_candidates(), _resolve_country_code(), _contains_numeric_token() (+9 more)

### Community 106 - "x-app-environment"
Cohesion: 0.09
Nodes (22): x-app-environment, AI_PROVIDER, APP_ENV, DATABASE_URL, DEBUG, GMAIL_APP_PASSWORD, GMAIL_FROM_EMAIL, GMAIL_SMTP_USERNAME (+14 more)

### Community 108 - "environment"
Cohesion: 0.12
Nodes (20): environment, BIND_ON_IP, DB, DB_PORT, DBNAME, POSTGRES_DB, POSTGRES_PASSWORD, POSTGRES_PWD (+12 more)

### Community 110 - "_connect_with_retry"
Cohesion: 0.11
Nodes (7): create_worker(), _register_shutdown_handlers(), _remove_shutdown_handlers(), _request_shutdown(), workflow_activities(), WorkerShutdownSignalTests, WorkflowWorkerTests

### Community 111 - "OnboardingWizard.tsx"
Cohesion: 0.16
Nodes (15): createOrganization(), listOrganizations(), COUNTRY_NAMES, CountryOption, describeError(), isAmbiguousCreateFailure(), OnboardingWizard(), findExistingOrganization() (+7 more)

### Community 113 - "OpeningRequestNormalizationTests"
Cohesion: 0.06
Nodes (5): extract_normalized_requirement(), _extract_payment_terms(), OpeningRequestAdversarialStressTests, AdversarialExtractionChallengerTests, OpeningRequestNormalizationTests

### Community 114 - "healthcheck"
Cohesion: 0.16
Nodes (18): healthcheck, healthcheck, image, restart, volumes, temporal-schema, interval, retries (+10 more)

### Community 115 - "Design Direction: SyncAlly (Trade Folio)"
Cohesion: 0.17
Nodes (11): 1. Visual & Product Concept, 2. 3D Idea: The Consensus Core (Three.js WebGL), 3. Typographic System, 4. Colour Palette & Tokens, 5. Motion Language (Anime.js v4 + Three.js), 6.1 Unified Stage Header, 6.2 The Split-Desk Layout (Desktop), 6.3 Progressive Disclosure Sub-Tabs (+3 more)

### Community 116 - "NegotiationCommand"
Cohesion: 0.42
Nodes (3): negotiate(), NegotiationCommand, NegotiationRepository

### Community 117 - "AiContextSelectionTests"
Cohesion: 0.24
Nodes (4): select_ai_context(), AiContextSelectionTests, constraint(), message()

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

### Community 139 - "Customer journey: buyer and seller"
Cohesion: 0.29
Nodes (6): Customer contract, Customer journey: buyer and seller, Evidence and limits, Implementation constraints discovered during task mapping, Outcome, Task graph

### Community 141 - "sqlalchemy"
Cohesion: 0.03
Nodes (52): upgrade(), uuid_column(), upgrade(), upgrade(), upgrade(), upgrade(), downgrade(), upgrade() (+44 more)

### Community 142 - "scaling"
Cohesion: 0.10
Nodes (20): build, build_context_directory, max_cpu, max_memory, min_cpu, min_memory, system, dockerfile_path (+12 more)

### Community 143 - "Deal"
Cohesion: 0.07
Nodes (15): Deal, _deal_to_domain(), _to_domain(), _domain_deal(), FakeDealRepository, 1. Executive Summary & Change Stack Digest, 1. Medium (P2) — Parallel Alembic Migration Heads Branching From 0024_amendments, 2. Reviewer's Guide (+7 more)

### Community 144 - "SyncAlly deployment"
Cohesion: 0.20
Nodes (9): 1. Provision the VM and DNS, 2. Configure secrets, 3. Start the stack, Configure the Hostless App, Connect the Render frontend, Current $0 demo: Render + Hostless, OCI single-VM deployment, SyncAlly deployment (+1 more)

### Community 145 - "@playwright/test"
Cohesion: 0.11
Nodes (12): BUYER, SELLER, @playwright/test@^1.65.0, pngjs@^7.0.0, unzipper@^0.12.5, BUYER, SELLER, BUYER (+4 more)

### Community 146 - "DealDetailPage.test.tsx"
Cohesion: 0.04
Nodes (65): addCaseEvidence(), getCurrentAgreement(), getDeal(), getDealFulfillment(), listDealCases(), raiseDealCase(), recordDealFulfillment(), respondToDealCase() (+57 more)

### Community 147 - "ProposalComparison.tsx"
Cohesion: 0.19
Nodes (20): paymentTimingLabel(), allocations(), Change, compareEntries(), comparisonChanges(), entries(), Entry, entrySignature() (+12 more)

### Community 148 - "api/fulfillment.py"
Cohesion: 0.06
Nodes (32): _event_response(), FulfillmentEventResponse, FulfillmentSnapshotResponse, get_fulfillment_repository(), _raise_fulfillment_error(), read_fulfillment_route(), _record_fulfillment_event(), record_fulfillment_route() (+24 more)

### Community 149 - "DealReminder"
Cohesion: 0.17
Nodes (3): DealReminder, ensure_utc(), ReminderDomainTests

### Community 150 - "MessageIdempotencyPostgresTests"
Cohesion: 0.22
Nodes (5): MessageIdempotencyPostgresTests, _find_conversation(), _find_keyed_message(), rendezvous(), wait_for()

### Community 151 - "volumes"
Cohesion: 0.50
Nodes (4): volumes, caddy_config, caddy_data, postgres_data

### Community 152 - "MASTER BOARD"
Cohesion: 0.18
Nodes (10): ARBITRATION LOG, CAPABILITY MATRIX, CONSTRAINTS, CONTRACTS, DIRECTIVES, MASTER BOARD, OBJECTIVE, REQUIREMENTS (+2 more)

### Community 153 - "setup-temporal-postgres.sh"
Cohesion: 0.67
Nodes (3): PGPASSWORD, setup-temporal-postgres.sh script, update_database_schema()

### Community 156 - "read_deal_route"
Cohesion: 0.18
Nodes (7): DealResponse, DealSummaryResponse, list_deals_route(), read_deal_route(), _to_response(), _viewer_role(), list_deals()

### Community 157 - "record_paypal_webhook_event"
Cohesion: 0.20
Nodes (3): _persist_paypal_webhook_event(), receive_paypal_invoice_webhook(), record_paypal_webhook_event()

### Community 162 - "amendment.py"
Cohesion: 0.19
Nodes (6): compare_agreement_terms(), AmendmentAlreadyCommitted, AmendmentImpact, assess_amendment_impact(), FulfillmentObligationImpact, PaymentMilestoneImpact

### Community 163 - "ConversationUseCaseTests"
Cohesion: 0.17
Nodes (8): AddMessageCommand, import_thread(), preview_thread_import(), _thread_import_preview(), ThreadImportPreview, send(), ConversationUseCaseTests, write_message()

### Community 164 - "repositories/reminders.py"
Cohesion: 0.20
Nodes (6): build_deduplication_key(), ReminderChannel, ReminderScope, ReminderStatus, SuppressionReason, _to_domain()

### Community 165 - "application/conversations.py"
Cohesion: 0.06
Nodes (20): add_message(), can_view_constraint(), can_view_message(), CommunicationRepository, correct_constraint(), create_manual_constraint(), deal_has_any_message(), list_visible_constraints() (+12 more)

### Community 166 - "STATE LOG: developer"
Cohesion: 0.25
Nodes (7): BLOCKERS & ESCALATIONS, CURRENT_STATE, ENVIRONMENT_SNAPSHOT (ENV), GOAL & ACCEPTANCE CRITERIA, IDENTITY & ROLE, IMPLEMENTATION_LEDGER, STATE LOG: developer

### Community 167 - "Frontend Audit: SyncAlly Web Client"
Cohesion: 0.40
Nodes (4): 1. Executive Summary, 2. Audit Table Against the 10 UI Principles, 3. Specific Bugs Identified, Frontend Audit: SyncAlly Web Client

### Community 168 - "platform.py"
Cohesion: 0.24
Nodes (4): list_platform_organizations(), _organization_summary(), OrganizationStatusUpdate, update_platform_organization_status()

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
Nodes (24): update_organization_profile_route(), ContactVisibility, _normalize_string(), Organization, OrganizationCapability, OrganizationContact, OrganizationMember, OrganizationMemberRole (+16 more)

### Community 176 - "eslint.config.js"
Cohesion: 0.18
Nodes (10): @eslint/js@^10.0.1, eslint-plugin-react-hooks@^7.1.1, eslint-plugin-react-refresh@^0.4.20, globals@^17.13.0, typescript-eslint@^8.71.2, @eslint/js, eslint-plugin-react-hooks, eslint-plugin-react-refresh (+2 more)

### Community 177 - "get_commercial_document_draft_route"
Cohesion: 0.24
Nodes (3): CommercialDocumentDraftResponse, get_commercial_document_draft_route(), get_trade_pack_route()

### Community 178 - "NegotiationCommand"
Cohesion: 0.22
Nodes (4): NegotiationPostgresRaceTests, run(), failing(), succeed()

### Community 179 - "Constraint"
Cohesion: 0.08
Nodes (4): Constraint, FakeCommunicationRepository, FakeCommunicationRepository, FakeCommunicationRepository

### Community 180 - "scripts"
Cohesion: 0.29
Nodes (7): scripts, build, dev, lint, lint:check, preview, test

### Community 181 - "VerifiedProviderPaymentState"
Cohesion: 0.18
Nodes (6): PaymentInvoiceReconciliation, VerifiedProviderPaymentState, transition(), FakePayPalInvoiceProvider, get_invoice_reconciliation(), get_invoice_reconciliation()

### Community 183 - "vite.config.ts"
Cohesion: 0.33
Nodes (5): vite@^8.1.0, @vitejs/plugin-react@^6.1.2, API_PATH_PREFIXES, vite, @vitejs/plugin-react

### Community 184 - "MarketplaceRFQRequest"
Cohesion: 0.22
Nodes (4): MarketplaceListingRequest, MarketplaceListingResponse, MarketplaceRFQRequest, MarketplaceRFQResponse

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

### Community 195 - "AddMessageRequest"
Cohesion: 0.19
Nodes (3): AddMessageRequest, CreateFactRequest, AddMessageRequestTests

### Community 196 - "TEST_READY.md — E2E Test Suite Readiness Declaration"
Cohesion: 0.14
Nodes (13): 1. Executive Summary, 2. Test Files Inventory, 3.1 Backend E2E Test Suite, 3.2 Frontend E2E Test Suite, 3.3 Full Combined E2E Verification, 3. Reproduction & Execution Commands, 4. Test Tier Breakdown, 5. Verification Results (+5 more)

### Community 197 - "0004_communication_sources_and_scope_indexes.py"
Cohesion: 0.60
Nodes (4): _create_scope_index(), downgrade(), _drop_scope_index(), upgrade()

### Community 200 - "Frontend product review"
Cohesion: 0.50
Nodes (3): Findings and fixes, Frontend product review, Walkthrough coverage

### Community 206 - "Proposal"
Cohesion: 0.17
Nodes (8): NegotiationSession, NegotiationSubmissionOutcome, Proposal, ProposalStatus, NegotiationSessionId, build_proposal(), HumanNegotiationTests, NegotiationTests

### Community 208 - "auth.py"
Cohesion: 0.07
Nodes (29): _as_utc(), bootstrap_system_admin(), create_refresh_token(), CredentialsRequest, current_user(), CurrentUserResponse, _decode_token(), _development_actor() (+21 more)

### Community 209 - "maybe_complete_deal"
Cohesion: 0.48
Nodes (3): delivery_obligation_fulfilled(), maybe_complete_deal(), payments_reconciled()

## Knowledge Gaps
- **48 isolated node(s):** `syncally`, `PGPASSWORD`, `F1a Curated Repeatable Demo Fixture`, `Editorial Dark Theme Design System`, `ZIP HTML and Print Export Verification` (+43 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1929 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **56 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ActorContext` connect `Test Organization Invitations & Organizations` to `Conversations & Test Conversation Use`, `ConfiguredAIProvider`, `repositories/agreements.py`, `api/agreements.py`, `Test Conversation Routes (ConversationRouteTests)`, `InvalidTransition`, `ConversationContractTests`, `Test Agreement Routes (AgreementRouteTests)`, `AISuggestionProvider`, `OrganizationPermissionsTests`, `api/fulfillment.py`, `OrganizationId`, `MessageIdempotencyPostgresTests`, `Simulate Deal Flow & Test`, `CommunicationRepositoryTests`, `read_deal_route`, `identifiers.py`, `api/negotiation.py`, `ConversationUseCaseTests`, `application/conversations.py`, `platform.py`, `DealCasesTests`, `api/deals.py`, `PaymentIntentRepositoryTests`, `Agreement`, `api/organizations.py`, `organization.py`, `Test Organization Directory & Organizations`, `create_deal`, `get_commercial_document_draft_route`, `typing`, `Constraint`, `api/payments.py`, `AISuggestionProviderTests`, `._request`, `_active_admin_membership`, `CommercialDocumentDraftTests`, `create_counterparty_invitation`, `Test Deal Routes & Identity`, `CommitAgreementCommand`, `add_organization_member`, `require_system_admin`, `simulate_payment`, `Money`, `.setUp`, `SqlAlchemyReminderRepository`, `repositories/agreements.py`, `IdentityBoundaryTests`, `auth.py`, `NormalizedRequirement`, `authorize_payment_route`, `NegotiationRouteTests`, `PaymentNeedsAction`, `api/reminders.py`, `ai.py`, `review_constraint`, `ApprovalRoutingRouteTests`, `AiContextSelectionTests`?**
  _High betweenness centrality (0.094) - this node is a cross-community bridge._
- **Are the 160 inferred relationships involving `ActorContext` (e.g. with `approve_agreement_route()` and `commit_agreement_route()`) actually correct?**
  _`ActorContext` has 160 INFERRED edges - model-reasoned connections that need verification._
- **What connects `syncally`, `PGPASSWORD`, `F1a Curated Repeatable Demo Fixture` to the rest of the system?**
  _48 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Conversations & Test Conversation Use` be split into smaller, more focused modules?**
  _Cohesion score 0.05833905284831846 - nodes in this community are weakly interconnected._
- **Why does `OrganizationId` connect `OrganizationId` to `AIContractError`, `repositories/agreements.py`, `ConfiguredAIProvider`, `schedule_deal_reminders`, `repositories/agreements.py`, `api/agreements.py`, `Test Conversation Routes (ConversationRouteTests)`, `InvalidTransition`, `Test Agreement Routes (AgreementRouteTests)`, `repositories/communications.py`, `ConversationContractTests`, `Deal`, `NegotiationTests`, `OrganizationPermissionsTests`, `api/fulfillment.py`, `DealReminder`, `Test Outbox Dispatcher & Outbox`, `Test Organization Invitations & Organizations`, `CommunicationRepositoryTests`, `identifiers.py`, `api/negotiation.py`, `workflow_state.py`, `ConversationUseCaseTests`, `application/deal_cases.py`, `application/conversations.py`, `ApprovalRoutingTestCase`, `repositories/reminders.py`, `PaymentIntentRepositoryTests`, `DealCasesTests`, `Agreement`, `api/organizations.py`, `organization.py`, `create_deal`, `SqlAlchemyDealRepository`, `Constraint`, `api/payments.py`, `AISuggestionProviderTests`, `SqlAlchemyNegotiationRepository`, `CommercialDocumentDraftTests`, `NegotiationMigrationTests`, `CommitAgreementCommand`, `Money`, `repositories/agreements.py`, `Proposal`, `maybe_complete_deal`, `ai.py`, `ApprovalRoutingRouteTests`, `AiContextSelectionTests`?**
  _High betweenness centrality (0.063) - this node is a cross-community bridge._
- **Are the 74 inferred relationships involving `OrganizationId` (e.g. with `build_trade_terms_from_request()` and `create_reviewed_agreement_draft_route()`) actually correct?**
  _`OrganizationId` has 74 INFERRED edges - model-reasoned connections that need verification._
- **Should `AIContractError` be split into smaller, more focused modules?**
  _Cohesion score 0.10666666666666667 - nodes in this community are weakly interconnected._