# Graph Report - SyncAlly  (2026-11-01)

## Corpus Check
- 274 files · ~224,354 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 8 file(s) not represented in the graph (top: (none) 4, .example 1, .ini 1)

## Summary
- 4085 nodes · 13203 edges · 151 communities (87 shown, 64 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 1744 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `39a70591`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Conversations & Test Conversation Use
- contracts.py
- Deals & Identity
- Payments & Intent
- Test Ai Provider & Ai
- Test Communication Repositories & Conversations
- Seed Demo & Deals
- Paypal & Payment Processing
- Router & Signinpage
- Agreements & Obligations
- Test Conversation Routes (ConversationRouteTests)
- Test Organization Domain & Trade
- Test Agreement Routes (AgreementRouteTests)
- Auth & Test Identity Boundary
- Payment Processing & Payment Outbox
- Agreements & Agreement
- NegotiationTests
- Types & Client
- ProposedTerms
- Proposal & Intent
- Documents & Test Commercial Documents
- Test Outbox Dispatcher & Outbox
- Simulate Deal Flow & Test
- Test Organization Invitations & Organizations
- Communications & Conversations
- Package & Vite.Config
- App.Test & Dealspage
- Dealconversationreview & Dealconversationreview.Test
- Skill & Skill.Md
- 0001 Initial Schema & 0002
- Ai & Contracts
- Dealdetailpage.Test & Dealdetailpage
- Agreements & Counterparty Onboarding
- Aisuggestionreview & Suggestionpreview
- SyncAlly Implementation Plan Document
- ._snapshot
- Test Agreements & Test Local
- Operations & Test Workflow Worker
- Organizations & Organization
- Paymentstatuspanel & Paymentstatuspanel.Test
- Test Payment Intent Repository &
- Main & Paypal Webhooks
- Deals & Test Deal Use
- test_gmail.py
- Test Demo Lifecycle & Test
- Test Dev Routes (DevRoutesTests)
- OrganizationInvitationTests
- Test Communication Migration & Test
- Test Organization Directory & Organizations
- Negotiation & Proposal
- Outbox & Temporal
- Deal & Test Deal Authorization
- Test Payment Outbox & Test
- Onboardingwizard & Organizationspanel
- Workflow State & Test Workflow
- Test Deal Workflow & Deal
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
- Organizations (datetime)
- Deal & Workflow Notifications
- Test Payment Reconciliation & Intent
- Deals (CreateDealRequest)
- Test Demo Lifecycle Lock &
- Test Deal Repository & Deals
- Createdealpage & Createdealpage.Test
- Negotiation (BaseRequest)
- Test Organization Invitations & Organizations
- Test Conversation Use Cases &
- 13 Postgres Temporal & 14
- Tsconfig (tsconfig.json)
- Test Paypal Webhooks (FakeWebhookVerifier)
- Test Counterparty Onboarding Migration &
- Test Communication Repositories (MessageIdempotencyPostgresTests)
- Test Operations & Test Outbox
- Conversations & Test Conversation Routes
- Test Ai Context & Conversations
- Main & Test Identity Boundary
- Deals
- Human Bilateral Amendment Workflow
- Worker & Test Workflow Worker
- Test Organization Index Migration (OrganizationIndexPostgresMigrationTests)
- Server-Enforced Capability Matrix
- Test Deal Use Cases (FakeDealRepository)
- Test Negotiation (NegotiationRouteTests)
- Operations (OperationalRequestMiddleware)
- Simulate Deal Flow & Database
- Test Ai Provider (FakeCommunicationRepository)
- Test Database (DatabasePersistenceTests)
- Master Execution Contract
- 0005 Conversation Party Unique (Enforce
- Main (Request)
- Safe Operations and Recovery Guide
- Test Migration Config & Migration
- Test Negotiation Migration (NegotiationMigrationTests)
- Test Payment Mode Migration (PaymentModeMigrationTests)
- PersistentDemoSeedTests
- Test Communication Migration (ConversationPartyUniquenessMigrationTests)
- Test Demo Seed (DemoSeedTests)
- 0004 Communication Sources And Scope
- Test Provider Invoice Unique Migration
- Organizations & Test Identity Boundary
- Config (model_validator)
- Final Gates and Truthful Completion Specification
- Skill (Repo Idea Thinker Skill)
- Test Identity Boundary
- Vite Env.D (ImportMeta)
- Test Organization Domain (DomainDependencyTests)
- Test Outbox Dispatcher (OutboxDispatchMigrationTests)
- Index (Frontend HTML Root Document)
- Pyproject (syncally)
- NegotiationPostgresRaceTests
- DealDomainTests
- OutboxEvent
- write_negotiation
- NegotiationCommand
- main
- _is_one_active_per_milestone_violation
- AI Provider Boundary Specification
- Four-Dimension Profile Collections
- Two-Party Judge Journey

## God Nodes (most connected - your core abstractions)
1. `ActorContext` - 223 edges
2. `OrganizationId` - 155 edges
3. `Deal` - 97 edges
4. `InvariantViolation` - 93 edges
5. `DealId` - 93 edges
6. `Money` - 93 edges
7. `AISuggestionProviderTests` - 87 edges
8. `UserId` - 80 edges
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

## Communities (151 total, 64 thin omitted)

### Community 0 - "Conversations & Test Conversation Use"
Cohesion: 0.05
Nodes (60): add_message_route(), AISuggestionRequest, clarify_fact_route(), confirm_fact_route(), ConstraintResponse, correct_fact_route(), CorrectFactRequest, create_fact_route() (+52 more)

### Community 1 - "contracts.py"
Cohesion: 0.09
Nodes (23): AIContractError, AIValidationClaim, _check_keys(), _contains_numeric_token(), _contains_token(), _date_value_is_present(), _decimal(), _fact_value_is_supported_by_quote() (+15 more)

### Community 3 - "Payments & Intent"
Cohesion: 0.05
Nodes (34): authorize_payment_route(), AuthorizePaymentRequest, AuthorizePaymentResponse, get_payment_status_repository(), list_payment_statuses_route(), PaymentOutboxStatus, PaymentPreviewResponse, preview_payment_route() (+26 more)

### Community 4 - "Test Ai Provider & Ai"
Cohesion: 0.07
Nodes (15): extract_facts_from_context(), DeterministicFakeAIProvider, ConfiguredAIProvider, AISuggestionProviderTests, respond(), respond(), respond(), respond() (+7 more)

### Community 5 - "Test Communication Repositories & Conversations"
Cohesion: 0.04
Nodes (24): can_view_message(), ConcurrentConstraintUpdate, confirm_constraint(), ConstraintNotFound, Constraint, Conversation, Message, ConstraintId (+16 more)

### Community 6 - "Seed Demo & Deals"
Cohesion: 0.07
Nodes (33): _accept_invitation(), CounterpartyInvitationResponse, _decode_invitation_token(), InvitationResponse, _clear_fixture(), _create_fixture(), _delete_scoped(), DemoCollisionError (+25 more)

### Community 7 - "Paypal & Payment Processing"
Cohesion: 0.05
Nodes (22): get_paypal_webhook_configuration(), receive_paypal_invoice_webhook(), PaymentInvoiceLookup, PaymentInvoiceNotice, PaymentInvoiceRequest, PaymentNeedsAction, PaymentOutcomeUnknown, PaymentRetryableError (+14 more)

### Community 8 - "Router & Signinpage"
Cohesion: 0.07
Nodes (50): login(), clearAccessToken(), getAccessToken(), setAccessToken(), setTokens(), TokenResponse, App(), handleInvitationAccepted() (+42 more)

### Community 9 - "Agreements & Obligations"
Cohesion: 0.06
Nodes (22): AgreementRepository, AuditEventDraft, AuditRepository, commit_agreement(), create_agreement_draft(), CreateAgreementDraftCommand, ObligationRepository, OutboxEventDraft (+14 more)

### Community 10 - "Test Conversation Routes (ConversationRouteTests)"
Cohesion: 0.10
Nodes (3): ConversationRouteTests, respond(), send()

### Community 11 - "Test Organization Domain & Trade"
Cohesion: 0.07
Nodes (17): Agreement, Approval, _decimal(), _normalized_text(), PaymentTerm, _require_decimal(), ShipmentTerm, TradeLineItem (+9 more)

### Community 13 - "Auth & Test Identity Boundary"
Cohesion: 0.08
Nodes (22): _as_utc(), create_refresh_token(), CredentialsRequest, _decode_token(), _development_actor(), development_login(), _encode_access_token(), get_current_actor() (+14 more)

### Community 14 - "Payment Processing & Payment Outbox"
Cohesion: 0.06
Nodes (12): payment_invoice_number(), PaymentInvoiceProvider, PaymentProcessingRepository, process_payment_intent(), reconcile_payment_intent(), _request_id_retry_window_expired(), require_payment_provider(), FakeInvoiceProvider (+4 more)

### Community 15 - "Agreements & Agreement"
Cohesion: 0.07
Nodes (28): AgreementVersionResponse, ApprovalResponse, approve_agreement_route(), commit_agreement_route(), CommitAgreementRequest, compare_agreements_route(), create_agreement_draft_route(), create_reviewed_agreement_draft_route() (+20 more)

### Community 16 - "NegotiationTests"
Cohesion: 0.21
Nodes (4): CandidateAcknowledgement, ProposalBase, negotiate_in_transaction(), NegotiationTests

### Community 17 - "Types & Client"
Cohesion: 0.07
Nodes (55): describeDetail(), getDealMessageExistence(), isAbortError(), isRecord(), negotiateDeal(), readErrorDetail(), AgreementApproval, AgreementComparison (+47 more)

### Community 18 - "ProposedTerms"
Cohesion: 0.06
Nodes (24): get_ai_suggestion_provider(), AIConfigurationError, AIPermanentError, AIProviderError, AITransientError, FactExtractionRequest, parse_extracted_facts(), parse_proposed_terms() (+16 more)

### Community 19 - "Proposal & Intent"
Cohesion: 0.09
Nodes (14): create_reviewed_agreement_draft(), CreateReviewedAgreementDraftCommand, NegotiationSession, NegotiationSubmissionOutcome, Proposal, ProposalStatus, PaymentIntent, InvalidTransition (+6 more)

### Community 20 - "Documents & Test Commercial Documents"
Cohesion: 0.08
Nodes (19): CommercialDocumentDraftResponse, get_commercial_document_draft_route(), get_trade_pack_route(), AgreementNotCommitted, CommercialDocumentDraft, _display(), export_display_terms(), generate_commercial_document_draft() (+11 more)

### Community 21 - "Test Outbox Dispatcher & Outbox"
Cohesion: 0.09
Nodes (14): build_deal_workflow_id(), dispatch_outbox_event(), OutboxDispatchResult, PendingOutboxEvent, lock_outbox_dispatch(), apply_dispatch_result(), claim_next_pending_event(), _claim_statement() (+6 more)

### Community 22 - "Simulate Deal Flow & Test"
Cohesion: 0.06
Nodes (12): _build_in_process_client(), dispatch_payment(), session_factory(), ci_deal_flow_hook(), DealFlowContext, DealFlowSimulator, _is_live_backend_healthy(), run_simulation() (+4 more)

### Community 23 - "Test Organization Invitations & Organizations"
Cohesion: 0.24
Nodes (5): accept_invitation(), AcceptInvitationRequest, create_organization_invitation(), CreateInvitationRequest, AuditEvent

### Community 24 - "Communications & Conversations"
Cohesion: 0.08
Nodes (13): message_fingerprint(), ConstraintKind, ConstraintStatus, MessageSourceType, Visibility, CommunicationScopeError, _constraint_to_domain(), _conversation_to_domain() (+5 more)

### Community 25 - "Package & Vite.Config"
Cohesion: 0.06
Nodes (47): devDependencies, eslint@^10.13.0, @eslint/js@^10.0.1, eslint-plugin-react-hooks@^7.1.1, eslint-plugin-react-refresh@^0.4.20, globals@^17.13.0, happy-dom@^21.0.3, @testing-library/dom@^10.4.1 (+39 more)

### Community 26 - "App.Test & Dealspage"
Cohesion: 0.06
Nodes (38): ApiError, getTradePack(), listDeals(), TradePackFormat, AgreementVersion, ViewerRole, mockedApiRequest, mockedCreateOrganization (+30 more)

### Community 27 - "Dealconversationreview & Dealconversationreview.Test"
Cohesion: 0.07
Nodes (40): createDealMessage(), importDealThread(), listDealFacts(), listDealMessages(), previewDealThreadImport(), reviewDealFact(), updateFactVisibility(), areFactsEqual() (+32 more)

### Community 28 - "Skill & Skill.Md"
Cohesion: 0.04
Nodes (43): API and Database Engineer Skill, API Design and Contract Semantics, Data Integrity and Invariant Enforcement, Query Performance and Projection Optimization, Schema Migration and Backward Compatibility, Transaction Boundaries and Atomicity, Archify Diagrammer Skill, Archify CLI Global Tool (+35 more)

### Community 29 - "0001 Initial Schema & 0002"
Cohesion: 0.06
Nodes (19): upgrade(), uuid_column(), upgrade(), upgrade(), upgrade(), upgrade(), downgrade(), upgrade() (+11 more)

### Community 30 - "Ai & Contracts"
Cohesion: 0.08
Nodes (17): AIProvenance, AIRetryPolicy, AISuggestionProvider, call_with_bounded_retry(), draft_proposal(), draft_proposal_from_context(), extract_facts(), FactExtractionResult (+9 more)

### Community 31 - "Dealdetailpage.Test & Dealdetailpage"
Cohesion: 0.06
Nodes (35): dependencies, react@^19.3.0, react-dom@^19.3.0, three@^0.186.1, getCommercialDocumentDraft(), getDeal(), getOrganization(), DealConstellation() (+27 more)

### Community 32 - "Agreements & Counterparty Onboarding"
Cohesion: 0.11
Nodes (11): AgreementAccessDenied, AgreementNotFound, AgreementVersionConflict, StaleAgreementVersion, UnauthorizedApproval, WrongTermsHash, is_pending(), lock_deal() (+3 more)

### Community 33 - "Aisuggestionreview & Suggestionpreview"
Cohesion: 0.09
Nodes (37): correctDealFact(), createDealFact(), draftDealProposal(), getNegotiation(), suggestDealFacts(), AIProvenance, DealFact, FactReviewAction (+29 more)

### Community 34 - "SyncAlly Implementation Plan Document"
Cohesion: 0.16
Nodes (13): SyncAlly Architecture Document, System Topology and Ownership Boundaries, Temporal Worker and Outbox Architecture, Acceptance Criteria Verification Matrix, SyncAlly Implementation Plan Document, Issue #77 Architecture Contracts, Stage Lifecycle Roadmap, Frontend API Client and Authoritative State (+5 more)

### Community 36 - "Test Agreements & Test Local"
Cohesion: 0.09
Nodes (8): CommitAgreementCommand, compare_agreement_terms(), RecordApprovalCommand, commit_agreement_in_transaction(), record_approval_in_transaction(), AgreementCommitTests, LocalWorkflowSmokeTests, commit_once()

### Community 37 - "Operations & Test Workflow Worker"
Cohesion: 0.10
Nodes (16): _connect_with_retry(), main(), run_forever(), main(), run_forever(), is_permanent_rpc_error(), configure_logging(), log_operation() (+8 more)

### Community 38 - "Organizations & Organization"
Cohesion: 0.10
Nodes (11): Organization, OrganizationMember, OrganizationMemberRole, OrganizationMemberStatus, OrganizationStatus, _membership_to_domain(), _organization_to_domain(), SqlAlchemyOrganizationMemberRepository (+3 more)

### Community 39 - "Paymentstatuspanel & Paymentstatuspanel.Test"
Cohesion: 0.08
Nodes (34): API_REQUEST_TIMEOUT_MS, authorizeDealPayment(), listPaymentStatuses(), previewDealPayment(), CREATED_MESSAGE, fetchMock, lastRequest(), sentBody() (+26 more)

### Community 40 - "Test Payment Intent Repository &"
Cohesion: 0.12
Nodes (4): queue_simulated_reconciliation(), require_simulation_scope(), authorize_payment_intent_in_transaction(), PaymentIntentRepositoryTests

### Community 41 - "Main & Paypal Webhooks"
Cohesion: 0.07
Nodes (6): database_health(), health(), OperationalFastAPI, _persist_paypal_webhook_event(), record_paypal_webhook_event(), HealthRouteTests

### Community 42 - "Deals & Test Deal Use"
Cohesion: 0.10
Nodes (10): _both_organizations_active(), create_deal(), CreateDealCommand, DealAccessDenied, DealNotFound, DealRepository, get_deal(), list_deals() (+2 more)

### Community 44 - "Test Demo Lifecycle & Test"
Cohesion: 0.10
Nodes (12): PaymentInvoiceReconciliation, _money(), _parse_money(), VerifiedProviderPaymentState, Money, simulation_state(), transition(), FakePayPalInvoiceProvider (+4 more)

### Community 46 - "OrganizationInvitationTests"
Cohesion: 0.18
Nodes (3): create_counterparty_invitation(), CreateCounterpartyInvitationRequest, OrganizationInvitationTests

### Community 47 - "Test Communication Migration & Test"
Cohesion: 0.12
Nodes (4): CommunicationMigrationTests, MessageIdempotencyMigrationTests, OrganizationIndexMigrationTests, PaymentCreateStartedMigrationTests

### Community 48 - "Test Organization Directory & Organizations"
Cohesion: 0.14
Nodes (4): _case_insensitive_prefix(), _escape_like(), value(), OrganizationDirectoryTests

### Community 49 - "Negotiation & Proposal"
Cohesion: 0.22
Nodes (3): NegotiationConflict, SqlAlchemyNegotiationRepository, projection()

### Community 50 - "Outbox & Temporal"
Cohesion: 0.11
Nodes (8): DealWorkflowStarter, WorkflowStartError, WorkflowStartOutcome, WorkflowStartPermanentError, WorkflowStartTransientError, DealWorkflowNotification, TemporalDealWorkflowStarter, TemporalAdapterTests

### Community 51 - "Deal & Test Deal Authorization"
Cohesion: 0.10
Nodes (4): Deal, DealStatus, FakeDealRepository, FakeDealRepository

### Community 52 - "Test Payment Outbox & Test"
Cohesion: 0.08
Nodes (13): PaymentInvoiceNotifier, claim_next_payment_event(), _claim_statement(), _ClaimedPaymentEvent, dispatch_one_payment_event(), dispatch_pending_payment_events(), _finish_event(), _process_claimed_payment_event() (+5 more)

### Community 53 - "Onboardingwizard & Organizationspanel"
Cohesion: 0.11
Nodes (23): addOrganizationMember(), createOrganization(), listOrganizations(), Organization, COUNTRY_NAMES, CountryOption, describeError(), isAmbiguousCreateFailure() (+15 more)

### Community 54 - "Workflow State & Test Workflow"
Cohesion: 0.10
Nodes (10): DealWorkflowState, load_deal_workflow_state(), parse_workflow_uuid(), WorkflowAgreementRepository, WorkflowDealNotFound, WorkflowDealRepository, _domain_deal(), _FakeAgreementRepository (+2 more)

### Community 55 - "Test Deal Workflow & Deal"
Cohesion: 0.12
Nodes (5): DealWorkflow, DealWorkflowResult, DealWorkflowTests, DealWorkflowUnitTests, new_notification()

### Community 56 - "Agreementreview & Client"
Cohesion: 0.12
Nodes (29): acceptInvitation(), apiBaseUrl(), apiRequest(), commitAgreementVersion(), compareAgreementVersions(), createAgreementFromReviewedTerms(), getAgreementHistory(), getAgreementVersion() (+21 more)

### Community 57 - "Organizations & Test Organization Onboarding"
Cohesion: 0.18
Nodes (7): AcceptInvitationResponse, add_organization_member(), AddOrganizationMemberRequest, create_organization(), CreateOrganizationRequest, OrganizationDirectoryItem, OrganizationOnboardingTests

### Community 58 - "Test Workflow Activities & Activities"
Cohesion: 0.10
Nodes (8): RefreshDealStateActivity, _workflow_input_value(), DealWorkflowInput, new_workflow_input(), RefreshActivity, RefreshCall, RefreshDealStateActivityTests, factory()

### Community 59 - "Test Migration Lock & Env"
Cohesion: 0.10
Nodes (9): run_migrations_offline(), run_migrations_online(), serialize_migrations(), _make_postgres_connection(), _make_sqlite_connection(), MigrationLockTests, simulated_migration(), PostgresRealAdvisoryLockTests (+1 more)

### Community 60 - "Payment Processing & Test Payment"
Cohesion: 0.17
Nodes (4): PaymentInvoiceLineItem, SqlAlchemyPaymentProcessingRepository, transition(), transition()

### Community 61 - "01 Commercial Domain Model &"
Cohesion: 0.07
Nodes (19): AgreementVersion Aggregate, Append-Only AuditEvent Ledger, Commercial Constraint and Provenance, Deal Aggregate, Organization and Membership Entities, PaymentMilestone and Obligation, Proposal Aggregate and Terms Hash, Temporal Deal Workflow (+11 more)

### Community 65 - "Compose.Yaml (volumes)"
Cohesion: 0.09
Nodes (22): POSTGRES_DB, POSTGRES_PASSWORD, POSTGRES_USER, interval, retries, test, timeout, environment (+14 more)

### Community 66 - "Dev (DevResetResponse)"
Cohesion: 0.14
Nodes (8): DevResetResponse, DevRoleSwitchRequest, _require_demo_admin(), _require_dev_environment(), reset_demo(), simulate_payment(), SimulatePaymentRequest, switch_role()

### Community 67 - "Test Workflow Worker & Worker"
Cohesion: 0.11
Nodes (5): DealWorkflowStatus, create_worker(), workflow_activities(), WorkflowWorkerIntegrationTests, WorkflowWorkerTests

### Community 68 - "Organizations (datetime)"
Cohesion: 0.12
Nodes (7): _active_admin_membership(), _create_invitation_token(), _deal_awaiting_counterparty(), get_optional_actor(), get_organization_route(), list_my_organizations(), list_organization_directory()

### Community 71 - "Deals (CreateDealRequest)"
Cohesion: 0.13
Nodes (8): create_deal_route(), CreateDealRequest, DealResponse, DealSummaryResponse, list_deals_route(), read_deal_route(), _to_response(), _viewer_role()

### Community 72 - "Test Demo Lifecycle Lock &"
Cohesion: 0.20
Nodes (7): _acquire_lock(), _is_demo_deal(), lock_demo_deal_creation(), lock_demo_payment_processing(), lock_demo_reset(), DemoLifecycleLockTests, _postgres_session()

### Community 74 - "Createdealpage & Createdealpage.Test"
Cohesion: 0.16
Nodes (14): createCounterpartyInvitation(), createDeal(), CreateDealPage(), handleSubmit(), CreateDealPageProps, describeCreateError(), describeError(), DirectoryItem (+6 more)

### Community 75 - "Negotiation (BaseRequest)"
Cohesion: 0.18
Nodes (10): BaseRequest, CandidateRequest, EvidenceRequest, HistoryResponse, NegotiationRequest, NegotiationResponse, NegotiationResult, ProposalResponse (+2 more)

### Community 76 - "Test Organization Invitations & Organizations"
Cohesion: 0.19
Nodes (3): OnboardingConcurrencyCases, OnboardingPostgresConcurrencyTests, OnboardingSQLiteConcurrencyTests

### Community 77 - "Test Conversation Use Cases &"
Cohesion: 0.10
Nodes (6): AddMessageCommand, ConstraintRepository, review_constraint(), send(), ConversationUseCaseTests, write_message()

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

### Community 88 - "Human Bilateral Amendment Workflow"
Cohesion: 0.40
Nodes (3): Canonical Hash and Legacy Export Preservation, Human Bilateral Amendment Workflow, Cancellation and Dispute Case State Machine

### Community 89 - "Worker & Test Workflow Worker"
Cohesion: 0.27
Nodes (4): _register_shutdown_handlers(), _remove_shutdown_handlers(), _request_shutdown(), WorkerShutdownSignalTests

### Community 98 - "Master Execution Contract"
Cohesion: 0.14
Nodes (31): Execution Acceptance Gates, Master Execution Contract, Safe Windows PowerShell Runner, Private Contact Channels, Profiles Specification F14, Fresh Authorization Enforcement, Permissions Specification F15a, Append-Only Fulfillment Observations and Confirmations (+23 more)

### Community 99 - "0005 Conversation Party Unique (Enforce"
Cohesion: 0.36
Nodes (5): _create_party_unique_constraint(), _deduplicate_conversations(), downgrade(), _drop_party_unique_constraint(), upgrade()

### Community 101 - "Safe Operations and Recovery Guide"
Cohesion: 0.19
Nodes (15): PayPal Sandbox Invoicing and Reconciliation Flow, Backend README Document, F11a Explicit Payment Modes, F12 Committed Trade Packs, F1a Curated Repeatable Demo Fixture, F4 Invitations and Private Pending Deals, F5 Persisted Human Negotiation, F6 Agreement History and Comparison (+7 more)

### Community 111 - "0004 Communication Sources And Scope"
Cohesion: 0.60
Nodes (4): _create_scope_index(), downgrade(), _drop_scope_index(), upgrade()

### Community 119 - "Final Gates and Truthful Completion Specification"
Cohesion: 0.20
Nodes (9): Evidence-Free Projection and Safety Bounds, F12 Trade Pack Handoff Document, Trade Pack Export Contract, Browser Verification Specification, ZIP HTML and Print Export Verification, Two-Party Isolated Browser Testing, Final Gates and Truthful Completion Specification, Full Gate Verification Suite (+1 more)

### Community 120 - "Skill (Repo Idea Thinker Skill)"
Cohesion: 0.50
Nodes (3): Repo Idea Thinker Skill, Repository-Grounded Ideation Discipline, Idea Quality Standards and Lightweight Validation

### Community 139 - "NegotiationPostgresRaceTests"
Cohesion: 0.22
Nodes (4): NegotiationPostgresRaceTests, run(), failing(), succeed()

### Community 141 - "OutboxEvent"
Cohesion: 0.18
Nodes (3): OutboxEvent, start_deal_workflow(), dispatch()

### Community 142 - "write_negotiation"
Cohesion: 0.27
Nodes (3): _raise_error(), read_negotiation(), write_negotiation()

### Community 143 - "NegotiationCommand"
Cohesion: 0.31
Nodes (4): EvidenceReference, negotiate(), NegotiationCommand, NegotiationRepository

### Community 146 - "_is_one_active_per_milestone_violation"
Cohesion: 0.43
Nodes (3): _is_idempotency_key_violation(), _is_one_active_per_milestone_violation(), _violated_constraint_name()

### Community 147 - "AI Provider Boundary Specification"
Cohesion: 0.53
Nodes (4): F2 AI Configuration and Provider Boundary, AI Provider Boundary Specification, AI Resilience and Retry Policy, AISuggestionProvider Contract

## Knowledge Gaps
- **47 isolated node(s):** `syncally`, `Deterministic Version-Aware Export Downloads`, `Execution Acceptance Gates`, `Safe Windows PowerShell Runner`, `Authoring Integrity and Hash Preservation Proof` (+42 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1217 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **64 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ActorContext` connect `Test Deal Routes & Identity` to `Conversations & Test Conversation Use`, `Deals & Identity`, `Payments & Intent`, `Test Ai Provider & Ai`, `Test Communication Repositories & Conversations`, `Seed Demo & Deals`, `Agreements & Obligations`, `Test Conversation Routes (ConversationRouteTests)`, `Test Agreement Routes (AgreementRouteTests)`, `Auth & Test Identity Boundary`, `write_negotiation`, `Agreements & Agreement`, `Documents & Test Commercial Documents`, `Simulate Deal Flow & Test`, `Test Organization Invitations & Organizations`, `Ai & Contracts`, `Test Payment Intent Repository &`, `Deals & Test Deal Use`, `Test Demo Lifecycle & Test`, `OrganizationInvitationTests`, `Test Organization Directory & Organizations`, `Organizations & Test Organization Onboarding`, `Test Payment Processing & Test`, `Test Identity Boundary & Config`, `Dev (DevResetResponse)`, `Organizations (datetime)`, `Deals (CreateDealRequest)`, `Negotiation (BaseRequest)`, `Test Organization Invitations & Organizations`, `Test Conversation Use Cases &`, `Test Communication Repositories (MessageIdempotencyPostgresTests)`, `Test Ai Context & Conversations`, `Test Negotiation (NegotiationRouteTests)`?**
  _High betweenness centrality (0.112) - this node is a cross-community bridge._
- **Are the 97 inferred relationships involving `ActorContext` (e.g. with `approve_agreement_route()` and `commit_agreement_route()`) actually correct?**
  _`ActorContext` has 97 INFERRED edges - model-reasoned connections that need verification._
- **What connects `syncally`, `Deterministic Version-Aware Export Downloads`, `Execution Acceptance Gates` to the rest of the system?**
  _47 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Conversations & Test Conversation Use` be split into smaller, more focused modules?**
  _Cohesion score 0.045112781954887216 - nodes in this community are weakly interconnected._
- **Why does `OrganizationId` connect `Test Communication Repositories & Conversations` to `Conversations & Test Conversation Use`, `contracts.py`, `Deals & Identity`, `Payments & Intent`, `Test Ai Provider & Ai`, `Seed Demo & Deals`, `Agreements & Obligations`, `Test Conversation Routes (ConversationRouteTests)`, `Test Organization Domain & Trade`, `Test Agreement Routes (AgreementRouteTests)`, `DealDomainTests`, `write_negotiation`, `Agreements & Agreement`, `NegotiationTests`, `Auth & Test Identity Boundary`, `ProposedTerms`, `Proposal & Intent`, `Documents & Test Commercial Documents`, `Test Outbox Dispatcher & Outbox`, `Communications & Conversations`, `Ai & Contracts`, `Agreements & Counterparty Onboarding`, `Test Agreements & Test Local`, `Organizations & Organization`, `Test Payment Intent Repository &`, `Deals & Test Deal Use`, `Test Demo Lifecycle & Test`, `OrganizationInvitationTests`, `Negotiation & Proposal`, `Deal & Test Deal Authorization`, `Workflow State & Test Workflow`, `Test Payment Processing & Test`, `Test Deal Repository & Deals`, `Negotiation (BaseRequest)`, `Test Conversation Use Cases &`, `Test Counterparty Onboarding Migration &`, `Test Ai Context & Conversations`, `Deals`, `Test Negotiation Migration (NegotiationMigrationTests)`?**
  _High betweenness centrality (0.053) - this node is a cross-community bridge._
- **Are the 53 inferred relationships involving `OrganizationId` (e.g. with `create_reviewed_agreement_draft_route()` and `write_negotiation()`) actually correct?**
  _`OrganizationId` has 53 INFERRED edges - model-reasoned connections that need verification._
- **Should `contracts.py` be split into smaller, more focused modules?**
  _Cohesion score 0.08514013749338974 - nodes in this community are weakly interconnected._