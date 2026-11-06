# Graph Report - SyncAlly  (2026-11-06)

## Corpus Check
- 294 files · ~254,871 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 8 file(s) not represented in the graph (top: (none) 4, .example 1, .ini 1)

## Summary
- 4463 nodes · 14659 edges · 158 communities (108 shown, 50 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 1920 edges (avg confidence: 0.92)
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
- _raise_agreement_error
- Test Conversation Routes (ConversationRouteTests)
- SqlAlchemyPaymentIntentRepository
- Test Agreement Routes (AgreementRouteTests)
- NegotiationReview.tsx
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
- repositories/payment_processing.py
- User
- DealDetailPage.test.tsx
- application/agreements.py
- Aisuggestionreview & Suggestionpreview
- SyncAlly Implementation Plan Document
- PaymentProcessingTests
- AgreementCommitTests
- worker.py
- OrganizationCapability
- Paymentstatuspanel & Paymentstatuspanel.Test
- Test Payment Intent Repository &
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
- api/agreements.py
- load_deal_workflow_state
- canonical_decimal
- Agreementreview & Client
- add_organization_member
- authorize_payment_intent
- Test Migration Lock & Env
- Payment Processing & Test Payment
- 01 Commercial Domain Model &
- create_counterparty_invitation
- Test Deal Routes & Identity
- queue_simulated_reconciliation
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
- _is_one_active_per_milestone_violation
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
- Test Negotiation (NegotiationRouteTests)
- Constraint
- create_deal
- application/conversations.py
- DatabasePersistenceTests
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
- _is_weak_jwt_secret
- ConversationContractTests
- IdentityBoundaryTests
- auth.py
- HealthRouteTests
- deal_completion.py
- AiContextSelectionTests
- Final Gates and Truthful Completion Specification
- Skill (Repo Idea Thinker Skill)
- activities.py
- Vite Env.D (ImportMeta)
- VerifiedProviderPaymentState
- Index (Frontend HTML Root Document)
- Pyproject (syncally)
- bounded_decimal
- sqlalchemy
- FulfillmentRouteTests
- api/payments.py
- ConversationUseCaseTests
- .__call__
- AI Provider Boundary Specification
- agreements/fulfillment.py
- Four-Dimension Profile Collections
- Two-Party Judge Journey
- .test_login_rejects_demo_identities_outside_local_environments
- FulfillmentMigrationTests
- ProviderInvoiceUniqueMigrationTests
- AIConfigurationError
- MigrationConfigTests
- CollectionSchemaMigrationTests
- OrganizationId

## God Nodes (most connected - your core abstractions)
1. `ActorContext` - 254 edges
2. `OrganizationId` - 177 edges
3. `InvariantViolation` - 131 edges
4. `Deal` - 108 edges
5. `Money` - 107 edges
6. `DealId` - 97 edges
7. `UserId` - 89 edges
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
- `PayPal Sandbox Invoicing and Reconciliation Flow` --conceptually_related_to--> `F11a Explicit Payment Modes`  [INFERRED]
  ARCHITECTURE.md → backend/README.md

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

## Communities (158 total, 50 thin omitted)

### Community 0 - "Conversations & Test Conversation Use"
Cohesion: 0.06
Nodes (47): add_message_route(), AISuggestionRequest, clarify_fact_route(), confirm_fact_route(), ConstraintResponse, correct_fact_route(), CorrectFactRequest, create_fact_route() (+39 more)

### Community 1 - "AIContractError"
Cohesion: 0.09
Nodes (22): AIContractError, AIValidationClaim, _check_keys(), _contains_numeric_token(), _contains_token(), _date_value_is_present(), _decimal(), _fact_value_is_supported_by_quote() (+14 more)

### Community 2 - "BaseModel"
Cohesion: 0.12
Nodes (7): AcceptInvitationResponse, ContactPayload, ContactResponse, OrganizationDirectoryItem, OrganizationMemberResponse, ProfileResponse, UpdateProfileRequest

### Community 3 - "SqlAlchemyAgreementRepository"
Cohesion: 0.09
Nodes (16): AgreementAccessDenied, AgreementAlreadyCommitted, AgreementNotFound, AgreementVersionConflict, AmbiguousAgreementOrganization, DuplicateApproval, ProposalNotFound, StaleAgreementVersion (+8 more)

### Community 4 - "Test Ai Provider & Ai"
Cohesion: 0.11
Nodes (12): extract_facts_from_context(), ConfiguredAIProvider, respond(), respond(), respond(), respond(), respond(), respond() (+4 more)

### Community 5 - "DealId"
Cohesion: 0.08
Nodes (17): message_fingerprint(), ConstraintKind, ConstraintStatus, Message, MessageSourceType, Visibility, ConstraintId, ConversationId (+9 more)

### Community 6 - "Seed Demo & Deals"
Cohesion: 0.07
Nodes (32): _clear_fixture(), _create_fixture(), _delete_scoped(), DemoCollisionError, DemoIdentity, _normalized_index_predicate(), _password_for(), _preflight() (+24 more)

### Community 7 - "PaymentNeedsAction"
Cohesion: 0.09
Nodes (10): receive_paypal_invoice_webhook(), PaymentOutcomeUnknown, PaymentRetryableError, _has_excess_currency_precision(), PayPalSandboxInvoiceProvider, _provider_error_code(), _provider_request_id(), _send_request() (+2 more)

### Community 8 - "PaymentWorkItem"
Cohesion: 0.11
Nodes (10): get_paypal_webhook_configuration(), PaymentInvoiceLookup, PaymentInvoiceRequest, PaymentNeedsAction, PaymentWorkItem, GmailSettings, PayPalSettings, OfflineDemoInvoiceProvider (+2 more)

### Community 9 - "_raise_agreement_error"
Cohesion: 0.14
Nodes (13): AgreementVersionResponse, approve_agreement_route(), commit_agreement_route(), compare_agreements_route(), create_agreement_draft_route(), create_reviewed_agreement_draft_route(), get_agreement_repository(), _raise_agreement_error() (+5 more)

### Community 10 - "Test Conversation Routes (ConversationRouteTests)"
Cohesion: 0.10
Nodes (3): ConversationRouteTests, respond(), send()

### Community 11 - "SqlAlchemyPaymentIntentRepository"
Cohesion: 0.09
Nodes (8): AuthorizePaymentIntentCommand, PaymentIntentAuthorizationOutcome, PaymentIntentCommandMismatch, PaymentMilestoneNotFound, _build_invoice_url(), ExtendedPaymentStatusRecord, SqlAlchemyPaymentIntentRepository, _utc_timestamp()

### Community 13 - "NegotiationReview.tsx"
Cohesion: 0.12
Nodes (22): negotiateDeal(), Deal, NegotiationView, DealConversationReviewProps, ACTION_LABELS, defaultDraft(), isValidDecimal(), ItemDraft (+14 more)

### Community 14 - "process_payment_intent"
Cohesion: 0.08
Nodes (14): PaymentInvoiceNotifier, PaymentInvoiceProvider, PaymentProcessingRepository, process_payment_intent(), reconcile_payment_intent(), _request_id_retry_window_expired(), require_payment_provider(), claim_next_payment_event() (+6 more)

### Community 15 - "ProposedTerms"
Cohesion: 0.11
Nodes (8): FactExtractionRequest, ProposalDraftRequest, ExtractedFact, FactField, ProposedTerms, DemoAISuggestionProvider, _is_ambiguous_numeric_term(), _is_delivery_date_context()

### Community 16 - "NegotiationTests"
Cohesion: 0.13
Nodes (8): CandidateAcknowledgement, EvidenceReference, negotiate(), NegotiationCommand, NegotiationRepository, ProposalBase, negotiate_in_transaction(), NegotiationTests

### Community 17 - "Types & Client"
Cohesion: 0.05
Nodes (65): describeDetail(), getDealMessageExistence(), isAbortError(), isRecord(), listDeals(), readErrorDetail(), AgreementApproval, AgreementComparison (+57 more)

### Community 18 - "listOrganizations"
Cohesion: 0.07
Nodes (50): listOrganizations(), login(), clearAccessToken(), getAccessToken(), setTokens(), TokenResponse, App(), handleInvitationAccepted() (+42 more)

### Community 19 - "VerifiedProviderPaymentState"
Cohesion: 0.18
Nodes (6): PaymentInvoiceReconciliation, VerifiedProviderPaymentState, transition(), FakePayPalInvoiceProvider, get_invoice_reconciliation(), get_invoice_reconciliation()

### Community 20 - "DomainError"
Cohesion: 0.09
Nodes (16): CommercialDocumentDraftResponse, get_commercial_document_draft_route(), get_trade_pack_route(), AgreementNotCommitted, CommercialDocumentDraft, export_display_terms(), generate_commercial_document_draft(), generate_trade_pack() (+8 more)

### Community 21 - "Test Outbox Dispatcher & Outbox"
Cohesion: 0.09
Nodes (14): build_deal_workflow_id(), dispatch_outbox_event(), OutboxDispatchResult, PendingOutboxEvent, WorkflowStartTransientError, apply_dispatch_result(), claim_next_pending_event(), _claim_statement() (+6 more)

### Community 22 - "Simulate Deal Flow & Test"
Cohesion: 0.06
Nodes (13): _build_in_process_client(), dispatch_payment(), session_factory(), ci_deal_flow_hook(), DealFlowContext, DealFlowSimulator, _is_live_backend_healthy(), main() (+5 more)

### Community 23 - "Test Organization Invitations & Organizations"
Cohesion: 0.16
Nodes (5): accept_invitation(), AcceptInvitationRequest, create_organization_invitation(), CreateInvitationRequest, OrganizationInvitationTests

### Community 24 - "SqlAlchemyCommunicationRepository"
Cohesion: 0.11
Nodes (6): Conversation, CommunicationScopeError, _conversation_to_domain(), _is_unique_violation(), _page_bounds(), SqlAlchemyCommunicationRepository

### Community 25 - "Package & Vite.Config"
Cohesion: 0.06
Nodes (47): devDependencies, eslint@^10.13.0, @eslint/js@^10.0.1, eslint-plugin-react-hooks@^7.1.1, eslint-plugin-react-refresh@^0.4.20, globals@^17.13.0, happy-dom@^21.0.3, @testing-library/dom@^10.4.1 (+39 more)

### Community 26 - "client.test.ts"
Cohesion: 0.14
Nodes (16): listOrganizationMembers(), revokeOrganizationMember(), updateMemberPermissions(), setAccessToken(), OrganizationCapability, ALL_CAPABILITIES, describeError(), getCurrentUserId() (+8 more)

### Community 27 - "Dealconversationreview & Dealconversationreview.Test"
Cohesion: 0.05
Nodes (51): dependencies, react@^19.3.0, react-dom@^19.3.0, three@^0.186.1, createDealMessage(), importDealThread(), listDealFacts(), listDealMessages() (+43 more)

### Community 28 - "Skill & Skill.Md"
Cohesion: 0.04
Nodes (43): API and Database Engineer Skill, API Design and Contract Semantics, Data Integrity and Invariant Enforcement, Query Performance and Projection Optimization, Schema Migration and Backward Compatibility, Transaction Boundaries and Atomicity, Archify Diagrammer Skill, Archify CLI Global Tool (+35 more)

### Community 29 - "repositories/payment_processing.py"
Cohesion: 0.05
Nodes (3): OperationalFastAPI, DomainDependencyTests, OutboxDispatchMigrationTests

### Community 30 - "User"
Cohesion: 0.13
Nodes (3): update_member_permissions(), UpdateMemberPermissionsRequest, OrganizationPermissionsTests

### Community 31 - "DealDetailPage.test.tsx"
Cohesion: 0.07
Nodes (32): getDealFulfillment(), recordDealFulfillment(), FulfillmentStage, DEAL, flushMicrotasks(), mockedApiRequest, mockedCreateDealMessage, mockedGetCommercialDocumentDraft (+24 more)

### Community 32 - "application/agreements.py"
Cohesion: 0.06
Nodes (21): AgreementRepository, AuditEventDraft, AuditRepository, commit_agreement(), create_agreement_draft(), create_reviewed_agreement_draft(), CreateAgreementDraftCommand, CreateReviewedAgreementDraftCommand (+13 more)

### Community 33 - "Aisuggestionreview & Suggestionpreview"
Cohesion: 0.09
Nodes (37): correctDealFact(), createDealFact(), draftDealProposal(), getNegotiation(), suggestDealFacts(), AIProvenance, DealFact, isPaymentTrigger() (+29 more)

### Community 34 - "SyncAlly Implementation Plan Document"
Cohesion: 0.16
Nodes (13): SyncAlly Architecture Document, System Topology and Ownership Boundaries, Temporal Worker and Outbox Architecture, Acceptance Criteria Verification Matrix, SyncAlly Implementation Plan Document, Issue #77 Architecture Contracts, Stage Lifecycle Roadmap, Frontend API Client and Authoritative State (+5 more)

### Community 35 - "PaymentProcessingTests"
Cohesion: 0.14
Nodes (5): FakeInvoiceProvider, FakeProcessingRepository, PaymentProcessingTests, _request(), _work_item()

### Community 36 - "AgreementCommitTests"
Cohesion: 0.08
Nodes (8): CommitAgreementCommand, record_approval(), RecordApprovalCommand, commit_agreement_in_transaction(), record_approval_in_transaction(), AgreementCommitTests, LocalWorkflowSmokeTests, commit_once()

### Community 37 - "worker.py"
Cohesion: 0.10
Nodes (16): _connect_with_retry(), main(), run_forever(), main(), run_forever(), is_permanent_rpc_error(), configure_logging(), log_operation() (+8 more)

### Community 38 - "OrganizationCapability"
Cohesion: 0.06
Nodes (22): ContactVisibility, _normalize_string(), Organization, OrganizationCapability, OrganizationContact, OrganizationMember, OrganizationMemberRole, OrganizationMemberStatus (+14 more)

### Community 39 - "Paymentstatuspanel & Paymentstatuspanel.Test"
Cohesion: 0.06
Nodes (41): API_REQUEST_TIMEOUT_MS, authorizeDealPayment(), getDeal(), getOrganization(), listPaymentStatuses(), previewDealPayment(), CREATED_MESSAGE, fetchMock (+33 more)

### Community 41 - "api/fulfillment.py"
Cohesion: 0.11
Nodes (16): get_fulfillment_repository(), _raise_fulfillment_error(), record_fulfillment_route(), FulfillmentAccessDenied, FulfillmentConflict, FulfillmentEventRecord, FulfillmentRepository, FulfillmentSnapshot (+8 more)

### Community 42 - "InvalidTransition"
Cohesion: 0.17
Nodes (3): Proposal, PaymentIntent, InvalidTransition

### Community 43 - "build_terms"
Cohesion: 0.20
Nodes (9): compare_agreement_terms(), NegotiationSession, NegotiationSubmissionOutcome, NegotiationSessionId, build_proposal(), build_terms(), DecimalCanonicalizationTests, HumanNegotiationTests (+1 more)

### Community 44 - "DealWorkflow"
Cohesion: 0.17
Nodes (3): DealWorkflow, DealWorkflowUnitTests, run()

### Community 47 - "DealWorkflow"
Cohesion: 0.16
Nodes (5): DealWorkflowResult, DealWorkflowTests, new_notification(), new_workflow_input(), RefreshActivity

### Community 48 - "Test Organization Directory & Organizations"
Cohesion: 0.13
Nodes (4): _case_insensitive_prefix(), _escape_like(), value(), OrganizationDirectoryTests

### Community 49 - "repositories/negotiation.py"
Cohesion: 0.19
Nodes (7): NegotiationConflict, NegotiationNotFound, NegotiationOrganizationRequired, ProposalStatus, ProposalId, SqlAlchemyNegotiationRepository, projection()

### Community 50 - "DealWorkflowNotification"
Cohesion: 0.12
Nodes (4): DealWorkflowStarter, WorkflowStartOutcome, TemporalDealWorkflowStarter, TemporalAdapterTests

### Community 51 - "Deal"
Cohesion: 0.08
Nodes (5): Deal, DealStatus, _active_participation(), _to_domain(), FakeDealRepository

### Community 52 - "PaymentOutboxWorkerTests"
Cohesion: 0.11
Nodes (5): FakeRepository, NoCallProvider, PaymentOutboxWorkerTests, resolve(), _utc()

### Community 53 - "api/agreements.py"
Cohesion: 0.15
Nodes (14): ApprovalResponse, CommitAgreementRequest, CreateAgreementDraftRequest, get_deal_repository(), MoneyRequest, PaymentObligationAllocationRequest, PaymentTermDraftRequest, _record_decision() (+6 more)

### Community 54 - "load_deal_workflow_state"
Cohesion: 0.10
Nodes (9): DealWorkflowState, load_deal_workflow_state(), parse_workflow_uuid(), WorkflowAgreementRepository, WorkflowDealNotFound, WorkflowDealRepository, _FakeAgreementRepository, _FakeDealRepository (+1 more)

### Community 55 - "canonical_decimal"
Cohesion: 0.09
Nodes (5): PaymentInvoiceNotice, main(), GmailSMTPInvoiceNotifier, _FakeSMTP, GmailSMTPInvoiceNotifierTests

### Community 56 - "Agreementreview & Client"
Cohesion: 0.06
Nodes (53): acceptInvitation(), apiBaseUrl(), ApiError, apiRequest(), commitAgreementVersion(), compareAgreementVersions(), createAgreementFromReviewedTerms(), getAgreementHistory() (+45 more)

### Community 57 - "add_organization_member"
Cohesion: 0.22
Nodes (5): add_organization_member(), AddOrganizationMemberRequest, create_organization(), CreateOrganizationRequest, OrganizationOnboardingTests

### Community 58 - "authorize_payment_intent"
Cohesion: 0.15
Nodes (5): OutboxEventDraft, authorize_payment_intent(), PaymentIntentRepository, SellerMembershipRepository, SqlAlchemyOutboxRepository

### Community 59 - "Test Migration Lock & Env"
Cohesion: 0.12
Nodes (8): run_migrations_online(), serialize_migrations(), _make_postgres_connection(), _make_sqlite_connection(), MigrationLockTests, simulated_migration(), PostgresRealAdvisoryLockTests, worker()

### Community 60 - "Payment Processing & Test Payment"
Cohesion: 0.11
Nodes (7): payment_invoice_number(), PaymentInvoiceLineItem, require_simulation_scope(), simulation_state(), _restore_domain_intent(), SqlAlchemyPaymentProcessingRepository, transition()

### Community 61 - "01 Commercial Domain Model &"
Cohesion: 0.07
Nodes (19): AgreementVersion Aggregate, Append-Only AuditEvent Ledger, Commercial Constraint and Provenance, Deal Aggregate, Organization and Membership Entities, PaymentMilestone and Obligation, Proposal Aggregate and Terms Hash, Temporal Deal Workflow (+11 more)

### Community 62 - "create_counterparty_invitation"
Cohesion: 0.17
Nodes (5): create_counterparty_invitation(), CreateCounterpartyInvitationRequest, OnboardingConcurrencyCases, OnboardingPostgresConcurrencyTests, OnboardingSQLiteConcurrencyTests

### Community 64 - "queue_simulated_reconciliation"
Cohesion: 0.16
Nodes (3): _persist_paypal_webhook_event(), queue_simulated_reconciliation(), record_paypal_webhook_event()

### Community 65 - "Compose.Yaml (volumes)"
Cohesion: 0.09
Nodes (22): POSTGRES_DB, POSTGRES_PASSWORD, POSTGRES_USER, interval, retries, test, timeout, environment (+14 more)

### Community 66 - "SqlAlchemyPaymentIntentRepository"
Cohesion: 0.15
Nodes (3): PaymentStatusResponse, OutboxEvent, PaymentStatusExtendedModelTests

### Community 67 - "AddMessageRequest"
Cohesion: 0.19
Nodes (3): AddMessageRequest, CreateFactRequest, AddMessageRequestTests

### Community 68 - "Session"
Cohesion: 0.10
Nodes (17): _accept_invitation(), _active_admin_membership(), _compute_effective_capabilities(), CounterpartyInvitationResponse, _create_invitation_token(), _deal_awaiting_counterparty(), _decode_invitation_token(), get_optional_actor() (+9 more)

### Community 69 - "AgreementVersionId"
Cohesion: 0.28
Nodes (3): AgreementVersionId, DealDomainTests, make_deal()

### Community 70 - "Test Payment Reconciliation & Intent"
Cohesion: 0.19
Nodes (3): PaymentIntentStatus, VerifiedProviderPaymentStatus, PaymentReconciliationRepositoryTests

### Community 71 - "Money"
Cohesion: 0.15
Nodes (14): build_trade_terms_from_request(), _money(), _parse_money(), PaymentObligationAllocation, PaymentTerm, ShipmentItemAllocation, ShipmentTerm, TradeLineItem (+6 more)

### Community 72 - "PersistentDemoSeedTests"
Cohesion: 0.10
Nodes (7): fixture_id(), initialize_offline_database(), main(), PersistentDemoSeedTests, exercise_api(), start_deal_workflow(), dispatch()

### Community 73 - "_register_shutdown_handlers"
Cohesion: 0.27
Nodes (4): _register_shutdown_handlers(), _remove_shutdown_handlers(), _request_shutdown(), WorkerShutdownSignalTests

### Community 74 - "Createdealpage & Createdealpage.Test"
Cohesion: 0.16
Nodes (14): createCounterpartyInvitation(), createDeal(), CreateDealPage(), handleSubmit(), CreateDealPageProps, describeCreateError(), describeError(), DirectoryItem (+6 more)

### Community 75 - "Negotiation (BaseRequest)"
Cohesion: 0.10
Nodes (12): CreateReviewedAgreementDraftRequest, BaseRequest, CandidateRequest, EvidenceRequest, HistoryResponse, NegotiationRequest, NegotiationResponse, NegotiationResult (+4 more)

### Community 76 - "_is_one_active_per_milestone_violation"
Cohesion: 0.43
Nodes (3): _is_idempotency_key_violation(), _is_one_active_per_milestone_violation(), _violated_constraint_name()

### Community 77 - "Agreement"
Cohesion: 0.22
Nodes (7): _display(), _render(), Agreement, Approval, AgreementId, FakeAgreementRepository, FakeDealRepository

### Community 78 - "13 Postgres Temporal & 14"
Cohesion: 0.14
Nodes (9): Organization-Scoped Routing Policy, Durable Scoped Reminder Scheduling, Isolated PostgreSQL Migration and Constraint Testing, PostgreSQL and Temporal Verification Specification, Temporal Worker Crash Replay and Recovery, PayPal Sandbox Lifecycle Verification, PayPal Sandbox Specification F11b, Signature-Verified Webhook and Authenticated Reconciliation (+1 more)

### Community 79 - "Tsconfig (tsconfig.json)"
Cohesion: 0.11
Nodes (17): compilerOptions, allowImportingTsExtensions, jsx, lib, module, moduleDetection, moduleResolution, noEmit (+9 more)

### Community 81 - "Test Counterparty Onboarding Migration &"
Cohesion: 0.07
Nodes (8): create_database_engine(), CounterpartyOnboardingMigrationTests, DemoFixtureMigrationTests, NegotiationPostgresRaceTests, failing(), succeed(), replace_candidate(), NegotiationSqliteRaceTests

### Community 82 - "Test Communication Repositories (MessageIdempotencyPostgresTests)"
Cohesion: 0.20
Nodes (5): MessageIdempotencyPostgresTests, _find_conversation(), _find_keyed_message(), rendezvous(), wait_for()

### Community 83 - "Test Operations & Test Outbox"
Cohesion: 0.13
Nodes (6): WorkflowStartError, WorkflowStartPermanentError, captured_output(), SafeOperationsTests, exercise(), failed_db()

### Community 84 - "create_worker"
Cohesion: 0.20
Nodes (3): create_worker(), workflow_activities(), WorkflowWorkerTests

### Community 87 - "demo_lifecycle.py"
Cohesion: 0.19
Nodes (8): _acquire_lock(), _is_demo_deal(), lock_demo_deal_creation(), lock_demo_payment_processing(), lock_demo_reset(), lock_outbox_dispatch(), DemoLifecycleLockTests, _postgres_session()

### Community 88 - "Human Bilateral Amendment Workflow"
Cohesion: 0.40
Nodes (3): Canonical Hash and Legacy Export Preservation, Human Bilateral Amendment Workflow, Cancellation and Dispute Case State Machine

### Community 89 - "ApiError"
Cohesion: 0.05
Nodes (36): addOrganizationMember(), createOrganization(), getOrganizationProfile(), updateOrganizationProfile(), ContactVisibility, Organization, OrganizationContact, COUNTRY_NAMES (+28 more)

### Community 92 - "0004_communication_sources_and_scope_indexes.py"
Cohesion: 0.60
Nodes (4): _create_scope_index(), downgrade(), _drop_scope_index(), upgrade()

### Community 94 - "Constraint"
Cohesion: 0.08
Nodes (4): Constraint, FakeCommunicationRepository, FakeCommunicationRepository, FakeCommunicationRepository

### Community 95 - "create_deal"
Cohesion: 0.20
Nodes (4): create_deal(), CreateDealCommand, DealUseCaseTests, FakeDealRepository

### Community 96 - "application/conversations.py"
Cohesion: 0.05
Nodes (21): add_message(), can_view_constraint(), can_view_message(), CommunicationRepository, ConstraintRepository, correct_constraint(), create_manual_constraint(), CreateManualConstraintCommand (+13 more)

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
Cohesion: 0.07
Nodes (18): AIProvenance, AIRetryPolicy, AISuggestionProvider, call_with_bounded_retry(), draft_proposal(), draft_proposal_from_context(), extract_facts(), FactExtractionResult (+10 more)

### Community 104 - "openai.py"
Cohesion: 0.14
Nodes (11): AIPermanentError, AITransientError, parse_extracted_facts(), parse_proposed_terms(), _json(), _object(), OpenAIChatCompletions, _reject_constant() (+3 more)

### Community 105 - "AISuggestionProviderTests"
Cohesion: 0.12
Nodes (4): DeterministicFakeAIProvider, AISuggestionProviderTests, extract_facts(), FakeWebhookVerifier

### Community 111 - "ConversationContractTests"
Cohesion: 0.13
Nodes (3): confirm_constraint(), ConversationContractTests, FakeConstraintRepository

### Community 113 - "auth.py"
Cohesion: 0.06
Nodes (29): _as_utc(), create_refresh_token(), CredentialsRequest, _decode_token(), _development_actor(), development_login(), _encode_access_token(), get_current_actor() (+21 more)

### Community 115 - "deal_completion.py"
Cohesion: 0.12
Nodes (11): NotificationKind, delivery_obligation_fulfilled(), _event_total(), maybe_complete_deal(), payments_reconciled(), _scaled(), FulfillmentEvent, AuditEvent (+3 more)

### Community 119 - "Final Gates and Truthful Completion Specification"
Cohesion: 0.20
Nodes (9): Evidence-Free Projection and Safety Bounds, F12 Trade Pack Handoff Document, Trade Pack Export Contract, Browser Verification Specification, ZIP HTML and Print Export Verification, Two-Party Isolated Browser Testing, Final Gates and Truthful Completion Specification, Full Gate Verification Suite (+1 more)

### Community 120 - "Skill (Repo Idea Thinker Skill)"
Cohesion: 0.50
Nodes (3): Repo Idea Thinker Skill, Repository-Grounded Ideation Discipline, Idea Quality Standards and Lightweight Validation

### Community 122 - "activities.py"
Cohesion: 0.07
Nodes (10): DealWorkflowNotification, RefreshDealStateActivity, _workflow_input_value(), DealWorkflowInput, DealWorkflowStatus, _require_uuid(), RefreshCall, RefreshDealStateActivityTests (+2 more)

### Community 135 - "VerifiedProviderPaymentState"
Cohesion: 0.25
Nodes (4): PaymentMilestone, PaymentIntentId, PaymentMilestoneId, PaymentReconciliationTests

### Community 140 - "bounded_decimal"
Cohesion: 0.10
Nodes (5): _normalized_text(), _require_decimal(), InvariantViolation, bounded_decimal(), BoundedDecimalTests

### Community 141 - "sqlalchemy"
Cohesion: 0.04
Nodes (31): run_migrations_offline(), upgrade(), uuid_column(), upgrade(), upgrade(), upgrade(), upgrade(), downgrade() (+23 more)

### Community 142 - "FulfillmentRouteTests"
Cohesion: 0.18
Nodes (7): _event_response(), FulfillmentEventResponse, FulfillmentSnapshotResponse, read_fulfillment_route(), RecordFulfillmentRequest, _snapshot_response(), FulfillmentRouteTests

### Community 143 - "api/payments.py"
Cohesion: 0.04
Nodes (36): create_deal_route(), CreateDealRequest, DealResponse, DealSummaryResponse, get_deal_repository(), list_deals_route(), read_deal_route(), _to_response() (+28 more)

### Community 144 - "ConversationUseCaseTests"
Cohesion: 0.31
Nodes (4): AddMessageCommand, send(), ConversationUseCaseTests, write_message()

### Community 147 - "AI Provider Boundary Specification"
Cohesion: 0.53
Nodes (4): F2 AI Configuration and Provider Boundary, AI Provider Boundary Specification, AI Resilience and Retry Policy, AISuggestionProvider Contract

### Community 148 - "agreements/fulfillment.py"
Cohesion: 0.13
Nodes (6): bounded_quantity(), quantity_text(), _decimal(), canonical_decimal(), _request_hash(), FulfillmentDomainTests

### Community 156 - "AIConfigurationError"
Cohesion: 0.20
Nodes (3): get_ai_suggestion_provider(), AIConfigurationError, AIProviderError

### Community 166 - "OrganizationId"
Cohesion: 0.10
Nodes (7): OrganizationId, _domain_deal(), NegotiationMigrationTests, OrganizationDomainTests, OrganizationMemberDomainTests, OrganizationProfileDomainTests, _domain_deal()

## Knowledge Gaps
- **47 isolated node(s):** `syncally`, `F1a Curated Repeatable Demo Fixture`, `Editorial Dark Theme Design System`, `ZIP HTML and Print Export Verification`, `Whole-Worktree Independent Review` (+42 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1315 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **50 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ActorContext` connect `Test Deal Routes & Identity` to `Conversations & Test Conversation Use`, `DealId`, `Seed Demo & Deals`, `_raise_agreement_error`, `Test Conversation Routes (ConversationRouteTests)`, `Test Agreement Routes (AgreementRouteTests)`, `FulfillmentRouteTests`, `api/payments.py`, `ConversationUseCaseTests`, `DomainError`, `Simulate Deal Flow & Test`, `Test Organization Invitations & Organizations`, `repositories/payment_processing.py`, `User`, `application/agreements.py`, `OrganizationCapability`, `Test Payment Intent Repository &`, `api/fulfillment.py`, `Test Organization Directory & Organizations`, `api/agreements.py`, `add_organization_member`, `create_counterparty_invitation`, `queue_simulated_reconciliation`, `SqlAlchemyPaymentIntentRepository`, `Session`, `Negotiation (BaseRequest)`, `Agreement`, `Test Communication Repositories (MessageIdempotencyPostgresTests)`, `Test Negotiation (NegotiationRouteTests)`, `create_deal`, `application/conversations.py`, `ai.py`, `AISuggestionProviderTests`, `ConversationContractTests`, `IdentityBoundaryTests`, `auth.py`, `deal_completion.py`, `AiContextSelectionTests`?**
  _High betweenness centrality (0.109) - this node is a cross-community bridge._
- **Are the 113 inferred relationships involving `ActorContext` (e.g. with `approve_agreement_route()` and `commit_agreement_route()`) actually correct?**
  _`ActorContext` has 113 INFERRED edges - model-reasoned connections that need verification._
- **What connects `syncally`, `F1a Curated Repeatable Demo Fixture`, `Editorial Dark Theme Design System` to the rest of the system?**
  _47 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Conversations & Test Conversation Use` be split into smaller, more focused modules?**
  _Cohesion score 0.062421972534332085 - nodes in this community are weakly interconnected._
- **Why does `OrganizationId` connect `OrganizationId` to `Conversations & Test Conversation Use`, `AIContractError`, `SqlAlchemyAgreementRepository`, `DealId`, `Seed Demo & Deals`, `VerifiedProviderPaymentState`, `_raise_agreement_error`, `Test Conversation Routes (ConversationRouteTests)`, `SqlAlchemyPaymentIntentRepository`, `Test Agreement Routes (AgreementRouteTests)`, `FulfillmentRouteTests`, `api/payments.py`, `ProposedTerms`, `ConversationUseCaseTests`, `NegotiationTests`, `DomainError`, `Test Outbox Dispatcher & Outbox`, `SqlAlchemyCommunicationRepository`, `repositories/payment_processing.py`, `User`, `application/agreements.py`, `AgreementCommitTests`, `OrganizationCapability`, `Test Payment Intent Repository &`, `InvalidTransition`, `build_terms`, `SqlAlchemyDealRepository`, `repositories/negotiation.py`, `Deal`, `api/agreements.py`, `Payment Processing & Test Payment`, `create_counterparty_invitation`, `SqlAlchemyPaymentIntentRepository`, `Session`, `AgreementVersionId`, `Money`, `Negotiation (BaseRequest)`, `Agreement`, `Test Counterparty Onboarding Migration &`, `Constraint`, `create_deal`, `application/conversations.py`, `ai.py`, `AISuggestionProviderTests`, `ConversationContractTests`, `deal_completion.py`, `AiContextSelectionTests`?**
  _High betweenness centrality (0.069) - this node is a cross-community bridge._
- **Are the 60 inferred relationships involving `OrganizationId` (e.g. with `build_trade_terms_from_request()` and `create_reviewed_agreement_draft_route()`) actually correct?**
  _`OrganizationId` has 60 INFERRED edges - model-reasoned connections that need verification._
- **Should `AIContractError` be split into smaller, more focused modules?**
  _Cohesion score 0.09234365867913501 - nodes in this community are weakly interconnected._