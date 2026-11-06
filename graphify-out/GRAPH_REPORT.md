# Graph Report - SyncAlly  (2026-11-06)

## Corpus Check
- 297 files · ~261,763 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 8 file(s) not represented in the graph (top: (none) 4, .example 1, .ini 1)

## Summary
- 4531 nodes · 14951 edges · 176 communities (118 shown, 58 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 1974 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `fb6dd33f`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Conversations & Test Conversation Use
- AIContractError
- BaseModel
- SqlAlchemyAgreementRepository
- Test Ai Provider & Ai
- DealId
- Seed Demo & Deals
- PaymentNeedsAction
- PaymentWorkItem
- api/agreements.py
- Test Conversation Routes (ConversationRouteTests)
- repositories/payments.py
- Test Agreement Routes (AgreementRouteTests)
- api/payments.py
- process_payment_intent
- ProposedTerms
- NegotiationTests
- Types & Client
- listOrganizations
- VerifiedProviderPaymentState
- DomainError
- Test Outbox Dispatcher & Outbox
- Simulate Deal Flow & Test
- Test Organization Invitations & Organizations
- SqlAlchemyCommunicationRepository
- Package & Vite.Config
- client.test.ts
- Dealconversationreview & Dealconversationreview.Test
- Skill & Skill.Md
- sqlalchemy_orm
- User
- DealDetailPage.test.tsx
- application/agreements.py
- Aisuggestionreview & Suggestionpreview
- SyncAlly Implementation Plan Document
- PaymentProcessingTests
- AgreementCommitTests
- worker.py
- repositories/organizations.py
- Paymentstatuspanel & Paymentstatuspanel.Test
- PaymentIntentRepositoryTests
- api/fulfillment.py
- InvalidTransition
- build_terms
- DealWorkflow
- Test Dev Routes (DevRoutesTests)
- SqlAlchemyDealRepository
- DealWorkflow
- Test Organization Directory & Organizations
- repositories/negotiation.py
- DealWorkflowNotification
- Deal
- PaymentOutboxWorkerTests
- authorize_payment_route
- load_deal_workflow_state
- canonical_decimal
- Agreementreview & Client
- sqlalchemy_exc
- list_current_payment_statuses
- Test Migration Lock & Env
- Payment Processing & Test Payment
- 01 Commercial Domain Model &
- create_counterparty_invitation
- Test Deal Routes & Identity
- api/paypal_webhooks.py
- Compose.Yaml (volumes)
- SqlAlchemyPaymentIntentRepository
- AddMessageRequest
- Session
- AgreementVersionId
- Test Payment Reconciliation & Intent
- Money
- PersistentDemoSeedTests
- _register_shutdown_handlers
- Createdealpage & Createdealpage.Test
- Negotiation (BaseRequest)
- as_utc
- Agreement
- 13 Postgres Temporal & 14
- Tsconfig (tsconfig.json)
- Test Paypal Webhooks (FakeWebhookVerifier)
- Test Counterparty Onboarding Migration &
- Test Communication Repositories (MessageIdempotencyPostgresTests)
- Test Operations & Test Outbox
- create_worker
- database_health
- Main & Test Identity Boundary
- demo_lifecycle.py
- Human Bilateral Amendment Workflow
- ApiError
- Test Organization Index Migration (OrganizationIndexPostgresMigrationTests)
- Server-Enforced Capability Matrix
- 0004_communication_sources_and_scope_indexes.py
- CreateReviewedAgreementDraftCommand
- Constraint
- create_deal
- application/conversations.py
- OutboxEvent
- Master Execution Contract
- 0005 Conversation Party Unique (Enforce
- Main (Request)
- Safe Operations and Recovery Guide
- ai.py
- openai.py
- AISuggestionProviderTests
- Test Payment Mode Migration (PaymentModeMigrationTests)
- _is_duplicate_membership_error
- Test Communication Migration (ConversationPartyUniquenessMigrationTests)
- simulate_deal_flow.py
- ConversationContractTests
- IdentityBoundaryTests
- refresh_access_token
- HealthRouteTests
- maybe_complete_deal
- vitest
- AiContextSelectionTests
- test_outbox_dispatcher.py
- Final Gates and Truthful Completion Specification
- Skill (Repo Idea Thinker Skill)
- RefreshDealStateActivity
- Vite Env.D (ImportMeta)
- get_current_actor
- VerifiedProviderPaymentState
- Index (Frontend HTML Root Document)
- Pyproject (syncally)
- hashlib
- bounded_decimal
- sqlalchemy
- FulfillmentRouteTests
- DealRepository
- ConversationUseCaseTests
- simulate_payment
- .__call__
- AI Provider Boundary Specification
- repositories/fulfillment.py
- Four-Dimension Profile Collections
- Two-Party Judge Journey
- RefreshRequest
- contracts.py
- CommercialDocumentDraftTests
- FulfillmentMigrationTests
- ProviderInvoiceUniqueMigrationTests
- AIConfigurationError
- _to_domain
- MigrationConfigTests
- CollectionSchemaMigrationTests
- NegotiationPostgresRaceTests
- OrganizationContact
- _domain_deal
- OrganizationId
- NegotiationCommand
- MilestonePaymentsMigrationTests
- _case_insensitive_prefix
- NegotiationMigrationTests
- _decode_token
- ._seed

## God Nodes (most connected - your core abstractions)
1. `ActorContext` - 255 edges
2. `OrganizationId` - 190 edges
3. `InvariantViolation` - 132 edges
4. `Money` - 124 edges
5. `Deal` - 108 edges
6. `DealId` - 106 edges
7. `UserId` - 89 edges
8. `AISuggestionProviderTests` - 87 edges
9. `ConversationRouteTests` - 78 edges
10. `TradeTerms` - 77 edges

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

## Communities (176 total, 58 thin omitted)

### Community 0 - "Conversations & Test Conversation Use"
Cohesion: 0.07
Nodes (43): add_message_route(), AISuggestionRequest, clarify_fact_route(), confirm_fact_route(), ConstraintResponse, correct_fact_route(), CorrectFactRequest, create_fact_route() (+35 more)

### Community 1 - "AIContractError"
Cohesion: 0.09
Nodes (14): AIContractError, AIValidationClaim, _check_keys(), _decimal(), FactField, _required_string(), scope_extracted_facts(), ScopedFactCandidate (+6 more)

### Community 2 - "BaseModel"
Cohesion: 0.11
Nodes (9): AcceptInvitationResponse, ContactPayload, ContactResponse, CounterpartyInvitationResponse, InvitationResponse, OrganizationDirectoryItem, OrganizationMemberResponse, ProfileResponse (+1 more)

### Community 3 - "SqlAlchemyAgreementRepository"
Cohesion: 0.09
Nodes (14): AgreementAccessDenied, AgreementNotFound, AgreementVersionConflict, CreateAgreementDraftCommand, DuplicateApproval, ProposalNotFound, StaleAgreementVersion, UnauthorizedApproval (+6 more)

### Community 4 - "Test Ai Provider & Ai"
Cohesion: 0.10
Nodes (12): extract_facts_from_context(), ConfiguredAIProvider, respond(), respond(), respond(), respond(), respond(), respond() (+4 more)

### Community 5 - "DealId"
Cohesion: 0.09
Nodes (12): ConstraintKind, ConstraintStatus, MessageSourceType, Visibility, ConstraintId, ConversationId, MessageId, UserId (+4 more)

### Community 6 - "Seed Demo & Deals"
Cohesion: 0.07
Nodes (32): _require_dev_environment(), _accept_invitation(), _decode_invitation_token(), _create_fixture(), DemoIdentity, _password_for(), _seed_identities(), NegotiationSubmissionOutcome (+24 more)

### Community 7 - "PaymentNeedsAction"
Cohesion: 0.10
Nodes (8): PaymentOutcomeUnknown, PaymentRetryableError, _has_excess_currency_precision(), PayPalSandboxInvoiceProvider, _provider_request_id(), _send_request(), PayPalSandboxAdapterTests, sender()

### Community 8 - "PaymentWorkItem"
Cohesion: 0.12
Nodes (9): get_paypal_webhook_configuration(), PaymentInvoiceLookup, PaymentInvoiceRequest, PaymentNeedsAction, PaymentWorkItem, GmailSettings, PayPalSettings, OfflineDemoInvoiceProvider (+1 more)

### Community 9 - "api/agreements.py"
Cohesion: 0.08
Nodes (30): AgreementVersionResponse, ApprovalResponse, approve_agreement_route(), commit_agreement_route(), CommitAgreementRequest, compare_agreements_route(), create_agreement_draft_route(), create_reviewed_agreement_draft_route() (+22 more)

### Community 10 - "Test Conversation Routes (ConversationRouteTests)"
Cohesion: 0.10
Nodes (3): ConversationRouteTests, respond(), send()

### Community 11 - "repositories/payments.py"
Cohesion: 0.20
Nodes (6): PaymentIntentCommandMismatch, PaymentStatusRecord, _build_invoice_url(), _derive_lifecycle_state(), ExtendedPaymentStatusRecord, _utc_timestamp()

### Community 13 - "api/payments.py"
Cohesion: 0.07
Nodes (6): PaymentOutboxStatus, IdempotencyKeyReused, AgreementStatus, currency_precision(), has_excess_currency_precision(), DomainDependencyTests

### Community 14 - "process_payment_intent"
Cohesion: 0.09
Nodes (9): payment_invoice_number(), PaymentInvoiceNotifier, PaymentInvoiceProvider, PaymentProcessingRepository, process_payment_intent(), reconcile_payment_intent(), _request_id_retry_window_expired(), require_payment_provider() (+1 more)

### Community 15 - "ProposedTerms"
Cohesion: 0.08
Nodes (14): AIPermanentError, AIProviderError, AISuggestionProvider, draft_proposal_from_context(), FactExtractionRequest, parse_proposed_terms(), ProposalDraftRequest, provider_provenance() (+6 more)

### Community 16 - "NegotiationTests"
Cohesion: 0.21
Nodes (3): EvidenceReference, negotiate_in_transaction(), NegotiationTests

### Community 17 - "Types & Client"
Cohesion: 0.06
Nodes (55): describeDetail(), getDealMessageExistence(), isAbortError(), isRecord(), readErrorDetail(), AgreementApproval, AgreementComparison, AgreementEvidence (+47 more)

### Community 18 - "listOrganizations"
Cohesion: 0.06
Nodes (58): dependencies, react@^19.3.0, react-dom@^19.3.0, three@^0.186.1, listOrganizations(), login(), clearAccessToken(), getAccessToken() (+50 more)

### Community 19 - "VerifiedProviderPaymentState"
Cohesion: 0.21
Nodes (4): PaymentInvoiceReconciliation, FakePayPalInvoiceProvider, get_invoice_reconciliation(), get_invoice_reconciliation()

### Community 20 - "DomainError"
Cohesion: 0.07
Nodes (21): CommercialDocumentDraftResponse, get_commercial_document_draft_route(), get_trade_pack_route(), AgreementAlreadyCommitted, AgreementNotCommitted, CommercialDocumentDraft, export_display_terms(), generate_commercial_document_draft() (+13 more)

### Community 21 - "Test Outbox Dispatcher & Outbox"
Cohesion: 0.08
Nodes (14): build_deal_workflow_id(), DealWorkflowStarter, dispatch_outbox_event(), OutboxDispatchResult, PendingOutboxEvent, apply_dispatch_result(), claim_next_pending_event(), _claim_statement() (+6 more)

### Community 22 - "Simulate Deal Flow & Test"
Cohesion: 0.07
Nodes (11): _build_in_process_client(), dispatch_payment(), session_factory(), ci_deal_flow_hook(), DealFlowContext, DealFlowSimulator, run_simulation(), SimulationError (+3 more)

### Community 23 - "Test Organization Invitations & Organizations"
Cohesion: 0.17
Nodes (6): accept_invitation(), AcceptInvitationRequest, create_organization_invitation(), CreateInvitationRequest, ActorContext, OrganizationInvitationTests

### Community 24 - "SqlAlchemyCommunicationRepository"
Cohesion: 0.08
Nodes (12): ConcurrentConstraintUpdate, message_fingerprint(), NotificationKind, Conversation, Message, CommunicationScopeError, _conversation_to_domain(), _is_unique_violation() (+4 more)

### Community 25 - "Package & Vite.Config"
Cohesion: 0.06
Nodes (47): devDependencies, eslint@^10.13.0, @eslint/js@^10.0.1, eslint-plugin-react-hooks@^7.1.1, eslint-plugin-react-refresh@^0.4.20, globals@^17.13.0, happy-dom@^21.0.3, @testing-library/dom@^10.4.1 (+39 more)

### Community 26 - "client.test.ts"
Cohesion: 0.14
Nodes (16): listOrganizationMembers(), revokeOrganizationMember(), updateMemberPermissions(), setAccessToken(), OrganizationCapability, ALL_CAPABILITIES, describeError(), getCurrentUserId() (+8 more)

### Community 27 - "Dealconversationreview & Dealconversationreview.Test"
Cohesion: 0.07
Nodes (43): createDealMessage(), importDealThread(), listDealFacts(), previewDealThreadImport(), updateFactVisibility(), Deal, DealMessage, NegotiationView (+35 more)

### Community 28 - "Skill & Skill.Md"
Cohesion: 0.04
Nodes (43): API and Database Engineer Skill, API Design and Contract Semantics, Data Integrity and Invariant Enforcement, Query Performance and Projection Optimization, Schema Migration and Backward Compatibility, Transaction Boundaries and Atomicity, Archify Diagrammer Skill, Archify CLI Global Tool (+35 more)

### Community 30 - "User"
Cohesion: 0.11
Nodes (5): _compute_effective_capabilities(), list_my_organizations(), update_member_permissions(), UpdateMemberPermissionsRequest, OrganizationPermissionsTests

### Community 31 - "DealDetailPage.test.tsx"
Cohesion: 0.05
Nodes (44): getCurrentAgreement(), getDeal(), getDealFulfillment(), getOrganization(), listDealMessages(), recordDealFulfillment(), FulfillmentStage, DealConstellation() (+36 more)

### Community 32 - "application/agreements.py"
Cohesion: 0.07
Nodes (17): AgreementRepository, AuditEventDraft, AuditRepository, commit_agreement(), create_agreement_draft(), ObligationRepository, OutboxEventDraft, OutboxRepository (+9 more)

### Community 33 - "Aisuggestionreview & Suggestionpreview"
Cohesion: 0.06
Nodes (56): correctDealFact(), createDealFact(), draftDealProposal(), getNegotiation(), negotiateDeal(), reviewDealFact(), suggestDealFacts(), AIProvenance (+48 more)

### Community 34 - "SyncAlly Implementation Plan Document"
Cohesion: 0.16
Nodes (13): SyncAlly Architecture Document, System Topology and Ownership Boundaries, Temporal Worker and Outbox Architecture, Acceptance Criteria Verification Matrix, SyncAlly Implementation Plan Document, Issue #77 Architecture Contracts, Stage Lifecycle Roadmap, Frontend API Client and Authoritative State (+5 more)

### Community 35 - "PaymentProcessingTests"
Cohesion: 0.14
Nodes (5): FakeInvoiceProvider, FakeProcessingRepository, PaymentProcessingTests, _request(), _work_item()

### Community 36 - "AgreementCommitTests"
Cohesion: 0.07
Nodes (9): CommitAgreementCommand, compare_agreement_terms(), record_approval(), RecordApprovalCommand, commit_agreement_in_transaction(), record_approval_in_transaction(), AgreementCommitTests, LocalWorkflowSmokeTests (+1 more)

### Community 37 - "worker.py"
Cohesion: 0.10
Nodes (16): _connect_with_retry(), main(), run_forever(), main(), run_forever(), is_permanent_rpc_error(), configure_logging(), log_operation() (+8 more)

### Community 38 - "repositories/organizations.py"
Cohesion: 0.16
Nodes (12): ContactVisibility, OrganizationCapability, OrganizationMember, OrganizationMemberRole, OrganizationMemberStatus, OrganizationStatus, OrganizationVerificationStatus, resolve_effective_capabilities() (+4 more)

### Community 39 - "Paymentstatuspanel & Paymentstatuspanel.Test"
Cohesion: 0.09
Nodes (31): authorizeDealPayment(), listDealPaymentMilestones(), listPaymentStatuses(), previewDealPayment(), PaymentIntentStatus, formatCountdown(), parseTimestamp(), describeStatus() (+23 more)

### Community 40 - "PaymentIntentRepositoryTests"
Cohesion: 0.08
Nodes (9): AuthorizePaymentIntentCommand, queue_simulated_reconciliation(), require_simulation_scope(), authorize_payment_intent_in_transaction(), _is_idempotency_key_violation(), _is_one_active_per_milestone_violation(), _violated_constraint_name(), MilestoneRepositoryAndIsolationTests (+1 more)

### Community 41 - "api/fulfillment.py"
Cohesion: 0.12
Nodes (16): _event_response(), FulfillmentEventResponse, FulfillmentSnapshotResponse, get_fulfillment_repository(), _raise_fulfillment_error(), read_fulfillment_route(), record_fulfillment_route(), _snapshot_response() (+8 more)

### Community 42 - "InvalidTransition"
Cohesion: 0.17
Nodes (3): Proposal, PaymentIntent, InvalidTransition

### Community 43 - "build_terms"
Cohesion: 0.24
Nodes (7): NegotiationSession, NegotiationSessionId, build_proposal(), build_terms(), DecimalCanonicalizationTests, HumanNegotiationTests, NegotiationTests

### Community 44 - "DealWorkflow"
Cohesion: 0.10
Nodes (8): DealWorkflow, DealWorkflowInput, _require_uuid(), DealWorkflowUnitTests, new_workflow_input(), RefreshActivity, RefreshCall, run()

### Community 47 - "DealWorkflow"
Cohesion: 0.29
Nodes (3): DealWorkflowResult, DealWorkflowTests, new_notification()

### Community 49 - "repositories/negotiation.py"
Cohesion: 0.19
Nodes (6): NegotiationConflict, NegotiationNotFound, NegotiationOrganizationRequired, ProposalId, SqlAlchemyNegotiationRepository, projection()

### Community 50 - "DealWorkflowNotification"
Cohesion: 0.14
Nodes (7): WorkflowStartError, WorkflowStartOutcome, WorkflowStartPermanentError, WorkflowStartTransientError, DealWorkflowNotification, TemporalDealWorkflowStarter, TemporalAdapterTests

### Community 51 - "Deal"
Cohesion: 0.10
Nodes (6): Deal, DealStatus, _deal_to_domain(), FakeDealRepository, DealAuthorizationTests, FakeDealRepository

### Community 52 - "PaymentOutboxWorkerTests"
Cohesion: 0.09
Nodes (11): claim_next_payment_event(), _claim_statement(), _ClaimedPaymentEvent, dispatch_one_payment_event(), dispatch_pending_payment_events(), _finish_event(), FakeRepository, NoCallProvider (+3 more)

### Community 53 - "authorize_payment_route"
Cohesion: 0.08
Nodes (18): authorize_payment_route(), AuthorizePaymentRequest, AuthorizePaymentResponse, _check_milestone_delivery_confirmed(), list_payment_milestones_route(), list_payment_statuses_route(), MilestoneAllocationResponse, MilestonePaymentSummaryResponse (+10 more)

### Community 54 - "load_deal_workflow_state"
Cohesion: 0.11
Nodes (7): DealWorkflowState, load_deal_workflow_state(), parse_workflow_uuid(), WorkflowAgreementRepository, WorkflowDealNotFound, WorkflowDealRepository, _workflow_input_value()

### Community 55 - "canonical_decimal"
Cohesion: 0.08
Nodes (5): PaymentInvoiceNotice, main(), GmailSMTPInvoiceNotifier, _FakeSMTP, GmailSMTPInvoiceNotifierTests

### Community 56 - "Agreementreview & Client"
Cohesion: 0.06
Nodes (53): API_REQUEST_TIMEOUT_MS, ApiError, commitAgreementVersion(), compareAgreementVersions(), getAgreementHistory(), getAgreementVersion(), getCommercialDocumentDraft(), getTradePack() (+45 more)

### Community 57 - "sqlalchemy_exc"
Cohesion: 0.12
Nodes (4): CommunicationMigrationTests, MessageIdempotencyMigrationTests, OrganizationIndexMigrationTests, PaymentCreateStartedMigrationTests

### Community 58 - "list_current_payment_statuses"
Cohesion: 0.15
Nodes (5): get_payment_status_repository(), list_current_payment_statuses(), PaymentIntentRepository, PaymentStatusRepository, SellerMembershipRepository

### Community 59 - "Test Migration Lock & Env"
Cohesion: 0.12
Nodes (8): run_migrations_online(), serialize_migrations(), _make_postgres_connection(), _make_sqlite_connection(), MigrationLockTests, simulated_migration(), PostgresRealAdvisoryLockTests, worker()

### Community 60 - "Payment Processing & Test Payment"
Cohesion: 0.15
Nodes (5): PaymentInvoiceLineItem, simulation_state(), SqlAlchemyPaymentProcessingRepository, transition(), transition()

### Community 61 - "01 Commercial Domain Model &"
Cohesion: 0.07
Nodes (19): AgreementVersion Aggregate, Append-Only AuditEvent Ledger, Commercial Constraint and Provenance, Deal Aggregate, Organization and Membership Entities, PaymentMilestone and Obligation, Proposal Aggregate and Terms Hash, Temporal Deal Workflow (+11 more)

### Community 62 - "create_counterparty_invitation"
Cohesion: 0.17
Nodes (5): create_counterparty_invitation(), CreateCounterpartyInvitationRequest, OnboardingConcurrencyCases, OnboardingPostgresConcurrencyTests, OnboardingSQLiteConcurrencyTests

### Community 64 - "api/paypal_webhooks.py"
Cohesion: 0.20
Nodes (3): _persist_paypal_webhook_event(), receive_paypal_invoice_webhook(), record_paypal_webhook_event()

### Community 65 - "Compose.Yaml (volumes)"
Cohesion: 0.09
Nodes (22): POSTGRES_DB, POSTGRES_PASSWORD, POSTGRES_USER, interval, retries, test, timeout, environment (+14 more)

### Community 66 - "SqlAlchemyPaymentIntentRepository"
Cohesion: 0.09
Nodes (4): PaymentStatusResponse, PaymentMilestoneNotFound, SqlAlchemyPaymentIntentRepository, PaymentStatusExtendedModelTests

### Community 67 - "AddMessageRequest"
Cohesion: 0.19
Nodes (3): AddMessageRequest, CreateFactRequest, AddMessageRequestTests

### Community 68 - "Session"
Cohesion: 0.09
Nodes (14): _active_admin_membership(), add_organization_member(), AddOrganizationMemberRequest, _create_invitation_token(), create_organization(), CreateOrganizationRequest, _deal_awaiting_counterparty(), get_organization_profile_route() (+6 more)

### Community 70 - "Test Payment Reconciliation & Intent"
Cohesion: 0.20
Nodes (3): PaymentIntentStatus, VerifiedProviderPaymentStatus, PaymentReconciliationRepositoryTests

### Community 71 - "Money"
Cohesion: 0.13
Nodes (16): build_trade_terms_from_request(), _trade_pack_html(), _money(), _parse_money(), PaymentObligationAllocation, PaymentTerm, ShipmentItemAllocation, ShipmentTerm (+8 more)

### Community 72 - "PersistentDemoSeedTests"
Cohesion: 0.12
Nodes (4): fixture_id(), initialize_offline_database(), main(), PersistentDemoSeedTests

### Community 73 - "_register_shutdown_handlers"
Cohesion: 0.27
Nodes (4): _register_shutdown_handlers(), _remove_shutdown_handlers(), _request_shutdown(), WorkerShutdownSignalTests

### Community 74 - "Createdealpage & Createdealpage.Test"
Cohesion: 0.13
Nodes (18): acceptInvitation(), apiBaseUrl(), apiRequest(), createAgreementFromReviewedTerms(), createCounterpartyInvitation(), createDeal(), CreateDealPage(), handleSubmit() (+10 more)

### Community 75 - "Negotiation (BaseRequest)"
Cohesion: 0.13
Nodes (12): BaseRequest, CandidateRequest, EvidenceRequest, HistoryResponse, NegotiationRequest, NegotiationResponse, NegotiationResult, ProposalResponse (+4 more)

### Community 76 - "as_utc"
Cohesion: 0.12
Nodes (8): update_organization_profile_route(), Organization, OrganizationProfile, _organization_to_domain(), _profile_to_domain(), SqlAlchemyOrganizationRepository, as_utc(), OrganizationRepositoryTests

### Community 77 - "Agreement"
Cohesion: 0.25
Nodes (6): _display(), _render(), Agreement, Approval, AgreementId, FakeAgreementRepository

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
Cohesion: 0.22
Nodes (4): captured_output(), SafeOperationsTests, exercise(), failed_db()

### Community 84 - "create_worker"
Cohesion: 0.11
Nodes (5): DealWorkflowStatus, create_worker(), workflow_activities(), WorkflowWorkerIntegrationTests, WorkflowWorkerTests

### Community 87 - "demo_lifecycle.py"
Cohesion: 0.19
Nodes (8): _acquire_lock(), _is_demo_deal(), lock_demo_deal_creation(), lock_demo_payment_processing(), lock_demo_reset(), lock_outbox_dispatch(), DemoLifecycleLockTests, _postgres_session()

### Community 88 - "Human Bilateral Amendment Workflow"
Cohesion: 0.40
Nodes (3): Canonical Hash and Legacy Export Preservation, Human Bilateral Amendment Workflow, Cancellation and Dispute Case State Machine

### Community 89 - "ApiError"
Cohesion: 0.06
Nodes (30): addOrganizationMember(), createOrganization(), getOrganizationProfile(), updateOrganizationProfile(), ContactVisibility, Organization, OrganizationContact, COUNTRY_NAMES (+22 more)

### Community 92 - "0004_communication_sources_and_scope_indexes.py"
Cohesion: 0.60
Nodes (4): _create_scope_index(), downgrade(), _drop_scope_index(), upgrade()

### Community 93 - "CreateReviewedAgreementDraftCommand"
Cohesion: 0.12
Nodes (7): create_reviewed_agreement_draft(), CreateReviewedAgreementDraftCommand, ProposalBase, create_reviewed_agreement_draft_in_transaction(), create_legacy_draft(), replace_candidate(), NegotiationRouteTests

### Community 94 - "Constraint"
Cohesion: 0.08
Nodes (4): Constraint, FakeCommunicationRepository, FakeCommunicationRepository, FakeCommunicationRepository

### Community 95 - "create_deal"
Cohesion: 0.15
Nodes (6): _both_organizations_active(), create_deal(), CreateDealCommand, DealAccessDenied, DealUseCaseTests, FakeDealRepository

### Community 96 - "application/conversations.py"
Cohesion: 0.05
Nodes (21): add_message(), can_view_constraint(), CommunicationRepository, ConstraintNotFound, ConstraintRepository, correct_constraint(), create_manual_constraint(), CreateManualConstraintCommand (+13 more)

### Community 97 - "OutboxEvent"
Cohesion: 0.11
Nodes (4): OutboxEvent, DatabasePersistenceTests, start_deal_workflow(), dispatch()

### Community 98 - "Master Execution Contract"
Cohesion: 0.14
Nodes (31): Execution Acceptance Gates, Master Execution Contract, Safe Windows PowerShell Runner, Private Contact Channels, Profiles Specification F14, Fresh Authorization Enforcement, Permissions Specification F15a, Append-Only Fulfillment Observations and Confirmations (+23 more)

### Community 99 - "0005 Conversation Party Unique (Enforce"
Cohesion: 0.36
Nodes (5): _create_party_unique_constraint(), _deduplicate_conversations(), downgrade(), _drop_party_unique_constraint(), upgrade()

### Community 101 - "Safe Operations and Recovery Guide"
Cohesion: 0.19
Nodes (15): PayPal Sandbox Invoicing and Reconciliation Flow, Backend README Document, F11a Explicit Payment Modes, F12 Committed Trade Packs, F1a Curated Repeatable Demo Fixture, F4 Invitations and Private Pending Deals, F5 Persisted Human Negotiation, F6 Agreement History and Comparison (+7 more)

### Community 103 - "ai.py"
Cohesion: 0.13
Nodes (11): AIProvenance, draft_proposal(), extract_facts(), FactExtractionResult, _list_all_constraints_for_owner(), persist_fact_candidates(), ProposalDraftResult, _rejected_fact_result() (+3 more)

### Community 104 - "openai.py"
Cohesion: 0.12
Nodes (12): AITransientError, parse_extracted_facts(), _provider_context(), AiContext, _json(), _object(), OpenAIChatCompletions, _reject_constant() (+4 more)

### Community 105 - "AISuggestionProviderTests"
Cohesion: 0.09
Nodes (6): AIRetryPolicy, call_with_bounded_retry(), DeterministicFakeAIProvider, AISuggestionProviderTests, extract_facts(), FakeWebhookVerifier

### Community 110 - "simulate_deal_flow.py"
Cohesion: 0.10
Nodes (10): _clear_fixture(), _delete_scoped(), DemoCollisionError, _normalized_index_predicate(), _preflight(), seed_demo_data(), _is_live_backend_healthy(), main() (+2 more)

### Community 111 - "ConversationContractTests"
Cohesion: 0.11
Nodes (4): can_view_message(), confirm_constraint(), ConversationContractTests, FakeConstraintRepository

### Community 112 - "IdentityBoundaryTests"
Cohesion: 0.14
Nodes (3): _is_weak_jwt_secret(), Settings, IdentityBoundaryTests

### Community 113 - "refresh_access_token"
Cohesion: 0.19
Nodes (9): _as_utc(), create_refresh_token(), _encode_access_token(), _issue_tokens(), refresh_access_token(), _replay_rotation(), _revoke_family(), _unauthorized() (+1 more)

### Community 116 - "vitest"
Cohesion: 0.10
Nodes (18): listDeals(), DealSummary, ViewerRole, mockedApiRequest, mockedLogin, DealsPage(), DealsPageProps, DealsState (+10 more)

### Community 119 - "Final Gates and Truthful Completion Specification"
Cohesion: 0.20
Nodes (9): Evidence-Free Projection and Safety Bounds, F12 Trade Pack Handoff Document, Trade Pack Export Contract, Browser Verification Specification, ZIP HTML and Print Export Verification, Two-Party Isolated Browser Testing, Final Gates and Truthful Completion Specification, Full Gate Verification Suite (+1 more)

### Community 120 - "Skill (Repo Idea Thinker Skill)"
Cohesion: 0.50
Nodes (3): Repo Idea Thinker Skill, Repository-Grounded Ideation Discipline, Idea Quality Standards and Lightweight Validation

### Community 122 - "RefreshDealStateActivity"
Cohesion: 0.20
Nodes (3): RefreshDealStateActivity, RefreshDealStateActivityTests, factory()

### Community 134 - "get_current_actor"
Cohesion: 0.13
Nodes (5): _development_actor(), development_login(), get_current_actor(), get_optional_actor(), resolve_actor()

### Community 135 - "VerifiedProviderPaymentState"
Cohesion: 0.23
Nodes (4): VerifiedProviderPaymentState, PaymentIntentId, transition(), PaymentReconciliationTests

### Community 139 - "hashlib"
Cohesion: 0.19
Nodes (4): _hash_refresh_token(), hash_password(), verify_password(), RefreshToken

### Community 140 - "bounded_decimal"
Cohesion: 0.13
Nodes (5): _normalized_text(), _require_decimal(), InvariantViolation, bounded_decimal(), BoundedDecimalTests

### Community 141 - "sqlalchemy"
Cohesion: 0.04
Nodes (30): run_migrations_offline(), upgrade(), uuid_column(), upgrade(), upgrade(), upgrade(), upgrade(), downgrade() (+22 more)

### Community 143 - "DealRepository"
Cohesion: 0.09
Nodes (11): create_deal_route(), CreateDealRequest, DealResponse, DealSummaryResponse, get_deal_repository(), list_deals_route(), read_deal_route(), _to_response() (+3 more)

### Community 144 - "ConversationUseCaseTests"
Cohesion: 0.28
Nodes (4): AddMessageCommand, send(), ConversationUseCaseTests, write_message()

### Community 145 - "simulate_payment"
Cohesion: 0.19
Nodes (6): DevResetResponse, DevRoleSwitchRequest, reset_demo(), simulate_payment(), SimulatePaymentRequest, switch_role()

### Community 147 - "AI Provider Boundary Specification"
Cohesion: 0.53
Nodes (4): F2 AI Configuration and Provider Boundary, AI Provider Boundary Specification, AI Resilience and Retry Policy, AISuggestionProvider Contract

### Community 148 - "repositories/fulfillment.py"
Cohesion: 0.11
Nodes (15): FulfillmentEventRecord, FulfillmentUnavailable, RecordFulfillmentCommand, bounded_quantity(), FulfillmentStage, quantity_text(), delivery_obligation_fulfilled(), _event_total() (+7 more)

### Community 151 - "RefreshRequest"
Cohesion: 0.22
Nodes (6): CredentialsRequest, login(), RefreshRequest, TokenResponse, fail(), scalar()

### Community 152 - "contracts.py"
Cohesion: 0.33
Nodes (9): _contains_numeric_token(), _contains_token(), _date_value_is_present(), _fact_value_is_supported_by_quote(), _flexible_whitespace_pattern(), _number_with_currency_is_present(), _number_with_unit_is_present(), _numeric_pattern() (+1 more)

### Community 161 - "NegotiationPostgresRaceTests"
Cohesion: 0.24
Nodes (3): NegotiationPostgresRaceTests, failing(), succeed()

### Community 162 - "OrganizationContact"
Cohesion: 0.25
Nodes (3): _normalize_string(), OrganizationContact, OrganizationContactDomainTests

### Community 163 - "_domain_deal"
Cohesion: 0.36
Nodes (4): _domain_deal(), _FakeAgreementRepository, _FakeDealRepository, WorkflowStateApplicationTests

### Community 166 - "OrganizationId"
Cohesion: 0.14
Nodes (12): PaymentMilestone, AgreementVersionId, DealId, OrganizationId, PaymentMilestoneId, _restore_domain_intent(), constraint(), _domain_deal() (+4 more)

### Community 167 - "NegotiationCommand"
Cohesion: 0.42
Nodes (3): negotiate(), NegotiationCommand, NegotiationRepository

### Community 171 - "_case_insensitive_prefix"
Cohesion: 0.29
Nodes (3): _case_insensitive_prefix(), _escape_like(), value()

## Knowledge Gaps
- **47 isolated node(s):** `syncally`, `F1a Curated Repeatable Demo Fixture`, `Editorial Dark Theme Design System`, `ZIP HTML and Print Export Verification`, `Whole-Worktree Independent Review` (+42 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1337 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **58 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ActorContext` connect `Test Organization Invitations & Organizations` to `Conversations & Test Conversation Use`, `DealId`, `get_current_actor`, `Seed Demo & Deals`, `api/agreements.py`, `Test Conversation Routes (ConversationRouteTests)`, `Test Agreement Routes (AgreementRouteTests)`, `api/payments.py`, `FulfillmentRouteTests`, `DealRepository`, `ConversationUseCaseTests`, `simulate_payment`, `DomainError`, `repositories/fulfillment.py`, `Simulate Deal Flow & Test`, `CommercialDocumentDraftTests`, `sqlalchemy_orm`, `User`, `application/agreements.py`, `repositories/organizations.py`, `OrganizationId`, `PaymentIntentRepositoryTests`, `api/fulfillment.py`, `_decode_token`, `._seed`, `.has_capability`, `Test Organization Directory & Organizations`, `Deal`, `authorize_payment_route`, `list_current_payment_statuses`, `create_counterparty_invitation`, `Test Deal Routes & Identity`, `SqlAlchemyPaymentIntentRepository`, `Session`, `Negotiation (BaseRequest)`, `as_utc`, `Agreement`, `Test Communication Repositories (MessageIdempotencyPostgresTests)`, `CreateReviewedAgreementDraftCommand`, `create_deal`, `application/conversations.py`, `ai.py`, `AISuggestionProviderTests`, `ConversationContractTests`, `IdentityBoundaryTests`, `AiContextSelectionTests`?**
  _High betweenness centrality (0.134) - this node is a cross-community bridge._
- **Are the 114 inferred relationships involving `ActorContext` (e.g. with `approve_agreement_route()` and `commit_agreement_route()`) actually correct?**
  _`ActorContext` has 114 INFERRED edges - model-reasoned connections that need verification._
- **What connects `syncally`, `F1a Curated Repeatable Demo Fixture`, `Editorial Dark Theme Design System` to the rest of the system?**
  _47 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Conversations & Test Conversation Use` be split into smaller, more focused modules?**
  _Cohesion score 0.07006172839506172 - nodes in this community are weakly interconnected._
- **Why does `OrganizationId` connect `OrganizationId` to `AIContractError`, `SqlAlchemyAgreementRepository`, `DealId`, `Seed Demo & Deals`, `VerifiedProviderPaymentState`, `api/agreements.py`, `Test Conversation Routes (ConversationRouteTests)`, `repositories/payments.py`, `Test Agreement Routes (AgreementRouteTests)`, `api/payments.py`, `FulfillmentRouteTests`, `ProposedTerms`, `ConversationUseCaseTests`, `NegotiationTests`, `Test Outbox Dispatcher & Outbox`, `SqlAlchemyCommunicationRepository`, `contracts.py`, `CommercialDocumentDraftTests`, `_to_domain`, `User`, `application/agreements.py`, `_domain_deal`, `AgreementCommitTests`, `repositories/organizations.py`, `PaymentIntentRepositoryTests`, `InvalidTransition`, `build_terms`, `NegotiationMigrationTests`, `SqlAlchemyDealRepository`, `._seed`, `repositories/negotiation.py`, `Deal`, `create_counterparty_invitation`, `SqlAlchemyPaymentIntentRepository`, `AgreementVersionId`, `Money`, `Negotiation (BaseRequest)`, `as_utc`, `Agreement`, `Test Counterparty Onboarding Migration &`, `Constraint`, `create_deal`, `application/conversations.py`, `ai.py`, `AISuggestionProviderTests`, `ConversationContractTests`, `maybe_complete_deal`, `AiContextSelectionTests`?**
  _High betweenness centrality (0.062) - this node is a cross-community bridge._
- **Are the 62 inferred relationships involving `OrganizationId` (e.g. with `build_trade_terms_from_request()` and `create_reviewed_agreement_draft_route()`) actually correct?**
  _`OrganizationId` has 62 INFERRED edges - model-reasoned connections that need verification._
- **Should `AIContractError` be split into smaller, more focused modules?**
  _Cohesion score 0.09200603318250378 - nodes in this community are weakly interconnected._