# Graph Report - SyncAlly  (2026-11-06)

## Corpus Check
- 308 files · ~264,723 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 8 file(s) not represented in the graph (top: (none) 4, .example 1, .ini 1)

## Summary
- 4602 nodes · 14867 edges · 155 communities (108 shown, 47 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 2003 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `10305ceb`
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
- BRIEFING — 2026-11-06T06:00:00Z
- Test Agreement Routes (AgreementRouteTests)
- process_payment_intent
- ai.py
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
- NegotiationPostgresRaceTests
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
- Requirements
- load_deal_workflow_state
- canonical_decimal
- Agreementreview & Client
- add_organization_member
- Test Workflow Activities & Activities
- Test Migration Lock & Env
- Payment Processing & Test Payment
- 01 Commercial Domain Model &
- create_counterparty_invitation
- Test Deal Routes & Identity
- Requirements
- Compose.Yaml (volumes)
- SqlAlchemyPaymentIntentRepository
- AddMessageRequest
- Session
- Requirements
- Test Payment Reconciliation & Intent
- Money
- PersistentDemoSeedTests
- DEVELOPER Dispatch: Task 05 (Collections API UI Docs - Feature Code F10b)
- Createdealpage & Createdealpage.Test
- Negotiation (BaseRequest)
- authorize_payment_intent
- Agreement
- 13 Postgres Temporal & 14
- Tsconfig (tsconfig.json)
- Test Paypal Webhooks (FakeWebhookVerifier)
- Test Counterparty Onboarding Migration &
- Test Communication Repositories (MessageIdempotencyPostgresTests)
- Test Operations & Test Outbox
- create_worker
- BRIEFING — 2026-11-06T06:23:30Z
- Main & Test Identity Boundary
- demo_lifecycle.py
- Human Bilateral Amendment Workflow
- ApiError
- Test Organization Index Migration (OrganizationIndexPostgresMigrationTests)
- Server-Enforced Capability Matrix
- Handoff Report: Task 05 (Collections API UI Docs - Feature Code F10b)
- Test Negotiation (NegotiationRouteTests)
- Message
- api/deals.py
- application/conversations.py
- OutboxEvent
- Master Execution Contract
- 0005 Conversation Party Unique (Enforce
- Main (Request)
- Safe Operations and Recovery Guide
- BRIEFING — 2026-11-06T05:44:20Z
- _normalized_text
- Project: Task 05 (Collections API UI Docs - Feature Code F10b)
- PLANNER Dispatch
- Test Payment Mode Migration (PaymentModeMigrationTests)
- App.test.tsx
- Test Communication Migration (ConversationPartyUniquenessMigrationTests)
- Progress — orchestrator_1
- ConversationContractTests
- contracts.py
- FakeCommunicationRepository
- Progress — Task 05 Planner
- .test_cli_prepared_file_is_readable_and_resettable_by_api_in_fresh_sessions
- OrganizationId
- Developer Progress Tracker - Task 05 (F10b)
- Final Gates and Truthful Completion Specification
- Skill (Repo Idea Thinker Skill)
- Vite Env.D (ImportMeta)
- dev.py
- Index (Frontend HTML Root Document)
- Pyproject (syncally)
- bounded_decimal
- sqlalchemy
- DomainError
- .__call__
- AI Provider Boundary Specification
- _register_shutdown_handlers
- Four-Dimension Profile Collections
- Two-Party Judge Journey
- authorize_payment_route
- FulfillmentMigrationTests
- ProviderInvoiceUniqueMigrationTests
- NegotiationCommand
- MigrationConfigTests
- CollectionSchemaMigrationTests
- auth.py
- HealthRouteTests
- 0004_communication_sources_and_scope_indexes.py
- database_health

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
- `Phase 3: Frontend UI Components Implementation` --references--> `ComparedValue()`  [INFERRED]
  .agents/teamwork/planner_1/handoff.md → frontend/src/deals/AgreementReview.tsx
- `Architecture` --references--> `TradeLineItemDraftRequest`  [INFERRED]
  .agents/teamwork/orchestrator_1/PROJECT.md → backend/src/syncally/api/agreements.py
- `Architecture` --references--> `ShipmentTermDraftRequest`  [INFERRED]
  .agents/teamwork/orchestrator_1/PROJECT.md → backend/src/syncally/api/agreements.py
- `Architecture` --references--> `PaymentTermDraftRequest`  [INFERRED]
  .agents/teamwork/orchestrator_1/PROJECT.md → backend/src/syncally/api/agreements.py
- `Client ↔ Agreements / Negotiation API` --references--> `CreateReviewedAgreementDraftRequest`  [INFERRED]
  .agents/teamwork/orchestrator_1/PROJECT.md → backend/src/syncally/api/agreements.py

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

## Communities (155 total, 47 thin omitted)

### Community 0 - "Conversations & Test Conversation Use"
Cohesion: 0.06
Nodes (49): add_message_route(), AISuggestionRequest, clarify_fact_route(), confirm_fact_route(), ConstraintResponse, correct_fact_route(), CorrectFactRequest, create_fact_route() (+41 more)

### Community 1 - "AIContractError"
Cohesion: 0.11
Nodes (13): AIContractError, AIValidationClaim, _check_keys(), _decimal(), _required_string(), scope_extracted_facts(), ScopedFactCandidate, _validate_decimal() (+5 more)

### Community 2 - "BaseModel"
Cohesion: 0.15
Nodes (7): AcceptInvitationResponse, ContactPayload, ContactResponse, OrganizationDirectoryItem, OrganizationMemberResponse, ProfileResponse, UpdateProfileRequest

### Community 3 - "SqlAlchemyAgreementRepository"
Cohesion: 0.07
Nodes (20): AgreementAlreadyCommitted, AgreementVersionConflict, CreateAgreementDraftCommand, CreateReviewedAgreementDraftCommand, DuplicateApproval, ProposalNotFound, StaleAgreementVersion, UnauthorizedApproval (+12 more)

### Community 4 - "Test Ai Provider & Ai"
Cohesion: 0.06
Nodes (17): AIRetryPolicy, call_with_bounded_retry(), extract_facts_from_context(), DeterministicFakeAIProvider, ConfiguredAIProvider, AISuggestionProviderTests, respond(), respond() (+9 more)

### Community 5 - "DealId"
Cohesion: 0.11
Nodes (9): ConstraintId, ConversationId, DealId, MessageId, UserId, constraint(), message(), CommunicationRepositoryTests (+1 more)

### Community 6 - "Seed Demo & Deals"
Cohesion: 0.07
Nodes (36): _accept_invitation(), CounterpartyInvitationResponse, _create_invitation_token(), _decode_invitation_token(), InvitationResponse, NotificationKind, _create_fixture(), DemoIdentity (+28 more)

### Community 7 - "PaymentNeedsAction"
Cohesion: 0.10
Nodes (11): PaymentInvoiceRequest, PaymentNeedsAction, PaymentOutcomeUnknown, _has_excess_currency_precision(), PayPalSandboxInvoiceProvider, _provider_error_code(), _provider_request_id(), _send_request() (+3 more)

### Community 8 - "PaymentWorkItem"
Cohesion: 0.24
Nodes (3): PaymentInvoiceLookup, PaymentWorkItem, OfflineDemoInvoiceProvider

### Community 9 - "api/agreements.py"
Cohesion: 0.08
Nodes (30): AgreementVersionResponse, ApprovalResponse, approve_agreement_route(), commit_agreement_route(), CommitAgreementRequest, compare_agreements_route(), create_agreement_draft_route(), create_reviewed_agreement_draft_route() (+22 more)

### Community 10 - "Test Conversation Routes (ConversationRouteTests)"
Cohesion: 0.10
Nodes (3): ConversationRouteTests, respond(), send()

### Community 11 - "BRIEFING — 2026-11-06T06:00:00Z"
Cohesion: 0.10
Nodes (17): Artifact Index, BRIEFING — 2026-11-06T06:00:00Z, Change Tracker, Current Parent, 🔒 Key Constraints, Loaded Skills, Mission, 🔒 My Identity (+9 more)

### Community 14 - "process_payment_intent"
Cohesion: 0.08
Nodes (7): payment_invoice_number(), PaymentInvoiceProvider, PaymentProcessingRepository, process_payment_intent(), reconcile_payment_intent(), _request_id_retry_window_expired(), require_payment_provider()

### Community 15 - "ai.py"
Cohesion: 0.04
Nodes (37): get_ai_suggestion_provider(), AIConfigurationError, AIPermanentError, AIProvenance, AIProviderError, AISuggestionProvider, AITransientError, draft_proposal() (+29 more)

### Community 16 - "NegotiationTests"
Cohesion: 0.19
Nodes (5): CandidateAcknowledgement, EvidenceReference, ProposalBase, negotiate_in_transaction(), NegotiationTests

### Community 17 - "Types & Client"
Cohesion: 0.04
Nodes (79): Phase 2: Frontend Types & Client, Phase 2: Frontend Types & Client Implementation, createAgreementFromReviewedTerms(), describeDetail(), getDealMessageExistence(), isAbortError(), isRecord(), readErrorDetail() (+71 more)

### Community 18 - "listOrganizations"
Cohesion: 0.06
Nodes (53): dependencies, react@^19.3.0, react-dom@^19.3.0, three@^0.186.1, listOrganizations(), login(), clearAccessToken(), getAccessToken() (+45 more)

### Community 19 - "VerifiedProviderPaymentState"
Cohesion: 0.18
Nodes (5): PaymentInvoiceReconciliation, VerifiedProviderPaymentState, transition(), FakePayPalInvoiceProvider, get_invoice_reconciliation()

### Community 20 - "DomainError"
Cohesion: 0.08
Nodes (17): CommercialDocumentDraftResponse, get_commercial_document_draft_route(), get_trade_pack_route(), AgreementNotCommitted, CommercialDocumentDraft, _display(), export_display_terms(), generate_commercial_document_draft() (+9 more)

### Community 21 - "Test Outbox Dispatcher & Outbox"
Cohesion: 0.08
Nodes (14): build_deal_workflow_id(), DealWorkflowStarter, dispatch_outbox_event(), OutboxDispatchResult, PendingOutboxEvent, apply_dispatch_result(), claim_next_pending_event(), _claim_statement() (+6 more)

### Community 22 - "Simulate Deal Flow & Test"
Cohesion: 0.06
Nodes (12): _build_in_process_client(), dispatch_payment(), session_factory(), ci_deal_flow_hook(), DealFlowContext, DealFlowSimulator, run_simulation(), SimulationError (+4 more)

### Community 23 - "Test Organization Invitations & Organizations"
Cohesion: 0.16
Nodes (5): accept_invitation(), AcceptInvitationRequest, create_organization_invitation(), CreateInvitationRequest, OrganizationInvitationTests

### Community 24 - "SqlAlchemyCommunicationRepository"
Cohesion: 0.11
Nodes (6): Conversation, CommunicationScopeError, _constraint_to_domain(), _conversation_to_domain(), _page_bounds(), SqlAlchemyCommunicationRepository

### Community 25 - "Package & Vite.Config"
Cohesion: 0.06
Nodes (47): devDependencies, eslint@^10.13.0, @eslint/js@^10.0.1, eslint-plugin-react-hooks@^7.1.1, eslint-plugin-react-refresh@^0.4.20, globals@^17.13.0, happy-dom@^21.0.3, @testing-library/dom@^10.4.1 (+39 more)

### Community 26 - "client.test.ts"
Cohesion: 0.10
Nodes (23): API_REQUEST_TIMEOUT_MS, listOrganizationMembers(), revokeOrganizationMember(), CREATED_MESSAGE, fetchMock, lastRequest(), sentBody(), updateMemberPermissions() (+15 more)

### Community 27 - "Dealconversationreview & Dealconversationreview.Test"
Cohesion: 0.07
Nodes (40): createDealMessage(), importDealThread(), listDealFacts(), listDealMessages(), previewDealThreadImport(), reviewDealFact(), updateFactVisibility(), areFactsEqual() (+32 more)

### Community 28 - "Skill & Skill.Md"
Cohesion: 0.04
Nodes (43): API and Database Engineer Skill, API Design and Contract Semantics, Data Integrity and Invariant Enforcement, Query Performance and Projection Optimization, Schema Migration and Backward Compatibility, Transaction Boundaries and Atomicity, Archify Diagrammer Skill, Archify CLI Global Tool (+35 more)

### Community 30 - "User"
Cohesion: 0.12
Nodes (5): _compute_effective_capabilities(), list_my_organizations(), update_member_permissions(), UpdateMemberPermissionsRequest, OrganizationPermissionsTests

### Community 31 - "DealDetailPage.test.tsx"
Cohesion: 0.06
Nodes (44): acceptInvitation(), apiBaseUrl(), apiRequest(), getCurrentAgreement(), getDeal(), getDealFulfillment(), getOrganization(), recordDealFulfillment() (+36 more)

### Community 32 - "application/agreements.py"
Cohesion: 0.10
Nodes (12): AgreementRepository, AuditEventDraft, AuditRepository, commit_agreement(), create_agreement_draft(), create_reviewed_agreement_draft(), get_current_agreement(), ObligationRepository (+4 more)

### Community 33 - "Aisuggestionreview & Suggestionpreview"
Cohesion: 0.09
Nodes (38): correctDealFact(), createDealFact(), draftDealProposal(), getNegotiation(), negotiateDeal(), suggestDealFacts(), AIProvenance, DealFact (+30 more)

### Community 34 - "SyncAlly Implementation Plan Document"
Cohesion: 0.16
Nodes (13): SyncAlly Architecture Document, System Topology and Ownership Boundaries, Temporal Worker and Outbox Architecture, Acceptance Criteria Verification Matrix, SyncAlly Implementation Plan Document, Issue #77 Architecture Contracts, Stage Lifecycle Roadmap, Frontend API Client and Authoritative State (+5 more)

### Community 35 - "PaymentProcessingTests"
Cohesion: 0.11
Nodes (6): PaymentProviderResolver, FakeInvoiceProvider, FakeProcessingRepository, PaymentProcessingTests, get_invoice_reconciliation(), _work_item()

### Community 36 - "AgreementCommitTests"
Cohesion: 0.09
Nodes (7): CommitAgreementCommand, RecordApprovalCommand, commit_agreement_in_transaction(), record_approval_in_transaction(), AgreementCommitTests, LocalWorkflowSmokeTests, commit_once()

### Community 37 - "worker.py"
Cohesion: 0.09
Nodes (16): _connect_with_retry(), main(), run_forever(), main(), run_forever(), is_permanent_rpc_error(), configure_logging(), log_operation() (+8 more)

### Community 38 - "OrganizationCapability"
Cohesion: 0.06
Nodes (25): ContactVisibility, _normalize_string(), Organization, OrganizationCapability, OrganizationContact, OrganizationMember, OrganizationMemberRole, OrganizationMemberStatus (+17 more)

### Community 39 - "Paymentstatuspanel & Paymentstatuspanel.Test"
Cohesion: 0.10
Nodes (29): authorizeDealPayment(), listPaymentStatuses(), previewDealPayment(), PaymentIntentStatus, describeStatus(), displayAmount(), extractInvoiceNumber(), firstMilestoneAmount() (+21 more)

### Community 40 - "Test Payment Intent Repository &"
Cohesion: 0.12
Nodes (4): queue_simulated_reconciliation(), require_simulation_scope(), authorize_payment_intent_in_transaction(), PaymentIntentRepositoryTests

### Community 41 - "api/fulfillment.py"
Cohesion: 0.06
Nodes (31): _event_response(), FulfillmentEventResponse, FulfillmentSnapshotResponse, get_fulfillment_repository(), _raise_fulfillment_error(), read_fulfillment_route(), record_fulfillment_route(), RecordFulfillmentRequest (+23 more)

### Community 42 - "NegotiationPostgresRaceTests"
Cohesion: 0.15
Nodes (7): NegotiationPostgresRaceTests, run(), failing(), succeed(), create_legacy_draft(), replace_candidate(), NegotiationSqliteRaceTests

### Community 43 - "build_terms"
Cohesion: 0.16
Nodes (8): NegotiationSession, NegotiationSubmissionOutcome, Proposal, ProposalStatus, NegotiationSessionId, build_proposal(), HumanNegotiationTests, NegotiationTests

### Community 47 - "DealWorkflow"
Cohesion: 0.29
Nodes (3): DealWorkflowResult, DealWorkflowTests, new_notification()

### Community 48 - "Test Organization Directory & Organizations"
Cohesion: 0.13
Nodes (4): _case_insensitive_prefix(), _escape_like(), value(), OrganizationDirectoryTests

### Community 49 - "repositories/negotiation.py"
Cohesion: 0.17
Nodes (7): _raise_error(), NegotiationConflict, NegotiationNotFound, NegotiationOrganizationRequired, ProposalId, SqlAlchemyNegotiationRepository, projection()

### Community 50 - "DealWorkflowNotification"
Cohesion: 0.16
Nodes (5): WorkflowStartOutcome, WorkflowStartPermanentError, DealWorkflowNotification, TemporalDealWorkflowStarter, TemporalAdapterTests

### Community 51 - "Deal"
Cohesion: 0.07
Nodes (9): Deal, DealStatus, _active_participation(), _to_domain(), FakeDealRepository, DealAuthorizationTests, _domain_deal(), FakeDealRepository (+1 more)

### Community 52 - "PaymentOutboxWorkerTests"
Cohesion: 0.09
Nodes (14): PaymentInvoiceNotifier, claim_next_payment_event(), _claim_statement(), _ClaimedPaymentEvent, dispatch_one_payment_event(), dispatch_pending_payment_events(), _finish_event(), _process_claimed_payment_event() (+6 more)

### Community 53 - "Requirements"
Cohesion: 0.13
Nodes (14): 2026-11-06T05:44:19Z, Acceptance Criteria, Collection Contracts & Bilateral Review, Dispatch History, R1. Dependency Verification & Foundation Reuse, R2. Schema-Versioned Collection Authoring and Contracts, R3. Bilateral Review & Approval Invalidation, R4. Version-Aware Exports and Provenance (+6 more)

### Community 54 - "load_deal_workflow_state"
Cohesion: 0.09
Nodes (10): DealWorkflowState, load_deal_workflow_state(), parse_workflow_uuid(), WorkflowAgreementRepository, WorkflowDealNotFound, WorkflowDealRepository, _workflow_input_value(), _FakeAgreementRepository (+2 more)

### Community 55 - "canonical_decimal"
Cohesion: 0.05
Nodes (14): get_paypal_webhook_configuration(), _persist_paypal_webhook_event(), receive_paypal_invoice_webhook(), PaymentInvoiceNotice, PaymentRetryableError, main(), GmailSettings, PayPalSettings (+6 more)

### Community 56 - "Agreementreview & Client"
Cohesion: 0.10
Nodes (34): commitAgreementVersion(), compareAgreementVersions(), getAgreementHistory(), getAgreementVersion(), getTradePack(), recordAgreementDecision(), TradePackFormat, AgreementVersion (+26 more)

### Community 57 - "add_organization_member"
Cohesion: 0.14
Nodes (6): add_organization_member(), AddOrganizationMemberRequest, create_organization(), CreateOrganizationRequest, _is_duplicate_membership_error(), OrganizationOnboardingTests

### Community 58 - "Test Workflow Activities & Activities"
Cohesion: 0.11
Nodes (8): RefreshDealStateActivity, DealWorkflowInput, _require_uuid(), new_workflow_input(), RefreshActivity, RefreshCall, RefreshDealStateActivityTests, factory()

### Community 59 - "Test Migration Lock & Env"
Cohesion: 0.12
Nodes (8): run_migrations_online(), serialize_migrations(), _make_postgres_connection(), _make_sqlite_connection(), MigrationLockTests, simulated_migration(), PostgresRealAdvisoryLockTests, worker()

### Community 60 - "Payment Processing & Test Payment"
Cohesion: 0.16
Nodes (4): PaymentInvoiceLineItem, SqlAlchemyPaymentProcessingRepository, transition(), transition()

### Community 61 - "01 Commercial Domain Model &"
Cohesion: 0.07
Nodes (19): AgreementVersion Aggregate, Append-Only AuditEvent Ledger, Commercial Constraint and Provenance, Deal Aggregate, Organization and Membership Entities, PaymentMilestone and Obligation, Proposal Aggregate and Terms Hash, Temporal Deal Workflow (+11 more)

### Community 62 - "create_counterparty_invitation"
Cohesion: 0.16
Nodes (5): create_counterparty_invitation(), CreateCounterpartyInvitationRequest, OnboardingConcurrencyCases, OnboardingPostgresConcurrencyTests, OnboardingSQLiteConcurrencyTests

### Community 64 - "Requirements"
Cohesion: 0.13
Nodes (14): Acceptance Criteria, Collection Contracts & Bilateral Review, Initial Request — 2026-11-06T05:43:13Z, Original User Request, R1. Dependency Verification & Foundation Reuse, R2. Schema-Versioned Collection Authoring and Contracts, R3. Bilateral Review & Approval Invalidation, R4. Version-Aware Exports and Provenance (+6 more)

### Community 65 - "Compose.Yaml (volumes)"
Cohesion: 0.09
Nodes (22): POSTGRES_DB, POSTGRES_PASSWORD, POSTGRES_USER, interval, retries, test, timeout, environment (+14 more)

### Community 66 - "SqlAlchemyPaymentIntentRepository"
Cohesion: 0.10
Nodes (4): PaymentStatusResponse, PaymentIntent, InvalidTransition, PaymentStatusExtendedModelTests

### Community 67 - "AddMessageRequest"
Cohesion: 0.19
Nodes (3): AddMessageRequest, CreateFactRequest, AddMessageRequestTests

### Community 68 - "Session"
Cohesion: 0.11
Nodes (10): _active_admin_membership(), _deal_awaiting_counterparty(), get_optional_actor(), get_organization_profile_route(), get_organization_route(), list_organization_directory(), list_organization_members(), repair_organization_finance_route() (+2 more)

### Community 69 - "Requirements"
Cohesion: 0.15
Nodes (12): Acceptance Criteria, Collection Contracts & Bilateral Review, R1. Dependency Verification & Foundation Reuse, R2. Schema-Versioned Collection Authoring and Contracts, R3. Bilateral Review & Approval Invalidation, R4. Version-Aware Exports and Provenance, R5. Documentation, Operational Safeguards & Role Execution, Requirements (+4 more)

### Community 71 - "Money"
Cohesion: 0.08
Nodes (30): Key Decisions Made, Phase 1: Backend API & Application Implementation, Architecture, Investigation State, 2. Logic Chain, Current Workspace and Dependency Verification (R1), Phase 1: Backend API & Application Implementation, build_trade_terms_from_request() (+22 more)

### Community 72 - "PersistentDemoSeedTests"
Cohesion: 0.13
Nodes (4): fixture_id(), initialize_offline_database(), main(), PersistentDemoSeedTests

### Community 73 - "DEVELOPER Dispatch: Task 05 (Collections API UI Docs - Feature Code F10b)"
Cohesion: 0.17
Nodes (11): 2026-11-06T06:13:30Z, DEVELOPER Dispatch: Task 05 (Collections API UI Docs - Feature Code F10b), Execution Plan & Scope, Handoff Deliverables, Identity and Role, Mandatory Inputs to Read, MANDATORY INTEGRITY WARNING, Operational Safeguards & Constraints (+3 more)

### Community 74 - "Createdealpage & Createdealpage.Test"
Cohesion: 0.16
Nodes (14): createCounterpartyInvitation(), createDeal(), CreateDealPage(), handleSubmit(), CreateDealPageProps, describeCreateError(), describeError(), DirectoryItem (+6 more)

### Community 75 - "Negotiation (BaseRequest)"
Cohesion: 0.16
Nodes (9): BaseRequest, CandidateRequest, EvidenceRequest, HistoryResponse, NegotiationRequest, NegotiationResponse, NegotiationResult, ProposalResponse (+1 more)

### Community 76 - "authorize_payment_intent"
Cohesion: 0.11
Nodes (9): OutboxEventDraft, OutboxRepository, authorize_payment_intent(), AuthorizePaymentIntentCommand, PaymentIntentAuthorizationOutcome, PaymentIntentRepository, SellerMembershipRepository, UnauthorizedPaymentAuthorization (+1 more)

### Community 77 - "Agreement"
Cohesion: 0.16
Nodes (7): Agreement, Approval, AgreementId, AgreementVersionId, FakeAgreementRepository, DealDomainTests, make_deal()

### Community 78 - "13 Postgres Temporal & 14"
Cohesion: 0.14
Nodes (9): Organization-Scoped Routing Policy, Durable Scoped Reminder Scheduling, Isolated PostgreSQL Migration and Constraint Testing, PostgreSQL and Temporal Verification Specification, Temporal Worker Crash Replay and Recovery, PayPal Sandbox Lifecycle Verification, PayPal Sandbox Specification F11b, Signature-Verified Webhook and Authenticated Reconciliation (+1 more)

### Community 79 - "Tsconfig (tsconfig.json)"
Cohesion: 0.11
Nodes (17): compilerOptions, allowImportingTsExtensions, jsx, lib, module, moduleDetection, moduleResolution, noEmit (+9 more)

### Community 81 - "Test Counterparty Onboarding Migration &"
Cohesion: 0.12
Nodes (3): create_database_engine(), CounterpartyOnboardingMigrationTests, DemoFixtureMigrationTests

### Community 82 - "Test Communication Repositories (MessageIdempotencyPostgresTests)"
Cohesion: 0.20
Nodes (5): MessageIdempotencyPostgresTests, _find_conversation(), _find_keyed_message(), rendezvous(), wait_for()

### Community 83 - "Test Operations & Test Outbox"
Cohesion: 0.16
Nodes (6): WorkflowStartError, WorkflowStartTransientError, captured_output(), SafeOperationsTests, exercise(), failed_db()

### Community 84 - "create_worker"
Cohesion: 0.11
Nodes (5): DealWorkflowStatus, create_worker(), workflow_activities(), WorkflowWorkerIntegrationTests, WorkflowWorkerTests

### Community 85 - "BRIEFING — 2026-11-06T06:23:30Z"
Cohesion: 0.17
Nodes (11): Active Timers, Artifact Index, BRIEFING — 2026-11-06T06:23:30Z, Current Parent, 🔒 Key Constraints, Key Decisions Made, Mission, 🔒 My Identity (+3 more)

### Community 87 - "demo_lifecycle.py"
Cohesion: 0.19
Nodes (8): _acquire_lock(), _is_demo_deal(), lock_demo_deal_creation(), lock_demo_payment_processing(), lock_demo_reset(), lock_outbox_dispatch(), DemoLifecycleLockTests, _postgres_session()

### Community 88 - "Human Bilateral Amendment Workflow"
Cohesion: 0.40
Nodes (3): Canonical Hash and Legacy Export Preservation, Human Bilateral Amendment Workflow, Cancellation and Dispute Case State Machine

### Community 89 - "ApiError"
Cohesion: 0.06
Nodes (33): addOrganizationMember(), ApiError, getOrganizationProfile(), listDeals(), updateOrganizationProfile(), ContactVisibility, OrganizationContact, ViewerRole (+25 more)

### Community 92 - "Handoff Report: Task 05 (Collections API UI Docs - Feature Code F10b)"
Cohesion: 0.18
Nodes (10): 1. Observation, 3. Caveats, 4. Conclusion & Actionable Developer Execution Plan, 5. Verification Method, Detailed Step-by-Step Plan for the DEVELOPER, Handoff Report: Task 05 (Collections API UI Docs - Feature Code F10b), Invalidation Conditions, Mandatory Commands & Exact Targets (+2 more)

### Community 94 - "Message"
Cohesion: 0.11
Nodes (5): Message, _is_unique_violation(), _message_to_domain(), FakeCommunicationRepository, FakeCommunicationRepository

### Community 95 - "api/deals.py"
Cohesion: 0.06
Nodes (19): create_deal_route(), CreateDealRequest, DealResponse, DealSummaryResponse, get_deal_repository(), list_deals_route(), read_deal_route(), _to_response() (+11 more)

### Community 96 - "application/conversations.py"
Cohesion: 0.04
Nodes (29): _list_all_constraints_for_owner(), persist_fact_candidates(), add_message(), AddMessageCommand, can_view_constraint(), ConstraintRepository, correct_constraint(), create_manual_constraint() (+21 more)

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

### Community 102 - "BRIEFING — 2026-11-06T05:44:20Z"
Cohesion: 0.22
Nodes (8): Artifact Index, BRIEFING — 2026-11-06T05:44:20Z, 🔒 Key Constraints, Mission, 🔒 My Identity, Project Status, User Context, Victory Audit Status

### Community 105 - "Project: Task 05 (Collections API UI Docs - Feature Code F10b)"
Cohesion: 0.29
Nodes (6): Client ↔ Agreements / Negotiation API, Code Layout, Feature Inventory, Interface Contracts, Milestones, Project: Task 05 (Collections API UI Docs - Feature Code F10b)

### Community 106 - "PLANNER Dispatch"
Cohesion: 0.33
Nodes (5): 2026-11-06T05:45:32Z, Constraints, Identity and Role, Objectives, PLANNER Dispatch

### Community 108 - "App.test.tsx"
Cohesion: 0.06
Nodes (32): createOrganization(), getCommercialDocumentDraft(), mockedApiRequest, mockedCreateOrganization, mockedGetCommercialDocumentDraft, mockedGetCurrentAgreement, mockedGetDeal, mockedGetDealMessageExistence (+24 more)

### Community 110 - "Progress — orchestrator_1"
Cohesion: 0.50
Nodes (3): Current Status, Iteration Status, Progress — orchestrator_1

### Community 111 - "ConversationContractTests"
Cohesion: 0.10
Nodes (4): can_view_message(), confirm_constraint(), ConversationContractTests, FakeConstraintRepository

### Community 112 - "contracts.py"
Cohesion: 0.30
Nodes (9): _is_weak_jwt_secret(), _contains_numeric_token(), _contains_token(), _date_value_is_present(), _fact_value_is_supported_by_quote(), _flexible_whitespace_pattern(), _number_with_currency_is_present(), _number_with_unit_is_present() (+1 more)

### Community 114 - "Progress — Task 05 Planner"
Cohesion: 0.50
Nodes (3): Progress — Task 05 Planner, Status, Steps

### Community 117 - "OrganizationId"
Cohesion: 0.08
Nodes (6): OrganizationId, AiContextSelectionTests, NegotiationMigrationTests, OrganizationDomainTests, OrganizationMemberDomainTests, OrganizationProfileDomainTests

### Community 119 - "Final Gates and Truthful Completion Specification"
Cohesion: 0.20
Nodes (9): Evidence-Free Projection and Safety Bounds, F12 Trade Pack Handoff Document, Trade Pack Export Contract, Browser Verification Specification, ZIP HTML and Print Export Verification, Two-Party Isolated Browser Testing, Final Gates and Truthful Completion Specification, Full Gate Verification Suite (+1 more)

### Community 120 - "Skill (Repo Idea Thinker Skill)"
Cohesion: 0.50
Nodes (3): Repo Idea Thinker Skill, Repository-Grounded Ideation Discipline, Idea Quality Standards and Lightweight Validation

### Community 134 - "dev.py"
Cohesion: 0.05
Nodes (17): DevResetResponse, DevRoleSwitchRequest, _require_demo_admin(), _require_dev_environment(), reset_demo(), simulate_payment(), SimulatePaymentRequest, switch_role() (+9 more)

### Community 141 - "sqlalchemy"
Cohesion: 0.04
Nodes (33): run_migrations_offline(), upgrade(), uuid_column(), upgrade(), upgrade(), upgrade(), upgrade(), downgrade() (+25 more)

### Community 143 - "DomainError"
Cohesion: 0.07
Nodes (19): DuplicateActivePaymentIntent, PaymentIntentCommandMismatch, PaymentMilestoneNotFound, PaymentModeChanged, PaymentStatusRecord, PaymentIntentStatus, PaymentMilestone, DomainError (+11 more)

### Community 147 - "AI Provider Boundary Specification"
Cohesion: 0.53
Nodes (4): F2 AI Configuration and Provider Boundary, AI Provider Boundary Specification, AI Resilience and Retry Policy, AISuggestionProvider Contract

### Community 148 - "_register_shutdown_handlers"
Cohesion: 0.27
Nodes (4): _register_shutdown_handlers(), _remove_shutdown_handlers(), _request_shutdown(), WorkerShutdownSignalTests

### Community 153 - "authorize_payment_route"
Cohesion: 0.10
Nodes (15): authorize_payment_route(), AuthorizePaymentRequest, AuthorizePaymentResponse, get_payment_status_repository(), list_payment_statuses_route(), PaymentOutboxStatus, PaymentPreviewResponse, preview_payment_route() (+7 more)

### Community 157 - "NegotiationCommand"
Cohesion: 0.42
Nodes (3): negotiate(), NegotiationCommand, NegotiationRepository

### Community 160 - "auth.py"
Cohesion: 0.03
Nodes (25): _as_utc(), create_refresh_token(), CredentialsRequest, _decode_token(), _development_actor(), development_login(), _encode_access_token(), get_current_actor() (+17 more)

### Community 163 - "0004_communication_sources_and_scope_indexes.py"
Cohesion: 0.60
Nodes (4): _create_scope_index(), downgrade(), _drop_scope_index(), upgrade()

## Knowledge Gaps
- **47 isolated node(s):** `syncally`, `F1a Curated Repeatable Demo Fixture`, `Editorial Dark Theme Design System`, `ZIP HTML and Print Export Verification`, `Whole-Worktree Independent Review` (+42 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1413 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **47 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ActorContext` connect `Test Deal Routes & Identity` to `Conversations & Test Conversation Use`, `Test Ai Provider & Ai`, `DealId`, `dev.py`, `Seed Demo & Deals`, `api/agreements.py`, `Test Conversation Routes (ConversationRouteTests)`, `Test Agreement Routes (AgreementRouteTests)`, `ai.py`, `DomainError`, `Simulate Deal Flow & Test`, `Test Organization Invitations & Organizations`, `authorize_payment_route`, `repositories/payment_processing.py`, `User`, `auth.py`, `application/agreements.py`, `OrganizationCapability`, `Test Payment Intent Repository &`, `api/fulfillment.py`, `Test Organization Directory & Organizations`, `Deal`, `add_organization_member`, `create_counterparty_invitation`, `SqlAlchemyPaymentIntentRepository`, `Session`, `Money`, `Negotiation (BaseRequest)`, `authorize_payment_intent`, `Agreement`, `Test Communication Repositories (MessageIdempotencyPostgresTests)`, `Test Negotiation (NegotiationRouteTests)`, `api/deals.py`, `application/conversations.py`, `ConversationContractTests`, `OrganizationId`?**
  _High betweenness centrality (0.125) - this node is a cross-community bridge._
- **Are the 113 inferred relationships involving `ActorContext` (e.g. with `approve_agreement_route()` and `commit_agreement_route()`) actually correct?**
  _`ActorContext` has 113 INFERRED edges - model-reasoned connections that need verification._
- **What connects `syncally`, `F1a Curated Repeatable Demo Fixture`, `Editorial Dark Theme Design System` to the rest of the system?**
  _47 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Conversations & Test Conversation Use` be split into smaller, more focused modules?**
  _Cohesion score 0.0586997685672207 - nodes in this community are weakly interconnected._
- **Why does `Current Workspace and Dependency Verification (R1)` connect `Money` to `api/agreements.py`, `Handoff Report: Task 05 (Collections API UI Docs - Feature Code F10b)`, `DomainError`, `Types & Client`?**
  _High betweenness centrality (0.105) - this node is a cross-community bridge._
- **Are the 60 inferred relationships involving `OrganizationId` (e.g. with `build_trade_terms_from_request()` and `create_reviewed_agreement_draft_route()`) actually correct?**
  _`OrganizationId` has 60 INFERRED edges - model-reasoned connections that need verification._
- **Should `AIContractError` be split into smaller, more focused modules?**
  _Cohesion score 0.10628019323671498 - nodes in this community are weakly interconnected._