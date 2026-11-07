# Graph Report - SyncAlly  (2026-11-07)

## Corpus Check
- 316 files · ~278,779 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 14 file(s) not represented in the graph (top: (none) 8, .example 2, .ini 1)

## Summary
- 4930 nodes · 16012 edges · 183 communities (126 shown, 57 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 2077 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `f2df0c1d`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Conversations & Test Conversation Use
- AIContractError
- BaseModel
- .create_draft_from_reviewed_terms
- Test Ai Provider & Ai
- DealId
- repositories/agreements.py
- PaymentNeedsAction
- PaymentWorkItem
- api/agreements.py
- Test Conversation Routes (ConversationRouteTests)
- PaymentStatusExtendedModelTests
- Test Agreement Routes (AgreementRouteTests)
- SqlAlchemyAgreementRepository
- process_payment_intent
- ExtractedFact
- NegotiationTests
- Types & Client
- listOrganizations
- OrganizationPermissionsTests
- application/documents.py
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
- RecordApprovalCommand
- worker.py
- DealDetailPage.tsx
- Paymentstatuspanel & Paymentstatuspanel.Test
- PaymentIntentRepositoryTests
- services
- NegotiationPostgresRaceTests
- AgreementRepository
- DealWorkflow
- Test Dev Routes (DevRoutesTests)
- api/organizations.py
- DealWorkflow
- Test Organization Directory & Organizations
- read_deal_route
- DealWorkflowNotification
- Deal
- PaymentOutboxWorkerTests
- api/payments.py
- load_deal_workflow_state
- _FakeSMTP
- ApiError
- MessageIdempotencyPostgresTests
- Agreement
- Test Migration Lock & Env
- Payment Processing & Test Payment
- 01 Commercial Domain Model &
- create_counterparty_invitation
- Test Deal Routes & Identity
- seed_demo_data
- Compose.Yaml (volumes)
- InvalidTransition
- FulfillmentRouteTests
- CommitAgreementCommand
- OrganizationId
- PaymentReconciliationRepositoryTests
- Money
- PersistentDemoSeedTests
- AgreementReview.tsx
- refresh_access_token
- api/negotiation.py
- Proposal
- IdentityBoundaryTests
- 13 Postgres Temporal & 14
- Tsconfig (tsconfig.json)
- Test Paypal Webhooks (FakeWebhookVerifier)
- Test Counterparty Onboarding Migration &
- SqlAlchemyNegotiationRepository
- Test Operations & Test Outbox
- ConversationUseCaseTests
- environment
- Main & Test Identity Boundary
- dev.py
- Human Bilateral Amendment Workflow
- ApiError
- Test Organization Index Migration (OrganizationIndexPostgresMigrationTests)
- Server-Enforced Capability Matrix
- authorize_payment_route
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
- payment_outbox.py
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
- contracts.py
- setup-temporal-postgres.sh
- FulfillmentMigrationTests
- ProviderInvoiceUniqueMigrationTests
- test_outbox_dispatcher.py
- DealDomainTests
- MigrationConfigTests
- CollectionSchemaMigrationTests
- create-temporal-namespace.sh
- postgres-init.sh
- get_commercial_document_draft_route
- repositories/fulfillment.py
- NegotiationCommand
- AIConfigurationError
- 0004_communication_sources_and_scope_indexes.py
- database_health
- MilestonePaymentsMigrationTests
- FakeCommunicationRepository
- NegotiationMigrationTests
- VerifiedProviderPaymentState
- DealWorkflowInput
- repositories/organizations.py
- sqlalchemy_orm
- WorkflowWorkerIntegrationTests
- require_system_admin
- hostless-start.sh

## God Nodes (most connected - your core abstractions)
1. `ActorContext` - 273 edges
2. `OrganizationId` - 194 edges
3. `InvariantViolation` - 134 edges
4. `Money` - 127 edges
5. `Deal` - 108 edges
6. `DealId` - 106 edges
7. `SqlAlchemyAgreementRepository` - 93 edges
8. `UserId` - 89 edges
9. `AISuggestionProviderTests` - 87 edges
10. `TradeTerms` - 86 edges

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

## Communities (183 total, 57 thin omitted)

### Community 0 - "Conversations & Test Conversation Use"
Cohesion: 0.07
Nodes (43): add_message_route(), AISuggestionRequest, clarify_fact_route(), confirm_fact_route(), ConstraintResponse, correct_fact_route(), CorrectFactRequest, create_fact_route() (+35 more)

### Community 1 - "AIContractError"
Cohesion: 0.12
Nodes (12): AIContractError, AIValidationClaim, _check_keys(), _decimal(), _required_string(), scope_extracted_facts(), _validate_decimal(), _validate_fact_value() (+4 more)

### Community 3 - ".create_draft_from_reviewed_terms"
Cohesion: 0.12
Nodes (10): AgreementAlreadyCommitted, AgreementNotFound, AgreementVersionConflict, ProposalNotFound, UnauthorizedApproval, WrongTermsHash, is_pending(), lock_deal() (+2 more)

### Community 4 - "Test Ai Provider & Ai"
Cohesion: 0.09
Nodes (13): extract_facts_from_context(), ConfiguredAIProvider, AISuggestionProviderTests, respond(), respond(), respond(), respond(), respond() (+5 more)

### Community 5 - "DealId"
Cohesion: 0.11
Nodes (9): can_view_message(), Message, ConstraintId, ConversationId, MessageId, UserId, message(), CommunicationRepositoryTests (+1 more)

### Community 6 - "repositories/agreements.py"
Cohesion: 0.08
Nodes (29): NotificationKind, _create_fixture(), DemoIdentity, _password_for(), _seed_identities(), AgreementVersion, Approval, Obligation (+21 more)

### Community 7 - "PaymentNeedsAction"
Cohesion: 0.09
Nodes (10): receive_paypal_invoice_webhook(), PaymentOutcomeUnknown, PaymentRetryableError, _has_excess_currency_precision(), PayPalSandboxInvoiceProvider, _provider_error_code(), _provider_request_id(), _send_request() (+2 more)

### Community 8 - "PaymentWorkItem"
Cohesion: 0.07
Nodes (14): get_paypal_webhook_configuration(), PaymentInvoiceLookup, PaymentInvoiceNotice, PaymentInvoiceRequest, PaymentNeedsAction, PaymentWorkItem, main(), GmailSettings (+6 more)

### Community 9 - "api/agreements.py"
Cohesion: 0.06
Nodes (42): AgreementVersionResponse, AmendmentImpactResponse, ApprovalResponse, approve_agreement_route(), commit_agreement_route(), CommitAgreementRequest, compare_agreements_route(), create_agreement_draft_route() (+34 more)

### Community 10 - "Test Conversation Routes (ConversationRouteTests)"
Cohesion: 0.10
Nodes (3): ConversationRouteTests, respond(), send()

### Community 11 - "PaymentStatusExtendedModelTests"
Cohesion: 0.12
Nodes (3): PaymentStatusResponse, OutboxEvent, PaymentStatusExtendedModelTests

### Community 13 - "SqlAlchemyAgreementRepository"
Cohesion: 0.08
Nodes (10): get_agreement_repository(), DuplicateApproval, StaleAgreementVersion, create_agreement_draft_in_transaction(), create_reviewed_agreement_draft_in_transaction(), SqlAlchemyAgreementRepository, SqlAlchemyAuditRepository, SqlAlchemyObligationRepository (+2 more)

### Community 14 - "process_payment_intent"
Cohesion: 0.08
Nodes (7): payment_invoice_number(), PaymentInvoiceProvider, PaymentProcessingRepository, process_payment_intent(), reconcile_payment_intent(), _request_id_retry_window_expired(), require_payment_provider()

### Community 15 - "ExtractedFact"
Cohesion: 0.12
Nodes (7): FactExtractionRequest, ExtractedFact, FactField, SourceReference, DemoAISuggestionProvider, _is_ambiguous_numeric_term(), _is_delivery_date_context()

### Community 16 - "NegotiationTests"
Cohesion: 0.21
Nodes (3): EvidenceReference, negotiate_in_transaction(), NegotiationTests

### Community 17 - "Types & Client"
Cohesion: 0.05
Nodes (67): describeDetail(), getDealMessageExistence(), isAbortError(), isRecord(), listPlatformOrganizations(), readErrorDetail(), updatePlatformOrganizationStatus(), AgreementApproval (+59 more)

### Community 18 - "listOrganizations"
Cohesion: 0.06
Nodes (60): dependencies, react@^19.3.0, react-dom@^19.3.0, three@^0.186.1, getCurrentUser(), listOrganizations(), login(), clearAccessToken() (+52 more)

### Community 19 - "OrganizationPermissionsTests"
Cohesion: 0.12
Nodes (4): _compute_effective_capabilities(), update_member_permissions(), UpdateMemberPermissionsRequest, OrganizationPermissionsTests

### Community 20 - "application/documents.py"
Cohesion: 0.15
Nodes (9): export_display_terms(), generate_commercial_document_draft(), generate_trade_pack(), InvalidTradePack, _json_bytes(), _shape(), TradePack, TradePackTooLarge (+1 more)

### Community 21 - "Test Outbox Dispatcher & Outbox"
Cohesion: 0.10
Nodes (13): dispatch_outbox_event(), OutboxDispatchResult, PendingOutboxEvent, WorkflowStartTransientError, apply_dispatch_result(), claim_next_pending_event(), _claim_statement(), dispatch_one_pending_event() (+5 more)

### Community 22 - "Simulate Deal Flow & Test"
Cohesion: 0.06
Nodes (12): _build_in_process_client(), dispatch_payment(), session_factory(), ci_deal_flow_hook(), DealFlowContext, DealFlowSimulator, _is_live_backend_healthy(), run_simulation() (+4 more)

### Community 23 - "Test Organization Invitations & Organizations"
Cohesion: 0.14
Nodes (9): accept_invitation(), AcceptInvitationRequest, create_counterparty_invitation(), create_organization_invitation(), CreateCounterpartyInvitationRequest, CreateInvitationRequest, _decode_invitation_token(), ActorContext (+1 more)

### Community 24 - "SqlAlchemyCommunicationRepository"
Cohesion: 0.11
Nodes (7): Conversation, CommunicationScopeError, _conversation_to_domain(), _is_unique_violation(), _message_to_domain(), _page_bounds(), SqlAlchemyCommunicationRepository

### Community 25 - "Package & Vite.Config"
Cohesion: 0.06
Nodes (47): devDependencies, eslint@^10.13.0, @eslint/js@^10.0.1, eslint-plugin-react-hooks@^7.1.1, eslint-plugin-react-refresh@^0.4.20, globals@^17.13.0, happy-dom@^21.0.3, @testing-library/dom@^10.4.1 (+39 more)

### Community 26 - "client.test.ts"
Cohesion: 0.10
Nodes (21): API_REQUEST_TIMEOUT_MS, listOrganizationMembers(), revokeOrganizationMember(), CREATED_MESSAGE, fetchMock, lastRequest(), sentBody(), updateMemberPermissions() (+13 more)

### Community 27 - "Dealconversationreview & Dealconversationreview.Test"
Cohesion: 0.07
Nodes (41): createDealMessage(), importDealThread(), listDealFacts(), listDealMessages(), previewDealThreadImport(), reviewDealFact(), updateFactVisibility(), areFactsEqual() (+33 more)

### Community 28 - "Skill & Skill.Md"
Cohesion: 0.04
Nodes (43): API and Database Engineer Skill, API Design and Contract Semantics, Data Integrity and Invariant Enforcement, Query Performance and Projection Optimization, Schema Migration and Backward Compatibility, Transaction Boundaries and Atomicity, Archify Diagrammer Skill, Archify CLI Global Tool (+35 more)

### Community 29 - "identifiers.py"
Cohesion: 0.07
Nodes (4): PaymentIntentId, currency_precision(), has_excess_currency_precision(), DomainDependencyTests

### Community 30 - "User"
Cohesion: 0.17
Nodes (6): add_organization_member(), AddOrganizationMemberRequest, create_organization(), CreateOrganizationRequest, _is_duplicate_membership_error(), OrganizationOnboardingTests

### Community 31 - "DealDetailPage.test.tsx"
Cohesion: 0.05
Nodes (48): getCommercialDocumentDraft(), getTradePack(), TradePackFormat, AgreementVersion, mockedApiRequest, mockedCreateOrganization, mockedGetCommercialDocumentDraft, mockedGetCurrentAgreement (+40 more)

### Community 32 - "demo_lifecycle.py"
Cohesion: 0.19
Nodes (8): _acquire_lock(), _is_demo_deal(), lock_demo_deal_creation(), lock_demo_payment_processing(), lock_demo_reset(), lock_outbox_dispatch(), DemoLifecycleLockTests, _postgres_session()

### Community 33 - "Aisuggestionreview & Suggestionpreview"
Cohesion: 0.09
Nodes (37): correctDealFact(), createDealFact(), draftDealProposal(), getNegotiation(), negotiateDeal(), suggestDealFacts(), AIProvenance, DealFact (+29 more)

### Community 34 - "SyncAlly Implementation Plan Document"
Cohesion: 0.16
Nodes (13): SyncAlly Architecture Document, System Topology and Ownership Boundaries, Temporal Worker and Outbox Architecture, Acceptance Criteria Verification Matrix, SyncAlly Implementation Plan Document, Issue #77 Architecture Contracts, Stage Lifecycle Roadmap, Frontend API Client and Authoritative State (+5 more)

### Community 35 - "PaymentProcessingTests"
Cohesion: 0.14
Nodes (5): FakeInvoiceProvider, FakeProcessingRepository, PaymentProcessingTests, _request(), _work_item()

### Community 36 - "RecordApprovalCommand"
Cohesion: 0.13
Nodes (7): AuthorizePaymentRequest, ProposeAmendmentCommand, record_approval(), RecordApprovalCommand, propose_amendment_in_transaction(), record_approval_in_transaction(), AmendmentTests

### Community 37 - "worker.py"
Cohesion: 0.08
Nodes (17): OperationalRequestMiddleware, _connect_with_retry(), main(), run_forever(), main(), run_forever(), is_permanent_rpc_error(), configure_logging() (+9 more)

### Community 38 - "DealDetailPage.tsx"
Cohesion: 0.06
Nodes (40): getDeal(), Deal, NegotiationView, DealConstellation(), DealConstellationProps, DealConversationReviewProps, DealDetailPage(), handleGenerateInvite() (+32 more)

### Community 39 - "Paymentstatuspanel & Paymentstatuspanel.Test"
Cohesion: 0.09
Nodes (37): acceptInvitation(), apiBaseUrl(), apiRequest(), authorizeDealPayment(), createAgreementFromReviewedTerms(), getCurrentAgreement(), getOrganization(), listDealPaymentMilestones() (+29 more)

### Community 40 - "PaymentIntentRepositoryTests"
Cohesion: 0.05
Nodes (13): _persist_paypal_webhook_event(), authorize_payment_intent(), AuthorizePaymentIntentCommand, PaymentIntentAuthorizationOutcome, PaymentIntentRepository, SellerMembershipRepository, authorize_payment_intent_in_transaction(), _is_idempotency_key_violation() (+5 more)

### Community 41 - "services"
Cohesion: 0.09
Nodes (32): build, depends_on, restart, context, dockerfile, migrate, temporal-namespace, build (+24 more)

### Community 42 - "NegotiationPostgresRaceTests"
Cohesion: 0.17
Nodes (7): ProposalBase, NegotiationPostgresRaceTests, run(), failing(), succeed(), create_legacy_draft(), replace_candidate()

### Community 43 - "AgreementRepository"
Cohesion: 0.06
Nodes (20): AgreementRepository, assess_amendment_impact(), AuditEventDraft, AuditRepository, commit_agreement(), create_agreement_draft(), create_reviewed_agreement_draft(), CreateAgreementDraftCommand (+12 more)

### Community 46 - "api/organizations.py"
Cohesion: 0.08
Nodes (21): _accept_invitation(), AcceptInvitationResponse, _active_admin_membership(), _case_insensitive_prefix(), ContactResponse, CounterpartyInvitationResponse, _create_invitation_token(), _deal_awaiting_counterparty() (+13 more)

### Community 47 - "DealWorkflow"
Cohesion: 0.29
Nodes (3): DealWorkflowResult, DealWorkflowTests, new_notification()

### Community 49 - "read_deal_route"
Cohesion: 0.08
Nodes (17): create_deal_route(), CreateDealRequest, DealResponse, DealSummaryResponse, get_deal_repository(), list_deals_route(), read_deal_route(), _to_response() (+9 more)

### Community 50 - "DealWorkflowNotification"
Cohesion: 0.12
Nodes (6): build_deal_workflow_id(), DealWorkflowStarter, WorkflowStartOutcome, DealWorkflowNotification, TemporalDealWorkflowStarter, TemporalAdapterTests

### Community 51 - "Deal"
Cohesion: 0.14
Nodes (3): _active_participation(), SqlAlchemyDealRepository, DealRepositoryTests

### Community 52 - "PaymentOutboxWorkerTests"
Cohesion: 0.10
Nodes (5): FakeRepository, NoCallProvider, PaymentOutboxWorkerTests, resolve(), _utc()

### Community 53 - "api/payments.py"
Cohesion: 0.07
Nodes (23): get_payment_status_repository(), PaymentOutboxStatus, PaymentPreviewResponse, DuplicateActivePaymentIntent, IdempotencyKeyReused, list_current_payment_statuses(), PaymentIntentCommandMismatch, PaymentMilestoneIneligible (+15 more)

### Community 54 - "load_deal_workflow_state"
Cohesion: 0.09
Nodes (10): DealWorkflowState, load_deal_workflow_state(), parse_workflow_uuid(), WorkflowAgreementRepository, WorkflowDealNotFound, WorkflowDealRepository, _workflow_input_value(), _FakeAgreementRepository (+2 more)

### Community 56 - "ApiError"
Cohesion: 0.17
Nodes (10): listDeals(), ViewerRole, DealsPage(), DealsPageProps, DealsState, describeError(), ROLE_LABELS, mockedGetOrganization (+2 more)

### Community 57 - "MessageIdempotencyPostgresTests"
Cohesion: 0.20
Nodes (5): MessageIdempotencyPostgresTests, _find_conversation(), _find_keyed_message(), rendezvous(), wait_for()

### Community 58 - "Agreement"
Cohesion: 0.23
Nodes (7): _display(), _render(), Agreement, Approval, AgreementId, FakeAgreementRepository, TradeTermsTests

### Community 59 - "Test Migration Lock & Env"
Cohesion: 0.12
Nodes (8): run_migrations_online(), serialize_migrations(), _make_postgres_connection(), _make_sqlite_connection(), MigrationLockTests, simulated_migration(), PostgresRealAdvisoryLockTests, worker()

### Community 60 - "Payment Processing & Test Payment"
Cohesion: 0.18
Nodes (3): PaymentInvoiceLineItem, SqlAlchemyPaymentProcessingRepository, transition()

### Community 61 - "01 Commercial Domain Model &"
Cohesion: 0.07
Nodes (19): AgreementVersion Aggregate, Append-Only AuditEvent Ledger, Commercial Constraint and Provenance, Deal Aggregate, Organization and Membership Entities, PaymentMilestone and Obligation, Proposal Aggregate and Terms Hash, Temporal Deal Workflow (+11 more)

### Community 62 - "create_counterparty_invitation"
Cohesion: 0.19
Nodes (3): OnboardingConcurrencyCases, OnboardingPostgresConcurrencyTests, OnboardingSQLiteConcurrencyTests

### Community 64 - "seed_demo_data"
Cohesion: 0.17
Nodes (7): _clear_fixture(), _delete_scoped(), DemoCollisionError, _normalized_index_predicate(), _preflight(), seed_demo_data(), DemoSeedTests

### Community 65 - "Compose.Yaml (volumes)"
Cohesion: 0.09
Nodes (22): POSTGRES_DB, POSTGRES_PASSWORD, POSTGRES_USER, interval, retries, test, timeout, environment (+14 more)

### Community 66 - "InvalidTransition"
Cohesion: 0.17
Nodes (3): Proposal, PaymentIntent, InvalidTransition

### Community 68 - "CommitAgreementCommand"
Cohesion: 0.09
Nodes (5): CommitAgreementCommand, commit_agreement_in_transaction(), AgreementCommitTests, LocalWorkflowSmokeTests, commit_once()

### Community 69 - "OrganizationId"
Cohesion: 0.12
Nodes (13): PaymentMilestone, AgreementVersionId, DealId, OrganizationId, PaymentMilestoneId, _to_domain(), _restore_domain_intent(), constraint() (+5 more)

### Community 71 - "Money"
Cohesion: 0.13
Nodes (17): build_trade_terms_from_request(), _trade_pack_html(), section(), _decimal(), _money(), _parse_money(), PaymentObligationAllocation, PaymentTerm (+9 more)

### Community 72 - "PersistentDemoSeedTests"
Cohesion: 0.10
Nodes (7): fixture_id(), initialize_offline_database(), main(), PersistentDemoSeedTests, exercise_api(), start_deal_workflow(), dispatch()

### Community 73 - "AgreementReview.tsx"
Cohesion: 0.09
Nodes (41): commitAgreementVersion(), compareAgreementVersions(), getAgreementHistory(), getAgreementVersion(), getAmendmentImpact(), previewAmendmentImpact(), proposeAmendment(), recordAgreementDecision() (+33 more)

### Community 74 - "refresh_access_token"
Cohesion: 0.10
Nodes (4): _hash_refresh_token(), refresh_access_token(), RefreshRequest, RefreshToken

### Community 75 - "api/negotiation.py"
Cohesion: 0.12
Nodes (14): BaseRequest, CandidateRequest, EvidenceRequest, HistoryResponse, NegotiationRequest, NegotiationResponse, NegotiationResult, ProposalResponse (+6 more)

### Community 76 - "Proposal"
Cohesion: 0.15
Nodes (11): compare_agreement_terms(), NegotiationSession, NegotiationSubmissionOutcome, ProposalStatus, NegotiationSessionId, ProposalId, build_proposal(), build_terms() (+3 more)

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
Nodes (4): create_database_engine(), CounterpartyOnboardingMigrationTests, DemoFixtureMigrationTests, NegotiationSqliteRaceTests

### Community 82 - "SqlAlchemyNegotiationRepository"
Cohesion: 0.24
Nodes (3): NegotiationConflict, SqlAlchemyNegotiationRepository, projection()

### Community 83 - "Test Operations & Test Outbox"
Cohesion: 0.16
Nodes (6): WorkflowStartError, WorkflowStartPermanentError, captured_output(), SafeOperationsTests, exercise(), failed_db()

### Community 84 - "ConversationUseCaseTests"
Cohesion: 0.10
Nodes (7): AddMessageCommand, ConstraintRepository, message_fingerprint(), review_constraint(), send(), ConversationUseCaseTests, write_message()

### Community 85 - "environment"
Cohesion: 0.29
Nodes (27): environment, AI_PROVIDER, APP_ENV, DATABASE_URL, DEBUG, DEFAULT_NAMESPACE, GMAIL_APP_PASSWORD, GMAIL_FROM_EMAIL (+19 more)

### Community 87 - "dev.py"
Cohesion: 0.15
Nodes (7): DevResetResponse, DevRoleSwitchRequest, _require_demo_admin(), reset_demo(), simulate_payment(), SimulatePaymentRequest, switch_role()

### Community 88 - "Human Bilateral Amendment Workflow"
Cohesion: 0.40
Nodes (3): Canonical Hash and Legacy Export Preservation, Human Bilateral Amendment Workflow, Cancellation and Dispute Case State Machine

### Community 89 - "ApiError"
Cohesion: 0.05
Nodes (48): addOrganizationMember(), ApiError, createCounterpartyInvitation(), createDeal(), createOrganization(), getOrganizationProfile(), updateOrganizationProfile(), ContactVisibility (+40 more)

### Community 92 - "authorize_payment_route"
Cohesion: 0.12
Nodes (11): authorize_payment_route(), AuthorizePaymentResponse, _check_milestone_delivery_confirmed(), list_payment_milestones_route(), list_payment_statuses_route(), MilestoneAllocationResponse, MilestonePaymentSummaryResponse, preview_payment_route() (+3 more)

### Community 94 - "Constraint"
Cohesion: 0.08
Nodes (10): persist_fact_candidates(), CreateManualConstraintCommand, Constraint, ConstraintKind, ConstraintStatus, MessageSourceType, Visibility, _constraint_to_domain() (+2 more)

### Community 95 - "amendment.py"
Cohesion: 0.13
Nodes (10): AmendmentAlreadyCommitted, AmendmentConflict, AmendmentError, AmendmentImpact, AmendmentImpactBlocked, assess_amendment_impact(), FulfillmentObligationImpact, PaymentMilestoneImpact (+2 more)

### Community 96 - "application/conversations.py"
Cohesion: 0.07
Nodes (18): _list_all_visible_constraints(), _list_all_constraints_for_owner(), add_message(), can_view_constraint(), CommunicationRepository, correct_constraint(), create_manual_constraint(), deal_has_any_message() (+10 more)

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
Nodes (22): AIProvenance, AIRetryPolicy, AISuggestionProvider, call_with_bounded_retry(), draft_proposal(), draft_proposal_from_context(), extract_facts(), fact_suggestion_guidance() (+14 more)

### Community 104 - "openai.py"
Cohesion: 0.09
Nodes (16): AIPermanentError, AIProviderError, AITransientError, parse_extracted_facts(), parse_proposed_terms(), ProposalDraftRequest, AiContext, ProposedTerms (+8 more)

### Community 105 - "AISuggestionProviderTests"
Cohesion: 0.15
Nodes (3): DeterministicFakeAIProvider, extract_facts(), FakeWebhookVerifier

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
Cohesion: 0.11
Nodes (5): ConcurrentConstraintUpdate, confirm_constraint(), ConstraintNotFound, ConversationContractTests, FakeConstraintRepository

### Community 112 - "auth.py"
Cohesion: 0.13
Nodes (16): _as_utc(), create_refresh_token(), current_user(), CurrentUserResponse, _decode_token(), _development_actor(), development_login(), _encode_access_token() (+8 more)

### Community 113 - "PaymentInvoiceReconciliation"
Cohesion: 0.21
Nodes (4): PaymentInvoiceReconciliation, FakePayPalInvoiceProvider, get_invoice_reconciliation(), get_invoice_reconciliation()

### Community 114 - "healthcheck"
Cohesion: 0.16
Nodes (18): healthcheck, healthcheck, image, restart, volumes, temporal-schema, interval, retries (+10 more)

### Community 115 - "AddMessageRequest"
Cohesion: 0.19
Nodes (3): AddMessageRequest, CreateFactRequest, AddMessageRequestTests

### Community 116 - "DealWorkflowInput"
Cohesion: 0.18
Nodes (3): RefreshDealStateActivity, RefreshDealStateActivityTests, factory()

### Community 118 - "payment_outbox.py"
Cohesion: 0.13
Nodes (13): PaymentInvoiceNotifier, PaymentIntentStatus, VerifiedProviderPaymentStatus, claim_next_payment_event(), _claim_statement(), _ClaimedPaymentEvent, dispatch_one_payment_event(), dispatch_pending_payment_events() (+5 more)

### Community 119 - "Final Gates and Truthful Completion Specification"
Cohesion: 0.20
Nodes (9): Evidence-Free Projection and Safety Bounds, F12 Trade Pack Handoff Document, Trade Pack Export Contract, Browser Verification Specification, ZIP HTML and Print Export Verification, Two-Party Isolated Browser Testing, Final Gates and Truthful Completion Specification, Full Gate Verification Suite (+1 more)

### Community 120 - "Skill (Repo Idea Thinker Skill)"
Cohesion: 0.50
Nodes (3): Repo Idea Thinker Skill, Repository-Grounded Ideation Discipline, Idea Quality Standards and Lightweight Validation

### Community 122 - "hash_password"
Cohesion: 0.11
Nodes (7): bootstrap_system_admin(), CredentialsRequest, SystemAdminBootstrapRequest, hash_password(), verify_password(), fail(), scalar()

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
Cohesion: 0.11
Nodes (5): _normalized_text(), _require_decimal(), InvariantViolation, bounded_decimal(), BoundedDecimalTests

### Community 141 - "sqlalchemy"
Cohesion: 0.03
Nodes (40): run_migrations_offline(), upgrade(), uuid_column(), upgrade(), upgrade(), upgrade(), upgrade(), downgrade() (+32 more)

### Community 142 - "scaling"
Cohesion: 0.10
Nodes (20): build, build_context_directory, max_cpu, max_memory, min_cpu, min_memory, system, dockerfile_path (+12 more)

### Community 143 - "Deal"
Cohesion: 0.08
Nodes (6): Deal, DealStatus, FakeDealRepository, DealAuthorizationTests, FakeDealRepository, _domain_deal()

### Community 144 - "SyncAlly deployment"
Cohesion: 0.20
Nodes (9): 1. Provision the VM and DNS, 2. Configure secrets, 3. Start the stack, Configure the Hostless App, Connect the Render frontend, Current $0 demo: Render + Hostless, OCI single-VM deployment, SyncAlly deployment (+1 more)

### Community 145 - "AuditEvent"
Cohesion: 0.12
Nodes (7): list_platform_organizations(), _organization_summary(), OrganizationStatusUpdate, update_platform_organization_status(), repair_organization_finance_membership(), verify_member_capability(), AuditEvent

### Community 146 - "FulfillmentPanel.tsx"
Cohesion: 0.19
Nodes (14): getDealFulfillment(), recordDealFulfillment(), FulfillmentStage, errorMessage(), eventReporter(), FulfillmentPanel(), submit(), FulfillmentPanelProps (+6 more)

### Community 147 - "AI Provider Boundary Specification"
Cohesion: 0.53
Nodes (4): F2 AI Configuration and Provider Boundary, AI Provider Boundary Specification, AI Resilience and Retry Policy, AISuggestionProvider Contract

### Community 148 - "api/fulfillment.py"
Cohesion: 0.11
Nodes (18): _event_response(), FulfillmentEventResponse, FulfillmentSnapshotResponse, get_fulfillment_repository(), _raise_fulfillment_error(), read_fulfillment_route(), record_fulfillment_route(), RecordFulfillmentRequest (+10 more)

### Community 151 - "volumes"
Cohesion: 0.50
Nodes (4): volumes, caddy_config, caddy_data, postgres_data

### Community 152 - "contracts.py"
Cohesion: 0.22
Nodes (9): _contains_numeric_token(), _contains_token(), _date_value_is_present(), _fact_value_is_supported_by_quote(), _flexible_whitespace_pattern(), _number_with_currency_is_present(), _number_with_unit_is_present(), _numeric_pattern() (+1 more)

### Community 153 - "setup-temporal-postgres.sh"
Cohesion: 0.67
Nodes (3): PGPASSWORD, setup-temporal-postgres.sh script, update_database_schema()

### Community 162 - "get_commercial_document_draft_route"
Cohesion: 0.16
Nodes (5): CommercialDocumentDraftResponse, get_commercial_document_draft_route(), get_trade_pack_route(), AgreementNotCommitted, CommercialDocumentDraft

### Community 163 - "repositories/fulfillment.py"
Cohesion: 0.10
Nodes (15): FulfillmentConflict, FulfillmentUnavailable, bounded_quantity(), quantity_text(), delivery_obligation_fulfilled(), _event_total(), maybe_complete_deal(), payments_reconciled() (+7 more)

### Community 166 - "NegotiationCommand"
Cohesion: 0.42
Nodes (3): negotiate(), NegotiationCommand, NegotiationRepository

### Community 168 - "0004_communication_sources_and_scope_indexes.py"
Cohesion: 0.60
Nodes (4): _create_scope_index(), downgrade(), _drop_scope_index(), upgrade()

### Community 173 - "VerifiedProviderPaymentState"
Cohesion: 0.35
Nodes (3): VerifiedProviderPaymentState, transition(), PaymentReconciliationTests

### Community 174 - "DealWorkflowInput"
Cohesion: 0.24
Nodes (5): DealWorkflowInput, _require_uuid(), new_workflow_input(), RefreshActivity, RefreshCall

### Community 175 - "repositories/organizations.py"
Cohesion: 0.07
Nodes (23): get_organization_profile_route(), update_organization_profile_route(), ContactVisibility, _normalize_string(), Organization, OrganizationCapability, OrganizationContact, OrganizationMember (+15 more)

### Community 177 - "sqlalchemy_orm"
Cohesion: 0.07
Nodes (4): _require_dev_environment(), OperationalFastAPI, get_db(), HealthRouteTests

## Knowledge Gaps
- **48 isolated node(s):** `syncally`, `PGPASSWORD`, `F1a Curated Repeatable Demo Fixture`, `Editorial Dark Theme Design System`, `ZIP HTML and Print Export Verification` (+43 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1509 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **57 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ActorContext` connect `Test Organization Invitations & Organizations` to `Conversations & Test Conversation Use`, `Test Ai Provider & Ai`, `DealId`, `repositories/agreements.py`, `api/agreements.py`, `Test Conversation Routes (ConversationRouteTests)`, `PaymentStatusExtendedModelTests`, `Test Agreement Routes (AgreementRouteTests)`, `Deal`, `AuditEvent`, `OrganizationPermissionsTests`, `api/fulfillment.py`, `application/documents.py`, `Simulate Deal Flow & Test`, `identifiers.py`, `User`, `get_commercial_document_draft_route`, `repositories/fulfillment.py`, `RecordApprovalCommand`, `PaymentIntentRepositoryTests`, `AgreementRepository`, `api/organizations.py`, `repositories/organizations.py`, `Test Organization Directory & Organizations`, `read_deal_route`, `sqlalchemy_orm`, `require_system_admin`, `api/payments.py`, `.has_capability`, `MessageIdempotencyPostgresTests`, `Agreement`, `create_counterparty_invitation`, `Test Deal Routes & Identity`, `FulfillmentRouteTests`, `OrganizationId`, `api/negotiation.py`, `IdentityBoundaryTests`, `ConversationUseCaseTests`, `dev.py`, `authorize_payment_route`, `NegotiationRouteTests`, `Constraint`, `application/conversations.py`, `ai.py`, `AISuggestionProviderTests`, `ConversationContractTests`, `auth.py`, `AiContextSelectionTests`?**
  _High betweenness centrality (0.105) - this node is a cross-community bridge._
- **Are the 123 inferred relationships involving `ActorContext` (e.g. with `approve_agreement_route()` and `commit_agreement_route()`) actually correct?**
  _`ActorContext` has 123 INFERRED edges - model-reasoned connections that need verification._
- **What connects `syncally`, `PGPASSWORD`, `F1a Curated Repeatable Demo Fixture` to the rest of the system?**
  _48 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Conversations & Test Conversation Use` be split into smaller, more focused modules?**
  _Cohesion score 0.07006172839506172 - nodes in this community are weakly interconnected._
- **Why does `OrganizationId` connect `OrganizationId` to `AIContractError`, `.create_draft_from_reviewed_terms`, `Test Ai Provider & Ai`, `DealId`, `repositories/agreements.py`, `api/agreements.py`, `Test Conversation Routes (ConversationRouteTests)`, `PaymentStatusExtendedModelTests`, `Test Agreement Routes (AgreementRouteTests)`, `SqlAlchemyAgreementRepository`, `Deal`, `NegotiationTests`, `OrganizationPermissionsTests`, `application/documents.py`, `Test Outbox Dispatcher & Outbox`, `Test Organization Invitations & Organizations`, `contracts.py`, `SqlAlchemyCommunicationRepository`, `identifiers.py`, `DealDomainTests`, `repositories/fulfillment.py`, `RecordApprovalCommand`, `PaymentIntentRepositoryTests`, `AgreementRepository`, `FakeCommunicationRepository`, `VerifiedProviderPaymentState`, `api/organizations.py`, `repositories/organizations.py`, `NegotiationMigrationTests`, `read_deal_route`, `Deal`, `api/payments.py`, `Agreement`, `InvalidTransition`, `FulfillmentRouteTests`, `CommitAgreementCommand`, `Money`, `api/negotiation.py`, `Proposal`, `Test Counterparty Onboarding Migration &`, `SqlAlchemyNegotiationRepository`, `ConversationUseCaseTests`, `Constraint`, `application/conversations.py`, `ai.py`, `openai.py`, `AISuggestionProviderTests`, `ConversationContractTests`, `AiContextSelectionTests`?**
  _High betweenness centrality (0.072) - this node is a cross-community bridge._
- **Are the 65 inferred relationships involving `OrganizationId` (e.g. with `build_trade_terms_from_request()` and `create_reviewed_agreement_draft_route()`) actually correct?**
  _`OrganizationId` has 65 INFERRED edges - model-reasoned connections that need verification._
- **Should `AIContractError` be split into smaller, more focused modules?**
  _Cohesion score 0.11738648947951273 - nodes in this community are weakly interconnected._