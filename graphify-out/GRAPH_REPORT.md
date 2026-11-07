# Graph Report - SyncAlly  (2026-11-07)

## Corpus Check
- 332 files · ~294,029 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 14 file(s) not represented in the graph (top: (none) 8, .example 2, .ini 1)

## Summary
- 5141 nodes · 16736 edges · 186 communities (127 shown, 59 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 2220 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `f2df0c1d`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Conversations & Test Conversation Use
- AIContractError
- BaseModel
- repositories/agreements.py
- Test Ai Provider & Ai
- DealId
- repositories/agreements.py
- PaymentNeedsAction
- canonical_decimal
- api/agreements.py
- Test Conversation Routes (ConversationRouteTests)
- PaymentStatusExtendedModelTests
- Test Agreement Routes (AgreementRouteTests)
- Session
- process_payment_intent
- ExtractedFact
- NegotiationTests
- Types & Client
- listOrganizations
- OrganizationPermissionsTests
- generate_trade_pack
- Test Outbox Dispatcher & Outbox
- Simulate Deal Flow & Test
- Test Organization Invitations & Organizations
- SqlAlchemyCommunicationRepository
- Package & Vite.Config
- client.test.ts
- Dealconversationreview & Dealconversationreview.Test
- Skill & Skill.Md
- identifiers.py
- User
- DealDetailPage.test.tsx
- demo_lifecycle.py
- Aisuggestionreview & Suggestionpreview
- SyncAlly Implementation Plan Document
- PaymentProcessingTests
- application/deal_cases.py
- worker.py
- DealDetailPage.tsx
- Paymentstatuspanel & Paymentstatuspanel.Test
- PaymentIntentRepositoryTests
- services
- api/deals.py
- UUID
- DealWorkflow
- Test Dev Routes (DevRoutesTests)
- api/organizations.py
- DealWorkflow
- Test Organization Directory & Organizations
- create_deal
- DealWorkflowNotification
- Deal
- PaymentOutboxWorkerTests
- api/payments.py
- load_deal_workflow_state
- apiRequest
- NegotiationReview.tsx
- MessageIdempotencyPostgresTests
- Agreement
- Test Migration Lock & Env
- Payment Processing & Test Payment
- 01 Commercial Domain Model &
- create_counterparty_invitation
- Test Deal Routes & Identity
- seed_demo_data
- Compose.Yaml (volumes)
- Architectural & Implementation Plan: Step 08 Cancel Disputes (F8)
- CreateDealPage.tsx
- AmendmentTests
- OrganizationId
- PaymentReconciliationRepositoryTests
- Money
- PersistentDemoSeedTests
- AgreementReview.tsx
- refresh_access_token
- api/negotiation.py
- PaymentRetryableError
- IdentityBoundaryTests
- 13 Postgres Temporal & 14
- Tsconfig (tsconfig.json)
- Test Paypal Webhooks (FakeWebhookVerifier)
- Test Counterparty Onboarding Migration &
- InvalidTransition
- Test Operations & Test Outbox
- PaymentWorkItem
- environment
- Main & Test Identity Boundary
- dev.py
- Human Bilateral Amendment Workflow
- ApiError
- Test Organization Index Migration (OrganizationIndexPostgresMigrationTests)
- Server-Enforced Capability Matrix
- check_milestone_trigger_eligibility
- NegotiationRouteTests
- Constraint
- amendment.py
- application/conversations.py
- DatabasePersistenceTests
- Master Execution Contract
- 0005 Conversation Party Unique (Enforce
- Main (Request)
- Safe Operations and Recovery Guide
- temporal-namespace
- ai.py
- openai.py
- AISuggestionProviderTests
- x-app-environment
- Test Payment Mode Migration (PaymentModeMigrationTests)
- environment
- Test Communication Migration (ConversationPartyUniquenessMigrationTests)
- WorkflowWorkerIntegrationTests
- ConversationContractTests
- auth.py
- PaymentInvoiceReconciliation
- healthcheck
- AddMessageRequest
- DealWorkflowInput
- AiContextSelectionTests
- DealCasesTests
- Final Gates and Truthful Completion Specification
- Skill (Repo Idea Thinker Skill)
- hash_password
- Vite Env.D (ImportMeta)
- temporal-schema
- _register_shutdown_handlers
- Index (Frontend HTML Root Document)
- Pyproject (syncally)
- Customer journey: buyer and seller
- bounded_decimal
- sqlalchemy
- scaling
- Deal
- SyncAlly deployment
- AuditEvent
- FulfillmentPanel.tsx
- AI Provider Boundary Specification
- api/fulfillment.py
- Four-Dimension Profile Collections
- Two-Party Judge Journey
- volumes
- MASTER BOARD
- setup-temporal-postgres.sh
- FulfillmentMigrationTests
- ProviderInvoiceUniqueMigrationTests
- activities.py
- simulate_deal_flow.py
- MigrationConfigTests
- CollectionSchemaMigrationTests
- create-temporal-namespace.sh
- postgres-init.sh
- DomainError
- maybe_complete_deal
- STATE LOG: developer
- AIConfigurationError
- 0004_communication_sources_and_scope_indexes.py
- database_health
- MilestonePaymentsMigrationTests
- STATE LOG: planner
- NegotiationMigrationTests
- STATE LOG: reviewer
- CONTRACT: cancel-disputes-contract v1   status: FROZEN
- repositories/organizations.py
- sqlalchemy_orm
- Code Review: Step 08 Cancel Disputes (F8) — Work Package RV1
- _clear_fixture
- require_system_admin
- HealthRouteTests
- hostless-start.sh
- .test_login_rejects_demo_identities_outside_local_environments
- LiveClock.tsx
- _normalized_index_predicate

## God Nodes (most connected - your core abstractions)
1. `ActorContext` - 288 edges
2. `OrganizationId` - 207 edges
3. `InvariantViolation` - 134 edges
4. `Money` - 127 edges
5. `Deal` - 114 edges
6. `DealId` - 114 edges
7. `UserId` - 100 edges
8. `SqlAlchemyAgreementRepository` - 93 edges
9. `AISuggestionProviderTests` - 87 edges
10. `TradeTerms` - 86 edges

## Surprising Connections (you probably didn't know these)
- `1. Executive Summary & Change Stack Digest` --references--> `_resolve_deal_party_organization()`  [INFERRED]
  .orchestrator/reviews/RV1/review.md → backend/src/syncally/api/deals.py
- `5. Audit Checklist Verification` --references--> `_resolve_deal_party_organization()`  [INFERRED]
  .orchestrator/reviews/RV1/review.md → backend/src/syncally/api/deals.py
- `AST Metrics Table` --references--> `_raise_case_impl()`  [INFERRED]
  .orchestrator/reviews/RV1/review.md → backend/src/syncally/api/deals.py
- `AST Metrics Table` --references--> `_respond_case_impl()`  [INFERRED]
  .orchestrator/reviews/RV1/review.md → backend/src/syncally/api/deals.py
- `8. Import Safety Fix for `backend/src/syncally/infrastructure/ai/graph.py`` --references--> `draft_proposal_from_context()`  [INFERRED]
  .orchestrator/plans/cancel_disputes_plan.md → backend/src/syncally/application/ai.py

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

## Communities (186 total, 59 thin omitted)

### Community 0 - "Conversations & Test Conversation Use"
Cohesion: 0.06
Nodes (46): add_message_route(), AISuggestionRequest, clarify_fact_route(), confirm_fact_route(), ConstraintResponse, correct_fact_route(), CorrectFactRequest, create_fact_route() (+38 more)

### Community 1 - "AIContractError"
Cohesion: 0.09
Nodes (21): AIContractError, AIValidationClaim, _check_keys(), _contains_numeric_token(), _contains_token(), _date_value_is_present(), _decimal(), _fact_value_is_supported_by_quote() (+13 more)

### Community 3 - "repositories/agreements.py"
Cohesion: 0.08
Nodes (20): AgreementAccessDenied, AgreementAlreadyCommitted, AgreementNotFound, AgreementVersionConflict, create_agreement_draft(), CreateAgreementDraftCommand, DuplicateApproval, ProposalNotFound (+12 more)

### Community 4 - "Test Ai Provider & Ai"
Cohesion: 0.11
Nodes (12): extract_facts_from_context(), ConfiguredAIProvider, respond(), respond(), respond(), respond(), respond(), respond() (+4 more)

### Community 5 - "DealId"
Cohesion: 0.12
Nodes (5): ConstraintId, MessageId, constraint(), message(), CommunicationRepositoryTests

### Community 6 - "repositories/agreements.py"
Cohesion: 0.07
Nodes (28): _create_fixture(), DemoIdentity, _password_for(), _preflight(), _seed_identities(), AgreementVersion, Approval, Obligation (+20 more)

### Community 7 - "PaymentNeedsAction"
Cohesion: 0.09
Nodes (12): PaymentInvoiceRequest, PaymentNeedsAction, PaymentOutcomeUnknown, _has_excess_currency_precision(), PayPalSandboxInvoiceProvider, _provider_error_code(), _provider_request_id(), _send_request() (+4 more)

### Community 8 - "canonical_decimal"
Cohesion: 0.06
Nodes (10): get_paypal_webhook_configuration(), PaymentInvoiceNotice, main(), GmailSettings, PayPalSettings, _decimal(), canonical_decimal(), GmailSMTPInvoiceNotifier (+2 more)

### Community 9 - "api/agreements.py"
Cohesion: 0.05
Nodes (48): AgreementVersionResponse, AmendmentImpactResponse, ApprovalResponse, approve_agreement_route(), commit_agreement_route(), CommitAgreementRequest, compare_agreements_route(), create_agreement_draft_route() (+40 more)

### Community 10 - "Test Conversation Routes (ConversationRouteTests)"
Cohesion: 0.10
Nodes (3): ConversationRouteTests, respond(), send()

### Community 11 - "PaymentStatusExtendedModelTests"
Cohesion: 0.10
Nodes (3): PaymentStatusResponse, PaymentIntent, PaymentStatusExtendedModelTests

### Community 14 - "process_payment_intent"
Cohesion: 0.09
Nodes (9): payment_invoice_number(), PaymentInvoiceNotifier, PaymentInvoiceProvider, PaymentProcessingRepository, process_payment_intent(), reconcile_payment_intent(), _request_id_retry_window_expired(), require_payment_provider() (+1 more)

### Community 15 - "ExtractedFact"
Cohesion: 0.10
Nodes (9): FactExtractionRequest, ProposalDraftRequest, ExtractedFact, FactField, ProposedTerms, SourceReference, DemoAISuggestionProvider, _is_ambiguous_numeric_term() (+1 more)

### Community 16 - "NegotiationTests"
Cohesion: 0.08
Nodes (16): CreateReviewedAgreementDraftCommand, CandidateAcknowledgement, EvidenceReference, negotiate(), NegotiationCommand, NegotiationRepository, ProposalBase, create_reviewed_agreement_draft_in_transaction() (+8 more)

### Community 17 - "Types & Client"
Cohesion: 0.05
Nodes (73): describeDetail(), getDealMessageExistence(), isAbortError(), isRecord(), listPlatformOrganizations(), readErrorDetail(), updatePlatformOrganizationStatus(), AddCaseEvidenceInput (+65 more)

### Community 18 - "listOrganizations"
Cohesion: 0.06
Nodes (58): dependencies, react@^19.3.0, react-dom@^19.3.0, three@^0.186.1, getCurrentUser(), listOrganizations(), login(), clearAccessToken() (+50 more)

### Community 20 - "generate_trade_pack"
Cohesion: 0.32
Nodes (9): export_display_terms(), generate_trade_pack(), InvalidTradePack, _json_bytes(), _shape(), _trade_pack_html(), section(), TradePack (+1 more)

### Community 21 - "Test Outbox Dispatcher & Outbox"
Cohesion: 0.09
Nodes (14): build_deal_workflow_id(), dispatch_outbox_event(), OutboxDispatchResult, PendingOutboxEvent, apply_dispatch_result(), claim_next_pending_event(), _claim_statement(), dispatch_one_pending_event() (+6 more)

### Community 22 - "Simulate Deal Flow & Test"
Cohesion: 0.07
Nodes (8): ci_deal_flow_hook(), DealFlowContext, DealFlowSimulator, run_simulation(), SimulationError, StepRecord, TerminalFormatter, DemoLifecycleTests

### Community 23 - "Test Organization Invitations & Organizations"
Cohesion: 0.15
Nodes (8): accept_invitation(), _accept_invitation(), AcceptInvitationRequest, create_organization_invitation(), CreateInvitationRequest, _decode_invitation_token(), ActorContext, OrganizationInvitationTests

### Community 24 - "SqlAlchemyCommunicationRepository"
Cohesion: 0.06
Nodes (18): can_view_message(), ConcurrentConstraintUpdate, message_fingerprint(), ConstraintKind, ConstraintStatus, Conversation, Message, MessageSourceType (+10 more)

### Community 25 - "Package & Vite.Config"
Cohesion: 0.06
Nodes (47): devDependencies, eslint@^10.13.0, @eslint/js@^10.0.1, eslint-plugin-react-hooks@^7.1.1, eslint-plugin-react-refresh@^0.4.20, globals@^17.13.0, happy-dom@^21.0.3, @testing-library/dom@^10.4.1 (+39 more)

### Community 26 - "client.test.ts"
Cohesion: 0.11
Nodes (20): API_REQUEST_TIMEOUT_MS, listOrganizationMembers(), revokeOrganizationMember(), CREATED_MESSAGE, fetchMock, lastRequest(), sentBody(), updateMemberPermissions() (+12 more)

### Community 27 - "Dealconversationreview & Dealconversationreview.Test"
Cohesion: 0.07
Nodes (42): createDealMessage(), getNegotiation(), importDealThread(), listDealFacts(), listDealMessages(), previewDealThreadImport(), reviewDealFact(), updateFactVisibility() (+34 more)

### Community 28 - "Skill & Skill.Md"
Cohesion: 0.04
Nodes (43): API and Database Engineer Skill, API Design and Contract Semantics, Data Integrity and Invariant Enforcement, Query Performance and Projection Optimization, Schema Migration and Backward Compatibility, Transaction Boundaries and Atomicity, Archify Diagrammer Skill, Archify CLI Global Tool (+35 more)

### Community 29 - "identifiers.py"
Cohesion: 0.06
Nodes (13): AuditEventDraft, AuditRepository, commit_agreement(), ObligationRepository, PaymentMilestoneRepository, build_obligations(), build_payment_milestones(), ObligationDraft (+5 more)

### Community 30 - "User"
Cohesion: 0.15
Nodes (6): add_organization_member(), AddOrganizationMemberRequest, create_organization(), CreateOrganizationRequest, _is_duplicate_membership_error(), OrganizationOnboardingTests

### Community 31 - "DealDetailPage.test.tsx"
Cohesion: 0.08
Nodes (30): ApiError, getCommercialDocumentDraft(), getTradePack(), TradePackFormat, AgreementVersion, mockedApiRequest, mockedCreateOrganization, mockedGetCommercialDocumentDraft (+22 more)

### Community 32 - "demo_lifecycle.py"
Cohesion: 0.19
Nodes (8): _acquire_lock(), _is_demo_deal(), lock_demo_deal_creation(), lock_demo_payment_processing(), lock_demo_reset(), lock_outbox_dispatch(), DemoLifecycleLockTests, _postgres_session()

### Community 33 - "Aisuggestionreview & Suggestionpreview"
Cohesion: 0.09
Nodes (36): correctDealFact(), createDealFact(), draftDealProposal(), suggestDealFacts(), AIProvenance, DealFact, FactReviewAction, isPaymentTrigger() (+28 more)

### Community 34 - "SyncAlly Implementation Plan Document"
Cohesion: 0.16
Nodes (13): SyncAlly Architecture Document, System Topology and Ownership Boundaries, Temporal Worker and Outbox Architecture, Acceptance Criteria Verification Matrix, SyncAlly Implementation Plan Document, Issue #77 Architecture Contracts, Stage Lifecycle Roadmap, Frontend API Client and Authoritative State (+5 more)

### Community 35 - "PaymentProcessingTests"
Cohesion: 0.10
Nodes (6): PaymentProviderResolver, FakeInvoiceProvider, FakeProcessingRepository, PaymentProcessingTests, get_invoice_reconciliation(), _work_item()

### Community 36 - "application/deal_cases.py"
Cohesion: 0.09
Nodes (27): add_case_evidence(), AddCaseEvidenceCommand, assess_deal_case_blockers(), DealCaseRepository, DealNotFound, list_deal_cases(), raise_deal_case(), RaiseDealCaseCommand (+19 more)

### Community 37 - "worker.py"
Cohesion: 0.08
Nodes (17): OperationalRequestMiddleware, _connect_with_retry(), main(), run_forever(), main(), run_forever(), is_permanent_rpc_error(), configure_logging() (+9 more)

### Community 38 - "DealDetailPage.tsx"
Cohesion: 0.06
Nodes (37): getDeal(), getOrganization(), listDeals(), Deal, ViewerRole, AgreementReviewProps, DealCasesPanelProps, DealConstellation() (+29 more)

### Community 39 - "Paymentstatuspanel & Paymentstatuspanel.Test"
Cohesion: 0.09
Nodes (31): authorizeDealPayment(), listDealPaymentMilestones(), listPaymentStatuses(), previewDealPayment(), PaymentIntentStatus, formatCountdown(), parseTimestamp(), describeStatus() (+23 more)

### Community 40 - "PaymentIntentRepositoryTests"
Cohesion: 0.11
Nodes (6): VerifiedProviderPaymentStatus, queue_simulated_reconciliation(), require_simulation_scope(), simulation_state(), authorize_payment_intent_in_transaction(), PaymentIntentRepositoryTests

### Community 41 - "services"
Cohesion: 0.09
Nodes (32): build, depends_on, restart, context, dockerfile, migrate, temporal-namespace, build (+24 more)

### Community 42 - "api/deals.py"
Cohesion: 0.12
Nodes (31): add_evidence_deals_route(), _add_evidence_impl(), add_evidence_v1_route(), AddEvidenceRequest, CaseEvidenceResponse, CaseResponse, create_deal_route(), CreateDealRequest (+23 more)

### Community 44 - "DealWorkflow"
Cohesion: 0.09
Nodes (8): DealWorkflow, DealWorkflowInput, DealWorkflowUnitTests, new_workflow_input(), RefreshActivity, RefreshCall, run(), WorkflowWorkerIntegrationTests

### Community 46 - "api/organizations.py"
Cohesion: 0.07
Nodes (24): AcceptInvitationResponse, _active_admin_membership(), _case_insensitive_prefix(), _compute_effective_capabilities(), ContactResponse, CounterpartyInvitationResponse, _create_invitation_token(), _deal_awaiting_counterparty() (+16 more)

### Community 47 - "DealWorkflow"
Cohesion: 0.29
Nodes (3): DealWorkflowResult, DealWorkflowTests, new_notification()

### Community 49 - "create_deal"
Cohesion: 0.15
Nodes (6): _both_organizations_active(), create_deal(), CreateDealCommand, DealAccessDenied, DealUseCaseTests, FakeDealRepository

### Community 50 - "DealWorkflowNotification"
Cohesion: 0.11
Nodes (8): DealWorkflowStarter, WorkflowStartError, WorkflowStartOutcome, WorkflowStartPermanentError, WorkflowStartTransientError, DealWorkflowNotification, TemporalDealWorkflowStarter, TemporalAdapterTests

### Community 51 - "Deal"
Cohesion: 0.15
Nodes (3): _active_participation(), SqlAlchemyDealRepository, DealRepositoryTests

### Community 52 - "PaymentOutboxWorkerTests"
Cohesion: 0.09
Nodes (11): claim_next_payment_event(), _claim_statement(), _ClaimedPaymentEvent, dispatch_one_payment_event(), dispatch_pending_payment_events(), _finish_event(), FakeRepository, NoCallProvider (+3 more)

### Community 53 - "api/payments.py"
Cohesion: 0.04
Nodes (37): authorize_payment_route(), AuthorizePaymentRequest, AuthorizePaymentResponse, _check_milestone_delivery_confirmed(), get_payment_status_repository(), list_payment_milestones_route(), list_payment_statuses_route(), MilestoneAllocationResponse (+29 more)

### Community 54 - "load_deal_workflow_state"
Cohesion: 0.10
Nodes (10): DealWorkflowState, load_deal_workflow_state(), parse_workflow_uuid(), WorkflowAgreementRepository, WorkflowDealNotFound, WorkflowDealRepository, _domain_deal(), _FakeAgreementRepository (+2 more)

### Community 55 - "apiRequest"
Cohesion: 0.07
Nodes (36): acceptInvitation(), addCaseEvidence(), apiBaseUrl(), apiRequest(), createAgreementFromReviewedTerms(), getCurrentAgreement(), listDealCases(), raiseDealCase() (+28 more)

### Community 56 - "NegotiationReview.tsx"
Cohesion: 0.11
Nodes (23): negotiateDeal(), NegotiationView, DealConversationReviewProps, ACTION_LABELS, defaultDraft(), historyActionLabel(), isValidDecimal(), ItemDraft (+15 more)

### Community 57 - "MessageIdempotencyPostgresTests"
Cohesion: 0.12
Nodes (9): AddMessageCommand, MessageIdempotencyPostgresTests, _find_conversation(), _find_keyed_message(), rendezvous(), send(), wait_for(), ConversationUseCaseTests (+1 more)

### Community 58 - "Agreement"
Cohesion: 0.13
Nodes (9): _display(), generate_commercial_document_draft(), _render(), Agreement, Approval, AgreementId, CommercialDocumentDraftTests, FakeAgreementRepository (+1 more)

### Community 59 - "Test Migration Lock & Env"
Cohesion: 0.12
Nodes (8): run_migrations_online(), serialize_migrations(), _make_postgres_connection(), _make_sqlite_connection(), MigrationLockTests, simulated_migration(), PostgresRealAdvisoryLockTests, worker()

### Community 60 - "Payment Processing & Test Payment"
Cohesion: 0.14
Nodes (7): PaymentInvoiceLineItem, _build_in_process_client(), dispatch_payment(), session_factory(), SqlAlchemyPaymentProcessingRepository, transition(), transition()

### Community 61 - "01 Commercial Domain Model &"
Cohesion: 0.07
Nodes (19): AgreementVersion Aggregate, Append-Only AuditEvent Ledger, Commercial Constraint and Provenance, Deal Aggregate, Organization and Membership Entities, PaymentMilestone and Obligation, Proposal Aggregate and Terms Hash, Temporal Deal Workflow (+11 more)

### Community 62 - "create_counterparty_invitation"
Cohesion: 0.18
Nodes (5): create_counterparty_invitation(), CreateCounterpartyInvitationRequest, OnboardingConcurrencyCases, OnboardingPostgresConcurrencyTests, OnboardingSQLiteConcurrencyTests

### Community 64 - "seed_demo_data"
Cohesion: 0.20
Nodes (3): DemoCollisionError, seed_demo_data(), DemoSeedTests

### Community 65 - "Compose.Yaml (volumes)"
Cohesion: 0.09
Nodes (22): POSTGRES_DB, POSTGRES_PASSWORD, POSTGRES_USER, interval, retries, test, timeout, environment (+14 more)

### Community 66 - "Architectural & Implementation Plan: Step 08 Cancel Disputes (F8)"
Cohesion: 0.10
Nodes (20): 1. Executive Summary & Existing vs. Required Behavior, 2. Domain Entities & Value Objects, 3. Deal Aggregate Coordination, 4. Persistence Models & Alembic Migration 0025, 5. Application Layer: Use Cases & Operational Impact Assessment, 6. HTTP API Layer, 7. Frontend Integration, 8. Import Safety Fix for `backend/src/syncally/infrastructure/ai/graph.py` (+12 more)

### Community 67 - "CreateDealPage.tsx"
Cohesion: 0.16
Nodes (14): createCounterpartyInvitation(), createDeal(), CreateDealPage(), handleSubmit(), CreateDealPageProps, describeCreateError(), describeError(), DirectoryItem (+6 more)

### Community 68 - "AmendmentTests"
Cohesion: 0.05
Nodes (16): AgreementRepository, CommitAgreementCommand, create_reviewed_agreement_draft(), propose_amendment(), ProposeAmendmentCommand, record_approval(), RecordApprovalCommand, withdraw_amendment() (+8 more)

### Community 69 - "OrganizationId"
Cohesion: 0.07
Nodes (18): PaymentMilestone, VerifiedProviderPaymentState, AgreementVersionId, DealId, OrganizationId, PaymentIntentId, PaymentMilestoneId, UserId (+10 more)

### Community 71 - "Money"
Cohesion: 0.11
Nodes (17): build_trade_terms_from_request(), compare_agreement_terms(), _money(), _parse_money(), PaymentObligationAllocation, PaymentTerm, ShipmentItemAllocation, ShipmentTerm (+9 more)

### Community 72 - "PersistentDemoSeedTests"
Cohesion: 0.11
Nodes (7): fixture_id(), initialize_offline_database(), main(), OutboxEvent, PersistentDemoSeedTests, exercise_api(), start_deal_workflow()

### Community 73 - "AgreementReview.tsx"
Cohesion: 0.10
Nodes (38): commitAgreementVersion(), compareAgreementVersions(), getAgreementHistory(), getAgreementVersion(), getAmendmentImpact(), previewAmendmentImpact(), proposeAmendment(), recordAgreementDecision() (+30 more)

### Community 74 - "refresh_access_token"
Cohesion: 0.08
Nodes (5): _hash_refresh_token(), refresh_access_token(), RefreshRequest, RefreshToken, User

### Community 75 - "api/negotiation.py"
Cohesion: 0.14
Nodes (11): BaseRequest, CandidateRequest, EvidenceRequest, HistoryResponse, NegotiationRequest, NegotiationResponse, NegotiationResult, ProposalResponse (+3 more)

### Community 76 - "PaymentRetryableError"
Cohesion: 0.14
Nodes (4): _persist_paypal_webhook_event(), receive_paypal_invoice_webhook(), PaymentRetryableError, record_paypal_webhook_event()

### Community 77 - "IdentityBoundaryTests"
Cohesion: 0.10
Nodes (4): _is_loopback_temporal_address(), _is_weak_jwt_secret(), Settings, IdentityBoundaryTests

### Community 78 - "13 Postgres Temporal & 14"
Cohesion: 0.14
Nodes (9): Organization-Scoped Routing Policy, Durable Scoped Reminder Scheduling, Isolated PostgreSQL Migration and Constraint Testing, PostgreSQL and Temporal Verification Specification, Temporal Worker Crash Replay and Recovery, PayPal Sandbox Lifecycle Verification, PayPal Sandbox Specification F11b, Signature-Verified Webhook and Authenticated Reconciliation (+1 more)

### Community 79 - "Tsconfig (tsconfig.json)"
Cohesion: 0.11
Nodes (17): compilerOptions, allowImportingTsExtensions, jsx, lib, module, moduleDetection, moduleResolution, noEmit (+9 more)

### Community 81 - "Test Counterparty Onboarding Migration &"
Cohesion: 0.11
Nodes (3): create_database_engine(), CounterpartyOnboardingMigrationTests, DemoFixtureMigrationTests

### Community 82 - "InvalidTransition"
Cohesion: 0.10
Nodes (15): NegotiationConflict, NegotiationNotFound, NegotiationOrganizationRequired, NegotiationSession, NegotiationSubmissionOutcome, Proposal, ProposalStatus, InvalidTransition (+7 more)

### Community 83 - "Test Operations & Test Outbox"
Cohesion: 0.16
Nodes (5): OperationalFastAPI, captured_output(), SafeOperationsTests, exercise(), failed_db()

### Community 84 - "PaymentWorkItem"
Cohesion: 0.25
Nodes (3): PaymentInvoiceLookup, PaymentWorkItem, OfflineDemoInvoiceProvider

### Community 85 - "environment"
Cohesion: 0.29
Nodes (27): environment, AI_PROVIDER, APP_ENV, DATABASE_URL, DEBUG, DEFAULT_NAMESPACE, GMAIL_APP_PASSWORD, GMAIL_FROM_EMAIL (+19 more)

### Community 87 - "dev.py"
Cohesion: 0.14
Nodes (8): DevResetResponse, DevRoleSwitchRequest, _require_demo_admin(), _require_dev_environment(), reset_demo(), simulate_payment(), SimulatePaymentRequest, switch_role()

### Community 88 - "Human Bilateral Amendment Workflow"
Cohesion: 0.40
Nodes (3): Canonical Hash and Legacy Export Preservation, Human Bilateral Amendment Workflow, Cancellation and Dispute Case State Machine

### Community 89 - "ApiError"
Cohesion: 0.06
Nodes (31): addOrganizationMember(), createOrganization(), getOrganizationProfile(), updateOrganizationProfile(), ContactVisibility, Organization, OrganizationContact, COUNTRY_NAMES (+23 more)

### Community 94 - "Constraint"
Cohesion: 0.07
Nodes (4): Constraint, FakeCommunicationRepository, FakeCommunicationRepository, FakeCommunicationRepository

### Community 95 - "amendment.py"
Cohesion: 0.31
Nodes (4): AmendmentImpact, assess_amendment_impact(), FulfillmentObligationImpact, PaymentMilestoneImpact

### Community 96 - "application/conversations.py"
Cohesion: 0.06
Nodes (21): _list_all_constraints_for_owner(), add_message(), can_view_constraint(), CommunicationRepository, ConstraintRepository, correct_constraint(), create_manual_constraint(), CreateManualConstraintCommand (+13 more)

### Community 98 - "Master Execution Contract"
Cohesion: 0.14
Nodes (31): Execution Acceptance Gates, Master Execution Contract, Safe Windows PowerShell Runner, Private Contact Channels, Profiles Specification F14, Fresh Authorization Enforcement, Permissions Specification F15a, Append-Only Fulfillment Observations and Confirmations (+23 more)

### Community 99 - "0005 Conversation Party Unique (Enforce"
Cohesion: 0.36
Nodes (5): _create_party_unique_constraint(), _deduplicate_conversations(), downgrade(), _drop_party_unique_constraint(), upgrade()

### Community 101 - "Safe Operations and Recovery Guide"
Cohesion: 0.19
Nodes (15): PayPal Sandbox Invoicing and Reconciliation Flow, Backend README Document, F11a Explicit Payment Modes, F12 Committed Trade Packs, F1a Curated Repeatable Demo Fixture, F4 Invitations and Private Pending Deals, F5 Persisted Human Negotiation, F6 Agreement History and Comparison (+7 more)

### Community 102 - "temporal-namespace"
Cohesion: 0.09
Nodes (22): condition, aliases, api, temporal, APP_DOMAIN, TEMPORAL_DOMAIN, default, temporal-namespace (+14 more)

### Community 103 - "ai.py"
Cohesion: 0.08
Nodes (20): AIProvenance, AIRetryPolicy, AISuggestionProvider, call_with_bounded_retry(), draft_proposal(), draft_proposal_from_context(), extract_facts(), FactExtractionResult (+12 more)

### Community 104 - "openai.py"
Cohesion: 0.13
Nodes (13): AIPermanentError, AITransientError, parse_extracted_facts(), parse_proposed_terms(), AiContext, _json(), _object(), OpenAIChatCompletions (+5 more)

### Community 105 - "AISuggestionProviderTests"
Cohesion: 0.12
Nodes (4): DeterministicFakeAIProvider, AISuggestionProviderTests, extract_facts(), FakeWebhookVerifier

### Community 106 - "x-app-environment"
Cohesion: 0.10
Nodes (21): x-app-environment, AI_PROVIDER, APP_ENV, DATABASE_URL, DEBUG, GMAIL_APP_PASSWORD, GMAIL_FROM_EMAIL, GMAIL_SMTP_USERNAME (+13 more)

### Community 108 - "environment"
Cohesion: 0.12
Nodes (20): environment, BIND_ON_IP, DB, DB_PORT, DBNAME, POSTGRES_DB, POSTGRES_PASSWORD, POSTGRES_PWD (+12 more)

### Community 110 - "WorkflowWorkerIntegrationTests"
Cohesion: 0.20
Nodes (3): create_worker(), workflow_activities(), WorkflowWorkerTests

### Community 111 - "ConversationContractTests"
Cohesion: 0.12
Nodes (4): confirm_constraint(), ConstraintNotFound, ConversationContractTests, FakeConstraintRepository

### Community 112 - "auth.py"
Cohesion: 0.12
Nodes (17): _as_utc(), create_refresh_token(), CredentialsRequest, current_user(), CurrentUserResponse, _decode_token(), _development_actor(), development_login() (+9 more)

### Community 113 - "PaymentInvoiceReconciliation"
Cohesion: 0.25
Nodes (3): PaymentInvoiceReconciliation, FakePayPalInvoiceProvider, get_invoice_reconciliation()

### Community 114 - "healthcheck"
Cohesion: 0.16
Nodes (18): healthcheck, healthcheck, image, restart, volumes, temporal-schema, interval, retries (+10 more)

### Community 115 - "AddMessageRequest"
Cohesion: 0.19
Nodes (3): AddMessageRequest, CreateFactRequest, AddMessageRequestTests

### Community 116 - "DealWorkflowInput"
Cohesion: 0.13
Nodes (4): RefreshDealStateActivity, _workflow_input_value(), RefreshDealStateActivityTests, factory()

### Community 119 - "Final Gates and Truthful Completion Specification"
Cohesion: 0.20
Nodes (9): Evidence-Free Projection and Safety Bounds, F12 Trade Pack Handoff Document, Trade Pack Export Contract, Browser Verification Specification, ZIP HTML and Print Export Verification, Two-Party Isolated Browser Testing, Final Gates and Truthful Completion Specification, Full Gate Verification Suite (+1 more)

### Community 120 - "Skill (Repo Idea Thinker Skill)"
Cohesion: 0.50
Nodes (3): Repo Idea Thinker Skill, Repository-Grounded Ideation Discipline, Idea Quality Standards and Lightweight Validation

### Community 122 - "hash_password"
Cohesion: 0.14
Nodes (4): bootstrap_system_admin(), SystemAdminBootstrapRequest, hash_password(), verify_password()

### Community 134 - "temporal-schema"
Cohesion: 0.20
Nodes (10): condition, db, depends_on, temporal-schema, command, depends_on, entrypoint, image (+2 more)

### Community 135 - "_register_shutdown_handlers"
Cohesion: 0.27
Nodes (4): _register_shutdown_handlers(), _remove_shutdown_handlers(), _request_shutdown(), WorkerShutdownSignalTests

### Community 139 - "Customer journey: buyer and seller"
Cohesion: 0.29
Nodes (6): Customer contract, Customer journey: buyer and seller, Evidence and limits, Implementation constraints discovered during task mapping, Outcome, Task graph

### Community 140 - "bounded_decimal"
Cohesion: 0.09
Nodes (8): _normalized_text(), _require_decimal(), InvariantViolation, bounded_decimal(), currency_precision(), has_excess_currency_precision(), FulfillmentDomainTests, BoundedDecimalTests

### Community 141 - "sqlalchemy"
Cohesion: 0.03
Nodes (43): run_migrations_offline(), upgrade(), uuid_column(), upgrade(), upgrade(), upgrade(), upgrade(), downgrade() (+35 more)

### Community 142 - "scaling"
Cohesion: 0.10
Nodes (20): build, build_context_directory, max_cpu, max_memory, min_cpu, min_memory, system, dockerfile_path (+12 more)

### Community 143 - "Deal"
Cohesion: 0.09
Nodes (9): Deal, FakeDealRepository, DealAuthorizationTests, FakeDealRepository, 1. Executive Summary & Change Stack Digest, 2. Reviewer's Guide, AST Metrics Table, Blast-Radius & File Risk Table (+1 more)

### Community 144 - "SyncAlly deployment"
Cohesion: 0.20
Nodes (9): 1. Provision the VM and DNS, 2. Configure secrets, 3. Start the stack, Configure the Hostless App, Connect the Render frontend, Current $0 demo: Render + Hostless, OCI single-VM deployment, SyncAlly deployment (+1 more)

### Community 145 - "AuditEvent"
Cohesion: 0.22
Nodes (4): list_platform_organizations(), _organization_summary(), OrganizationStatusUpdate, update_platform_organization_status()

### Community 146 - "FulfillmentPanel.tsx"
Cohesion: 0.19
Nodes (14): getDealFulfillment(), recordDealFulfillment(), FulfillmentStage, errorMessage(), eventReporter(), FulfillmentPanel(), submit(), FulfillmentPanelProps (+6 more)

### Community 147 - "AI Provider Boundary Specification"
Cohesion: 0.53
Nodes (4): F2 AI Configuration and Provider Boundary, AI Provider Boundary Specification, AI Resilience and Retry Policy, AISuggestionProvider Contract

### Community 148 - "api/fulfillment.py"
Cohesion: 0.06
Nodes (28): _event_response(), FulfillmentEventResponse, FulfillmentSnapshotResponse, get_fulfillment_repository(), _raise_fulfillment_error(), read_fulfillment_route(), record_fulfillment_route(), RecordFulfillmentRequest (+20 more)

### Community 151 - "volumes"
Cohesion: 0.50
Nodes (4): volumes, caddy_config, caddy_data, postgres_data

### Community 152 - "MASTER BOARD"
Cohesion: 0.18
Nodes (10): ARBITRATION LOG, CAPABILITY MATRIX, CONSTRAINTS, CONTRACTS, DIRECTIVES, MASTER BOARD, OBJECTIVE, REQUIREMENTS (+2 more)

### Community 153 - "setup-temporal-postgres.sh"
Cohesion: 0.67
Nodes (3): PGPASSWORD, setup-temporal-postgres.sh script, update_database_schema()

### Community 156 - "activities.py"
Cohesion: 0.12
Nodes (3): NotificationKind, DealWorkflowStatus, _require_uuid()

### Community 162 - "DomainError"
Cohesion: 0.06
Nodes (16): CommercialDocumentDraftResponse, get_commercial_document_draft_route(), get_trade_pack_route(), OutboxEventDraft, OutboxRepository, AgreementNotCommitted, CommercialDocumentDraft, authorize_payment_intent() (+8 more)

### Community 163 - "maybe_complete_deal"
Cohesion: 0.48
Nodes (3): delivery_obligation_fulfilled(), maybe_complete_deal(), payments_reconciled()

### Community 166 - "STATE LOG: developer"
Cohesion: 0.25
Nodes (7): BLOCKERS & ESCALATIONS, CURRENT_STATE, ENVIRONMENT_SNAPSHOT (ENV), GOAL & ACCEPTANCE CRITERIA, IDENTITY & ROLE, IMPLEMENTATION_LEDGER, STATE LOG: developer

### Community 167 - "AIConfigurationError"
Cohesion: 0.20
Nodes (3): get_ai_suggestion_provider(), AIConfigurationError, AIProviderError

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

### Community 175 - "repositories/organizations.py"
Cohesion: 0.07
Nodes (21): ContactVisibility, _normalize_string(), Organization, OrganizationCapability, OrganizationContact, OrganizationMember, OrganizationMemberRole, OrganizationMemberStatus (+13 more)

### Community 178 - "Code Review: Step 08 Cancel Disputes (F8) — Work Package RV1"
Cohesion: 0.29
Nodes (6): 1. Medium (P2) — Parallel Alembic Migration Heads Branching From 0024_amendments, 3. Merge Gate, 4. Findings, 6. Empirical Verification Summary, 7. Review Verdict, Code Review: Step 08 Cancel Disputes (F8) — Work Package RV1

## Knowledge Gaps
- **48 isolated node(s):** `syncally`, `PGPASSWORD`, `F1a Curated Repeatable Demo Fixture`, `Editorial Dark Theme Design System`, `ZIP HTML and Print Export Verification` (+43 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1597 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **59 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ActorContext` connect `Test Organization Invitations & Organizations` to `Conversations & Test Conversation Use`, `DealId`, `api/agreements.py`, `Test Conversation Routes (ConversationRouteTests)`, `PaymentStatusExtendedModelTests`, `Test Agreement Routes (AgreementRouteTests)`, `Deal`, `AuditEvent`, `OrganizationPermissionsTests`, `api/fulfillment.py`, `Simulate Deal Flow & Test`, `SqlAlchemyCommunicationRepository`, `identifiers.py`, `User`, `DomainError`, `PaymentIntentRepositoryTests`, `api/deals.py`, `api/organizations.py`, `repositories/organizations.py`, `Test Organization Directory & Organizations`, `sqlalchemy_orm`, `create_deal`, `require_system_admin`, `api/payments.py`, `MessageIdempotencyPostgresTests`, `Agreement`, `create_counterparty_invitation`, `Test Deal Routes & Identity`, `AmendmentTests`, `OrganizationId`, `api/negotiation.py`, `IdentityBoundaryTests`, `dev.py`, `NegotiationRouteTests`, `Constraint`, `application/conversations.py`, `ai.py`, `AISuggestionProviderTests`, `ConversationContractTests`, `auth.py`, `AiContextSelectionTests`, `DealCasesTests`?**
  _High betweenness centrality (0.136) - this node is a cross-community bridge._
- **Are the 137 inferred relationships involving `ActorContext` (e.g. with `approve_agreement_route()` and `commit_agreement_route()`) actually correct?**
  _`ActorContext` has 137 INFERRED edges - model-reasoned connections that need verification._
- **What connects `syncally`, `PGPASSWORD`, `F1a Curated Repeatable Demo Fixture` to the rest of the system?**
  _48 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Conversations & Test Conversation Use` be split into smaller, more focused modules?**
  _Cohesion score 0.06335204490777867 - nodes in this community are weakly interconnected._
- **Why does `OrganizationId` connect `OrganizationId` to `Conversations & Test Conversation Use`, `AIContractError`, `repositories/agreements.py`, `DealId`, `repositories/agreements.py`, `api/agreements.py`, `Test Conversation Routes (ConversationRouteTests)`, `PaymentStatusExtendedModelTests`, `Test Agreement Routes (AgreementRouteTests)`, `ExtractedFact`, `Deal`, `NegotiationTests`, `OrganizationPermissionsTests`, `api/fulfillment.py`, `Test Outbox Dispatcher & Outbox`, `SqlAlchemyCommunicationRepository`, `identifiers.py`, `maybe_complete_deal`, `application/deal_cases.py`, `PaymentIntentRepositoryTests`, `NegotiationMigrationTests`, `api/organizations.py`, `repositories/organizations.py`, `create_deal`, `Deal`, `api/payments.py`, `load_deal_workflow_state`, `MessageIdempotencyPostgresTests`, `Agreement`, `create_counterparty_invitation`, `AmendmentTests`, `Money`, `api/negotiation.py`, `Test Counterparty Onboarding Migration &`, `InvalidTransition`, `Constraint`, `application/conversations.py`, `ai.py`, `AISuggestionProviderTests`, `ConversationContractTests`, `AiContextSelectionTests`, `DealCasesTests`?**
  _High betweenness centrality (0.056) - this node is a cross-community bridge._
- **Are the 68 inferred relationships involving `OrganizationId` (e.g. with `build_trade_terms_from_request()` and `create_reviewed_agreement_draft_route()`) actually correct?**
  _`OrganizationId` has 68 INFERRED edges - model-reasoned connections that need verification._
- **Should `AIContractError` be split into smaller, more focused modules?**
  _Cohesion score 0.09074410163339383 - nodes in this community are weakly interconnected._