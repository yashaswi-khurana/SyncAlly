# Graph Report - SyncAlly  (2026-11-06)

## Corpus Check
- 310 files · ~276,704 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 13 file(s) not represented in the graph (top: (none) 8, .example 2, .ini 1)

## Summary
- 4849 nodes · 15836 edges · 167 communities (114 shown, 53 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 2063 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `16ae3b2b`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Conversations & Test Conversation Use
- AIContractError
- BaseModel
- repositories/agreements.py
- Test Ai Provider & Ai
- DealId
- models/__init__.py
- PaymentNeedsAction
- PaymentWorkItem
- api/agreements.py
- Test Conversation Routes (ConversationRouteTests)
- PaymentStatusExtendedModelTests
- Test Agreement Routes (AgreementRouteTests)
- application/agreements.py
- process_payment_intent
- ProposedTerms
- NegotiationTests
- Types & Client
- listOrganizations
- _raise_agreement_error
- application/documents.py
- Test Outbox Dispatcher & Outbox
- Simulate Deal Flow & Test
- Test Organization Invitations & Organizations
- SqlAlchemyCommunicationRepository
- Package & Vite.Config
- client.test.ts
- Dealconversationreview & Dealconversationreview.Test
- Skill & Skill.Md
- auth.py
- User
- DealDetailPage.test.tsx
- demo_lifecycle.py
- Aisuggestionreview & Suggestionpreview
- SyncAlly Implementation Plan Document
- PaymentProcessingTests
- AmendmentTests
- worker.py
- DealDetailPage.tsx
- Paymentstatuspanel & Paymentstatuspanel.Test
- PaymentIntentRepositoryTests
- services
- NegotiationPostgresRaceTests
- DealRepository
- DealWorkflow
- Test Dev Routes (DevRoutesTests)
- api/organizations.py
- DealWorkflow
- Test Organization Directory & Organizations
- read_deal_route
- DealWorkflowNotification
- SqlAlchemyDealRepository
- PaymentOutboxWorkerTests
- api/payments.py
- Deal
- test_gmail.py
- ApiError
- ConversationUseCaseTests
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
- test_deal_workflow.py
- OrganizationId
- VerifiedProviderPaymentState
- Money
- PersistentDemoSeedTests
- AgreementReview.tsx
- ApprovalDecision
- api/negotiation.py
- OrganizationRepositoryTests
- IdentityBoundaryTests
- 13 Postgres Temporal & 14
- Tsconfig (tsconfig.json)
- Test Paypal Webhooks (FakeWebhookVerifier)
- Test Counterparty Onboarding Migration &
- CreateReviewedAgreementDraftCommand
- Test Operations & Test Outbox
- OrganizationContact
- environment
- Main & Test Identity Boundary
- dev.py
- Human Bilateral Amendment Workflow
- ApiError
- Test Organization Index Migration (OrganizationIndexPostgresMigrationTests)
- Server-Enforced Capability Matrix
- UUID
- NegotiationRouteTests
- Constraint
- infrastructure/outbox.py
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
- .refresh_deal_state
- healthcheck
- AddMessageRequest
- DealWorkflowInput
- AiContextSelectionTests
- Final Gates and Truthful Completion Specification
- Skill (Repo Idea Thinker Skill)
- Vite Env.D (ImportMeta)
- temporal-schema
- Index (Frontend HTML Root Document)
- Pyproject (syncally)
- Customer journey: buyer and seller
- bounded_decimal
- sqlalchemy
- application/deals.py
- Free single-VM deployment
- env.py
- repositories/fulfillment.py
- AI Provider Boundary Specification
- api/fulfillment.py
- Four-Dimension Profile Collections
- Two-Party Judge Journey
- volumes
- AIContractTests
- setup-temporal-postgres.sh
- FulfillmentMigrationTests
- ProviderInvoiceUniqueMigrationTests
- unittest
- Visibility
- MigrationConfigTests
- CollectionSchemaMigrationTests
- create-temporal-namespace.sh
- postgres-init.sh
- repositories/communications.py
- NegotiationCommand
- database_health
- MilestonePaymentsMigrationTests
- record_paypal_webhook_event
- NegotiationMigrationTests
- OrganizationCapability

## God Nodes (most connected - your core abstractions)
1. `ActorContext` - 267 edges
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

## Communities (167 total, 53 thin omitted)

### Community 0 - "Conversations & Test Conversation Use"
Cohesion: 0.07
Nodes (43): add_message_route(), AISuggestionRequest, clarify_fact_route(), confirm_fact_route(), ConstraintResponse, correct_fact_route(), CorrectFactRequest, create_fact_route() (+35 more)

### Community 1 - "AIContractError"
Cohesion: 0.15
Nodes (19): AIContractError, AIValidationClaim, _check_keys(), _contains_numeric_token(), _contains_token(), _date_value_is_present(), _decimal(), _fact_value_is_supported_by_quote() (+11 more)

### Community 3 - "repositories/agreements.py"
Cohesion: 0.05
Nodes (34): AgreementAccessDenied, AgreementAlreadyCommitted, AgreementNotFound, AgreementVersionConflict, AmbiguousAgreementOrganization, create_agreement_draft(), CreateAgreementDraftCommand, DuplicateApproval (+26 more)

### Community 4 - "Test Ai Provider & Ai"
Cohesion: 0.11
Nodes (12): extract_facts_from_context(), ConfiguredAIProvider, respond(), respond(), respond(), respond(), respond(), respond() (+4 more)

### Community 5 - "DealId"
Cohesion: 0.09
Nodes (11): Message, ConstraintId, ConversationId, MessageId, UserId, _message_to_domain(), constraint(), message() (+3 more)

### Community 6 - "models/__init__.py"
Cohesion: 0.08
Nodes (19): _create_fixture(), DemoIdentity, _password_for(), Approval, Obligation, Base, Constraint, Conversation (+11 more)

### Community 7 - "PaymentNeedsAction"
Cohesion: 0.09
Nodes (10): receive_paypal_invoice_webhook(), PaymentOutcomeUnknown, PaymentRetryableError, _has_excess_currency_precision(), PayPalSandboxInvoiceProvider, _provider_error_code(), _provider_request_id(), _send_request() (+2 more)

### Community 8 - "PaymentWorkItem"
Cohesion: 0.08
Nodes (11): get_paypal_webhook_configuration(), PaymentInvoiceLookup, PaymentInvoiceNotice, PaymentInvoiceRequest, PaymentNeedsAction, PaymentWorkItem, main(), GmailSettings (+3 more)

### Community 9 - "api/agreements.py"
Cohesion: 0.09
Nodes (18): AmendmentImpactResponse, CommitAgreementRequest, CreateAgreementDraftRequest, CreateReviewedAgreementDraftRequest, FulfillmentObligationImpactResponse, get_agreement_repository(), MoneyRequest, PaymentMilestoneImpactResponse (+10 more)

### Community 10 - "Test Conversation Routes (ConversationRouteTests)"
Cohesion: 0.10
Nodes (3): ConversationRouteTests, respond(), send()

### Community 13 - "application/agreements.py"
Cohesion: 0.04
Nodes (35): AuditRepository, commit_agreement(), ObligationRepository, OutboxEventDraft, OutboxRepository, PaymentMilestoneRepository, ProposalNotFound, AgreementNotCommitted (+27 more)

### Community 14 - "process_payment_intent"
Cohesion: 0.08
Nodes (7): payment_invoice_number(), PaymentInvoiceProvider, PaymentProcessingRepository, process_payment_intent(), reconcile_payment_intent(), _request_id_retry_window_expired(), require_payment_provider()

### Community 15 - "ProposedTerms"
Cohesion: 0.08
Nodes (11): get_ai_suggestion_provider(), AIConfigurationError, AIProviderError, FactExtractionRequest, ProposalDraftRequest, ExtractedFact, FactField, ProposedTerms (+3 more)

### Community 17 - "Types & Client"
Cohesion: 0.06
Nodes (51): acceptInvitation(), apiBaseUrl(), createAgreementFromReviewedTerms(), describeDetail(), getDealMessageExistence(), isAbortError(), isRecord(), readErrorDetail() (+43 more)

### Community 18 - "listOrganizations"
Cohesion: 0.06
Nodes (56): dependencies, react@^19.3.0, react-dom@^19.3.0, three@^0.186.1, login(), clearAccessToken(), getAccessToken(), setTokens() (+48 more)

### Community 19 - "_raise_agreement_error"
Cohesion: 0.16
Nodes (13): AgreementVersionResponse, commit_agreement_route(), compare_agreements_route(), create_agreement_draft_route(), create_reviewed_agreement_draft_route(), propose_amendment_route(), _raise_agreement_error(), read_agreement_history_route() (+5 more)

### Community 20 - "application/documents.py"
Cohesion: 0.09
Nodes (15): CommercialDocumentDraftResponse, get_commercial_document_draft_route(), get_trade_pack_route(), CommercialDocumentDraft, export_display_terms(), generate_commercial_document_draft(), generate_trade_pack(), InvalidTradePack (+7 more)

### Community 21 - "Test Outbox Dispatcher & Outbox"
Cohesion: 0.13
Nodes (7): build_deal_workflow_id(), dispatch_outbox_event(), PendingOutboxEvent, dispatch_one_pending_event(), FakeDealWorkflowStarter, OutboxDispatcherTests, start_deal_workflow()

### Community 22 - "Simulate Deal Flow & Test"
Cohesion: 0.07
Nodes (11): _build_in_process_client(), dispatch_payment(), session_factory(), ci_deal_flow_hook(), DealFlowContext, DealFlowSimulator, run_simulation(), SimulationError (+3 more)

### Community 23 - "Test Organization Invitations & Organizations"
Cohesion: 0.15
Nodes (9): accept_invitation(), AcceptInvitationRequest, create_counterparty_invitation(), create_organization_invitation(), CreateCounterpartyInvitationRequest, CreateInvitationRequest, _decode_invitation_token(), ActorContext (+1 more)

### Community 24 - "SqlAlchemyCommunicationRepository"
Cohesion: 0.10
Nodes (6): Conversation, CommunicationScopeError, _conversation_to_domain(), _is_unique_violation(), _page_bounds(), SqlAlchemyCommunicationRepository

### Community 25 - "Package & Vite.Config"
Cohesion: 0.06
Nodes (45): devDependencies, eslint@^10.13.0, @eslint/js@^10.0.1, eslint-plugin-react-hooks@^7.1.1, eslint-plugin-react-refresh@^0.4.20, globals@^17.13.0, happy-dom@^21.0.3, @testing-library/dom@^10.4.1 (+37 more)

### Community 26 - "client.test.ts"
Cohesion: 0.15
Nodes (16): listOrganizationMembers(), revokeOrganizationMember(), updateMemberPermissions(), setAccessToken(), OrganizationCapability, OrganizationMember, ALL_CAPABILITIES, describeError() (+8 more)

### Community 27 - "Dealconversationreview & Dealconversationreview.Test"
Cohesion: 0.07
Nodes (43): createDealMessage(), importDealThread(), listDealFacts(), listDealMessages(), previewDealThreadImport(), reviewDealFact(), updateFactVisibility(), DealMessage (+35 more)

### Community 28 - "Skill & Skill.Md"
Cohesion: 0.04
Nodes (43): API and Database Engineer Skill, API Design and Contract Semantics, Data Integrity and Invariant Enforcement, Query Performance and Projection Optimization, Schema Migration and Backward Compatibility, Transaction Boundaries and Atomicity, Archify Diagrammer Skill, Archify CLI Global Tool (+35 more)

### Community 30 - "User"
Cohesion: 0.09
Nodes (7): revoke_organization_member(), update_member_permissions(), UpdateMemberPermissionsRequest, User, DealAuthorizationTests, FakeWebhookVerifier, OrganizationPermissionsTests

### Community 31 - "DealDetailPage.test.tsx"
Cohesion: 0.04
Nodes (61): ApiError, getCommercialDocumentDraft(), getDealFulfillment(), getTradePack(), recordDealFulfillment(), TradePackFormat, AgreementVersion, FulfillmentSnapshot (+53 more)

### Community 32 - "demo_lifecycle.py"
Cohesion: 0.19
Nodes (8): _acquire_lock(), _is_demo_deal(), lock_demo_deal_creation(), lock_demo_payment_processing(), lock_demo_reset(), lock_outbox_dispatch(), DemoLifecycleLockTests, _postgres_session()

### Community 33 - "Aisuggestionreview & Suggestionpreview"
Cohesion: 0.06
Nodes (58): correctDealFact(), createDealFact(), draftDealProposal(), getNegotiation(), negotiateDeal(), suggestDealFacts(), AIProvenance, DealFact (+50 more)

### Community 34 - "SyncAlly Implementation Plan Document"
Cohesion: 0.16
Nodes (13): SyncAlly Architecture Document, System Topology and Ownership Boundaries, Temporal Worker and Outbox Architecture, Acceptance Criteria Verification Matrix, SyncAlly Implementation Plan Document, Issue #77 Architecture Contracts, Stage Lifecycle Roadmap, Frontend API Client and Authoritative State (+5 more)

### Community 35 - "PaymentProcessingTests"
Cohesion: 0.14
Nodes (5): FakeInvoiceProvider, FakeProcessingRepository, PaymentProcessingTests, _request(), _work_item()

### Community 36 - "AmendmentTests"
Cohesion: 0.05
Nodes (15): AuditEventDraft, CommitAgreementCommand, propose_amendment(), ProposeAmendmentCommand, RecordApprovalCommand, AgreementVersion, commit_agreement_in_transaction(), propose_amendment_in_transaction() (+7 more)

### Community 37 - "worker.py"
Cohesion: 0.04
Nodes (27): OperationalFastAPI, OperationalRequestMiddleware, _connect_with_retry(), main(), run_forever(), main(), run_forever(), _is_live_backend_healthy() (+19 more)

### Community 38 - "DealDetailPage.tsx"
Cohesion: 0.09
Nodes (23): getDeal(), AgreementApproval, Deal, AgreementReviewProps, DealConstellation(), DealConstellationProps, DealDetailPage(), handleGenerateInvite() (+15 more)

### Community 39 - "Paymentstatuspanel & Paymentstatuspanel.Test"
Cohesion: 0.07
Nodes (41): API_REQUEST_TIMEOUT_MS, authorizeDealPayment(), listDealPaymentMilestones(), listPaymentStatuses(), previewDealPayment(), CREATED_MESSAGE, fetchMock, lastRequest() (+33 more)

### Community 40 - "PaymentIntentRepositoryTests"
Cohesion: 0.05
Nodes (13): authorize_payment_intent(), AuthorizePaymentIntentCommand, PaymentIntentAuthorizationOutcome, PaymentIntentRepository, SellerMembershipRepository, queue_simulated_reconciliation(), require_simulation_scope(), authorize_payment_intent_in_transaction() (+5 more)

### Community 41 - "services"
Cohesion: 0.09
Nodes (32): build, depends_on, restart, context, dockerfile, migrate, temporal-namespace, build (+24 more)

### Community 42 - "NegotiationPostgresRaceTests"
Cohesion: 0.22
Nodes (4): NegotiationPostgresRaceTests, run(), failing(), succeed()

### Community 43 - "DealRepository"
Cohesion: 0.12
Nodes (5): get_deal_repository(), read_deal_route(), _both_organizations_active(), DealRepository, get_deal()

### Community 46 - "api/organizations.py"
Cohesion: 0.06
Nodes (31): _accept_invitation(), AcceptInvitationResponse, _active_admin_membership(), add_organization_member(), AddOrganizationMemberRequest, _compute_effective_capabilities(), ContactResponse, CounterpartyInvitationResponse (+23 more)

### Community 47 - "DealWorkflow"
Cohesion: 0.29
Nodes (3): DealWorkflowResult, DealWorkflowTests, new_notification()

### Community 48 - "Test Organization Directory & Organizations"
Cohesion: 0.13
Nodes (4): _case_insensitive_prefix(), _escape_like(), value(), OrganizationDirectoryTests

### Community 49 - "read_deal_route"
Cohesion: 0.15
Nodes (8): CreateDealRequest, DealResponse, DealSummaryResponse, list_deals_route(), _to_response(), _viewer_role(), list_deals(), get_db()

### Community 50 - "DealWorkflowNotification"
Cohesion: 0.10
Nodes (9): DealWorkflowStarter, WorkflowStartError, WorkflowStartOutcome, WorkflowStartPermanentError, WorkflowStartTransientError, DealWorkflowNotification, TemporalDealWorkflowStarter, start_deal_workflow() (+1 more)

### Community 52 - "PaymentOutboxWorkerTests"
Cohesion: 0.09
Nodes (14): PaymentInvoiceNotifier, PaymentProviderResolver, claim_next_payment_event(), _claim_statement(), _ClaimedPaymentEvent, dispatch_one_payment_event(), dispatch_pending_payment_events(), _finish_event() (+6 more)

### Community 53 - "api/payments.py"
Cohesion: 0.07
Nodes (24): authorize_payment_route(), AuthorizePaymentRequest, AuthorizePaymentResponse, _check_milestone_delivery_confirmed(), get_payment_status_repository(), list_payment_milestones_route(), list_payment_statuses_route(), MilestoneAllocationResponse (+16 more)

### Community 54 - "Deal"
Cohesion: 0.05
Nodes (14): DealWorkflowState, load_deal_workflow_state(), parse_workflow_uuid(), WorkflowAgreementRepository, WorkflowDealRepository, Deal, DealStatus, _to_domain() (+6 more)

### Community 56 - "ApiError"
Cohesion: 0.17
Nodes (12): getOrganization(), listDeals(), DealSummary, ViewerRole, DealsPage(), DealsPageProps, DealsState, describeError() (+4 more)

### Community 57 - "ConversationUseCaseTests"
Cohesion: 0.12
Nodes (10): AddMessageCommand, message_fingerprint(), MessageIdempotencyPostgresTests, _find_conversation(), _find_keyed_message(), rendezvous(), send(), wait_for() (+2 more)

### Community 58 - "Agreement"
Cohesion: 0.09
Nodes (13): AgreementRepository, assess_amendment_impact(), create_reviewed_agreement_draft(), record_approval(), withdraw_amendment(), WithdrawAmendmentCommand, _display(), _render() (+5 more)

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
Cohesion: 0.19
Nodes (3): OnboardingConcurrencyCases, OnboardingPostgresConcurrencyTests, OnboardingSQLiteConcurrencyTests

### Community 64 - "seed_demo_data"
Cohesion: 0.16
Nodes (7): _clear_fixture(), _delete_scoped(), DemoCollisionError, _normalized_index_predicate(), _preflight(), seed_demo_data(), DemoSeedTests

### Community 65 - "Compose.Yaml (volumes)"
Cohesion: 0.09
Nodes (22): POSTGRES_DB, POSTGRES_PASSWORD, POSTGRES_USER, interval, retries, test, timeout, environment (+14 more)

### Community 66 - "InvalidTransition"
Cohesion: 0.20
Nodes (3): PaymentIntent, InvalidTransition, OutboxEvent

### Community 68 - "test_deal_workflow.py"
Cohesion: 0.15
Nodes (5): DealWorkflowInput, _require_uuid(), new_workflow_input(), RefreshActivity, RefreshCall

### Community 69 - "OrganizationId"
Cohesion: 0.06
Nodes (17): PaymentStatusRecord, PaymentMilestone, AgreementVersionId, DealId, OrganizationId, PaymentMilestoneId, _restore_domain_intent(), ExtendedPaymentStatusRecord (+9 more)

### Community 70 - "VerifiedProviderPaymentState"
Cohesion: 0.10
Nodes (8): PaymentInvoiceReconciliation, PaymentIntentStatus, VerifiedProviderPaymentState, transition(), FakePayPalInvoiceProvider, get_invoice_reconciliation(), get_invoice_reconciliation(), PaymentReconciliationRepositoryTests

### Community 71 - "Money"
Cohesion: 0.09
Nodes (22): build_trade_terms_from_request(), compare_agreement_terms(), assess_amendment_impact(), FulfillmentObligationImpact, PaymentMilestoneImpact, _money(), _parse_money(), PaymentObligationAllocation (+14 more)

### Community 72 - "PersistentDemoSeedTests"
Cohesion: 0.10
Nodes (6): fixture_id(), initialize_offline_database(), main(), PersistentDemoSeedTests, exercise_api(), dispatch()

### Community 73 - "AgreementReview.tsx"
Cohesion: 0.11
Nodes (40): apiRequest(), commitAgreementVersion(), compareAgreementVersions(), getAgreementHistory(), getAgreementVersion(), getAmendmentImpact(), getCurrentAgreement(), previewAmendmentImpact() (+32 more)

### Community 74 - "ApprovalDecision"
Cohesion: 0.27
Nodes (7): ApprovalResponse, approve_agreement_route(), _record_decision(), RecordApprovalRequest, reject_agreement_route(), _to_approval_response(), ApprovalDecision

### Community 75 - "api/negotiation.py"
Cohesion: 0.13
Nodes (12): BaseRequest, CandidateRequest, EvidenceRequest, HistoryResponse, NegotiationRequest, NegotiationResponse, NegotiationResult, ProposalResponse (+4 more)

### Community 76 - "OrganizationRepositoryTests"
Cohesion: 0.14
Nodes (6): Organization, OrganizationProfile, _organization_to_domain(), _profile_to_domain(), SqlAlchemyOrganizationRepository, OrganizationRepositoryTests

### Community 77 - "IdentityBoundaryTests"
Cohesion: 0.04
Nodes (3): _is_weak_jwt_secret(), Settings, IdentityBoundaryTests

### Community 78 - "13 Postgres Temporal & 14"
Cohesion: 0.14
Nodes (9): Organization-Scoped Routing Policy, Durable Scoped Reminder Scheduling, Isolated PostgreSQL Migration and Constraint Testing, PostgreSQL and Temporal Verification Specification, Temporal Worker Crash Replay and Recovery, PayPal Sandbox Lifecycle Verification, PayPal Sandbox Specification F11b, Signature-Verified Webhook and Authenticated Reconciliation (+1 more)

### Community 79 - "Tsconfig (tsconfig.json)"
Cohesion: 0.11
Nodes (17): compilerOptions, allowImportingTsExtensions, jsx, lib, module, moduleDetection, moduleResolution, noEmit (+9 more)

### Community 81 - "Test Counterparty Onboarding Migration &"
Cohesion: 0.11
Nodes (4): create_database_engine(), CounterpartyOnboardingMigrationTests, DemoFixtureMigrationTests, NegotiationSqliteRaceTests

### Community 82 - "CreateReviewedAgreementDraftCommand"
Cohesion: 0.24
Nodes (5): CreateReviewedAgreementDraftCommand, ProposalBase, create_reviewed_agreement_draft_in_transaction(), create_legacy_draft(), replace_candidate()

### Community 83 - "Test Operations & Test Outbox"
Cohesion: 0.22
Nodes (4): captured_output(), SafeOperationsTests, exercise(), failed_db()

### Community 84 - "OrganizationContact"
Cohesion: 0.31
Nodes (4): OrganizationContact, _contact_to_dict(), _contact_to_domain(), OrganizationContactDomainTests

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
Cohesion: 0.04
Nodes (57): addOrganizationMember(), createCounterpartyInvitation(), createDeal(), createOrganization(), getOrganizationProfile(), listOrganizations(), updateOrganizationProfile(), ContactVisibility (+49 more)

### Community 94 - "Constraint"
Cohesion: 0.09
Nodes (3): Constraint, FakeCommunicationRepository, FakeCommunicationRepository

### Community 95 - "infrastructure/outbox.py"
Cohesion: 0.18
Nodes (6): OutboxDispatchResult, apply_dispatch_result(), claim_next_pending_event(), _claim_statement(), dispatch_pending_outbox_events(), PostgresDispatcherTests

### Community 96 - "application/conversations.py"
Cohesion: 0.05
Nodes (21): add_message(), can_view_constraint(), can_view_message(), CommunicationRepository, ConstraintRepository, correct_constraint(), create_manual_constraint(), deal_has_any_message() (+13 more)

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
Cohesion: 0.07
Nodes (16): AIRetryPolicy, AISuggestionProvider, call_with_bounded_retry(), draft_proposal(), draft_proposal_from_context(), extract_facts(), FactExtractionResult, _list_all_constraints_for_owner() (+8 more)

### Community 104 - "openai.py"
Cohesion: 0.13
Nodes (13): AIPermanentError, AITransientError, parse_extracted_facts(), parse_proposed_terms(), AiContext, _json(), _object(), OpenAIChatCompletions (+5 more)

### Community 105 - "AISuggestionProviderTests"
Cohesion: 0.14
Nodes (3): DeterministicFakeAIProvider, AISuggestionProviderTests, extract_facts()

### Community 106 - "x-app-environment"
Cohesion: 0.10
Nodes (21): x-app-environment, AI_PROVIDER, APP_ENV, DATABASE_URL, DEBUG, GMAIL_APP_PASSWORD, GMAIL_FROM_EMAIL, GMAIL_SMTP_USERNAME (+13 more)

### Community 108 - "environment"
Cohesion: 0.12
Nodes (20): environment, BIND_ON_IP, DB, DB_PORT, DBNAME, POSTGRES_DB, POSTGRES_PASSWORD, POSTGRES_PWD (+12 more)

### Community 111 - "ConversationContractTests"
Cohesion: 0.11
Nodes (5): ConcurrentConstraintUpdate, confirm_constraint(), ConstraintNotFound, ConversationContractTests, FakeConstraintRepository

### Community 112 - "auth.py"
Cohesion: 0.07
Nodes (23): _as_utc(), create_refresh_token(), CredentialsRequest, _decode_token(), _development_actor(), development_login(), _encode_access_token(), get_current_actor() (+15 more)

### Community 114 - "healthcheck"
Cohesion: 0.16
Nodes (18): healthcheck, healthcheck, image, restart, volumes, temporal-schema, interval, retries (+10 more)

### Community 115 - "AddMessageRequest"
Cohesion: 0.21
Nodes (3): AddMessageRequest, CreateFactRequest, AddMessageRequestTests

### Community 116 - "DealWorkflowInput"
Cohesion: 0.18
Nodes (3): RefreshDealStateActivity, RefreshDealStateActivityTests, factory()

### Community 117 - "AiContextSelectionTests"
Cohesion: 0.17
Nodes (3): select_ai_context(), AiContextSelectionTests, FakeCommunicationRepository

### Community 119 - "Final Gates and Truthful Completion Specification"
Cohesion: 0.20
Nodes (9): Evidence-Free Projection and Safety Bounds, F12 Trade Pack Handoff Document, Trade Pack Export Contract, Browser Verification Specification, ZIP HTML and Print Export Verification, Two-Party Isolated Browser Testing, Final Gates and Truthful Completion Specification, Full Gate Verification Suite (+1 more)

### Community 120 - "Skill (Repo Idea Thinker Skill)"
Cohesion: 0.50
Nodes (3): Repo Idea Thinker Skill, Repository-Grounded Ideation Discipline, Idea Quality Standards and Lightweight Validation

### Community 134 - "temporal-schema"
Cohesion: 0.20
Nodes (10): condition, db, depends_on, temporal-schema, command, depends_on, entrypoint, image (+2 more)

### Community 139 - "Customer journey: buyer and seller"
Cohesion: 0.29
Nodes (6): Customer contract, Customer journey: buyer and seller, Evidence and limits, Implementation constraints discovered during task mapping, Outcome, Task graph

### Community 140 - "bounded_decimal"
Cohesion: 0.09
Nodes (8): _normalized_text(), _require_decimal(), _normalize_string(), InvariantViolation, bounded_decimal(), currency_precision(), has_excess_currency_precision(), BoundedDecimalTests

### Community 141 - "sqlalchemy"
Cohesion: 0.04
Nodes (37): upgrade(), uuid_column(), upgrade(), upgrade(), _create_scope_index(), downgrade(), _drop_scope_index(), upgrade() (+29 more)

### Community 143 - "application/deals.py"
Cohesion: 0.12
Nodes (7): create_deal_route(), get_deal_repository(), create_deal(), CreateDealCommand, DealAccessDenied, DealUseCaseTests, FakeDealRepository

### Community 144 - "Free single-VM deployment"
Cohesion: 0.33
Nodes (5): 1. Provision the VM and DNS, 2. Configure secrets, 3. Start the stack, Free single-VM deployment, Updating and operating

### Community 146 - "repositories/fulfillment.py"
Cohesion: 0.13
Nodes (11): FulfillmentConflict, FulfillmentUnavailable, bounded_quantity(), quantity_text(), _scaled(), _quantity(), _record(), _request_hash() (+3 more)

### Community 147 - "AI Provider Boundary Specification"
Cohesion: 0.53
Nodes (4): F2 AI Configuration and Provider Boundary, AI Provider Boundary Specification, AI Resilience and Retry Policy, AISuggestionProvider Contract

### Community 148 - "api/fulfillment.py"
Cohesion: 0.14
Nodes (16): _event_response(), FulfillmentEventResponse, FulfillmentSnapshotResponse, get_fulfillment_repository(), _raise_fulfillment_error(), read_fulfillment_route(), record_fulfillment_route(), _snapshot_response() (+8 more)

### Community 151 - "volumes"
Cohesion: 0.50
Nodes (4): volumes, caddy_config, caddy_data, postgres_data

### Community 152 - "AIContractTests"
Cohesion: 0.18
Nodes (3): scope_extracted_facts(), ScopedFactCandidate, AIContractTests

### Community 153 - "setup-temporal-postgres.sh"
Cohesion: 0.67
Nodes (3): PGPASSWORD, setup-temporal-postgres.sh script, update_database_schema()

### Community 156 - "unittest"
Cohesion: 0.08
Nodes (6): CommunicationMigrationTests, MessageIdempotencyMigrationTests, InvitingPartyMigrationTests, OrganizationIndexMigrationTests, OutboxDispatchMigrationTests, PaymentCreateStartedMigrationTests

### Community 157 - "Visibility"
Cohesion: 0.18
Nodes (6): CreateManualConstraintCommand, ConstraintKind, ConstraintStatus, MessageSourceType, Visibility, _constraint_to_domain()

### Community 163 - "repositories/communications.py"
Cohesion: 0.10
Nodes (6): NotificationKind, delivery_obligation_fulfilled(), maybe_complete_deal(), payments_reconciled(), Deal, queue_deal_workflow_notification()

### Community 166 - "NegotiationCommand"
Cohesion: 0.31
Nodes (4): EvidenceReference, negotiate(), NegotiationCommand, NegotiationRepository

### Community 175 - "OrganizationCapability"
Cohesion: 0.16
Nodes (10): ContactVisibility, OrganizationCapability, OrganizationMember, OrganizationMemberRole, OrganizationMemberStatus, OrganizationStatus, OrganizationVerificationStatus, resolve_effective_capabilities() (+2 more)

## Knowledge Gaps
- **48 isolated node(s):** `syncally`, `PGPASSWORD`, `F1a Curated Repeatable Demo Fixture`, `Editorial Dark Theme Design System`, `ZIP HTML and Print Export Verification` (+43 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1470 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **53 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ActorContext` connect `Test Organization Invitations & Organizations` to `Conversations & Test Conversation Use`, `DealId`, `api/agreements.py`, `Test Conversation Routes (ConversationRouteTests)`, `PaymentStatusExtendedModelTests`, `Test Agreement Routes (AgreementRouteTests)`, `application/agreements.py`, `application/deals.py`, `repositories/fulfillment.py`, `_raise_agreement_error`, `application/documents.py`, `api/fulfillment.py`, `Simulate Deal Flow & Test`, `auth.py`, `User`, `AmendmentTests`, `PaymentIntentRepositoryTests`, `DealRepository`, `api/organizations.py`, `OrganizationCapability`, `Test Organization Directory & Organizations`, `read_deal_route`, `api/payments.py`, `Deal`, `ConversationUseCaseTests`, `Agreement`, `create_counterparty_invitation`, `Test Deal Routes & Identity`, `FulfillmentRouteTests`, `OrganizationId`, `ApprovalDecision`, `api/negotiation.py`, `IdentityBoundaryTests`, `dev.py`, `NegotiationRouteTests`, `application/conversations.py`, `ai.py`, `AISuggestionProviderTests`, `ConversationContractTests`, `auth.py`, `AiContextSelectionTests`, `.has_capability`?**
  _High betweenness centrality (0.109) - this node is a cross-community bridge._
- **Are the 119 inferred relationships involving `ActorContext` (e.g. with `approve_agreement_route()` and `commit_agreement_route()`) actually correct?**
  _`ActorContext` has 119 INFERRED edges - model-reasoned connections that need verification._
- **What connects `syncally`, `PGPASSWORD`, `F1a Curated Repeatable Demo Fixture` to the rest of the system?**
  _48 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Conversations & Test Conversation Use` be split into smaller, more focused modules?**
  _Cohesion score 0.06975308641975309 - nodes in this community are weakly interconnected._
- **Why does `OrganizationId` connect `OrganizationId` to `AIContractError`, `repositories/agreements.py`, `DealId`, `api/agreements.py`, `Test Conversation Routes (ConversationRouteTests)`, `PaymentStatusExtendedModelTests`, `Test Agreement Routes (AgreementRouteTests)`, `application/agreements.py`, `application/deals.py`, `ProposedTerms`, `NegotiationTests`, `_raise_agreement_error`, `application/documents.py`, `Test Outbox Dispatcher & Outbox`, `Test Organization Invitations & Organizations`, `AIContractTests`, `SqlAlchemyCommunicationRepository`, `Visibility`, `User`, `repositories/communications.py`, `AmendmentTests`, `PaymentIntentRepositoryTests`, `NegotiationMigrationTests`, `api/organizations.py`, `OrganizationCapability`, `SqlAlchemyDealRepository`, `Deal`, `ConversationUseCaseTests`, `Agreement`, `InvalidTransition`, `FulfillmentRouteTests`, `Money`, `api/negotiation.py`, `OrganizationRepositoryTests`, `Constraint`, `application/conversations.py`, `ai.py`, `AISuggestionProviderTests`, `ConversationContractTests`, `AiContextSelectionTests`?**
  _High betweenness centrality (0.063) - this node is a cross-community bridge._
- **Are the 65 inferred relationships involving `OrganizationId` (e.g. with `build_trade_terms_from_request()` and `create_reviewed_agreement_draft_route()`) actually correct?**
  _`OrganizationId` has 65 INFERRED edges - model-reasoned connections that need verification._
- **Should `AIContractError` be split into smaller, more focused modules?**
  _Cohesion score 0.14714714714714713 - nodes in this community are weakly interconnected._