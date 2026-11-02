# Graph Report - SyncAlly  (2026-11-02)

## Corpus Check
- 279 files · ~236,617 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 8 file(s) not represented in the graph (top: (none) 4, .example 1, .ini 1)

## Summary
- 4249 nodes · 13795 edges · 154 communities (96 shown, 58 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 1817 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `ffebaefc`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Conversations & Test Conversation Use
- AIContractError
- identifiers.py
- api/payments.py
- Test Ai Provider & Ai
- DealId
- Seed Demo & Deals
- PaymentNeedsAction
- test_outbox_dispatcher.py
- SqlAlchemyAgreementRepository
- Test Conversation Routes (ConversationRouteTests)
- Test Agreement Routes (AgreementRouteTests)
- get_current_actor
- process_payment_intent
- ai.py
- NegotiationTests
- Types & Client
- App.test.tsx
- Money
- application/documents.py
- Test Outbox Dispatcher & Outbox
- Simulate Deal Flow & Test
- Test Organization Invitations & Organizations
- SqlAlchemyCommunicationRepository
- Package & Vite.Config
- client.test.ts
- Dealconversationreview & Dealconversationreview.Test
- Skill & Skill.Md
- sqlalchemy
- User
- DealDetailPage.test.tsx
- api/agreements.py
- Aisuggestionreview & Suggestionpreview
- SyncAlly Implementation Plan Document
- PaymentProcessingTests
- AgreementCommitTests
- infrastructure/outbox.py
- InvariantViolation
- Paymentstatuspanel & Paymentstatuspanel.Test
- Test Payment Intent Repository &
- database_health
- AISuggestionProviderTests
- DemoSeedTests
- PaymentInvoiceReconciliation
- Test Dev Routes (DevRoutesTests)
- SqlAlchemyDealRepository
- DealWorkflow
- Test Organization Directory & Organizations
- Negotiation & Proposal
- DealWorkflowNotification
- Deal
- Test Payment Outbox & Test
- react
- load_deal_workflow_state
- canonical_decimal
- Agreementreview & Client
- Organizations & Test Organization Onboarding
- Test Workflow Activities & Activities
- Test Migration Lock & Env
- Payment Processing & Test Payment
- 01 Commercial Domain Model &
- ProposedTerms
- Test Deal Routes & Identity
- Test Identity Boundary & Config
- Compose.Yaml (volumes)
- InvalidTransition
- worker.py
- api/organizations.py
- ExtractedFact
- Test Payment Reconciliation & Intent
- TradeTermsTests
- PersistentDemoSeedTests
- AgreementVersionId
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
- contracts.py
- Test Ai Context & Conversations
- Main & Test Identity Boundary
- demo_lifecycle.py
- Human Bilateral Amendment Workflow
- App.tsx
- Test Organization Index Migration (OrganizationIndexPostgresMigrationTests)
- Server-Enforced Capability Matrix
- PaymentNeedsAction
- Test Negotiation (NegotiationRouteTests)
- Constraint
- AIConfigurationError
- _to_domain
- Test Database (DatabasePersistenceTests)
- Master Execution Contract
- 0005 Conversation Party Unique (Enforce
- Main (Request)
- Safe Operations and Recovery Guide
- env.py
- openai.py
- Test Negotiation Migration (NegotiationMigrationTests)
- Test Payment Mode Migration (PaymentModeMigrationTests)
- .refresh_deal_state
- Test Communication Migration (ConversationPartyUniquenessMigrationTests)
- _domain_deal
- ConversationContractTests
- DomainError
- build_terms
- Test Provider Invoice Unique Migration
- DealParticipation
- NegotiationPostgresRaceTests
- Final Gates and Truthful Completion Specification
- Skill (Repo Idea Thinker Skill)
- login
- Vite Env.D (ImportMeta)
- simulate_payment
- FakeDealRepository
- Index (Frontend HTML Root Document)
- Pyproject (syncally)
- auth.py
- InvariantViolation
- SafeOperationalFormatter
- NegotiationCommand
- Visibility
- field_validator
- AI Provider Boundary Specification
- Four-Dimension Profile Collections
- Two-Party Judge Journey
- .__call__
- MigrationConfigTests
- .test_refresh_rotates_token_and_revokes_previous_token
- 0004_communication_sources_and_scope_indexes.py
- _is_duplicate_membership_error

## God Nodes (most connected - your core abstractions)
1. `ActorContext` - 239 edges
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

## Communities (154 total, 58 thin omitted)

### Community 0 - "Conversations & Test Conversation Use"
Cohesion: 0.06
Nodes (51): add_message_route(), AISuggestionRequest, clarify_fact_route(), confirm_fact_route(), ConstraintResponse, correct_fact_route(), CorrectFactRequest, create_fact_route() (+43 more)

### Community 1 - "AIContractError"
Cohesion: 0.13
Nodes (12): AIContractError, AIValidationClaim, _check_keys(), _decimal(), _required_string(), scope_extracted_facts(), _validate_decimal(), _validate_fact_value() (+4 more)

### Community 3 - "api/payments.py"
Cohesion: 0.04
Nodes (30): create_deal_route(), CreateDealRequest, DealResponse, DealSummaryResponse, get_deal_repository(), list_deals_route(), read_deal_route(), _to_response() (+22 more)

### Community 4 - "Test Ai Provider & Ai"
Cohesion: 0.11
Nodes (12): extract_facts_from_context(), ConfiguredAIProvider, respond(), respond(), respond(), respond(), respond(), respond() (+4 more)

### Community 5 - "DealId"
Cohesion: 0.08
Nodes (15): create_manual_constraint(), ConstraintId, ConversationId, DealId, MessageId, OrganizationId, UserId, constraint() (+7 more)

### Community 6 - "Seed Demo & Deals"
Cohesion: 0.07
Nodes (35): _require_dev_environment(), _accept_invitation(), _decode_invitation_token(), _clear_fixture(), _create_fixture(), _delete_scoped(), DemoCollisionError, DemoIdentity (+27 more)

### Community 7 - "PaymentNeedsAction"
Cohesion: 0.08
Nodes (12): receive_paypal_invoice_webhook(), payment_invoice_number(), PaymentNeedsAction, PaymentOutcomeUnknown, PaymentRetryableError, _has_excess_currency_precision(), PayPalSandboxInvoiceProvider, _provider_error_code() (+4 more)

### Community 8 - "test_outbox_dispatcher.py"
Cohesion: 0.07
Nodes (4): NotificationKind, _is_live_backend_healthy(), main(), OutboxDispatchMigrationTests

### Community 9 - "SqlAlchemyAgreementRepository"
Cohesion: 0.10
Nodes (14): AgreementNotFound, AgreementVersionConflict, UnauthorizedApproval, DealStatus, ProposalStatus, AgreementVersionId, ProposalId, is_pending() (+6 more)

### Community 10 - "Test Conversation Routes (ConversationRouteTests)"
Cohesion: 0.10
Nodes (3): ConversationRouteTests, respond(), send()

### Community 13 - "get_current_actor"
Cohesion: 0.10
Nodes (13): create_refresh_token(), _decode_token(), _development_actor(), development_login(), _encode_access_token(), get_current_actor(), _issue_tokens(), _replay_rotation() (+5 more)

### Community 14 - "process_payment_intent"
Cohesion: 0.10
Nodes (8): PaymentInvoiceNotifier, PaymentInvoiceProvider, PaymentProcessingRepository, process_payment_intent(), reconcile_payment_intent(), _request_id_retry_window_expired(), require_payment_provider(), _process_claimed_payment_event()

### Community 15 - "ai.py"
Cohesion: 0.08
Nodes (18): get_ai_suggestion_provider(), AIProvenance, AIRetryPolicy, AISuggestionProvider, call_with_bounded_retry(), draft_proposal(), draft_proposal_from_context(), extract_facts() (+10 more)

### Community 16 - "NegotiationTests"
Cohesion: 0.21
Nodes (3): EvidenceReference, negotiate_in_transaction(), NegotiationTests

### Community 17 - "Types & Client"
Cohesion: 0.07
Nodes (47): describeDetail(), getDealMessageExistence(), isAbortError(), isRecord(), readErrorDetail(), AgreementApproval, AgreementComparison, AgreementEvidence (+39 more)

### Community 18 - "App.test.tsx"
Cohesion: 0.09
Nodes (31): listOrganizations(), clearAccessToken(), getAccessToken(), setTokens(), TokenResponse, mockedApiRequest, mockedCreateOrganization, mockedGetCommercialDocumentDraft (+23 more)

### Community 19 - "Money"
Cohesion: 0.14
Nodes (13): PaymentInvoiceReconciliation, _money(), _parse_money(), PaymentMilestone, VerifiedProviderPaymentState, PaymentIntentId, PaymentMilestoneId, Money (+5 more)

### Community 20 - "application/documents.py"
Cohesion: 0.08
Nodes (18): CommercialDocumentDraftResponse, get_commercial_document_draft_route(), get_trade_pack_route(), AgreementNotCommitted, CommercialDocumentDraft, _display(), export_display_terms(), generate_commercial_document_draft() (+10 more)

### Community 21 - "Test Outbox Dispatcher & Outbox"
Cohesion: 0.09
Nodes (13): build_deal_workflow_id(), dispatch_outbox_event(), OutboxDispatchResult, PendingOutboxEvent, WorkflowStartTransientError, apply_dispatch_result(), claim_next_pending_event(), _claim_statement() (+5 more)

### Community 22 - "Simulate Deal Flow & Test"
Cohesion: 0.07
Nodes (11): _build_in_process_client(), dispatch_payment(), session_factory(), ci_deal_flow_hook(), DealFlowContext, DealFlowSimulator, run_simulation(), SimulationError (+3 more)

### Community 23 - "Test Organization Invitations & Organizations"
Cohesion: 0.16
Nodes (5): accept_invitation(), AcceptInvitationRequest, create_organization_invitation(), CreateInvitationRequest, OrganizationInvitationTests

### Community 24 - "SqlAlchemyCommunicationRepository"
Cohesion: 0.07
Nodes (11): can_view_message(), message_fingerprint(), Conversation, Message, CommunicationScopeError, _constraint_to_domain(), _conversation_to_domain(), _is_unique_violation() (+3 more)

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
Cohesion: 0.04
Nodes (27): upgrade(), uuid_column(), upgrade(), upgrade(), upgrade(), upgrade(), downgrade(), upgrade() (+19 more)

### Community 30 - "User"
Cohesion: 0.13
Nodes (3): update_member_permissions(), UpdateMemberPermissionsRequest, OrganizationPermissionsTests

### Community 31 - "DealDetailPage.test.tsx"
Cohesion: 0.07
Nodes (37): getCommercialDocumentDraft(), getDeal(), getNegotiation(), negotiateDeal(), Deal, NegotiationView, createReviewedAgreement(), DealConstellation() (+29 more)

### Community 32 - "api/agreements.py"
Cohesion: 0.04
Nodes (53): AgreementVersionResponse, ApprovalResponse, approve_agreement_route(), commit_agreement_route(), CommitAgreementRequest, compare_agreements_route(), create_agreement_draft_route(), create_reviewed_agreement_draft_route() (+45 more)

### Community 33 - "Aisuggestionreview & Suggestionpreview"
Cohesion: 0.09
Nodes (35): correctDealFact(), createDealFact(), draftDealProposal(), suggestDealFacts(), AIProvenance, DealFact, FactReviewAction, isPaymentTrigger() (+27 more)

### Community 34 - "SyncAlly Implementation Plan Document"
Cohesion: 0.16
Nodes (13): SyncAlly Architecture Document, System Topology and Ownership Boundaries, Temporal Worker and Outbox Architecture, Acceptance Criteria Verification Matrix, SyncAlly Implementation Plan Document, Issue #77 Architecture Contracts, Stage Lifecycle Roadmap, Frontend API Client and Authoritative State (+5 more)

### Community 35 - "PaymentProcessingTests"
Cohesion: 0.13
Nodes (5): FakeInvoiceProvider, FakeProcessingRepository, PaymentProcessingTests, _request(), _work_item()

### Community 36 - "AgreementCommitTests"
Cohesion: 0.06
Nodes (12): CommitAgreementCommand, compare_agreement_terms(), RecordApprovalCommand, commit_agreement_in_transaction(), record_approval_in_transaction(), SqlAlchemyAuditRepository, SqlAlchemyObligationRepository, SqlAlchemyPaymentMilestoneRepository (+4 more)

### Community 37 - "infrastructure/outbox.py"
Cohesion: 0.13
Nodes (15): _connect_with_retry(), main(), run_forever(), main(), run_forever(), dispatch_pending_outbox_events(), is_permanent_rpc_error(), configure_logging() (+7 more)

### Community 38 - "InvariantViolation"
Cohesion: 0.07
Nodes (22): _compute_effective_capabilities(), ContactVisibility, _normalize_string(), Organization, OrganizationCapability, OrganizationContact, OrganizationMember, OrganizationMemberRole (+14 more)

### Community 39 - "Paymentstatuspanel & Paymentstatuspanel.Test"
Cohesion: 0.10
Nodes (30): authorizeDealPayment(), getOrganization(), listPaymentStatuses(), previewDealPayment(), PaymentIntentStatus, describeStatus(), displayAmount(), extractInvoiceNumber() (+22 more)

### Community 40 - "Test Payment Intent Repository &"
Cohesion: 0.12
Nodes (4): queue_simulated_reconciliation(), require_simulation_scope(), authorize_payment_intent_in_transaction(), PaymentIntentRepositoryTests

### Community 42 - "AISuggestionProviderTests"
Cohesion: 0.15
Nodes (3): DeterministicFakeAIProvider, AISuggestionProviderTests, extract_facts()

### Community 47 - "DealWorkflow"
Cohesion: 0.13
Nodes (5): DealWorkflow, DealWorkflowResult, DealWorkflowTests, DealWorkflowUnitTests, new_notification()

### Community 49 - "Negotiation & Proposal"
Cohesion: 0.17
Nodes (5): NegotiationConflict, NegotiationNotFound, NegotiationOrganizationRequired, SqlAlchemyNegotiationRepository, projection()

### Community 50 - "DealWorkflowNotification"
Cohesion: 0.11
Nodes (7): DealWorkflowStarter, WorkflowStartError, WorkflowStartOutcome, WorkflowStartPermanentError, DealWorkflowNotification, TemporalDealWorkflowStarter, TemporalAdapterTests

### Community 52 - "Test Payment Outbox & Test"
Cohesion: 0.09
Nodes (11): claim_next_payment_event(), _claim_statement(), _ClaimedPaymentEvent, dispatch_one_payment_event(), dispatch_pending_payment_events(), _finish_event(), FakeRepository, NoCallProvider (+3 more)

### Community 53 - "react"
Cohesion: 0.06
Nodes (32): addOrganizationMember(), createOrganization(), getOrganizationProfile(), updateOrganizationProfile(), ContactVisibility, Organization, OrganizationContact, COUNTRY_NAMES (+24 more)

### Community 54 - "load_deal_workflow_state"
Cohesion: 0.14
Nodes (6): DealWorkflowState, load_deal_workflow_state(), parse_workflow_uuid(), WorkflowAgreementRepository, WorkflowDealNotFound, WorkflowDealRepository

### Community 55 - "canonical_decimal"
Cohesion: 0.08
Nodes (4): PaymentInvoiceNotice, canonical_decimal(), _FakeSMTP, GmailSMTPInvoiceNotifierTests

### Community 56 - "Agreementreview & Client"
Cohesion: 0.08
Nodes (38): ApiError, commitAgreementVersion(), compareAgreementVersions(), getAgreementHistory(), getAgreementVersion(), getCurrentAgreement(), getTradePack(), recordAgreementDecision() (+30 more)

### Community 57 - "Organizations & Test Organization Onboarding"
Cohesion: 0.13
Nodes (12): AcceptInvitationResponse, add_organization_member(), AddOrganizationMemberRequest, ContactResponse, CounterpartyInvitationResponse, create_organization(), CreateOrganizationRequest, InvitationResponse (+4 more)

### Community 58 - "Test Workflow Activities & Activities"
Cohesion: 0.08
Nodes (10): RefreshDealStateActivity, DealWorkflowInput, DealWorkflowStatus, _require_uuid(), new_workflow_input(), RefreshActivity, RefreshCall, RefreshDealStateActivityTests (+2 more)

### Community 59 - "Test Migration Lock & Env"
Cohesion: 0.12
Nodes (8): run_migrations_online(), serialize_migrations(), _make_postgres_connection(), _make_sqlite_connection(), MigrationLockTests, simulated_migration(), PostgresRealAdvisoryLockTests, worker()

### Community 60 - "Payment Processing & Test Payment"
Cohesion: 0.15
Nodes (6): PaymentInvoiceLineItem, PaymentIntentStatus, _restore_domain_intent(), SqlAlchemyPaymentProcessingRepository, transition(), transition()

### Community 61 - "01 Commercial Domain Model &"
Cohesion: 0.07
Nodes (19): AgreementVersion Aggregate, Append-Only AuditEvent Ledger, Commercial Constraint and Provenance, Deal Aggregate, Organization and Membership Entities, PaymentMilestone and Obligation, Proposal Aggregate and Terms Hash, Temporal Deal Workflow (+11 more)

### Community 62 - "ProposedTerms"
Cohesion: 0.12
Nodes (4): FactExtractionRequest, ProposalDraftRequest, ProposedTerms, FakeWebhookVerifier

### Community 64 - "Test Identity Boundary & Config"
Cohesion: 0.15
Nodes (3): _is_weak_jwt_secret(), Settings, IdentityBoundaryTests

### Community 65 - "Compose.Yaml (volumes)"
Cohesion: 0.09
Nodes (22): POSTGRES_DB, POSTGRES_PASSWORD, POSTGRES_USER, interval, retries, test, timeout, environment (+14 more)

### Community 66 - "InvalidTransition"
Cohesion: 0.11
Nodes (4): PaymentStatusResponse, PaymentIntent, InvalidTransition, PaymentStatusExtendedModelTests

### Community 67 - "worker.py"
Cohesion: 0.11
Nodes (7): create_worker(), _register_shutdown_handlers(), _remove_shutdown_handlers(), _request_shutdown(), workflow_activities(), WorkerShutdownSignalTests, WorkflowWorkerTests

### Community 68 - "api/organizations.py"
Cohesion: 0.08
Nodes (14): _active_admin_membership(), _case_insensitive_prefix(), _create_invitation_token(), _deal_awaiting_counterparty(), _escape_like(), get_optional_actor(), get_organization_profile_route(), get_organization_route() (+6 more)

### Community 69 - "ExtractedFact"
Cohesion: 0.17
Nodes (6): ExtractedFact, FactField, SourceReference, DemoAISuggestionProvider, _is_ambiguous_numeric_term(), _is_delivery_date_context()

### Community 71 - "TradeTermsTests"
Cohesion: 0.10
Nodes (12): _decimal(), PaymentTerm, ShipmentTerm, TradeLineItem, TradeTerms, AgreementId, value(), with_timing() (+4 more)

### Community 72 - "PersistentDemoSeedTests"
Cohesion: 0.10
Nodes (7): fixture_id(), initialize_offline_database(), main(), OutboxEvent, PersistentDemoSeedTests, start_deal_workflow(), dispatch()

### Community 74 - "Createdealpage & Createdealpage.Test"
Cohesion: 0.08
Nodes (25): createCounterpartyInvitation(), createDeal(), listDeals(), ViewerRole, CreateDealPage(), handleSubmit(), CreateDealPageProps, describeCreateError() (+17 more)

### Community 75 - "Negotiation (BaseRequest)"
Cohesion: 0.13
Nodes (12): BaseRequest, CandidateRequest, EvidenceRequest, HistoryResponse, NegotiationRequest, NegotiationResponse, NegotiationResult, ProposalResponse (+4 more)

### Community 76 - "Test Organization Invitations & Organizations"
Cohesion: 0.16
Nodes (5): create_counterparty_invitation(), CreateCounterpartyInvitationRequest, OnboardingConcurrencyCases, OnboardingPostgresConcurrencyTests, OnboardingSQLiteConcurrencyTests

### Community 77 - "application/conversations.py"
Cohesion: 0.07
Nodes (15): add_message(), AddMessageCommand, can_view_constraint(), ConstraintRepository, import_thread(), list_visible_messages(), preview_thread_import(), review_constraint() (+7 more)

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

### Community 84 - "contracts.py"
Cohesion: 0.37
Nodes (8): _contains_numeric_token(), _contains_token(), _date_value_is_present(), _fact_value_is_supported_by_quote(), _flexible_whitespace_pattern(), _number_with_currency_is_present(), _number_with_unit_is_present(), _numeric_pattern()

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
Cohesion: 0.10
Nodes (10): get_paypal_webhook_configuration(), PaymentInvoiceLookup, PaymentInvoiceRequest, PaymentWorkItem, main(), GmailSettings, PayPalSettings, GmailSMTPInvoiceNotifier (+2 more)

### Community 94 - "Constraint"
Cohesion: 0.07
Nodes (4): Constraint, FakeCommunicationRepository, FakeCommunicationRepository, FakeCommunicationRepository

### Community 98 - "Master Execution Contract"
Cohesion: 0.14
Nodes (31): Execution Acceptance Gates, Master Execution Contract, Safe Windows PowerShell Runner, Private Contact Channels, Profiles Specification F14, Fresh Authorization Enforcement, Permissions Specification F15a, Append-Only Fulfillment Observations and Confirmations (+23 more)

### Community 99 - "0005 Conversation Party Unique (Enforce"
Cohesion: 0.36
Nodes (5): _create_party_unique_constraint(), _deduplicate_conversations(), downgrade(), _drop_party_unique_constraint(), upgrade()

### Community 101 - "Safe Operations and Recovery Guide"
Cohesion: 0.19
Nodes (15): PayPal Sandbox Invoicing and Reconciliation Flow, Backend README Document, F11a Explicit Payment Modes, F12 Committed Trade Packs, F1a Curated Repeatable Demo Fixture, F4 Invitations and Private Pending Deals, F5 Persisted Human Negotiation, F6 Agreement History and Comparison (+7 more)

### Community 104 - "openai.py"
Cohesion: 0.13
Nodes (13): AIPermanentError, AITransientError, parse_extracted_facts(), parse_proposed_terms(), AiContext, _json(), _object(), OpenAIChatCompletions (+5 more)

### Community 110 - "_domain_deal"
Cohesion: 0.36
Nodes (4): _domain_deal(), _FakeAgreementRepository, _FakeDealRepository, WorkflowStateApplicationTests

### Community 111 - "ConversationContractTests"
Cohesion: 0.13
Nodes (3): confirm_constraint(), ConversationContractTests, FakeConstraintRepository

### Community 113 - "DomainError"
Cohesion: 0.05
Nodes (26): get_payment_status_repository(), OutboxEventDraft, authorize_payment_intent(), AuthorizePaymentIntentCommand, DuplicateActivePaymentIntent, IdempotencyKeyReused, list_current_payment_statuses(), PaymentIntentAuthorizationOutcome (+18 more)

### Community 114 - "build_terms"
Cohesion: 0.17
Nodes (7): NegotiationSession, NegotiationSubmissionOutcome, Proposal, NegotiationSessionId, build_proposal(), HumanNegotiationTests, NegotiationTests

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
Cohesion: 0.27
Nodes (5): CredentialsRequest, login(), TokenResponse, fail(), scalar()

### Community 134 - "simulate_payment"
Cohesion: 0.19
Nodes (6): DevResetResponse, DevRoleSwitchRequest, reset_demo(), simulate_payment(), SimulatePaymentRequest, switch_role()

### Community 139 - "auth.py"
Cohesion: 0.06
Nodes (6): OperationalFastAPI, _persist_paypal_webhook_event(), hash_password(), verify_password(), record_paypal_webhook_event(), HealthRouteTests

### Community 140 - "InvariantViolation"
Cohesion: 0.13
Nodes (3): _normalized_text(), _require_decimal(), InvariantViolation

### Community 143 - "NegotiationCommand"
Cohesion: 0.42
Nodes (3): negotiate(), NegotiationCommand, NegotiationRepository

### Community 144 - "Visibility"
Cohesion: 0.10
Nodes (9): AddMessageRequest, CreateFactRequest, CreateManualConstraintCommand, ScopedFactCandidate, ConstraintKind, ConstraintStatus, MessageSourceType, Visibility (+1 more)

### Community 147 - "AI Provider Boundary Specification"
Cohesion: 0.53
Nodes (4): F2 AI Configuration and Provider Boundary, AI Provider Boundary Specification, AI Resilience and Retry Policy, AISuggestionProvider Contract

### Community 160 - ".test_refresh_rotates_token_and_revokes_previous_token"
Cohesion: 0.12
Nodes (5): _as_utc(), _hash_refresh_token(), refresh_access_token(), RefreshRequest, RefreshToken

### Community 162 - "0004_communication_sources_and_scope_indexes.py"
Cohesion: 0.60
Nodes (4): _create_scope_index(), downgrade(), _drop_scope_index(), upgrade()

## Knowledge Gaps
- **47 isolated node(s):** `syncally`, `F1a Curated Repeatable Demo Fixture`, `Editorial Dark Theme Design System`, `ZIP HTML and Print Export Verification`, `Whole-Worktree Independent Review` (+42 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1262 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **58 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ActorContext` connect `Test Deal Routes & Identity` to `Conversations & Test Conversation Use`, `identifiers.py`, `api/payments.py`, `DealId`, `Seed Demo & Deals`, `simulate_payment`, `FakeDealRepository`, `Test Conversation Routes (ConversationRouteTests)`, `auth.py`, `Test Agreement Routes (AgreementRouteTests)`, `get_current_actor`, `ai.py`, `application/documents.py`, `Simulate Deal Flow & Test`, `Test Organization Invitations & Organizations`, `SqlAlchemyCommunicationRepository`, `User`, `api/agreements.py`, `InvariantViolation`, `Test Payment Intent Repository &`, `AISuggestionProviderTests`, `Test Organization Directory & Organizations`, `Organizations & Test Organization Onboarding`, `ProposedTerms`, `Test Identity Boundary & Config`, `InvalidTransition`, `api/organizations.py`, `Negotiation (BaseRequest)`, `Test Organization Invitations & Organizations`, `application/conversations.py`, `Test Communication Repositories (MessageIdempotencyPostgresTests)`, `Test Ai Context & Conversations`, `Test Negotiation (NegotiationRouteTests)`, `ConversationContractTests`, `DomainError`?**
  _High betweenness centrality (0.119) - this node is a cross-community bridge._
- **Are the 106 inferred relationships involving `ActorContext` (e.g. with `approve_agreement_route()` and `commit_agreement_route()`) actually correct?**
  _`ActorContext` has 106 INFERRED edges - model-reasoned connections that need verification._
- **What connects `syncally`, `F1a Curated Repeatable Demo Fixture`, `Editorial Dark Theme Design System` to the rest of the system?**
  _47 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Conversations & Test Conversation Use` be split into smaller, more focused modules?**
  _Cohesion score 0.05539691604797259 - nodes in this community are weakly interconnected._
- **Why does `OrganizationId` connect `DealId` to `Conversations & Test Conversation Use`, `AIContractError`, `identifiers.py`, `api/payments.py`, `Seed Demo & Deals`, `SqlAlchemyAgreementRepository`, `Test Conversation Routes (ConversationRouteTests)`, `Test Agreement Routes (AgreementRouteTests)`, `ai.py`, `Visibility`, `NegotiationTests`, `Money`, `application/documents.py`, `Test Outbox Dispatcher & Outbox`, `SqlAlchemyCommunicationRepository`, `User`, `api/agreements.py`, `AgreementCommitTests`, `InvariantViolation`, `Test Payment Intent Repository &`, `AISuggestionProviderTests`, `SqlAlchemyDealRepository`, `Negotiation & Proposal`, `Deal`, `Payment Processing & Test Payment`, `ProposedTerms`, `InvalidTransition`, `api/organizations.py`, `TradeTermsTests`, `AgreementVersionId`, `Negotiation (BaseRequest)`, `Test Organization Invitations & Organizations`, `application/conversations.py`, `Test Counterparty Onboarding Migration &`, `contracts.py`, `Test Ai Context & Conversations`, `Constraint`, `_to_domain`, `Test Negotiation Migration (NegotiationMigrationTests)`, `_domain_deal`, `ConversationContractTests`, `DomainError`, `build_terms`?**
  _High betweenness centrality (0.087) - this node is a cross-community bridge._
- **Are the 57 inferred relationships involving `OrganizationId` (e.g. with `create_reviewed_agreement_draft_route()` and `write_negotiation()`) actually correct?**
  _`OrganizationId` has 57 INFERRED edges - model-reasoned connections that need verification._
- **Should `AIContractError` be split into smaller, more focused modules?**
  _Cohesion score 0.13205128205128205 - nodes in this community are weakly interconnected._