# Graph Report - SyncAlly  (2026-11-02)

## Corpus Check
- 279 files · ~236,766 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 8 file(s) not represented in the graph (top: (none) 4, .example 1, .ini 1)

## Summary
- 4261 nodes · 13711 edges · 177 communities (96 shown, 81 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 1772 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `20dce79b`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Conversations & Test Conversation Use
- AIContractError
- DomainDependencyTests
- api/payments.py
- Test Ai Provider & Ai
- DealId
- Seed Demo & Deals
- PaymentNeedsAction
- NotificationKind
- api/agreements.py
- Test Conversation Routes (ConversationRouteTests)
- create_deal
- Test Agreement Routes (AgreementRouteTests)
- get_current_actor
- process_payment_intent
- ai.py
- NegotiationTests
- Types & Client
- listOrganizations
- Money
- CommercialDocumentDraftTests
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
- App.test.tsx
- repositories/agreements.py
- Aisuggestionreview & Suggestionpreview
- SyncAlly Implementation Plan Document
- PaymentProcessingTests
- AgreementCommitTests
- worker.py
- InvariantViolation
- Paymentstatuspanel & Paymentstatuspanel.Test
- Test Payment Intent Repository &
- database_health
- AISuggestionProviderTests
- seed_demo.py
- DealWorkflow
- Test Dev Routes (DevRoutesTests)
- SqlAlchemyDealRepository
- DealWorkflow
- Test Organization Directory & Organizations
- repositories/negotiation.py
- DealWorkflowNotification
- Deal
- Test Payment Outbox & Test
- Organization
- load_deal_workflow_state
- canonical_decimal
- Agreementreview & Client
- Organizations & Test Organization Onboarding
- Test Workflow Activities & Activities
- Test Migration Lock & Env
- Payment Processing & Test Payment
- 01 Commercial Domain Model &
- ._offline_intent
- Test Deal Routes & Identity
- Test Identity Boundary & Config
- Compose.Yaml (volumes)
- InvalidTransition
- AddMessageRequest
- api/organizations.py
- ExtractedFact
- Test Payment Reconciliation & Intent
- build_terms
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
- authorize_payment_intent
- Test Ai Context & Conversations
- Main & Test Identity Boundary
- demo_lifecycle.py
- Human Bilateral Amendment Workflow
- react
- Test Organization Index Migration (OrganizationIndexPostgresMigrationTests)
- Server-Enforced Capability Matrix
- InvalidTransition
- Test Negotiation (NegotiationRouteTests)
- Constraint
- create_deal_route
- _to_domain
- Test Database (DatabasePersistenceTests)
- Master Execution Contract
- 0005 Conversation Party Unique (Enforce
- Main (Request)
- Safe Operations and Recovery Guide
- LocalWorkflowSmokeTests
- openai.py
- Test Negotiation Migration (NegotiationMigrationTests)
- Test Payment Mode Migration (PaymentModeMigrationTests)
- .refresh_deal_state
- Test Communication Migration (ConversationPartyUniquenessMigrationTests)
- ConversationContractTests
- .add
- build_terms
- .test_storage_dict_round_trip_preserves_destination_case
- .can_access_deal
- NegotiationPostgresRaceTests
- Final Gates and Truthful Completion Specification
- Skill (Repo Idea Thinker Skill)
- login
- Vite Env.D (ImportMeta)
- simulate_payment
- FakeDealRepository
- Index (Frontend HTML Root Document)
- Pyproject (syncally)
- passwords.py
- InvariantViolation
- 0001_initial_schema.py
- NegotiationCommand
- application/conversations.py
- field_validator
- AI Provider Boundary Specification
- dependencies
- Four-Dimension Profile Collections
- Two-Party Judge Journey
- 0003_user_password_hash.py
- 0008_payment_intent_last_checked.py
- 0010_unique_provider_invoice_id.py
- 0011_organization_active_legal_name_index.py
- 0012_message_idempotency.py
- 0013_curated_demo_fixture.py
- 0014_outbox_dispatch_started_at.py
- MigrationConfigTests
- .test_payment_terms_are_part_of_the_terms_hash
- .test_refresh_rotates_token_and_revokes_previous_token
- HealthRouteTests
- 0004_communication_sources_and_scope_indexes.py
- OrganizationIndexMigrationTests
- _is_duplicate_membership_error
- PostgresDispatcherTests
- PaymentCreateStartedMigrationTests

## God Nodes (most connected - your core abstractions)
1. `ActorContext` - 237 edges
2. `OrganizationId` - 164 edges
3. `InvariantViolation` - 104 edges
4. `Deal` - 96 edges
5. `Money` - 93 edges
6. `DealId` - 93 edges
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

## Communities (177 total, 81 thin omitted)

### Community 0 - "Conversations & Test Conversation Use"
Cohesion: 0.07
Nodes (44): add_message_route(), AISuggestionRequest, clarify_fact_route(), confirm_fact_route(), ConstraintResponse, correct_fact_route(), CorrectFactRequest, create_fact_route() (+36 more)

### Community 1 - "AIContractError"
Cohesion: 0.13
Nodes (12): AIContractError, AIValidationClaim, _check_keys(), _decimal(), _required_string(), scope_extracted_facts(), _validate_decimal(), _validate_fact_value() (+4 more)

### Community 3 - "api/payments.py"
Cohesion: 0.03
Nodes (47): get_deal_repository(), list_deals_route(), read_deal_route(), _viewer_role(), CommercialDocumentDraftResponse, get_commercial_document_draft_route(), get_trade_pack_route(), authorize_payment_route() (+39 more)

### Community 4 - "Test Ai Provider & Ai"
Cohesion: 0.09
Nodes (13): extract_facts_from_context(), ConfiguredAIProvider, AISuggestionProviderTests, respond(), respond(), respond(), respond(), respond() (+5 more)

### Community 5 - "DealId"
Cohesion: 0.07
Nodes (13): ConstraintId, ConversationId, DealId, MessageId, OrganizationId, UserId, constraint(), message() (+5 more)

### Community 6 - "Seed Demo & Deals"
Cohesion: 0.07
Nodes (26): PaymentStatusRecord, AgreementVersion, Approval, Obligation, Base, Constraint, Conversation, CounterpartyOnboarding (+18 more)

### Community 7 - "PaymentNeedsAction"
Cohesion: 0.07
Nodes (14): receive_paypal_invoice_webhook(), PaymentInvoiceLookup, PaymentInvoiceRequest, PaymentNeedsAction, PaymentOutcomeUnknown, PaymentRetryableError, canonical_decimal(), _has_excess_currency_precision() (+6 more)

### Community 8 - "NotificationKind"
Cohesion: 0.21
Nodes (3): NotificationKind, DealWorkflowStatus, WorkflowWorkerIntegrationTests

### Community 9 - "api/agreements.py"
Cohesion: 0.09
Nodes (26): AgreementVersionResponse, ApprovalResponse, approve_agreement_route(), commit_agreement_route(), CommitAgreementRequest, compare_agreements_route(), create_agreement_draft_route(), create_reviewed_agreement_draft_route() (+18 more)

### Community 10 - "Test Conversation Routes (ConversationRouteTests)"
Cohesion: 0.10
Nodes (3): ConversationRouteTests, respond(), send()

### Community 11 - "create_deal"
Cohesion: 0.17
Nodes (4): create_deal(), CreateDealCommand, DealUseCaseTests, FakeDealRepository

### Community 13 - "get_current_actor"
Cohesion: 0.11
Nodes (13): _as_utc(), create_refresh_token(), _decode_token(), _development_actor(), development_login(), _encode_access_token(), get_current_actor(), _issue_tokens() (+5 more)

### Community 14 - "process_payment_intent"
Cohesion: 0.08
Nodes (7): payment_invoice_number(), PaymentInvoiceProvider, PaymentProcessingRepository, process_payment_intent(), reconcile_payment_intent(), _request_id_retry_window_expired(), require_payment_provider()

### Community 15 - "ai.py"
Cohesion: 0.07
Nodes (19): get_ai_suggestion_provider(), AIConfigurationError, AIProvenance, AIRetryPolicy, AISuggestionProvider, call_with_bounded_retry(), draft_proposal(), draft_proposal_from_context() (+11 more)

### Community 16 - "NegotiationTests"
Cohesion: 0.20
Nodes (4): EvidenceReference, negotiate_in_transaction(), replace_candidate(), NegotiationTests

### Community 17 - "Types & Client"
Cohesion: 0.06
Nodes (57): describeDetail(), getDealMessageExistence(), isAbortError(), isRecord(), listDeals(), readErrorDetail(), AgreementApproval, AgreementComparison (+49 more)

### Community 18 - "listOrganizations"
Cohesion: 0.07
Nodes (44): listOrganizations(), login(), clearAccessToken(), getAccessToken(), setTokens(), TokenResponse, App(), handleInvitationAccepted() (+36 more)

### Community 19 - "Money"
Cohesion: 0.08
Nodes (19): PaymentInvoiceReconciliation, _money(), _parse_money(), PaymentIntentStatus, PaymentMilestone, VerifiedProviderPaymentState, VerifiedProviderPaymentStatus, PaymentIntentId (+11 more)

### Community 21 - "Test Outbox Dispatcher & Outbox"
Cohesion: 0.11
Nodes (11): dispatch_outbox_event(), OutboxDispatchResult, PendingOutboxEvent, apply_dispatch_result(), claim_next_pending_event(), _claim_statement(), dispatch_one_pending_event(), dispatch_pending_outbox_events() (+3 more)

### Community 22 - "Simulate Deal Flow & Test"
Cohesion: 0.06
Nodes (13): _build_in_process_client(), dispatch_payment(), session_factory(), ci_deal_flow_hook(), DealFlowContext, DealFlowSimulator, _is_live_backend_healthy(), main() (+5 more)

### Community 23 - "Test Organization Invitations & Organizations"
Cohesion: 0.16
Nodes (5): accept_invitation(), AcceptInvitationRequest, create_organization_invitation(), CreateInvitationRequest, OrganizationInvitationTests

### Community 24 - "SqlAlchemyCommunicationRepository"
Cohesion: 0.12
Nodes (5): Conversation, CommunicationScopeError, _conversation_to_domain(), _page_bounds(), SqlAlchemyCommunicationRepository

### Community 25 - "Package & Vite.Config"
Cohesion: 0.06
Nodes (45): devDependencies, eslint@^10.13.0, @eslint/js@^10.0.1, eslint-plugin-react-hooks@^7.1.1, eslint-plugin-react-refresh@^0.4.20, globals@^17.13.0, happy-dom@^21.0.3, @testing-library/dom@^10.4.1 (+37 more)

### Community 26 - "client.test.ts"
Cohesion: 0.10
Nodes (21): API_REQUEST_TIMEOUT_MS, listOrganizationMembers(), revokeOrganizationMember(), CREATED_MESSAGE, fetchMock, lastRequest(), sentBody(), updateMemberPermissions() (+13 more)

### Community 27 - "Dealconversationreview & Dealconversationreview.Test"
Cohesion: 0.07
Nodes (40): createDealMessage(), importDealThread(), listDealFacts(), listDealMessages(), previewDealThreadImport(), reviewDealFact(), updateFactVisibility(), areFactsEqual() (+32 more)

### Community 28 - "Skill & Skill.Md"
Cohesion: 0.04
Nodes (43): API and Database Engineer Skill, API Design and Contract Semantics, Data Integrity and Invariant Enforcement, Query Performance and Projection Optimization, Schema Migration and Backward Compatibility, Transaction Boundaries and Atomicity, Archify Diagrammer Skill, Archify CLI Global Tool (+35 more)

### Community 29 - "sqlalchemy"
Cohesion: 0.04
Nodes (17): upgrade(), upgrade(), downgrade(), upgrade(), downgrade(), upgrade(), downgrade(), upgrade() (+9 more)

### Community 30 - "User"
Cohesion: 0.13
Nodes (4): _compute_effective_capabilities(), update_member_permissions(), UpdateMemberPermissionsRequest, OrganizationPermissionsTests

### Community 31 - "App.test.tsx"
Cohesion: 0.05
Nodes (43): @testing-library/react@^16.3.3, ApiError, getCommercialDocumentDraft(), getTradePack(), TradePackFormat, AgreementVersion, mockedApiRequest, mockedCreateOrganization (+35 more)

### Community 32 - "repositories/agreements.py"
Cohesion: 0.04
Nodes (44): AgreementAccessDenied, AgreementAlreadyCommitted, AgreementRepository, AgreementVersionConflict, AuditEventDraft, AuditRepository, commit_agreement(), create_agreement_draft() (+36 more)

### Community 33 - "Aisuggestionreview & Suggestionpreview"
Cohesion: 0.08
Nodes (47): correctDealFact(), createDealFact(), draftDealProposal(), getNegotiation(), negotiateDeal(), suggestDealFacts(), AIProvenance, Deal (+39 more)

### Community 34 - "SyncAlly Implementation Plan Document"
Cohesion: 0.16
Nodes (13): SyncAlly Architecture Document, System Topology and Ownership Boundaries, Temporal Worker and Outbox Architecture, Acceptance Criteria Verification Matrix, SyncAlly Implementation Plan Document, Issue #77 Architecture Contracts, Stage Lifecycle Roadmap, Frontend API Client and Authoritative State (+5 more)

### Community 35 - "PaymentProcessingTests"
Cohesion: 0.14
Nodes (5): FakeInvoiceProvider, FakeProcessingRepository, PaymentProcessingTests, _request(), _work_item()

### Community 36 - "AgreementCommitTests"
Cohesion: 0.16
Nodes (4): CommitAgreementCommand, commit_agreement_in_transaction(), AgreementCommitTests, commit_once()

### Community 37 - "worker.py"
Cohesion: 0.05
Nodes (25): OperationalRequestMiddleware, _connect_with_retry(), main(), run_forever(), main(), run_forever(), is_permanent_rpc_error(), configure_logging() (+17 more)

### Community 38 - "InvariantViolation"
Cohesion: 0.06
Nodes (23): CounterpartyInvitationResponse, InvitationResponse, ContactVisibility, _normalize_string(), Organization, OrganizationCapability, OrganizationContact, OrganizationMember (+15 more)

### Community 39 - "Paymentstatuspanel & Paymentstatuspanel.Test"
Cohesion: 0.06
Nodes (43): authorizeDealPayment(), getDeal(), getOrganization(), listPaymentStatuses(), previewDealPayment(), PaymentIntentStatus, DealConstellation(), DealConstellationProps (+35 more)

### Community 42 - "AISuggestionProviderTests"
Cohesion: 0.15
Nodes (3): DeterministicFakeAIProvider, extract_facts(), FakeWebhookVerifier

### Community 43 - "seed_demo.py"
Cohesion: 0.12
Nodes (11): _clear_fixture(), _create_fixture(), _delete_scoped(), DemoCollisionError, DemoIdentity, _normalized_index_predicate(), _password_for(), _preflight() (+3 more)

### Community 47 - "DealWorkflow"
Cohesion: 0.29
Nodes (3): DealWorkflowResult, DealWorkflowTests, new_notification()

### Community 49 - "repositories/negotiation.py"
Cohesion: 0.12
Nodes (12): _trade_pack_html(), section(), NegotiationConflict, NegotiationNotFound, NegotiationOrganizationRequired, TradeTerms, NegotiationSubmissionOutcome, Proposal (+4 more)

### Community 50 - "DealWorkflowNotification"
Cohesion: 0.10
Nodes (9): build_deal_workflow_id(), DealWorkflowStarter, WorkflowStartError, WorkflowStartOutcome, WorkflowStartPermanentError, WorkflowStartTransientError, DealWorkflowNotification, TemporalDealWorkflowStarter (+1 more)

### Community 51 - "Deal"
Cohesion: 0.13
Nodes (4): _to_response(), Deal, DealStatus, FakeDealRepository

### Community 52 - "Test Payment Outbox & Test"
Cohesion: 0.06
Nodes (21): get_paypal_webhook_configuration(), PaymentInvoiceNotifier, PaymentWorkItem, main(), GmailSettings, PayPalSettings, GmailSMTPInvoiceNotifier, OfflineDemoInvoiceProvider (+13 more)

### Community 53 - "Organization"
Cohesion: 0.13
Nodes (12): getOrganizationProfile(), updateOrganizationProfile(), ContactVisibility, Organization, OrganizationContact, describeError(), OrganizationProfileSection(), handleSave() (+4 more)

### Community 54 - "load_deal_workflow_state"
Cohesion: 0.09
Nodes (10): DealWorkflowState, load_deal_workflow_state(), parse_workflow_uuid(), WorkflowAgreementRepository, WorkflowDealNotFound, WorkflowDealRepository, _domain_deal(), _FakeAgreementRepository (+2 more)

### Community 55 - "canonical_decimal"
Cohesion: 0.09
Nodes (3): PaymentInvoiceNotice, _FakeSMTP, GmailSMTPInvoiceNotifierTests

### Community 56 - "Agreementreview & Client"
Cohesion: 0.12
Nodes (29): acceptInvitation(), apiBaseUrl(), apiRequest(), commitAgreementVersion(), compareAgreementVersions(), createAgreementFromReviewedTerms(), getAgreementHistory(), getAgreementVersion() (+21 more)

### Community 57 - "Organizations & Test Organization Onboarding"
Cohesion: 0.20
Nodes (5): add_organization_member(), AddOrganizationMemberRequest, create_organization(), CreateOrganizationRequest, OrganizationOnboardingTests

### Community 58 - "Test Workflow Activities & Activities"
Cohesion: 0.12
Nodes (7): DealWorkflowInput, _require_uuid(), new_workflow_input(), RefreshActivity, RefreshCall, RefreshDealStateActivityTests, factory()

### Community 59 - "Test Migration Lock & Env"
Cohesion: 0.10
Nodes (9): run_migrations_offline(), run_migrations_online(), serialize_migrations(), _make_postgres_connection(), _make_sqlite_connection(), MigrationLockTests, simulated_migration(), PostgresRealAdvisoryLockTests (+1 more)

### Community 60 - "Payment Processing & Test Payment"
Cohesion: 0.18
Nodes (3): PaymentInvoiceLineItem, SqlAlchemyPaymentProcessingRepository, transition()

### Community 61 - "01 Commercial Domain Model &"
Cohesion: 0.07
Nodes (19): AgreementVersion Aggregate, Append-Only AuditEvent Ledger, Commercial Constraint and Provenance, Deal Aggregate, Organization and Membership Entities, PaymentMilestone and Obligation, Proposal Aggregate and Terms Hash, Temporal Deal Workflow (+11 more)

### Community 64 - "Test Identity Boundary & Config"
Cohesion: 0.13
Nodes (3): _is_weak_jwt_secret(), Settings, IdentityBoundaryTests

### Community 65 - "Compose.Yaml (volumes)"
Cohesion: 0.09
Nodes (22): POSTGRES_DB, POSTGRES_PASSWORD, POSTGRES_USER, interval, retries, test, timeout, environment (+14 more)

### Community 66 - "InvalidTransition"
Cohesion: 0.11
Nodes (3): PaymentStatusResponse, SqlAlchemyPaymentIntentRepository, PaymentStatusExtendedModelTests

### Community 67 - "AddMessageRequest"
Cohesion: 0.19
Nodes (3): AddMessageRequest, CreateFactRequest, AddMessageRequestTests

### Community 68 - "api/organizations.py"
Cohesion: 0.08
Nodes (17): _accept_invitation(), _active_admin_membership(), _case_insensitive_prefix(), _create_invitation_token(), _deal_awaiting_counterparty(), _decode_invitation_token(), _escape_like(), get_optional_actor() (+9 more)

### Community 69 - "ExtractedFact"
Cohesion: 0.10
Nodes (16): FactExtractionRequest, _contains_numeric_token(), _contains_token(), _date_value_is_present(), ExtractedFact, _fact_value_is_supported_by_quote(), FactField, _flexible_whitespace_pattern() (+8 more)

### Community 71 - "build_terms"
Cohesion: 0.31
Nodes (6): PaymentTerm, ShipmentTerm, TradeLineItem, build_terms(), DecimalCanonicalizationTests, TradeTermsTests

### Community 72 - "PersistentDemoSeedTests"
Cohesion: 0.10
Nodes (8): fixture_id(), initialize_offline_database(), main(), OutboxEvent, PersistentDemoSeedTests, exercise_api(), start_deal_workflow(), dispatch()

### Community 73 - "AgreementVersionId"
Cohesion: 0.29
Nodes (3): AgreementVersionId, DealDomainTests, make_deal()

### Community 74 - "Createdealpage & Createdealpage.Test"
Cohesion: 0.16
Nodes (14): createCounterpartyInvitation(), createDeal(), CreateDealPage(), handleSubmit(), CreateDealPageProps, describeCreateError(), describeError(), DirectoryItem (+6 more)

### Community 75 - "Negotiation (BaseRequest)"
Cohesion: 0.13
Nodes (12): BaseRequest, CandidateRequest, EvidenceRequest, HistoryResponse, NegotiationRequest, NegotiationResponse, NegotiationResult, ProposalResponse (+4 more)

### Community 76 - "Test Organization Invitations & Organizations"
Cohesion: 0.17
Nodes (5): create_counterparty_invitation(), CreateCounterpartyInvitationRequest, OnboardingConcurrencyCases, OnboardingPostgresConcurrencyTests, OnboardingSQLiteConcurrencyTests

### Community 77 - "application/conversations.py"
Cohesion: 0.06
Nodes (17): add_message(), AddMessageCommand, ConstraintRepository, create_manual_constraint(), deal_has_any_message(), import_thread(), list_visible_constraints(), list_visible_messages() (+9 more)

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
Cohesion: 0.21
Nodes (5): OperationalFastAPI, captured_output(), SafeOperationsTests, exercise(), failed_db()

### Community 84 - "authorize_payment_intent"
Cohesion: 0.20
Nodes (4): authorize_payment_intent(), PaymentIntentAuthorizationOutcome, PaymentIntentRepository, SellerMembershipRepository

### Community 87 - "demo_lifecycle.py"
Cohesion: 0.19
Nodes (8): _acquire_lock(), _is_demo_deal(), lock_demo_deal_creation(), lock_demo_payment_processing(), lock_demo_reset(), lock_outbox_dispatch(), DemoLifecycleLockTests, _postgres_session()

### Community 88 - "Human Bilateral Amendment Workflow"
Cohesion: 0.40
Nodes (3): Canonical Hash and Legacy Export Preservation, Human Bilateral Amendment Workflow, Cancellation and Dispute Case State Machine

### Community 89 - "react"
Cohesion: 0.08
Nodes (30): addOrganizationMember(), createOrganization(), useHashRoute(), describeError(), OrganizationsPanel(), handleCreate(), handleInvite(), OrganizationsState (+22 more)

### Community 94 - "Constraint"
Cohesion: 0.08
Nodes (5): Constraint, _constraint_to_domain(), FakeCommunicationRepository, FakeCommunicationRepository, FakeCommunicationRepository

### Community 95 - "create_deal_route"
Cohesion: 0.20
Nodes (4): create_deal_route(), CreateDealRequest, DealResponse, DealSummaryResponse

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
Cohesion: 0.09
Nodes (16): AIPermanentError, AIProviderError, AITransientError, parse_extracted_facts(), parse_proposed_terms(), ProposalDraftRequest, AiContext, ProposedTerms (+8 more)

### Community 111 - "ConversationContractTests"
Cohesion: 0.12
Nodes (6): ConcurrentConstraintUpdate, confirm_constraint(), ConstraintNotFound, correct_constraint(), ConversationContractTests, FakeConstraintRepository

### Community 113 - ".add"
Cohesion: 0.16
Nodes (5): AuthorizePaymentIntentCommand, PaymentExecutionMode, _is_idempotency_key_violation(), _is_one_active_per_milestone_violation(), _violated_constraint_name()

### Community 114 - "build_terms"
Cohesion: 0.21
Nodes (5): NegotiationSession, NegotiationSessionId, build_proposal(), HumanNegotiationTests, NegotiationTests

### Community 117 - "NegotiationPostgresRaceTests"
Cohesion: 0.15
Nodes (7): NegotiationCommand, ProposalBase, NegotiationPostgresRaceTests, run(), failing(), succeed(), create_legacy_draft()

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
Cohesion: 0.18
Nodes (7): DevResetResponse, DevRoleSwitchRequest, _require_dev_environment(), reset_demo(), simulate_payment(), SimulatePaymentRequest, switch_role()

### Community 140 - "InvariantViolation"
Cohesion: 0.12
Nodes (3): _normalized_text(), _require_decimal(), InvariantViolation

### Community 144 - "application/conversations.py"
Cohesion: 0.10
Nodes (15): can_view_message(), CreateManualConstraintCommand, message_fingerprint(), MessageIdempotencyConflict, visible_to_viewer(), ScopedFactCandidate, ConstraintKind, ConstraintStatus (+7 more)

### Community 145 - "field_validator"
Cohesion: 0.14
Nodes (7): AcceptInvitationResponse, ContactPayload, ContactResponse, OrganizationDirectoryItem, OrganizationMemberResponse, ProfileResponse, UpdateProfileRequest

### Community 147 - "AI Provider Boundary Specification"
Cohesion: 0.53
Nodes (4): F2 AI Configuration and Provider Boundary, AI Provider Boundary Specification, AI Resilience and Retry Policy, AISuggestionProvider Contract

### Community 148 - "dependencies"
Cohesion: 0.40
Nodes (5): dependencies, react@^19.3.0, react-dom@^19.3.0, three@^0.186.1, react-dom

### Community 160 - ".test_refresh_rotates_token_and_revokes_previous_token"
Cohesion: 0.13
Nodes (4): _hash_refresh_token(), refresh_access_token(), RefreshRequest, RefreshToken

### Community 162 - "0004_communication_sources_and_scope_indexes.py"
Cohesion: 0.60
Nodes (4): _create_scope_index(), downgrade(), _drop_scope_index(), upgrade()

## Knowledge Gaps
- **47 isolated node(s):** `syncally`, `F1a Curated Repeatable Demo Fixture`, `Editorial Dark Theme Design System`, `ZIP HTML and Print Export Verification`, `Whole-Worktree Independent Review` (+42 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1273 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **81 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ActorContext` connect `Test Deal Routes & Identity` to `Conversations & Test Conversation Use`, `api/payments.py`, `Test Ai Provider & Ai`, `DealId`, `simulate_payment`, `FakeDealRepository`, `api/agreements.py`, `Test Conversation Routes (ConversationRouteTests)`, `create_deal`, `Test Agreement Routes (AgreementRouteTests)`, `get_current_actor`, `ai.py`, `application/conversations.py`, `CommercialDocumentDraftTests`, `Simulate Deal Flow & Test`, `Test Organization Invitations & Organizations`, `sqlalchemy`, `User`, `repositories/agreements.py`, `InvariantViolation`, `Test Payment Intent Repository &`, `AISuggestionProviderTests`, `Test Organization Directory & Organizations`, `Organizations & Test Organization Onboarding`, `._offline_intent`, `Test Identity Boundary & Config`, `InvalidTransition`, `api/organizations.py`, `Negotiation (BaseRequest)`, `Test Organization Invitations & Organizations`, `application/conversations.py`, `Test Communication Repositories (MessageIdempotencyPostgresTests)`, `Test Ai Context & Conversations`, `Test Negotiation (NegotiationRouteTests)`, `create_deal_route`, `ConversationContractTests`, `.can_access_deal`?**
  _High betweenness centrality (0.096) - this node is a cross-community bridge._
- **Are the 93 inferred relationships involving `ActorContext` (e.g. with `approve_agreement_route()` and `commit_agreement_route()`) actually correct?**
  _`ActorContext` has 93 INFERRED edges - model-reasoned connections that need verification._
- **What connects `syncally`, `F1a Curated Repeatable Demo Fixture`, `Editorial Dark Theme Design System` to the rest of the system?**
  _47 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Conversations & Test Conversation Use` be split into smaller, more focused modules?**
  _Cohesion score 0.06839945280437756 - nodes in this community are weakly interconnected._
- **Why does `OrganizationId` connect `DealId` to `AIContractError`, `api/payments.py`, `Test Ai Provider & Ai`, `Seed Demo & Deals`, `api/agreements.py`, `Test Conversation Routes (ConversationRouteTests)`, `create_deal`, `InvariantViolation`, `Test Agreement Routes (AgreementRouteTests)`, `ai.py`, `application/conversations.py`, `NegotiationTests`, `Money`, `CommercialDocumentDraftTests`, `Test Outbox Dispatcher & Outbox`, `SqlAlchemyCommunicationRepository`, `sqlalchemy`, `repositories/agreements.py`, `AgreementCommitTests`, `InvariantViolation`, `Test Payment Intent Repository &`, `AISuggestionProviderTests`, `SqlAlchemyDealRepository`, `repositories/negotiation.py`, `Deal`, `load_deal_workflow_state`, `InvalidTransition`, `api/organizations.py`, `ExtractedFact`, `build_terms`, `AgreementVersionId`, `Negotiation (BaseRequest)`, `Test Organization Invitations & Organizations`, `application/conversations.py`, `Test Counterparty Onboarding Migration &`, `Test Ai Context & Conversations`, `InvalidTransition`, `Constraint`, `_to_domain`, `LocalWorkflowSmokeTests`, `openai.py`, `Test Negotiation Migration (NegotiationMigrationTests)`, `ConversationContractTests`, `.add`, `.test_storage_dict_round_trip_preserves_destination_case`, `.can_access_deal`?**
  _High betweenness centrality (0.048) - this node is a cross-community bridge._
- **Are the 53 inferred relationships involving `OrganizationId` (e.g. with `create_reviewed_agreement_draft_route()` and `write_negotiation()`) actually correct?**
  _`OrganizationId` has 53 INFERRED edges - model-reasoned connections that need verification._
- **Should `AIContractError` be split into smaller, more focused modules?**
  _Cohesion score 0.13076923076923078 - nodes in this community are weakly interconnected._