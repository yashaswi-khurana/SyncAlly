# Graph Report - SyncAlly  (2026-11-02)

## Corpus Check
- 275 files · ~230,310 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 8 file(s) not represented in the graph (top: (none) 4, .example 1, .ini 1)

## Summary
- 4157 nodes · 13451 edges · 153 communities (105 shown, 48 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 1786 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `f630eb54`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Conversations & Test Conversation Use
- contracts.py
- identifiers.py
- authorize_payment_route
- Test Ai Provider & Ai
- OrganizationId
- Seed Demo & Deals
- PaymentNeedsAction
- Router & Signinpage
- Agreements & Obligations
- Test Conversation Routes (ConversationRouteTests)
- Test Organization Domain & Trade
- Test Agreement Routes (AgreementRouteTests)
- get_current_actor
- process_payment_intent
- Agreements & Agreement
- NegotiationTests
- Types & Client
- ProposedTerms
- InvalidTransition
- CommercialDocumentDraftTests
- Test Outbox Dispatcher & Outbox
- Simulate Deal Flow & Test
- Test Organization Invitations & Organizations
- Communications & Conversations
- Package & Vite.Config
- vitest
- Dealconversationreview & Dealconversationreview.Test
- Skill & Skill.Md
- sqlalchemy
- draft_proposal_from_context
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
- api/organizations.py
- api/deals.py
- GmailSMTPInvoiceNotifier
- Test Demo Lifecycle & Test
- Test Dev Routes (DevRoutesTests)
- AISuggestionProviderTests
- DealWorkflow
- Test Organization Directory & Organizations
- Negotiation & Proposal
- Outbox & Temporal
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
- Test Payment Processing & Test
- Test Deal Routes & Identity
- Test Identity Boundary & Config
- Compose.Yaml (volumes)
- Dev (DevResetResponse)
- Test Workflow Worker & Worker
- AuditEvent
- Test Payment Reconciliation & Intent
- openai.py
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
- Conversations & Test Conversation Routes
- Test Ai Context & Conversations
- Main & Test Identity Boundary
- ConversationContractTests
- Human Bilateral Amendment Workflow
- ApiError
- Test Organization Index Migration (OrganizationIndexPostgresMigrationTests)
- Server-Enforced Capability Matrix
- PaymentWorkItem
- Test Negotiation (NegotiationRouteTests)
- Operations (OperationalRequestMiddleware)
- repositories/payment_processing.py
- Constraint
- Test Database (DatabasePersistenceTests)
- Master Execution Contract
- 0005 Conversation Party Unique (Enforce
- Main (Request)
- Safe Operations and Recovery Guide
- MigrationConfigTests
- refresh_access_token
- Test Negotiation Migration (NegotiationMigrationTests)
- Test Payment Mode Migration (PaymentModeMigrationTests)
- api/payments.py
- Test Communication Migration (ConversationPartyUniquenessMigrationTests)
- AuthorizePaymentIntentCommand
- 0004 Communication Sources And Scope
- ai.py
- create_refresh_token
- contracts.py
- Test Provider Invoice Unique Migration
- _is_duplicate_membership_error
- NegotiationPostgresRaceTests
- Final Gates and Truthful Completion Specification
- Skill (Repo Idea Thinker Skill)
- login
- Vite Env.D (ImportMeta)
- NegotiationSession
- ConversationUseCaseTests
- Index (Frontend HTML Root Document)
- Pyproject (syncally)
- _is_one_active_per_milestone_violation
- queue_simulated_reconciliation
- .list_for_agreement
- PaymentIntentCommandMismatch
- NegotiationCommand
- SafeOperationalFormatter
- field_validator
- AI Provider Boundary Specification
- database_health
- Four-Dimension Profile Collections
- Two-Party Judge Journey
- HealthRouteTests

## God Nodes (most connected - your core abstractions)
1. `ActorContext` - 230 edges
2. `OrganizationId` - 165 edges
3. `InvariantViolation` - 105 edges
4. `Deal` - 97 edges
5. `DealId` - 93 edges
6. `Money` - 93 edges
7. `AISuggestionProviderTests` - 87 edges
8. `UserId` - 85 edges
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

## Communities (153 total, 48 thin omitted)

### Community 0 - "Conversations & Test Conversation Use"
Cohesion: 0.06
Nodes (47): add_message_route(), AISuggestionRequest, clarify_fact_route(), confirm_fact_route(), ConstraintResponse, correct_fact_route(), CorrectFactRequest, create_fact_route() (+39 more)

### Community 1 - "contracts.py"
Cohesion: 0.14
Nodes (12): AIContractError, AIValidationClaim, _check_keys(), _decimal(), _required_string(), scope_extracted_facts(), _validate_decimal(), _validate_fact_value() (+4 more)

### Community 2 - "identifiers.py"
Cohesion: 0.07
Nodes (3): _decimal(), canonical_decimal(), DomainDependencyTests

### Community 3 - "authorize_payment_route"
Cohesion: 0.10
Nodes (12): authorize_payment_route(), AuthorizePaymentRequest, AuthorizePaymentResponse, get_payment_status_repository(), list_payment_statuses_route(), PaymentPreviewResponse, preview_payment_route(), list_current_payment_statuses() (+4 more)

### Community 4 - "Test Ai Provider & Ai"
Cohesion: 0.11
Nodes (12): extract_facts_from_context(), ConfiguredAIProvider, respond(), respond(), respond(), respond(), respond(), respond() (+4 more)

### Community 5 - "OrganizationId"
Cohesion: 0.08
Nodes (14): Message, ConstraintId, ConversationId, DealId, MessageId, OrganizationId, UserId, constraint() (+6 more)

### Community 6 - "Seed Demo & Deals"
Cohesion: 0.07
Nodes (33): _clear_fixture(), _create_fixture(), _delete_scoped(), DemoCollisionError, DemoIdentity, _normalized_index_predicate(), _password_for(), _preflight() (+25 more)

### Community 7 - "PaymentNeedsAction"
Cohesion: 0.10
Nodes (10): receive_paypal_invoice_webhook(), PaymentNeedsAction, PaymentOutcomeUnknown, PaymentRetryableError, PayPalSandboxInvoiceProvider, _provider_request_id(), _send_request(), transition() (+2 more)

### Community 8 - "Router & Signinpage"
Cohesion: 0.07
Nodes (52): listOrganizations(), clearAccessToken(), getAccessToken(), setAccessToken(), setTokens(), TokenResponse, App(), handleInvitationAccepted() (+44 more)

### Community 9 - "Agreements & Obligations"
Cohesion: 0.08
Nodes (17): AgreementRepository, AuditEventDraft, AuditRepository, commit_agreement(), create_agreement_draft(), create_reviewed_agreement_draft(), CreateReviewedAgreementDraftCommand, get_current_agreement() (+9 more)

### Community 10 - "Test Conversation Routes (ConversationRouteTests)"
Cohesion: 0.10
Nodes (3): ConversationRouteTests, respond(), send()

### Community 11 - "Test Organization Domain & Trade"
Cohesion: 0.08
Nodes (19): compare_agreement_terms(), _display(), _render(), Agreement, Approval, PaymentTerm, ShipmentTerm, TradeLineItem (+11 more)

### Community 13 - "get_current_actor"
Cohesion: 0.11
Nodes (7): _decode_token(), _development_actor(), development_login(), get_current_actor(), _unauthorized(), _require_demo_admin(), resolve_actor()

### Community 14 - "process_payment_intent"
Cohesion: 0.09
Nodes (6): PaymentInvoiceProvider, PaymentProcessingRepository, process_payment_intent(), reconcile_payment_intent(), _request_id_retry_window_expired(), require_payment_provider()

### Community 15 - "Agreements & Agreement"
Cohesion: 0.07
Nodes (25): AgreementVersionResponse, ApprovalResponse, approve_agreement_route(), commit_agreement_route(), CommitAgreementRequest, compare_agreements_route(), create_agreement_draft_route(), create_reviewed_agreement_draft_route() (+17 more)

### Community 16 - "NegotiationTests"
Cohesion: 0.20
Nodes (4): EvidenceReference, ProposalBase, negotiate_in_transaction(), NegotiationTests

### Community 17 - "Types & Client"
Cohesion: 0.07
Nodes (58): describeDetail(), getDealMessageExistence(), getNegotiation(), isAbortError(), isRecord(), negotiateDeal(), readErrorDetail(), AgreementApproval (+50 more)

### Community 18 - "ProposedTerms"
Cohesion: 0.08
Nodes (11): AIProviderError, FactExtractionRequest, ProposalDraftRequest, ExtractedFact, FactField, ProposedTerms, SourceReference, DemoAISuggestionProvider (+3 more)

### Community 19 - "InvalidTransition"
Cohesion: 0.18
Nodes (3): Proposal, PaymentIntent, InvalidTransition

### Community 20 - "CommercialDocumentDraftTests"
Cohesion: 0.09
Nodes (15): CommercialDocumentDraftResponse, get_commercial_document_draft_route(), get_trade_pack_route(), AgreementNotCommitted, export_display_terms(), generate_commercial_document_draft(), generate_trade_pack(), InvalidTradePack (+7 more)

### Community 21 - "Test Outbox Dispatcher & Outbox"
Cohesion: 0.08
Nodes (15): build_deal_workflow_id(), DealWorkflowStarter, dispatch_outbox_event(), OutboxDispatchResult, PendingOutboxEvent, NotificationKind, apply_dispatch_result(), claim_next_pending_event() (+7 more)

### Community 22 - "Simulate Deal Flow & Test"
Cohesion: 0.07
Nodes (11): _build_in_process_client(), dispatch_payment(), session_factory(), ci_deal_flow_hook(), DealFlowContext, DealFlowSimulator, run_simulation(), SimulationError (+3 more)

### Community 23 - "Test Organization Invitations & Organizations"
Cohesion: 0.16
Nodes (5): accept_invitation(), AcceptInvitationRequest, create_organization_invitation(), CreateInvitationRequest, OrganizationInvitationTests

### Community 24 - "Communications & Conversations"
Cohesion: 0.08
Nodes (15): message_fingerprint(), ConstraintKind, ConstraintStatus, Conversation, MessageSourceType, Visibility, CommunicationScopeError, _constraint_to_domain() (+7 more)

### Community 25 - "Package & Vite.Config"
Cohesion: 0.05
Nodes (52): dependencies, react@^19.3.0, react-dom@^19.3.0, three@^0.186.1, devDependencies, eslint@^10.13.0, @eslint/js@^10.0.1, eslint-plugin-react-hooks@^7.1.1 (+44 more)

### Community 26 - "vitest"
Cohesion: 0.09
Nodes (18): listDeals(), ViewerRole, DealsPage(), DealsPageProps, DealsState, describeError(), ROLE_LABELS, mockedListDeals (+10 more)

### Community 27 - "Dealconversationreview & Dealconversationreview.Test"
Cohesion: 0.07
Nodes (39): createDealMessage(), importDealThread(), listDealFacts(), listDealMessages(), previewDealThreadImport(), updateFactVisibility(), areFactsEqual(), ConversationState (+31 more)

### Community 28 - "Skill & Skill.Md"
Cohesion: 0.04
Nodes (43): API and Database Engineer Skill, API Design and Contract Semantics, Data Integrity and Invariant Enforcement, Query Performance and Projection Optimization, Schema Migration and Backward Compatibility, Transaction Boundaries and Atomicity, Archify Diagrammer Skill, Archify CLI Global Tool (+35 more)

### Community 29 - "sqlalchemy"
Cohesion: 0.04
Nodes (27): run_migrations_offline(), upgrade(), uuid_column(), upgrade(), upgrade(), upgrade(), upgrade(), downgrade() (+19 more)

### Community 30 - "draft_proposal_from_context"
Cohesion: 0.13
Nodes (7): AISuggestionProvider, draft_proposal_from_context(), _provider_context(), provider_provenance(), _rejected_fact_result(), ValidationIssue, ValidationResult

### Community 31 - "DealDetailPage.test.tsx"
Cohesion: 0.13
Nodes (14): getCommercialDocumentDraft(), DEAL, flushMicrotasks(), mockedApiRequest, mockedCreateDealMessage, mockedGetCommercialDocumentDraft, mockedGetCurrentAgreement, mockedGetDeal (+6 more)

### Community 32 - "Agreements & Counterparty Onboarding"
Cohesion: 0.08
Nodes (20): AgreementAccessDenied, AgreementAlreadyCommitted, AgreementNotFound, AgreementVersionConflict, AmbiguousAgreementOrganization, CreateAgreementDraftCommand, DuplicateApproval, ProposalNotFound (+12 more)

### Community 33 - "Aisuggestionreview & Suggestionpreview"
Cohesion: 0.09
Nodes (36): correctDealFact(), createDealFact(), draftDealProposal(), reviewDealFact(), suggestDealFacts(), AIProvenance, DealFact, FactReviewAction (+28 more)

### Community 34 - "SyncAlly Implementation Plan Document"
Cohesion: 0.16
Nodes (13): SyncAlly Architecture Document, System Topology and Ownership Boundaries, Temporal Worker and Outbox Architecture, Acceptance Criteria Verification Matrix, SyncAlly Implementation Plan Document, Issue #77 Architecture Contracts, Stage Lifecycle Roadmap, Frontend API Client and Authoritative State (+5 more)

### Community 35 - "PaymentProcessingTests"
Cohesion: 0.13
Nodes (6): payment_invoice_number(), FakeInvoiceProvider, FakeProcessingRepository, PaymentProcessingTests, _request(), _work_item()

### Community 36 - "Test Agreements & Test Local"
Cohesion: 0.07
Nodes (10): CommitAgreementCommand, RecordApprovalCommand, commit_agreement_in_transaction(), record_approval_in_transaction(), SqlAlchemyAuditRepository, SqlAlchemyObligationRepository, SqlAlchemyPaymentMilestoneRepository, AgreementCommitTests (+2 more)

### Community 37 - "log_operation"
Cohesion: 0.14
Nodes (14): _connect_with_retry(), main(), run_forever(), main(), run_forever(), is_permanent_rpc_error(), configure_logging(), log_operation() (+6 more)

### Community 38 - "InvariantViolation"
Cohesion: 0.06
Nodes (23): update_organization_profile_route(), _normalized_text(), _require_decimal(), ContactVisibility, _normalize_string(), Organization, OrganizationContact, OrganizationMember (+15 more)

### Community 39 - "Paymentstatuspanel & Paymentstatuspanel.Test"
Cohesion: 0.06
Nodes (42): authorizeDealPayment(), getCurrentAgreement(), getDeal(), getOrganization(), listPaymentStatuses(), previewDealPayment(), PaymentIntentStatus, DealDetailPage() (+34 more)

### Community 41 - "api/organizations.py"
Cohesion: 0.08
Nodes (8): _require_dev_environment(), OperationalFastAPI, CounterpartyInvitationResponse, InvitationResponse, CommercialDocumentDraft, hash_password(), verify_password(), get_db()

### Community 42 - "api/deals.py"
Cohesion: 0.07
Nodes (17): create_deal_route(), CreateDealRequest, DealResponse, DealSummaryResponse, get_deal_repository(), list_deals_route(), read_deal_route(), _to_response() (+9 more)

### Community 43 - "GmailSMTPInvoiceNotifier"
Cohesion: 0.07
Nodes (8): get_paypal_webhook_configuration(), PaymentInvoiceNotice, main(), GmailSettings, PayPalSettings, GmailSMTPInvoiceNotifier, _FakeSMTP, GmailSMTPInvoiceNotifierTests

### Community 44 - "Test Demo Lifecycle & Test"
Cohesion: 0.09
Nodes (17): PaymentInvoiceReconciliation, _money(), _parse_money(), PaymentIntentStatus, PaymentMilestone, VerifiedProviderPaymentState, PaymentIntentId, PaymentMilestoneId (+9 more)

### Community 46 - "AISuggestionProviderTests"
Cohesion: 0.12
Nodes (5): AIRetryPolicy, call_with_bounded_retry(), DeterministicFakeAIProvider, AISuggestionProviderTests, extract_facts()

### Community 47 - "DealWorkflow"
Cohesion: 0.08
Nodes (10): DealWorkflow, DealWorkflowInput, DealWorkflowStatus, _require_uuid(), DealWorkflowUnitTests, new_workflow_input(), RefreshActivity, RefreshCall (+2 more)

### Community 49 - "Negotiation & Proposal"
Cohesion: 0.19
Nodes (6): NegotiationConflict, NegotiationNotFound, NegotiationOrganizationRequired, ProposalId, SqlAlchemyNegotiationRepository, projection()

### Community 50 - "Outbox & Temporal"
Cohesion: 0.13
Nodes (7): WorkflowStartError, WorkflowStartOutcome, WorkflowStartPermanentError, WorkflowStartTransientError, DealWorkflowNotification, TemporalDealWorkflowStarter, TemporalAdapterTests

### Community 51 - "Deal & Test Deal Authorization"
Cohesion: 0.10
Nodes (6): Deal, DealStatus, _to_domain(), _domain_deal(), FakeDealRepository, _domain_deal()

### Community 52 - "Test Payment Outbox & Test"
Cohesion: 0.09
Nodes (13): PaymentInvoiceNotifier, claim_next_payment_event(), _claim_statement(), _ClaimedPaymentEvent, dispatch_one_payment_event(), dispatch_pending_payment_events(), _finish_event(), _process_claimed_payment_event() (+5 more)

### Community 53 - "react"
Cohesion: 0.06
Nodes (29): addOrganizationMember(), createOrganization(), getOrganizationProfile(), updateOrganizationProfile(), ContactVisibility, Organization, OrganizationContact, COUNTRY_NAMES (+21 more)

### Community 54 - "Workflow State & Test Workflow"
Cohesion: 0.11
Nodes (9): DealWorkflowState, load_deal_workflow_state(), parse_workflow_uuid(), WorkflowAgreementRepository, WorkflowDealNotFound, WorkflowDealRepository, _FakeAgreementRepository, _FakeDealRepository (+1 more)

### Community 55 - "DealWorkflowTests"
Cohesion: 0.29
Nodes (3): DealWorkflowResult, DealWorkflowTests, new_notification()

### Community 56 - "Agreementreview & Client"
Cohesion: 0.08
Nodes (39): API_REQUEST_TIMEOUT_MS, commitAgreementVersion(), compareAgreementVersions(), getAgreementHistory(), getAgreementVersion(), getTradePack(), recordAgreementDecision(), CREATED_MESSAGE (+31 more)

### Community 57 - "Organizations & Test Organization Onboarding"
Cohesion: 0.22
Nodes (5): add_organization_member(), AddOrganizationMemberRequest, create_organization(), CreateOrganizationRequest, OrganizationOnboardingTests

### Community 58 - "Test Workflow Activities & Activities"
Cohesion: 0.13
Nodes (4): RefreshDealStateActivity, _workflow_input_value(), RefreshDealStateActivityTests, factory()

### Community 59 - "Test Migration Lock & Env"
Cohesion: 0.12
Nodes (8): run_migrations_online(), serialize_migrations(), _make_postgres_connection(), _make_sqlite_connection(), MigrationLockTests, simulated_migration(), PostgresRealAdvisoryLockTests, worker()

### Community 61 - "01 Commercial Domain Model &"
Cohesion: 0.07
Nodes (19): AgreementVersion Aggregate, Append-Only AuditEvent Ledger, Commercial Constraint and Provenance, Deal Aggregate, Organization and Membership Entities, PaymentMilestone and Obligation, Proposal Aggregate and Terms Hash, Temporal Deal Workflow (+11 more)

### Community 62 - "Test Payment Processing & Test"
Cohesion: 0.13
Nodes (3): PaymentStatusResponse, SqlAlchemyPaymentIntentRepository, PaymentStatusExtendedModelTests

### Community 63 - "Test Deal Routes & Identity"
Cohesion: 0.21
Nodes (3): ActorContext, DealAuthorizationTests, DealRouteTests

### Community 64 - "Test Identity Boundary & Config"
Cohesion: 0.15
Nodes (3): _is_weak_jwt_secret(), Settings, IdentityBoundaryTests

### Community 65 - "Compose.Yaml (volumes)"
Cohesion: 0.09
Nodes (22): POSTGRES_DB, POSTGRES_PASSWORD, POSTGRES_USER, interval, retries, test, timeout, environment (+14 more)

### Community 66 - "Dev (DevResetResponse)"
Cohesion: 0.19
Nodes (6): DevResetResponse, DevRoleSwitchRequest, reset_demo(), simulate_payment(), SimulatePaymentRequest, switch_role()

### Community 67 - "Test Workflow Worker & Worker"
Cohesion: 0.11
Nodes (7): create_worker(), _register_shutdown_handlers(), _remove_shutdown_handlers(), _request_shutdown(), workflow_activities(), WorkerShutdownSignalTests, WorkflowWorkerTests

### Community 68 - "AuditEvent"
Cohesion: 0.08
Nodes (14): _accept_invitation(), _active_admin_membership(), _case_insensitive_prefix(), _create_invitation_token(), _deal_awaiting_counterparty(), _decode_invitation_token(), _escape_like(), get_optional_actor() (+6 more)

### Community 71 - "openai.py"
Cohesion: 0.13
Nodes (13): AIPermanentError, AITransientError, parse_extracted_facts(), parse_proposed_terms(), AiContext, _json(), _object(), OpenAIChatCompletions (+5 more)

### Community 72 - "PersistentDemoSeedTests"
Cohesion: 0.06
Nodes (14): fixture_id(), initialize_offline_database(), main(), _acquire_lock(), _is_demo_deal(), lock_demo_deal_creation(), lock_demo_payment_processing(), lock_demo_reset() (+6 more)

### Community 73 - "Test Deal Repository & Deals"
Cohesion: 0.18
Nodes (3): _active_participation(), SqlAlchemyDealRepository, DealRepositoryTests

### Community 74 - "Createdealpage & Createdealpage.Test"
Cohesion: 0.13
Nodes (18): acceptInvitation(), apiBaseUrl(), apiRequest(), createAgreementFromReviewedTerms(), createCounterpartyInvitation(), createDeal(), CreateDealPage(), handleSubmit() (+10 more)

### Community 75 - "Negotiation (BaseRequest)"
Cohesion: 0.13
Nodes (12): BaseRequest, CandidateRequest, EvidenceRequest, HistoryResponse, NegotiationRequest, NegotiationResponse, NegotiationResult, ProposalResponse (+4 more)

### Community 76 - "Test Organization Invitations & Organizations"
Cohesion: 0.16
Nodes (5): create_counterparty_invitation(), CreateCounterpartyInvitationRequest, OnboardingConcurrencyCases, OnboardingPostgresConcurrencyTests, OnboardingSQLiteConcurrencyTests

### Community 77 - "application/conversations.py"
Cohesion: 0.05
Nodes (23): _list_all_constraints_for_owner(), add_message(), can_view_constraint(), can_view_message(), CommunicationRepository, ConstraintNotFound, ConstraintRepository, correct_constraint() (+15 more)

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

### Community 84 - "Conversations & Test Conversation Routes"
Cohesion: 0.19
Nodes (3): AddMessageRequest, CreateFactRequest, AddMessageRequestTests

### Community 85 - "Test Ai Context & Conversations"
Cohesion: 0.17
Nodes (3): select_ai_context(), AiContextSelectionTests, FakeCommunicationRepository

### Community 87 - "ConversationContractTests"
Cohesion: 0.13
Nodes (3): confirm_constraint(), ConversationContractTests, FakeConstraintRepository

### Community 88 - "Human Bilateral Amendment Workflow"
Cohesion: 0.40
Nodes (3): Canonical Hash and Legacy Export Preservation, Human Bilateral Amendment Workflow, Cancellation and Dispute Case State Machine

### Community 89 - "ApiError"
Cohesion: 0.13
Nodes (17): ApiError, login(), InvitationAcceptance, invitationPresentation(), demoQuickFillEnabled(), FieldErrors, getInviteTokenFromHash(), SignInPage() (+9 more)

### Community 92 - "PaymentWorkItem"
Cohesion: 0.17
Nodes (5): PaymentInvoiceLookup, PaymentInvoiceRequest, PaymentWorkItem, OfflineDemoInvoiceProvider, PaymentProviderResolver

### Community 95 - "repositories/payment_processing.py"
Cohesion: 0.08
Nodes (7): _persist_paypal_webhook_event(), PaymentInvoiceLineItem, _is_live_backend_healthy(), main(), _has_excess_currency_precision(), _provider_error_code(), record_paypal_webhook_event()

### Community 96 - "Constraint"
Cohesion: 0.09
Nodes (3): Constraint, FakeCommunicationRepository, FakeCommunicationRepository

### Community 98 - "Master Execution Contract"
Cohesion: 0.14
Nodes (31): Execution Acceptance Gates, Master Execution Contract, Safe Windows PowerShell Runner, Private Contact Channels, Profiles Specification F14, Fresh Authorization Enforcement, Permissions Specification F15a, Append-Only Fulfillment Observations and Confirmations (+23 more)

### Community 99 - "0005 Conversation Party Unique (Enforce"
Cohesion: 0.36
Nodes (5): _create_party_unique_constraint(), _deduplicate_conversations(), downgrade(), _drop_party_unique_constraint(), upgrade()

### Community 101 - "Safe Operations and Recovery Guide"
Cohesion: 0.19
Nodes (15): PayPal Sandbox Invoicing and Reconciliation Flow, Backend README Document, F11a Explicit Payment Modes, F12 Committed Trade Packs, F1a Curated Repeatable Demo Fixture, F4 Invitations and Private Pending Deals, F5 Persisted Human Negotiation, F6 Agreement History and Comparison (+7 more)

### Community 105 - "refresh_access_token"
Cohesion: 0.13
Nodes (4): _hash_refresh_token(), refresh_access_token(), RefreshRequest, RefreshToken

### Community 108 - "api/payments.py"
Cohesion: 0.16
Nodes (7): PaymentOutboxStatus, OutboxEventDraft, DuplicateActivePaymentIntent, IdempotencyKeyReused, PaymentModeChanged, AgreementStatus, SqlAlchemyOutboxRepository

### Community 110 - "AuthorizePaymentIntentCommand"
Cohesion: 0.15
Nodes (5): authorize_payment_intent(), AuthorizePaymentIntentCommand, PaymentIntentAuthorizationOutcome, PaymentIntentRepository, SellerMembershipRepository

### Community 111 - "0004 Communication Sources And Scope"
Cohesion: 0.60
Nodes (4): _create_scope_index(), downgrade(), _drop_scope_index(), upgrade()

### Community 112 - "ai.py"
Cohesion: 0.19
Nodes (6): draft_proposal(), extract_facts(), FactExtractionResult, persist_fact_candidates(), ProposalDraftResult, ValidationStatus

### Community 113 - "create_refresh_token"
Cohesion: 0.22
Nodes (7): _as_utc(), create_refresh_token(), _encode_access_token(), _issue_tokens(), _replay_rotation(), _revoke_family(), exercise_api()

### Community 114 - "contracts.py"
Cohesion: 0.22
Nodes (9): _contains_numeric_token(), _contains_token(), _date_value_is_present(), _fact_value_is_supported_by_quote(), _flexible_whitespace_pattern(), _number_with_currency_is_present(), _number_with_unit_is_present(), _numeric_pattern() (+1 more)

### Community 117 - "NegotiationPostgresRaceTests"
Cohesion: 0.24
Nodes (3): NegotiationPostgresRaceTests, failing(), succeed()

### Community 119 - "Final Gates and Truthful Completion Specification"
Cohesion: 0.20
Nodes (9): Evidence-Free Projection and Safety Bounds, F12 Trade Pack Handoff Document, Trade Pack Export Contract, Browser Verification Specification, ZIP HTML and Print Export Verification, Two-Party Isolated Browser Testing, Final Gates and Truthful Completion Specification, Full Gate Verification Suite (+1 more)

### Community 120 - "Skill (Repo Idea Thinker Skill)"
Cohesion: 0.50
Nodes (3): Repo Idea Thinker Skill, Repository-Grounded Ideation Discipline, Idea Quality Standards and Lightweight Validation

### Community 122 - "login"
Cohesion: 0.27
Nodes (5): CredentialsRequest, login(), TokenResponse, fail(), scalar()

### Community 134 - "NegotiationSession"
Cohesion: 0.29
Nodes (7): NegotiationSession, NegotiationSubmissionOutcome, ProposalStatus, NegotiationSessionId, build_proposal(), HumanNegotiationTests, NegotiationTests

### Community 135 - "ConversationUseCaseTests"
Cohesion: 0.28
Nodes (4): AddMessageCommand, send(), ConversationUseCaseTests, write_message()

### Community 139 - "_is_one_active_per_milestone_violation"
Cohesion: 0.43
Nodes (3): _is_idempotency_key_violation(), _is_one_active_per_milestone_violation(), _violated_constraint_name()

### Community 141 - ".list_for_agreement"
Cohesion: 0.20
Nodes (3): _build_invoice_url(), ExtendedPaymentStatusRecord, _utc_timestamp()

### Community 143 - "NegotiationCommand"
Cohesion: 0.42
Nodes (3): negotiate(), NegotiationCommand, NegotiationRepository

### Community 145 - "field_validator"
Cohesion: 0.14
Nodes (6): AcceptInvitationResponse, ContactPayload, ContactResponse, OrganizationDirectoryItem, ProfileResponse, UpdateProfileRequest

### Community 147 - "AI Provider Boundary Specification"
Cohesion: 0.53
Nodes (4): F2 AI Configuration and Provider Boundary, AI Provider Boundary Specification, AI Resilience and Retry Policy, AISuggestionProvider Contract

## Knowledge Gaps
- **47 isolated node(s):** `syncally`, `F1a Curated Repeatable Demo Fixture`, `Editorial Dark Theme Design System`, `ZIP HTML and Print Export Verification`, `Whole-Worktree Independent Review` (+42 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1227 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **48 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ActorContext` connect `Test Deal Routes & Identity` to `Conversations & Test Conversation Use`, `identifiers.py`, `authorize_payment_route`, `OrganizationId`, `Seed Demo & Deals`, `ConversationUseCaseTests`, `Agreements & Obligations`, `Test Conversation Routes (ConversationRouteTests)`, `Test Organization Domain & Trade`, `Test Agreement Routes (AgreementRouteTests)`, `get_current_actor`, `queue_simulated_reconciliation`, `Agreements & Agreement`, `ProposedTerms`, `CommercialDocumentDraftTests`, `Simulate Deal Flow & Test`, `Test Organization Invitations & Organizations`, `InvariantViolation`, `Test Payment Intent Repository &`, `api/organizations.py`, `api/deals.py`, `AISuggestionProviderTests`, `Test Organization Directory & Organizations`, `Organizations & Test Organization Onboarding`, `Test Payment Processing & Test`, `Test Identity Boundary & Config`, `Dev (DevResetResponse)`, `AuditEvent`, `Negotiation (BaseRequest)`, `Test Organization Invitations & Organizations`, `application/conversations.py`, `Test Communication Repositories (MessageIdempotencyPostgresTests)`, `Test Ai Context & Conversations`, `ConversationContractTests`, `Test Negotiation (NegotiationRouteTests)`, `api/payments.py`, `ai.py`?**
  _High betweenness centrality (0.109) - this node is a cross-community bridge._
- **Are the 99 inferred relationships involving `ActorContext` (e.g. with `approve_agreement_route()` and `commit_agreement_route()`) actually correct?**
  _`ActorContext` has 99 INFERRED edges - model-reasoned connections that need verification._
- **What connects `syncally`, `F1a Curated Repeatable Demo Fixture`, `Editorial Dark Theme Design System` to the rest of the system?**
  _47 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Conversations & Test Conversation Use` be split into smaller, more focused modules?**
  _Cohesion score 0.060424469413233456 - nodes in this community are weakly interconnected._
- **Why does `OrganizationId` connect `OrganizationId` to `contracts.py`, `identifiers.py`, `Seed Demo & Deals`, `ConversationUseCaseTests`, `Agreements & Obligations`, `Test Conversation Routes (ConversationRouteTests)`, `Test Organization Domain & Trade`, `Test Agreement Routes (AgreementRouteTests)`, `Agreements & Agreement`, `NegotiationTests`, `ProposedTerms`, `InvalidTransition`, `CommercialDocumentDraftTests`, `Test Outbox Dispatcher & Outbox`, `Communications & Conversations`, `Agreements & Counterparty Onboarding`, `Test Agreements & Test Local`, `InvariantViolation`, `Test Payment Intent Repository &`, `api/organizations.py`, `api/deals.py`, `Test Demo Lifecycle & Test`, `AISuggestionProviderTests`, `Negotiation & Proposal`, `Deal & Test Deal Authorization`, `Test Payment Processing & Test`, `Test Deal Repository & Deals`, `Negotiation (BaseRequest)`, `Test Organization Invitations & Organizations`, `application/conversations.py`, `Test Counterparty Onboarding Migration &`, `Test Ai Context & Conversations`, `ConversationContractTests`, `repositories/payment_processing.py`, `Constraint`, `Test Negotiation Migration (NegotiationMigrationTests)`, `api/payments.py`, `ai.py`, `contracts.py`?**
  _High betweenness centrality (0.081) - this node is a cross-community bridge._
- **Are the 56 inferred relationships involving `OrganizationId` (e.g. with `create_reviewed_agreement_draft_route()` and `write_negotiation()`) actually correct?**
  _`OrganizationId` has 56 INFERRED edges - model-reasoned connections that need verification._
- **Should `contracts.py` be split into smaller, more focused modules?**
  _Cohesion score 0.1422475106685633 - nodes in this community are weakly interconnected._