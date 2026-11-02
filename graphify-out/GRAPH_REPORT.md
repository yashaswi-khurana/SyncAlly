# Graph Report - SyncAlly  (2026-11-02)

## Corpus Check
- 279 files · ~234,981 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 8 file(s) not represented in the graph (top: (none) 4, .example 1, .ini 1)

## Summary
- 4231 nodes · 13721 edges · 148 communities (96 shown, 52 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 1810 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `c7b7fe44`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Conversations & Test Conversation Use
- contracts.py
- identifiers.py
- api/payments.py
- Test Ai Provider & Ai
- OrganizationId
- Seed Demo & Deals
- PaymentNeedsAction
- App.test.tsx
- Agreements & Obligations
- Test Conversation Routes (ConversationRouteTests)
- Agreement
- Test Agreement Routes (AgreementRouteTests)
- auth.py
- process_payment_intent
- Agreements & Agreement
- NegotiationTests
- Types & Client
- ai.py
- CommercialDocumentDraftTests
- Test Outbox Dispatcher & Outbox
- Simulate Deal Flow & Test
- Test Organization Invitations & Organizations
- Communications & Conversations
- Package & Vite.Config
- client.test.ts
- Dealconversationreview & Dealconversationreview.Test
- Skill & Skill.Md
- sqlalchemy
- User
- DealDetailPage.test.tsx
- Agreements & Counterparty Onboarding
- Aisuggestionreview & Suggestionpreview
- SyncAlly Implementation Plan Document
- PaymentProcessingTests
- Test Agreements & Test Local
- log_operation
- InvariantViolation
- Paymentstatuspanel & Paymentstatuspanel.Test
- Test Payment Intent Repository &
- main.py
- api/deals.py
- GmailSMTPInvoiceNotifier
- PaymentInvoiceReconciliation
- Test Dev Routes (DevRoutesTests)
- database.py
- DealWorkflow
- Test Organization Directory & Organizations
- Negotiation & Proposal
- test_outbox_dispatcher.py
- Deal & Test Deal Authorization
- Test Payment Outbox & Test
- react
- Workflow State & Test Workflow
- DealWorkflowTests
- Agreementreview & Client
- Organizations & Test Organization Onboarding
- Test Workflow Activities & Activities
- Test Migration Lock & Env
- Payment Processing & Test Payment
- 01 Commercial Domain Model &
- simulate_deal_flow.py
- Test Deal Routes & Identity
- Test Identity Boundary & Config
- Compose.Yaml (volumes)
- SqlAlchemyPaymentIntentRepository
- Test Workflow Worker & Worker
- api/organizations.py
- worker.py
- Test Payment Reconciliation & Intent
- Money
- PersistentDemoSeedTests
- Test Deal Repository & Deals
- Createdealpage & Createdealpage.Test
- Negotiation (BaseRequest)
- Test Organization Invitations & Organizations
- application/conversations.py
- 13 Postgres Temporal & 14
- Tsconfig (tsconfig.json)
- Test Paypal Webhooks (FakeWebhookVerifier)
- Test Counterparty Onboarding Migration &
- Test Communication Repositories (MessageIdempotencyPostgresTests)
- Test Operations & Test Outbox
- TradeTerms
- Test Ai Context & Conversations
- Main & Test Identity Boundary
- demo_lifecycle.py
- Human Bilateral Amendment Workflow
- App.tsx
- Test Organization Index Migration (OrganizationIndexPostgresMigrationTests)
- Server-Enforced Capability Matrix
- PaymentNeedsAction
- Test Negotiation (NegotiationRouteTests)
- InvariantViolation
- application/identity.py
- AgreementVersionId
- Test Database (DatabasePersistenceTests)
- Master Execution Contract
- 0005 Conversation Party Unique (Enforce
- Main (Request)
- Safe Operations and Recovery Guide
- migration_config.py
- refresh_access_token
- Test Negotiation Migration (NegotiationMigrationTests)
- Test Payment Mode Migration (PaymentModeMigrationTests)
- _to_domain
- Test Communication Migration (ConversationPartyUniquenessMigrationTests)
- DealWorkflowInput
- VerifiedProviderPaymentState
- WorkflowWorkerIntegrationTests
- FakeDealRepository
- NegotiationSession
- Test Provider Invoice Unique Migration
- _domain_deal
- NegotiationPostgresRaceTests
- Final Gates and Truthful Completion Specification
- Skill (Repo Idea Thinker Skill)
- login
- Vite Env.D (ImportMeta)
- simulate_payment
- DealWorkflowStarter
- Index (Frontend HTML Root Document)
- Pyproject (syncally)
- .refresh_deal_state
- PostgresDispatcherTests
- NegotiationCommand
- field_validator
- AI Provider Boundary Specification
- Four-Dimension Profile Collections
- Two-Party Judge Journey

## God Nodes (most connected - your core abstractions)
1. `ActorContext` - 238 edges
2. `OrganizationId` - 168 edges
3. `InvariantViolation` - 110 edges
4. `Deal` - 97 edges
5. `DealId` - 93 edges
6. `Money` - 93 edges
7. `UserId` - 88 edges
8. `AISuggestionProviderTests` - 87 edges
9. `ConversationRouteTests` - 78 edges
10. `SqlAlchemyAgreementRepository` - 76 edges

## Surprising Connections (you probably didn't know these)
- `Message Idempotency and Constraints` --semantically_similar_to--> `PayPal Sandbox Invoicing and Reconciliation Flow`  [INFERRED] [semantically similar]
  backend/README.md → ARCHITECTURE.md
- `Webhook Reconciliation Protocol` --implements--> `PayPal Sandbox Invoicing and Reconciliation Flow`  [INFERRED]
  docs/operations.md → ARCHITECTURE.md
- `Temporal Worker and Outbox Architecture` --references--> `Outbox Recovery and Workflow Replay`  [INFERRED]
  ARCHITECTURE.md → docs/operations.md
- `Temporal Worker Restart Smoke Test` --conceptually_related_to--> `Temporal Deal Workflow`  [INFERRED]
  infra/README.md → docs/architecture/02-temporal-deal-workflow-contract.md
- `mockNegotiation()` --indirect_call--> `getNegotiation()`  [INFERRED]
  frontend/src/deals/DealConversationReview.test.tsx → frontend/src/api/client.ts

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

## Communities (148 total, 52 thin omitted)

### Community 0 - "Conversations & Test Conversation Use"
Cohesion: 0.05
Nodes (48): add_message_route(), AddMessageRequest, AISuggestionRequest, clarify_fact_route(), confirm_fact_route(), ConstraintResponse, correct_fact_route(), CorrectFactRequest (+40 more)

### Community 1 - "contracts.py"
Cohesion: 0.07
Nodes (25): _rejected_fact_result(), AIContractError, AIValidationClaim, _check_keys(), _contains_numeric_token(), _contains_token(), _date_value_is_present(), _decimal() (+17 more)

### Community 3 - "api/payments.py"
Cohesion: 0.05
Nodes (36): authorize_payment_route(), AuthorizePaymentRequest, AuthorizePaymentResponse, get_payment_status_repository(), list_payment_statuses_route(), PaymentOutboxStatus, PaymentPreviewResponse, preview_payment_route() (+28 more)

### Community 4 - "Test Ai Provider & Ai"
Cohesion: 0.06
Nodes (17): AIRetryPolicy, call_with_bounded_retry(), extract_facts_from_context(), DeterministicFakeAIProvider, ConfiguredAIProvider, AISuggestionProviderTests, respond(), respond() (+9 more)

### Community 5 - "OrganizationId"
Cohesion: 0.05
Nodes (18): ConcurrentConstraintUpdate, confirm_constraint(), ConstraintNotFound, ConstraintId, ConversationId, DealId, MessageId, OrganizationId (+10 more)

### Community 6 - "Seed Demo & Deals"
Cohesion: 0.06
Nodes (36): _accept_invitation(), _decode_invitation_token(), hash_password(), verify_password(), _clear_fixture(), _create_fixture(), _delete_scoped(), DemoCollisionError (+28 more)

### Community 7 - "PaymentNeedsAction"
Cohesion: 0.09
Nodes (11): receive_paypal_invoice_webhook(), PaymentOutcomeUnknown, PaymentRetryableError, _has_excess_currency_precision(), PayPalSandboxInvoiceProvider, _provider_error_code(), _provider_request_id(), _send_request() (+3 more)

### Community 8 - "App.test.tsx"
Cohesion: 0.09
Nodes (31): listOrganizations(), clearAccessToken(), getAccessToken(), setTokens(), TokenResponse, mockedApiRequest, mockedCreateOrganization, mockedGetCommercialDocumentDraft (+23 more)

### Community 9 - "Agreements & Obligations"
Cohesion: 0.10
Nodes (13): AgreementRepository, AuditEventDraft, AuditRepository, commit_agreement(), create_agreement_draft(), create_reviewed_agreement_draft(), CreateReviewedAgreementDraftCommand, ObligationRepository (+5 more)

### Community 10 - "Test Conversation Routes (ConversationRouteTests)"
Cohesion: 0.10
Nodes (3): ConversationRouteTests, respond(), send()

### Community 11 - "Agreement"
Cohesion: 0.32
Nodes (3): Agreement, AgreementId, FakeAgreementRepository

### Community 13 - "auth.py"
Cohesion: 0.10
Nodes (11): _as_utc(), create_refresh_token(), _decode_token(), _development_actor(), development_login(), _encode_access_token(), get_current_actor(), _replay_rotation() (+3 more)

### Community 14 - "process_payment_intent"
Cohesion: 0.08
Nodes (11): payment_invoice_number(), PaymentInvoiceNotifier, PaymentInvoiceProvider, PaymentProcessingRepository, process_payment_intent(), reconcile_payment_intent(), _request_id_retry_window_expired(), require_payment_provider() (+3 more)

### Community 15 - "Agreements & Agreement"
Cohesion: 0.08
Nodes (26): AgreementVersionResponse, ApprovalResponse, approve_agreement_route(), commit_agreement_route(), CommitAgreementRequest, compare_agreements_route(), create_agreement_draft_route(), create_reviewed_agreement_draft_route() (+18 more)

### Community 16 - "NegotiationTests"
Cohesion: 0.20
Nodes (4): EvidenceReference, ProposalBase, negotiate_in_transaction(), NegotiationTests

### Community 17 - "Types & Client"
Cohesion: 0.07
Nodes (47): describeDetail(), getDealMessageExistence(), isAbortError(), isRecord(), readErrorDetail(), AgreementApproval, AgreementComparison, AgreementEvidence (+39 more)

### Community 18 - "ai.py"
Cohesion: 0.05
Nodes (36): get_ai_suggestion_provider(), AIConfigurationError, AIPermanentError, AIProvenance, AIProviderError, AISuggestionProvider, AITransientError, draft_proposal() (+28 more)

### Community 20 - "CommercialDocumentDraftTests"
Cohesion: 0.08
Nodes (20): CommercialDocumentDraftResponse, get_commercial_document_draft_route(), get_trade_pack_route(), AgreementNotCommitted, CommercialDocumentDraft, _display(), export_display_terms(), generate_commercial_document_draft() (+12 more)

### Community 21 - "Test Outbox Dispatcher & Outbox"
Cohesion: 0.08
Nodes (15): build_deal_workflow_id(), dispatch_outbox_event(), OutboxDispatchResult, PendingOutboxEvent, WorkflowStartTransientError, apply_dispatch_result(), claim_next_pending_event(), _claim_statement() (+7 more)

### Community 22 - "Simulate Deal Flow & Test"
Cohesion: 0.07
Nodes (11): _build_in_process_client(), dispatch_payment(), session_factory(), ci_deal_flow_hook(), DealFlowContext, DealFlowSimulator, run_simulation(), SimulationError (+3 more)

### Community 23 - "Test Organization Invitations & Organizations"
Cohesion: 0.17
Nodes (6): accept_invitation(), AcceptInvitationRequest, create_organization_invitation(), CreateInvitationRequest, ActorContext, OrganizationInvitationTests

### Community 24 - "Communications & Conversations"
Cohesion: 0.04
Nodes (20): message_fingerprint(), Constraint, ConstraintKind, ConstraintStatus, Conversation, Message, MessageSourceType, Visibility (+12 more)

### Community 25 - "Package & Vite.Config"
Cohesion: 0.06
Nodes (47): devDependencies, eslint@^10.13.0, @eslint/js@^10.0.1, eslint-plugin-react-hooks@^7.1.1, eslint-plugin-react-refresh@^0.4.20, globals@^17.13.0, happy-dom@^21.0.3, @testing-library/dom@^10.4.1 (+39 more)

### Community 26 - "client.test.ts"
Cohesion: 0.10
Nodes (21): API_REQUEST_TIMEOUT_MS, listOrganizationMembers(), revokeOrganizationMember(), CREATED_MESSAGE, fetchMock, lastRequest(), sentBody(), updateMemberPermissions() (+13 more)

### Community 27 - "Dealconversationreview & Dealconversationreview.Test"
Cohesion: 0.07
Nodes (44): acceptInvitation(), apiBaseUrl(), apiRequest(), createAgreementFromReviewedTerms(), createDealMessage(), importDealThread(), listDealFacts(), listDealMessages() (+36 more)

### Community 28 - "Skill & Skill.Md"
Cohesion: 0.04
Nodes (43): API and Database Engineer Skill, API Design and Contract Semantics, Data Integrity and Invariant Enforcement, Query Performance and Projection Optimization, Schema Migration and Backward Compatibility, Transaction Boundaries and Atomicity, Archify Diagrammer Skill, Archify CLI Global Tool (+35 more)

### Community 29 - "sqlalchemy"
Cohesion: 0.05
Nodes (27): upgrade(), uuid_column(), upgrade(), upgrade(), _create_scope_index(), downgrade(), _drop_scope_index(), upgrade() (+19 more)

### Community 30 - "User"
Cohesion: 0.17
Nodes (5): update_member_permissions(), UpdateMemberPermissionsRequest, User, FakeWebhookVerifier, OrganizationPermissionsTests

### Community 31 - "DealDetailPage.test.tsx"
Cohesion: 0.07
Nodes (37): getCommercialDocumentDraft(), getDeal(), getNegotiation(), negotiateDeal(), Deal, NegotiationView, createReviewedAgreement(), DealConstellation() (+29 more)

### Community 32 - "Agreements & Counterparty Onboarding"
Cohesion: 0.07
Nodes (22): AgreementAlreadyCommitted, AgreementVersionConflict, CreateAgreementDraftCommand, DuplicateApproval, ProposalNotFound, StaleAgreementVersion, UnauthorizedApproval, WrongTermsHash (+14 more)

### Community 33 - "Aisuggestionreview & Suggestionpreview"
Cohesion: 0.09
Nodes (35): correctDealFact(), createDealFact(), draftDealProposal(), suggestDealFacts(), AIProvenance, DealFact, FactReviewAction, isPaymentTrigger() (+27 more)

### Community 34 - "SyncAlly Implementation Plan Document"
Cohesion: 0.16
Nodes (13): SyncAlly Architecture Document, System Topology and Ownership Boundaries, Temporal Worker and Outbox Architecture, Acceptance Criteria Verification Matrix, SyncAlly Implementation Plan Document, Issue #77 Architecture Contracts, Stage Lifecycle Roadmap, Frontend API Client and Authoritative State (+5 more)

### Community 35 - "PaymentProcessingTests"
Cohesion: 0.10
Nodes (6): PaymentProviderResolver, FakeInvoiceProvider, FakeProcessingRepository, PaymentProcessingTests, get_invoice_reconciliation(), _work_item()

### Community 36 - "Test Agreements & Test Local"
Cohesion: 0.08
Nodes (10): CommitAgreementCommand, compare_agreement_terms(), record_approval(), RecordApprovalCommand, Approval, commit_agreement_in_transaction(), record_approval_in_transaction(), AgreementCommitTests (+2 more)

### Community 37 - "log_operation"
Cohesion: 0.08
Nodes (16): OperationalRequestMiddleware, _connect_with_retry(), main(), run_forever(), main(), run_forever(), configure_logging(), log_operation() (+8 more)

### Community 38 - "InvariantViolation"
Cohesion: 0.07
Nodes (20): ContactVisibility, _normalize_string(), Organization, OrganizationCapability, OrganizationContact, OrganizationMember, OrganizationMemberRole, OrganizationMemberStatus (+12 more)

### Community 39 - "Paymentstatuspanel & Paymentstatuspanel.Test"
Cohesion: 0.10
Nodes (30): authorizeDealPayment(), getOrganization(), listPaymentStatuses(), previewDealPayment(), PaymentIntentStatus, describeStatus(), displayAmount(), extractInvoiceNumber() (+22 more)

### Community 40 - "Test Payment Intent Repository &"
Cohesion: 0.11
Nodes (4): _persist_paypal_webhook_event(), authorize_payment_intent_in_transaction(), record_paypal_webhook_event(), PaymentIntentRepositoryTests

### Community 41 - "main.py"
Cohesion: 0.09
Nodes (4): _require_dev_environment(), database_health(), health(), OperationalFastAPI

### Community 42 - "api/deals.py"
Cohesion: 0.06
Nodes (19): create_deal_route(), CreateDealRequest, DealResponse, DealSummaryResponse, get_deal_repository(), list_deals_route(), read_deal_route(), _to_response() (+11 more)

### Community 43 - "GmailSMTPInvoiceNotifier"
Cohesion: 0.07
Nodes (8): get_paypal_webhook_configuration(), PaymentInvoiceNotice, main(), GmailSettings, PayPalSettings, GmailSMTPInvoiceNotifier, _FakeSMTP, GmailSMTPInvoiceNotifierTests

### Community 44 - "PaymentInvoiceReconciliation"
Cohesion: 0.23
Nodes (3): PaymentInvoiceReconciliation, FakePayPalInvoiceProvider, get_invoice_reconciliation()

### Community 46 - "database.py"
Cohesion: 0.11
Nodes (4): CommunicationMigrationTests, MessageIdempotencyMigrationTests, OrganizationIndexMigrationTests, PaymentCreateStartedMigrationTests

### Community 49 - "Negotiation & Proposal"
Cohesion: 0.19
Nodes (6): NegotiationConflict, NegotiationNotFound, NegotiationOrganizationRequired, ProposalId, SqlAlchemyNegotiationRepository, projection()

### Community 50 - "test_outbox_dispatcher.py"
Cohesion: 0.08
Nodes (9): WorkflowStartError, WorkflowStartOutcome, WorkflowStartPermanentError, DealWorkflowNotification, NotificationKind, is_permanent_rpc_error(), TemporalDealWorkflowStarter, OutboxDispatchMigrationTests (+1 more)

### Community 51 - "Deal & Test Deal Authorization"
Cohesion: 0.14
Nodes (3): Deal, DealStatus, FakeDealRepository

### Community 52 - "Test Payment Outbox & Test"
Cohesion: 0.09
Nodes (10): claim_next_payment_event(), _claim_statement(), _ClaimedPaymentEvent, dispatch_one_payment_event(), _finish_event(), FakeRepository, NoCallProvider, PaymentOutboxWorkerTests (+2 more)

### Community 53 - "react"
Cohesion: 0.06
Nodes (32): addOrganizationMember(), createOrganization(), getOrganizationProfile(), updateOrganizationProfile(), ContactVisibility, Organization, OrganizationContact, COUNTRY_NAMES (+24 more)

### Community 54 - "Workflow State & Test Workflow"
Cohesion: 0.14
Nodes (6): DealWorkflowState, load_deal_workflow_state(), parse_workflow_uuid(), WorkflowAgreementRepository, WorkflowDealNotFound, WorkflowDealRepository

### Community 55 - "DealWorkflowTests"
Cohesion: 0.29
Nodes (3): DealWorkflowResult, DealWorkflowTests, new_notification()

### Community 56 - "Agreementreview & Client"
Cohesion: 0.08
Nodes (38): ApiError, commitAgreementVersion(), compareAgreementVersions(), getAgreementHistory(), getAgreementVersion(), getCurrentAgreement(), getTradePack(), recordAgreementDecision() (+30 more)

### Community 57 - "Organizations & Test Organization Onboarding"
Cohesion: 0.17
Nodes (6): add_organization_member(), AddOrganizationMemberRequest, create_organization(), CreateOrganizationRequest, _is_duplicate_membership_error(), OrganizationOnboardingTests

### Community 58 - "Test Workflow Activities & Activities"
Cohesion: 0.18
Nodes (3): RefreshDealStateActivity, RefreshDealStateActivityTests, factory()

### Community 59 - "Test Migration Lock & Env"
Cohesion: 0.12
Nodes (8): run_migrations_online(), serialize_migrations(), _make_postgres_connection(), _make_sqlite_connection(), MigrationLockTests, simulated_migration(), PostgresRealAdvisoryLockTests, worker()

### Community 60 - "Payment Processing & Test Payment"
Cohesion: 0.17
Nodes (4): PaymentInvoiceLineItem, SqlAlchemyPaymentProcessingRepository, transition(), transition()

### Community 61 - "01 Commercial Domain Model &"
Cohesion: 0.07
Nodes (19): AgreementVersion Aggregate, Append-Only AuditEvent Ledger, Commercial Constraint and Provenance, Deal Aggregate, Organization and Membership Entities, PaymentMilestone and Obligation, Proposal Aggregate and Terms Hash, Temporal Deal Workflow (+11 more)

### Community 64 - "Test Identity Boundary & Config"
Cohesion: 0.15
Nodes (3): _is_weak_jwt_secret(), Settings, IdentityBoundaryTests

### Community 65 - "Compose.Yaml (volumes)"
Cohesion: 0.09
Nodes (22): POSTGRES_DB, POSTGRES_PASSWORD, POSTGRES_USER, interval, retries, test, timeout, environment (+14 more)

### Community 66 - "SqlAlchemyPaymentIntentRepository"
Cohesion: 0.11
Nodes (4): PaymentStatusResponse, PaymentIntent, InvalidTransition, PaymentStatusExtendedModelTests

### Community 67 - "Test Workflow Worker & Worker"
Cohesion: 0.20
Nodes (3): create_worker(), workflow_activities(), WorkflowWorkerTests

### Community 68 - "api/organizations.py"
Cohesion: 0.08
Nodes (22): AcceptInvitationResponse, _active_admin_membership(), _case_insensitive_prefix(), _compute_effective_capabilities(), ContactResponse, CounterpartyInvitationResponse, _create_invitation_token(), _deal_awaiting_counterparty() (+14 more)

### Community 69 - "worker.py"
Cohesion: 0.08
Nodes (5): _register_shutdown_handlers(), _remove_shutdown_handlers(), _request_shutdown(), HealthRouteTests, WorkerShutdownSignalTests

### Community 71 - "Money"
Cohesion: 0.20
Nodes (9): _money(), _parse_money(), PaymentTerm, ShipmentTerm, TradeLineItem, Money, DecimalCanonicalizationTests, TradeTermsTests (+1 more)

### Community 72 - "PersistentDemoSeedTests"
Cohesion: 0.10
Nodes (6): fixture_id(), initialize_offline_database(), main(), OutboxEvent, PersistentDemoSeedTests, exercise_api()

### Community 74 - "Createdealpage & Createdealpage.Test"
Cohesion: 0.08
Nodes (25): createCounterpartyInvitation(), createDeal(), listDeals(), ViewerRole, CreateDealPage(), handleSubmit(), CreateDealPageProps, describeCreateError() (+17 more)

### Community 75 - "Negotiation (BaseRequest)"
Cohesion: 0.13
Nodes (12): BaseRequest, CandidateRequest, EvidenceRequest, HistoryResponse, NegotiationRequest, NegotiationResponse, NegotiationResult, ProposalResponse (+4 more)

### Community 76 - "Test Organization Invitations & Organizations"
Cohesion: 0.17
Nodes (5): create_counterparty_invitation(), CreateCounterpartyInvitationRequest, OnboardingConcurrencyCases, OnboardingPostgresConcurrencyTests, OnboardingSQLiteConcurrencyTests

### Community 77 - "application/conversations.py"
Cohesion: 0.05
Nodes (22): add_message(), AddMessageCommand, can_view_constraint(), can_view_message(), CommunicationRepository, ConstraintRepository, correct_constraint(), create_manual_constraint() (+14 more)

### Community 78 - "13 Postgres Temporal & 14"
Cohesion: 0.14
Nodes (9): Organization-Scoped Routing Policy, Durable Scoped Reminder Scheduling, Isolated PostgreSQL Migration and Constraint Testing, PostgreSQL and Temporal Verification Specification, Temporal Worker Crash Replay and Recovery, PayPal Sandbox Lifecycle Verification, PayPal Sandbox Specification F11b, Signature-Verified Webhook and Authenticated Reconciliation (+1 more)

### Community 79 - "Tsconfig (tsconfig.json)"
Cohesion: 0.11
Nodes (17): compilerOptions, allowImportingTsExtensions, jsx, lib, module, moduleDetection, moduleResolution, noEmit (+9 more)

### Community 81 - "Test Counterparty Onboarding Migration &"
Cohesion: 0.11
Nodes (4): create_database_engine(), CounterpartyOnboardingMigrationTests, DemoFixtureMigrationTests, NegotiationSqliteRaceTests

### Community 82 - "Test Communication Repositories (MessageIdempotencyPostgresTests)"
Cohesion: 0.20
Nodes (5): MessageIdempotencyPostgresTests, _find_conversation(), _find_keyed_message(), rendezvous(), wait_for()

### Community 83 - "Test Operations & Test Outbox"
Cohesion: 0.27
Nodes (4): captured_output(), SafeOperationsTests, exercise(), failed_db()

### Community 84 - "TradeTerms"
Cohesion: 0.13
Nodes (5): build_payment_milestones(), PaymentMilestoneDraft, _decimal(), TradeTerms, with_timing()

### Community 87 - "demo_lifecycle.py"
Cohesion: 0.19
Nodes (8): _acquire_lock(), _is_demo_deal(), lock_demo_deal_creation(), lock_demo_payment_processing(), lock_demo_reset(), lock_outbox_dispatch(), DemoLifecycleLockTests, _postgres_session()

### Community 88 - "Human Bilateral Amendment Workflow"
Cohesion: 0.40
Nodes (3): Canonical Hash and Legacy Export Preservation, Human Bilateral Amendment Workflow, Cancellation and Dispute Case State Machine

### Community 89 - "App.tsx"
Cohesion: 0.07
Nodes (43): dependencies, react@^19.3.0, react-dom@^19.3.0, three@^0.186.1, login(), InvitationAcceptance, App(), handleInvitationAccepted() (+35 more)

### Community 92 - "PaymentNeedsAction"
Cohesion: 0.11
Nodes (12): simulate_payment(), PaymentInvoiceLookup, PaymentInvoiceRequest, PaymentNeedsAction, PaymentWorkItem, VerifiedProviderPaymentStatus, canonical_decimal(), OfflineDemoInvoiceProvider (+4 more)

### Community 94 - "InvariantViolation"
Cohesion: 0.13
Nodes (3): _normalized_text(), _require_decimal(), InvariantViolation

### Community 96 - "AgreementVersionId"
Cohesion: 0.29
Nodes (3): AgreementVersionId, DealDomainTests, make_deal()

### Community 98 - "Master Execution Contract"
Cohesion: 0.14
Nodes (31): Execution Acceptance Gates, Master Execution Contract, Safe Windows PowerShell Runner, Private Contact Channels, Profiles Specification F14, Fresh Authorization Enforcement, Permissions Specification F15a, Append-Only Fulfillment Observations and Confirmations (+23 more)

### Community 99 - "0005 Conversation Party Unique (Enforce"
Cohesion: 0.36
Nodes (5): _create_party_unique_constraint(), _deduplicate_conversations(), downgrade(), _drop_party_unique_constraint(), upgrade()

### Community 101 - "Safe Operations and Recovery Guide"
Cohesion: 0.19
Nodes (15): PayPal Sandbox Invoicing and Reconciliation Flow, Backend README Document, F11a Explicit Payment Modes, F12 Committed Trade Packs, F1a Curated Repeatable Demo Fixture, F4 Invitations and Private Pending Deals, F5 Persisted Human Negotiation, F6 Agreement History and Comparison (+7 more)

### Community 102 - "migration_config.py"
Cohesion: 0.15
Nodes (3): run_migrations_offline(), MigrationSettings, MigrationConfigTests

### Community 105 - "refresh_access_token"
Cohesion: 0.10
Nodes (4): _hash_refresh_token(), refresh_access_token(), RefreshRequest, RefreshToken

### Community 110 - "DealWorkflowInput"
Cohesion: 0.21
Nodes (5): DealWorkflowInput, _require_uuid(), new_workflow_input(), RefreshActivity, RefreshCall

### Community 111 - "VerifiedProviderPaymentState"
Cohesion: 0.40
Nodes (3): VerifiedProviderPaymentState, transition(), PaymentReconciliationTests

### Community 114 - "NegotiationSession"
Cohesion: 0.16
Nodes (9): NegotiationSession, NegotiationSubmissionOutcome, Proposal, ProposalStatus, NegotiationSessionId, build_proposal(), build_terms(), HumanNegotiationTests (+1 more)

### Community 116 - "_domain_deal"
Cohesion: 0.36
Nodes (4): _domain_deal(), _FakeAgreementRepository, _FakeDealRepository, WorkflowStateApplicationTests

### Community 117 - "NegotiationPostgresRaceTests"
Cohesion: 0.22
Nodes (4): NegotiationPostgresRaceTests, run(), failing(), succeed()

### Community 119 - "Final Gates and Truthful Completion Specification"
Cohesion: 0.20
Nodes (9): Evidence-Free Projection and Safety Bounds, F12 Trade Pack Handoff Document, Trade Pack Export Contract, Browser Verification Specification, ZIP HTML and Print Export Verification, Two-Party Isolated Browser Testing, Final Gates and Truthful Completion Specification, Full Gate Verification Suite (+1 more)

### Community 120 - "Skill (Repo Idea Thinker Skill)"
Cohesion: 0.50
Nodes (3): Repo Idea Thinker Skill, Repository-Grounded Ideation Discipline, Idea Quality Standards and Lightweight Validation

### Community 122 - "login"
Cohesion: 0.22
Nodes (7): CredentialsRequest, _issue_tokens(), login(), TokenResponse, switch_role(), fail(), scalar()

### Community 134 - "simulate_payment"
Cohesion: 0.15
Nodes (5): DevResetResponse, DevRoleSwitchRequest, _require_demo_admin(), reset_demo(), SimulatePaymentRequest

### Community 143 - "NegotiationCommand"
Cohesion: 0.42
Nodes (3): negotiate(), NegotiationCommand, NegotiationRepository

### Community 147 - "AI Provider Boundary Specification"
Cohesion: 0.53
Nodes (4): F2 AI Configuration and Provider Boundary, AI Provider Boundary Specification, AI Resilience and Retry Policy, AISuggestionProvider Contract

## Knowledge Gaps
- **47 isolated node(s):** `syncally`, `F1a Curated Repeatable Demo Fixture`, `Editorial Dark Theme Design System`, `ZIP HTML and Print Export Verification`, `Whole-Worktree Independent Review` (+42 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1253 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **52 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ActorContext` connect `Test Organization Invitations & Organizations` to `Conversations & Test Conversation Use`, `api/payments.py`, `Test Ai Provider & Ai`, `OrganizationId`, `simulate_payment`, `Seed Demo & Deals`, `Agreements & Obligations`, `Test Conversation Routes (ConversationRouteTests)`, `Agreement`, `Test Agreement Routes (AgreementRouteTests)`, `auth.py`, `Agreements & Agreement`, `ai.py`, `CommercialDocumentDraftTests`, `Simulate Deal Flow & Test`, `User`, `InvariantViolation`, `Test Payment Intent Repository &`, `main.py`, `api/deals.py`, `Test Organization Directory & Organizations`, `Organizations & Test Organization Onboarding`, `Test Deal Routes & Identity`, `Test Identity Boundary & Config`, `SqlAlchemyPaymentIntentRepository`, `api/organizations.py`, `Negotiation (BaseRequest)`, `Test Organization Invitations & Organizations`, `application/conversations.py`, `Test Communication Repositories (MessageIdempotencyPostgresTests)`, `Test Ai Context & Conversations`, `PaymentNeedsAction`, `Test Negotiation (NegotiationRouteTests)`, `application/identity.py`, `FakeDealRepository`?**
  _High betweenness centrality (0.102) - this node is a cross-community bridge._
- **Are the 105 inferred relationships involving `ActorContext` (e.g. with `approve_agreement_route()` and `commit_agreement_route()`) actually correct?**
  _`ActorContext` has 105 INFERRED edges - model-reasoned connections that need verification._
- **What connects `syncally`, `F1a Curated Repeatable Demo Fixture`, `Editorial Dark Theme Design System` to the rest of the system?**
  _47 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Conversations & Test Conversation Use` be split into smaller, more focused modules?**
  _Cohesion score 0.05339105339105339 - nodes in this community are weakly interconnected._
- **Why does `OrganizationId` connect `OrganizationId` to `contracts.py`, `identifiers.py`, `api/payments.py`, `Test Ai Provider & Ai`, `Seed Demo & Deals`, `Agreements & Obligations`, `Test Conversation Routes (ConversationRouteTests)`, `Agreement`, `Test Agreement Routes (AgreementRouteTests)`, `Agreements & Agreement`, `NegotiationTests`, `ai.py`, `CommercialDocumentDraftTests`, `Test Outbox Dispatcher & Outbox`, `Communications & Conversations`, `User`, `Agreements & Counterparty Onboarding`, `Test Agreements & Test Local`, `InvariantViolation`, `Test Payment Intent Repository &`, `api/deals.py`, `Negotiation & Proposal`, `Deal & Test Deal Authorization`, `SqlAlchemyPaymentIntentRepository`, `api/organizations.py`, `Money`, `Test Deal Repository & Deals`, `Negotiation (BaseRequest)`, `Test Organization Invitations & Organizations`, `application/conversations.py`, `Test Counterparty Onboarding Migration &`, `TradeTerms`, `Test Ai Context & Conversations`, `PaymentNeedsAction`, `application/identity.py`, `AgreementVersionId`, `Test Negotiation Migration (NegotiationMigrationTests)`, `_to_domain`, `VerifiedProviderPaymentState`, `NegotiationSession`, `_domain_deal`?**
  _High betweenness centrality (0.072) - this node is a cross-community bridge._
- **Are the 57 inferred relationships involving `OrganizationId` (e.g. with `create_reviewed_agreement_draft_route()` and `write_negotiation()`) actually correct?**
  _`OrganizationId` has 57 INFERRED edges - model-reasoned connections that need verification._
- **Should `contracts.py` be split into smaller, more focused modules?**
  _Cohesion score 0.07283702213279677 - nodes in this community are weakly interconnected._