# Graph Report - SyncAlly  (2026-11-06)

## Corpus Check
- 310 files · ~274,526 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 13 file(s) not represented in the graph (top: (none) 8, .example 2, .ini 1)

## Summary
- 4840 nodes · 15776 edges · 182 communities (121 shown, 61 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 2052 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `16ae3b2b`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Conversations & Test Conversation Use
- AIContractError
- BaseModel
- SqlAlchemyAgreementRepository
- Test Ai Provider & Ai
- DealId
- repositories/agreements.py
- PaymentNeedsAction
- PaymentWorkItem
- api/agreements.py
- Test Conversation Routes (ConversationRouteTests)
- repositories/payments.py
- Test Agreement Routes (AgreementRouteTests)
- identifiers.py
- process_payment_intent
- ai.py
- NegotiationTests
- Types & Client
- listOrganizations
- VerifiedProviderPaymentState
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
- commit_agreement
- Aisuggestionreview & Suggestionpreview
- SyncAlly Implementation Plan Document
- PaymentProcessingTests
- AgreementCommitTests
- worker.py
- DealDetailPage.tsx
- Paymentstatuspanel & Paymentstatuspanel.Test
- PaymentIntentRepositoryTests
- services
- NegotiationCommand
- build_terms
- DealWorkflow
- Test Dev Routes (DevRoutesTests)
- add_organization_member
- DealWorkflow
- Test Organization Directory & Organizations
- read_deal_route
- DealWorkflowNotification
- SqlAlchemyDealRepository
- PaymentOutboxWorkerTests
- api/payments.py
- Deal
- GmailSMTPInvoiceNotifier
- ApiError
- ConversationUseCaseTests
- application/agreements.py
- Test Migration Lock & Env
- Payment Processing & Test Payment
- 01 Commercial Domain Model &
- create_counterparty_invitation
- Test Deal Routes & Identity
- App.test.tsx
- Compose.Yaml (volumes)
- repositories/payment_processing.py
- FulfillmentRouteTests
- api/organizations.py
- DealId
- Test Payment Reconciliation & Intent
- Money
- PersistentDemoSeedTests
- AgreementReview.tsx
- Createdealpage & Createdealpage.Test
- api/negotiation.py
- OrganizationRepositoryTests
- IdentityBoundaryTests
- 13 Postgres Temporal & 14
- Tsconfig (tsconfig.json)
- Test Paypal Webhooks (FakeWebhookVerifier)
- Test Counterparty Onboarding Migration &
- Test Communication Repositories (MessageIdempotencyPostgresTests)
- Test Operations & Test Outbox
- AmendmentTests
- environment
- Main & Test Identity Boundary
- dev.py
- Human Bilateral Amendment Workflow
- ApiError
- Test Organization Index Migration (OrganizationIndexPostgresMigrationTests)
- Server-Enforced Capability Matrix
- 0004_communication_sources_and_scope_indexes.py
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
- get_current_actor
- FakeDealRepository
- healthcheck
- AddMessageRequest
- DealWorkflowInput
- AiContextSelectionTests
- amendment.py
- Final Gates and Truthful Completion Specification
- Skill (Repo Idea Thinker Skill)
- refresh_access_token
- Vite Env.D (ImportMeta)
- temporal-schema
- check_milestone_trigger_eligibility
- Index (Frontend HTML Root Document)
- Pyproject (syncally)
- Customer journey: buyer and seller
- bounded_decimal
- sqlalchemy
- ExtractedFact
- application/deals.py
- Free single-VM deployment
- env.py
- repositories/fulfillment.py
- AI Provider Boundary Specification
- api/fulfillment.py
- Four-Dimension Profile Collections
- Two-Party Judge Journey
- volumes
- contracts.py
- setup-temporal-postgres.sh
- FulfillmentMigrationTests
- ProviderInvoiceUniqueMigrationTests
- unittest
- Visibility
- MigrationConfigTests
- CollectionSchemaMigrationTests
- create-temporal-namespace.sh
- postgres-init.sh
- SqlAlchemyNegotiationRepository
- CredentialsRequest
- .__call__
- NegotiationCommand
- database_health
- MilestonePaymentsMigrationTests
- record_paypal_webhook_event
- NegotiationMigrationTests
- OrganizationCapability
- _is_duplicate_membership_error
- HealthRouteTests
- PostgresDispatcherTests

## God Nodes (most connected - your core abstractions)
1. `ActorContext` - 265 edges
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

## Communities (182 total, 61 thin omitted)

### Community 0 - "Conversations & Test Conversation Use"
Cohesion: 0.07
Nodes (44): add_message_route(), AISuggestionRequest, clarify_fact_route(), confirm_fact_route(), ConstraintResponse, correct_fact_route(), CorrectFactRequest, create_fact_route() (+36 more)

### Community 1 - "AIContractError"
Cohesion: 0.12
Nodes (13): AIContractError, AIValidationClaim, _check_keys(), _decimal(), _required_string(), scope_extracted_facts(), _validate_decimal(), _validate_fact_value() (+5 more)

### Community 3 - "SqlAlchemyAgreementRepository"
Cohesion: 0.12
Nodes (10): AgreementAccessDenied, AgreementNotFound, AgreementVersionConflict, ProposalNotFound, StaleAgreementVersion, UnauthorizedApproval, WrongTermsHash, AmendmentConflict (+2 more)

### Community 4 - "Test Ai Provider & Ai"
Cohesion: 0.11
Nodes (12): extract_facts_from_context(), ConfiguredAIProvider, respond(), respond(), respond(), respond(), respond(), respond() (+4 more)

### Community 5 - "DealId"
Cohesion: 0.12
Nodes (6): ConstraintId, ConversationId, MessageId, constraint(), message(), CommunicationRepositoryTests

### Community 6 - "repositories/agreements.py"
Cohesion: 0.07
Nodes (37): _accept_invitation(), AuditEventDraft, OutboxEventDraft, NotificationKind, _clear_fixture(), _create_fixture(), _delete_scoped(), DemoIdentity (+29 more)

### Community 7 - "PaymentNeedsAction"
Cohesion: 0.08
Nodes (10): receive_paypal_invoice_webhook(), payment_invoice_number(), PaymentOutcomeUnknown, PaymentRetryableError, _has_excess_currency_precision(), PayPalSandboxInvoiceProvider, _provider_request_id(), _send_request() (+2 more)

### Community 8 - "PaymentWorkItem"
Cohesion: 0.12
Nodes (9): get_paypal_webhook_configuration(), PaymentInvoiceLookup, PaymentInvoiceRequest, PaymentNeedsAction, PaymentWorkItem, GmailSettings, PayPalSettings, OfflineDemoInvoiceProvider (+1 more)

### Community 9 - "api/agreements.py"
Cohesion: 0.06
Nodes (40): AgreementVersionResponse, AmendmentImpactResponse, ApprovalResponse, approve_agreement_route(), commit_agreement_route(), CommitAgreementRequest, compare_agreements_route(), create_agreement_draft_route() (+32 more)

### Community 10 - "Test Conversation Routes (ConversationRouteTests)"
Cohesion: 0.10
Nodes (3): ConversationRouteTests, respond(), send()

### Community 11 - "repositories/payments.py"
Cohesion: 0.05
Nodes (15): authorize_payment_intent(), AuthorizePaymentIntentCommand, DuplicateActivePaymentIntent, PaymentIntentAuthorizationOutcome, PaymentIntentCommandMismatch, PaymentIntentRepository, PaymentMilestoneNotFound, PaymentModeChanged (+7 more)

### Community 14 - "process_payment_intent"
Cohesion: 0.09
Nodes (9): PaymentInvoiceNotifier, PaymentInvoiceProvider, PaymentInvoiceReconciliation, PaymentProcessingRepository, process_payment_intent(), reconcile_payment_intent(), _request_id_retry_window_expired(), require_payment_provider() (+1 more)

### Community 15 - "ai.py"
Cohesion: 0.09
Nodes (6): AIConfigurationError, AIProviderError, FactExtractionRequest, ProposalDraftRequest, ProposedTerms, FakeWebhookVerifier

### Community 16 - "NegotiationTests"
Cohesion: 0.22
Nodes (3): EvidenceReference, negotiate_in_transaction(), NegotiationTests

### Community 17 - "Types & Client"
Cohesion: 0.05
Nodes (60): describeDetail(), getDealMessageExistence(), isAbortError(), isRecord(), readErrorDetail(), AgreementApproval, AgreementComparison, AgreementEvidence (+52 more)

### Community 18 - "listOrganizations"
Cohesion: 0.07
Nodes (43): dependencies, react@^19.3.0, react-dom@^19.3.0, three@^0.186.1, login(), InvitationAcceptance, App(), handleInvitationAccepted() (+35 more)

### Community 20 - "application/documents.py"
Cohesion: 0.07
Nodes (23): CommercialDocumentDraftResponse, get_commercial_document_draft_route(), get_trade_pack_route(), AgreementAlreadyCommitted, DuplicateApproval, AgreementNotCommitted, CommercialDocumentDraft, _display() (+15 more)

### Community 21 - "Test Outbox Dispatcher & Outbox"
Cohesion: 0.12
Nodes (7): build_deal_workflow_id(), dispatch_outbox_event(), PendingOutboxEvent, dispatch_one_pending_event(), FakeDealWorkflowStarter, OutboxDispatcherTests, start_deal_workflow()

### Community 22 - "Simulate Deal Flow & Test"
Cohesion: 0.07
Nodes (9): ci_deal_flow_hook(), DealFlowContext, DealFlowSimulator, _is_live_backend_healthy(), run_simulation(), SimulationError, StepRecord, TerminalFormatter (+1 more)

### Community 23 - "Test Organization Invitations & Organizations"
Cohesion: 0.16
Nodes (5): accept_invitation(), AcceptInvitationRequest, create_organization_invitation(), CreateInvitationRequest, OrganizationInvitationTests

### Community 24 - "SqlAlchemyCommunicationRepository"
Cohesion: 0.08
Nodes (10): can_view_message(), message_fingerprint(), Conversation, Message, CommunicationScopeError, _conversation_to_domain(), _is_unique_violation(), _message_to_domain() (+2 more)

### Community 25 - "Package & Vite.Config"
Cohesion: 0.06
Nodes (47): devDependencies, eslint@^10.13.0, @eslint/js@^10.0.1, eslint-plugin-react-hooks@^7.1.1, eslint-plugin-react-refresh@^0.4.20, globals@^17.13.0, happy-dom@^21.0.3, @testing-library/dom@^10.4.1 (+39 more)

### Community 26 - "client.test.ts"
Cohesion: 0.10
Nodes (21): API_REQUEST_TIMEOUT_MS, listOrganizationMembers(), revokeOrganizationMember(), CREATED_MESSAGE, fetchMock, lastRequest(), sentBody(), updateMemberPermissions() (+13 more)

### Community 27 - "Dealconversationreview & Dealconversationreview.Test"
Cohesion: 0.07
Nodes (39): createDealMessage(), importDealThread(), listDealFacts(), previewDealThreadImport(), updateFactVisibility(), areFactsEqual(), ConversationState, DealConversationReview() (+31 more)

### Community 28 - "Skill & Skill.Md"
Cohesion: 0.04
Nodes (43): API and Database Engineer Skill, API Design and Contract Semantics, Data Integrity and Invariant Enforcement, Query Performance and Projection Optimization, Schema Migration and Backward Compatibility, Transaction Boundaries and Atomicity, Archify Diagrammer Skill, Archify CLI Global Tool (+35 more)

### Community 30 - "User"
Cohesion: 0.13
Nodes (5): _compute_effective_capabilities(), revoke_organization_member(), update_member_permissions(), UpdateMemberPermissionsRequest, OrganizationPermissionsTests

### Community 31 - "DealDetailPage.test.tsx"
Cohesion: 0.08
Nodes (31): getDealFulfillment(), recordDealFulfillment(), FulfillmentSnapshot, FulfillmentStage, DEAL, flushMicrotasks(), mockedApiRequest, mockedCreateDealMessage (+23 more)

### Community 32 - "commit_agreement"
Cohesion: 0.12
Nodes (11): AuditRepository, commit_agreement(), ObligationRepository, OutboxRepository, PaymentMilestoneRepository, build_obligations(), build_payment_milestones(), ObligationDraft (+3 more)

### Community 33 - "Aisuggestionreview & Suggestionpreview"
Cohesion: 0.09
Nodes (39): correctDealFact(), createDealFact(), draftDealProposal(), getNegotiation(), negotiateDeal(), reviewDealFact(), suggestDealFacts(), AIProvenance (+31 more)

### Community 34 - "SyncAlly Implementation Plan Document"
Cohesion: 0.16
Nodes (13): SyncAlly Architecture Document, System Topology and Ownership Boundaries, Temporal Worker and Outbox Architecture, Acceptance Criteria Verification Matrix, SyncAlly Implementation Plan Document, Issue #77 Architecture Contracts, Stage Lifecycle Roadmap, Frontend API Client and Authoritative State (+5 more)

### Community 35 - "PaymentProcessingTests"
Cohesion: 0.13
Nodes (6): FakeInvoiceProvider, FakeProcessingRepository, PaymentProcessingTests, get_invoice_reconciliation(), _request(), _work_item()

### Community 36 - "AgreementCommitTests"
Cohesion: 0.09
Nodes (8): CommitAgreementCommand, record_approval(), RecordApprovalCommand, commit_agreement_in_transaction(), record_approval_in_transaction(), AgreementCommitTests, LocalWorkflowSmokeTests, commit_once()

### Community 37 - "worker.py"
Cohesion: 0.05
Nodes (26): _connect_with_retry(), main(), run_forever(), main(), run_forever(), main(), is_permanent_rpc_error(), configure_logging() (+18 more)

### Community 38 - "DealDetailPage.tsx"
Cohesion: 0.05
Nodes (46): getDeal(), listDealMessages(), Deal, NegotiationView, AgreementReviewProps, DealConstellation(), DealConstellationProps, DealConversationReviewProps (+38 more)

### Community 39 - "Paymentstatuspanel & Paymentstatuspanel.Test"
Cohesion: 0.09
Nodes (32): authorizeDealPayment(), getCurrentAgreement(), listDealPaymentMilestones(), listPaymentStatuses(), previewDealPayment(), PaymentIntentStatus, formatCountdown(), parseTimestamp() (+24 more)

### Community 40 - "PaymentIntentRepositoryTests"
Cohesion: 0.10
Nodes (7): queue_simulated_reconciliation(), require_simulation_scope(), authorize_payment_intent_in_transaction(), _is_idempotency_key_violation(), _is_one_active_per_milestone_violation(), _violated_constraint_name(), PaymentIntentRepositoryTests

### Community 41 - "services"
Cohesion: 0.09
Nodes (32): build, depends_on, restart, context, dockerfile, migrate, temporal-namespace, build (+24 more)

### Community 42 - "NegotiationCommand"
Cohesion: 0.12
Nodes (8): create_reviewed_agreement_draft(), CreateReviewedAgreementDraftCommand, ProposalBase, create_reviewed_agreement_draft_in_transaction(), NegotiationPostgresRaceTests, failing(), succeed(), replace_candidate()

### Community 43 - "build_terms"
Cohesion: 0.14
Nodes (10): NegotiationSession, NegotiationSubmissionOutcome, Proposal, ProposalStatus, NegotiationSessionId, ProposalId, build_proposal(), build_terms() (+2 more)

### Community 44 - "DealWorkflow"
Cohesion: 0.17
Nodes (3): DealWorkflow, DealWorkflowUnitTests, run()

### Community 46 - "add_organization_member"
Cohesion: 0.12
Nodes (8): _active_admin_membership(), add_organization_member(), AddOrganizationMemberRequest, create_organization(), CreateOrganizationRequest, get_optional_actor(), repair_organization_finance_route(), OrganizationOnboardingTests

### Community 47 - "DealWorkflow"
Cohesion: 0.29
Nodes (3): DealWorkflowResult, DealWorkflowTests, new_notification()

### Community 48 - "Test Organization Directory & Organizations"
Cohesion: 0.13
Nodes (4): _case_insensitive_prefix(), _escape_like(), value(), OrganizationDirectoryTests

### Community 49 - "read_deal_route"
Cohesion: 0.14
Nodes (6): CreateDealRequest, DealResponse, DealSummaryResponse, list_deals_route(), read_deal_route(), _viewer_role()

### Community 50 - "DealWorkflowNotification"
Cohesion: 0.13
Nodes (7): WorkflowStartError, WorkflowStartOutcome, WorkflowStartPermanentError, WorkflowStartTransientError, DealWorkflowNotification, TemporalDealWorkflowStarter, TemporalAdapterTests

### Community 51 - "SqlAlchemyDealRepository"
Cohesion: 0.16
Nodes (3): _active_participation(), SqlAlchemyDealRepository, DealRepositoryTests

### Community 52 - "PaymentOutboxWorkerTests"
Cohesion: 0.07
Nodes (15): _build_in_process_client(), dispatch_payment(), session_factory(), PaymentIntentStatus, claim_next_payment_event(), _claim_statement(), _ClaimedPaymentEvent, dispatch_one_payment_event() (+7 more)

### Community 53 - "api/payments.py"
Cohesion: 0.07
Nodes (25): authorize_payment_route(), AuthorizePaymentRequest, AuthorizePaymentResponse, _check_milestone_delivery_confirmed(), get_payment_status_repository(), list_payment_milestones_route(), list_payment_statuses_route(), MilestoneAllocationResponse (+17 more)

### Community 54 - "Deal"
Cohesion: 0.06
Nodes (16): _to_response(), DealWorkflowState, load_deal_workflow_state(), parse_workflow_uuid(), WorkflowAgreementRepository, WorkflowDealNotFound, WorkflowDealRepository, Deal (+8 more)

### Community 55 - "GmailSMTPInvoiceNotifier"
Cohesion: 0.08
Nodes (6): PaymentInvoiceNotice, main(), canonical_decimal(), GmailSMTPInvoiceNotifier, _FakeSMTP, GmailSMTPInvoiceNotifierTests

### Community 56 - "ApiError"
Cohesion: 0.10
Nodes (19): ApiError, getOrganization(), listDeals(), DealSummary, ViewerRole, mockedApiRequest, mockedLogin, DealsPage() (+11 more)

### Community 57 - "ConversationUseCaseTests"
Cohesion: 0.28
Nodes (4): AddMessageCommand, send(), ConversationUseCaseTests, write_message()

### Community 58 - "application/agreements.py"
Cohesion: 0.08
Nodes (10): AgreementRepository, assess_amendment_impact(), create_agreement_draft(), CreateAgreementDraftCommand, propose_amendment(), withdraw_amendment(), WithdrawAmendmentCommand, create_agreement_draft_in_transaction() (+2 more)

### Community 59 - "Test Migration Lock & Env"
Cohesion: 0.12
Nodes (8): run_migrations_online(), serialize_migrations(), _make_postgres_connection(), _make_sqlite_connection(), MigrationLockTests, simulated_migration(), PostgresRealAdvisoryLockTests, worker()

### Community 60 - "Payment Processing & Test Payment"
Cohesion: 0.18
Nodes (4): PaymentInvoiceLineItem, SqlAlchemyPaymentProcessingRepository, transition(), transition()

### Community 61 - "01 Commercial Domain Model &"
Cohesion: 0.07
Nodes (19): AgreementVersion Aggregate, Append-Only AuditEvent Ledger, Commercial Constraint and Provenance, Deal Aggregate, Organization and Membership Entities, PaymentMilestone and Obligation, Proposal Aggregate and Terms Hash, Temporal Deal Workflow (+11 more)

### Community 62 - "create_counterparty_invitation"
Cohesion: 0.15
Nodes (6): create_counterparty_invitation(), CreateCounterpartyInvitationRequest, _decode_invitation_token(), OnboardingConcurrencyCases, OnboardingPostgresConcurrencyTests, OnboardingSQLiteConcurrencyTests

### Community 64 - "App.test.tsx"
Cohesion: 0.11
Nodes (28): getCommercialDocumentDraft(), listOrganizations(), clearAccessToken(), getAccessToken(), setTokens(), TokenResponse, mockedApiRequest, mockedCreateOrganization (+20 more)

### Community 65 - "Compose.Yaml (volumes)"
Cohesion: 0.09
Nodes (22): POSTGRES_DB, POSTGRES_PASSWORD, POSTGRES_USER, interval, retries, test, timeout, environment (+14 more)

### Community 66 - "repositories/payment_processing.py"
Cohesion: 0.10
Nodes (11): PaymentIntent, VerifiedProviderPaymentState, VerifiedProviderPaymentStatus, InvalidTransition, PaymentIntentId, WebhookEvent, simulation_state(), _restore_domain_intent() (+3 more)

### Community 68 - "api/organizations.py"
Cohesion: 0.09
Nodes (16): AcceptInvitationResponse, ContactResponse, CounterpartyInvitationResponse, _create_invitation_token(), _deal_awaiting_counterparty(), get_organization_profile_route(), get_organization_route(), InvitationResponse (+8 more)

### Community 69 - "DealId"
Cohesion: 0.12
Nodes (13): Agreement, AgreementStatus, Approval, PaymentMilestone, AgreementId, AgreementVersionId, DealId, PaymentMilestoneId (+5 more)

### Community 71 - "Money"
Cohesion: 0.10
Nodes (20): build_trade_terms_from_request(), _money(), _parse_money(), PaymentObligationAllocation, PaymentTerm, ShipmentItemAllocation, ShipmentTerm, TradeLineItem (+12 more)

### Community 72 - "PersistentDemoSeedTests"
Cohesion: 0.05
Nodes (17): fixture_id(), DemoCollisionError, initialize_offline_database(), main(), seed_demo_data(), _acquire_lock(), _is_demo_deal(), lock_demo_deal_creation() (+9 more)

### Community 73 - "AgreementReview.tsx"
Cohesion: 0.08
Nodes (47): acceptInvitation(), apiBaseUrl(), apiRequest(), commitAgreementVersion(), compareAgreementVersions(), createAgreementFromReviewedTerms(), getAgreementHistory(), getAgreementVersion() (+39 more)

### Community 74 - "Createdealpage & Createdealpage.Test"
Cohesion: 0.16
Nodes (14): createCounterpartyInvitation(), createDeal(), CreateDealPage(), handleSubmit(), CreateDealPageProps, describeCreateError(), describeError(), DirectoryItem (+6 more)

### Community 75 - "api/negotiation.py"
Cohesion: 0.12
Nodes (14): BaseRequest, CandidateRequest, EvidenceRequest, HistoryResponse, NegotiationRequest, NegotiationResponse, NegotiationResult, ProposalResponse (+6 more)

### Community 76 - "OrganizationRepositoryTests"
Cohesion: 0.06
Nodes (22): update_organization_profile_route(), ContactVisibility, _normalize_string(), Organization, OrganizationContact, OrganizationProfile, OrganizationStatus, OrganizationVerificationStatus (+14 more)

### Community 77 - "IdentityBoundaryTests"
Cohesion: 0.13
Nodes (3): _is_weak_jwt_secret(), Settings, IdentityBoundaryTests

### Community 78 - "13 Postgres Temporal & 14"
Cohesion: 0.14
Nodes (9): Organization-Scoped Routing Policy, Durable Scoped Reminder Scheduling, Isolated PostgreSQL Migration and Constraint Testing, PostgreSQL and Temporal Verification Specification, Temporal Worker Crash Replay and Recovery, PayPal Sandbox Lifecycle Verification, PayPal Sandbox Specification F11b, Signature-Verified Webhook and Authenticated Reconciliation (+1 more)

### Community 79 - "Tsconfig (tsconfig.json)"
Cohesion: 0.11
Nodes (17): compilerOptions, allowImportingTsExtensions, jsx, lib, module, moduleDetection, moduleResolution, noEmit (+9 more)

### Community 81 - "Test Counterparty Onboarding Migration &"
Cohesion: 0.12
Nodes (4): create_database_engine(), CounterpartyOnboardingMigrationTests, DemoFixtureMigrationTests, NegotiationSqliteRaceTests

### Community 82 - "Test Communication Repositories (MessageIdempotencyPostgresTests)"
Cohesion: 0.20
Nodes (5): MessageIdempotencyPostgresTests, _find_conversation(), _find_keyed_message(), rendezvous(), wait_for()

### Community 83 - "Test Operations & Test Outbox"
Cohesion: 0.27
Nodes (4): captured_output(), SafeOperationsTests, exercise(), failed_db()

### Community 84 - "AmendmentTests"
Cohesion: 0.21
Nodes (3): ProposeAmendmentCommand, propose_amendment_in_transaction(), AmendmentTests

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
Cohesion: 0.06
Nodes (32): addOrganizationMember(), createOrganization(), getOrganizationProfile(), updateOrganizationProfile(), ContactVisibility, Organization, OrganizationContact, COUNTRY_NAMES (+24 more)

### Community 92 - "0004_communication_sources_and_scope_indexes.py"
Cohesion: 0.60
Nodes (4): _create_scope_index(), downgrade(), _drop_scope_index(), upgrade()

### Community 94 - "Constraint"
Cohesion: 0.08
Nodes (4): Constraint, FakeCommunicationRepository, FakeCommunicationRepository, FakeCommunicationRepository

### Community 95 - "infrastructure/outbox.py"
Cohesion: 0.19
Nodes (6): DealWorkflowStarter, OutboxDispatchResult, apply_dispatch_result(), claim_next_pending_event(), _claim_statement(), dispatch_pending_outbox_events()

### Community 96 - "application/conversations.py"
Cohesion: 0.06
Nodes (19): add_message(), can_view_constraint(), CommunicationRepository, ConstraintRepository, correct_constraint(), create_manual_constraint(), deal_has_any_message(), import_thread() (+11 more)

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
Cohesion: 0.09
Nodes (11): get_ai_suggestion_provider(), AISuggestionProvider, draft_proposal(), draft_proposal_from_context(), extract_facts(), FactExtractionResult, _list_all_constraints_for_owner(), ProposalDraftResult (+3 more)

### Community 104 - "openai.py"
Cohesion: 0.12
Nodes (14): AIPermanentError, AITransientError, parse_extracted_facts(), parse_proposed_terms(), _provider_context(), AiContext, _json(), _object() (+6 more)

### Community 105 - "AISuggestionProviderTests"
Cohesion: 0.11
Nodes (5): AIRetryPolicy, call_with_bounded_retry(), DeterministicFakeAIProvider, AISuggestionProviderTests, extract_facts()

### Community 106 - "x-app-environment"
Cohesion: 0.10
Nodes (21): x-app-environment, AI_PROVIDER, APP_ENV, DATABASE_URL, DEBUG, GMAIL_APP_PASSWORD, GMAIL_FROM_EMAIL, GMAIL_SMTP_USERNAME (+13 more)

### Community 108 - "environment"
Cohesion: 0.12
Nodes (20): environment, BIND_ON_IP, DB, DB_PORT, DBNAME, POSTGRES_DB, POSTGRES_PASSWORD, POSTGRES_PWD (+12 more)

### Community 111 - "ConversationContractTests"
Cohesion: 0.11
Nodes (5): ConcurrentConstraintUpdate, confirm_constraint(), ConstraintNotFound, ConversationContractTests, FakeConstraintRepository

### Community 112 - "get_current_actor"
Cohesion: 0.13
Nodes (13): create_refresh_token(), _decode_token(), _development_actor(), development_login(), _encode_access_token(), get_current_actor(), _issue_tokens(), login() (+5 more)

### Community 113 - "FakeDealRepository"
Cohesion: 0.22
Nodes (3): DealAuthorizationTests, _domain_deal(), FakeDealRepository

### Community 114 - "healthcheck"
Cohesion: 0.16
Nodes (18): healthcheck, healthcheck, image, restart, volumes, temporal-schema, interval, retries (+10 more)

### Community 115 - "AddMessageRequest"
Cohesion: 0.19
Nodes (3): AddMessageRequest, CreateFactRequest, AddMessageRequestTests

### Community 116 - "DealWorkflowInput"
Cohesion: 0.12
Nodes (7): DealWorkflowInput, _require_uuid(), new_workflow_input(), RefreshActivity, RefreshCall, RefreshDealStateActivityTests, factory()

### Community 118 - "amendment.py"
Cohesion: 0.14
Nodes (9): compare_agreement_terms(), AmendmentAlreadyCommitted, AmendmentError, AmendmentImpact, assess_amendment_impact(), FulfillmentObligationImpact, PaymentMilestoneImpact, StalePriorVersion (+1 more)

### Community 119 - "Final Gates and Truthful Completion Specification"
Cohesion: 0.20
Nodes (9): Evidence-Free Projection and Safety Bounds, F12 Trade Pack Handoff Document, Trade Pack Export Contract, Browser Verification Specification, ZIP HTML and Print Export Verification, Two-Party Isolated Browser Testing, Final Gates and Truthful Completion Specification, Full Gate Verification Suite (+1 more)

### Community 120 - "Skill (Repo Idea Thinker Skill)"
Cohesion: 0.50
Nodes (3): Repo Idea Thinker Skill, Repository-Grounded Ideation Discipline, Idea Quality Standards and Lightweight Validation

### Community 122 - "refresh_access_token"
Cohesion: 0.15
Nodes (5): _as_utc(), _hash_refresh_token(), refresh_access_token(), RefreshRequest, RefreshToken

### Community 134 - "temporal-schema"
Cohesion: 0.20
Nodes (10): condition, db, depends_on, temporal-schema, command, depends_on, entrypoint, image (+2 more)

### Community 139 - "Customer journey: buyer and seller"
Cohesion: 0.29
Nodes (6): Customer contract, Customer journey: buyer and seller, Evidence and limits, Implementation constraints discovered during task mapping, Outcome, Task graph

### Community 140 - "bounded_decimal"
Cohesion: 0.08
Nodes (7): _normalized_text(), _require_decimal(), InvariantViolation, bounded_decimal(), currency_precision(), has_excess_currency_precision(), BoundedDecimalTests

### Community 141 - "sqlalchemy"
Cohesion: 0.03
Nodes (36): upgrade(), uuid_column(), upgrade(), upgrade(), upgrade(), upgrade(), downgrade(), upgrade() (+28 more)

### Community 142 - "ExtractedFact"
Cohesion: 0.14
Nodes (6): ExtractedFact, FactField, SourceReference, DemoAISuggestionProvider, _is_ambiguous_numeric_term(), _is_delivery_date_context()

### Community 143 - "application/deals.py"
Cohesion: 0.08
Nodes (10): create_deal_route(), get_deal_repository(), _both_organizations_active(), create_deal(), CreateDealCommand, DealAccessDenied, DealRepository, list_deals() (+2 more)

### Community 144 - "Free single-VM deployment"
Cohesion: 0.33
Nodes (5): 1. Provision the VM and DNS, 2. Configure secrets, 3. Start the stack, Free single-VM deployment, Updating and operating

### Community 146 - "repositories/fulfillment.py"
Cohesion: 0.15
Nodes (9): FulfillmentUnavailable, bounded_quantity(), quantity_text(), _scaled(), _quantity(), _record(), _request_hash(), _scaled_total() (+1 more)

### Community 147 - "AI Provider Boundary Specification"
Cohesion: 0.53
Nodes (4): F2 AI Configuration and Provider Boundary, AI Provider Boundary Specification, AI Resilience and Retry Policy, AISuggestionProvider Contract

### Community 148 - "api/fulfillment.py"
Cohesion: 0.12
Nodes (18): _event_response(), FulfillmentEventResponse, FulfillmentSnapshotResponse, get_fulfillment_repository(), _raise_fulfillment_error(), read_fulfillment_route(), record_fulfillment_route(), _snapshot_response() (+10 more)

### Community 151 - "volumes"
Cohesion: 0.50
Nodes (4): volumes, caddy_config, caddy_data, postgres_data

### Community 152 - "contracts.py"
Cohesion: 0.18
Nodes (11): _contains_numeric_token(), _contains_token(), _date_value_is_present(), _fact_value_is_supported_by_quote(), _flexible_whitespace_pattern(), _number_with_currency_is_present(), _number_with_unit_is_present(), _numeric_pattern() (+3 more)

### Community 153 - "setup-temporal-postgres.sh"
Cohesion: 0.67
Nodes (3): PGPASSWORD, setup-temporal-postgres.sh script, update_database_schema()

### Community 156 - "unittest"
Cohesion: 0.11
Nodes (6): CommunicationMigrationTests, MessageIdempotencyMigrationTests, InvitingPartyMigrationTests, OrganizationIndexMigrationTests, OutboxDispatchMigrationTests, PaymentCreateStartedMigrationTests

### Community 157 - "Visibility"
Cohesion: 0.20
Nodes (7): persist_fact_candidates(), CreateManualConstraintCommand, ConstraintKind, ConstraintStatus, MessageSourceType, Visibility, DatabaseEngineTests

### Community 162 - "SqlAlchemyNegotiationRepository"
Cohesion: 0.25
Nodes (3): NegotiationConflict, SqlAlchemyNegotiationRepository, projection()

### Community 164 - "CredentialsRequest"
Cohesion: 0.25
Nodes (3): CredentialsRequest, fail(), scalar()

### Community 166 - "NegotiationCommand"
Cohesion: 0.42
Nodes (3): negotiate(), NegotiationCommand, NegotiationRepository

### Community 175 - "OrganizationCapability"
Cohesion: 0.12
Nodes (8): OrganizationCapability, OrganizationMember, OrganizationMemberRole, OrganizationMemberStatus, resolve_effective_capabilities(), resolve_actor(), _membership_to_domain(), SqlAlchemyOrganizationMemberRepository

## Knowledge Gaps
- **48 isolated node(s):** `syncally`, `PGPASSWORD`, `F1a Curated Repeatable Demo Fixture`, `Editorial Dark Theme Design System`, `ZIP HTML and Print Export Verification` (+43 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1466 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **61 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ActorContext` connect `Test Deal Routes & Identity` to `Conversations & Test Conversation Use`, `DealId`, `repositories/agreements.py`, `api/agreements.py`, `Test Conversation Routes (ConversationRouteTests)`, `repositories/payments.py`, `Test Agreement Routes (AgreementRouteTests)`, `identifiers.py`, `sqlalchemy`, `application/deals.py`, `ai.py`, `repositories/fulfillment.py`, `application/documents.py`, `api/fulfillment.py`, `Simulate Deal Flow & Test`, `Test Organization Invitations & Organizations`, `SqlAlchemyCommunicationRepository`, `auth.py`, `User`, `Visibility`, `PaymentIntentRepositoryTests`, `add_organization_member`, `OrganizationCapability`, `Test Organization Directory & Organizations`, `read_deal_route`, `api/payments.py`, `ConversationUseCaseTests`, `application/agreements.py`, `create_counterparty_invitation`, `FulfillmentRouteTests`, `api/organizations.py`, `DealId`, `api/negotiation.py`, `OrganizationRepositoryTests`, `IdentityBoundaryTests`, `Test Communication Repositories (MessageIdempotencyPostgresTests)`, `dev.py`, `NegotiationRouteTests`, `application/conversations.py`, `ai.py`, `AISuggestionProviderTests`, `ConversationContractTests`, `get_current_actor`, `FakeDealRepository`, `AiContextSelectionTests`?**
  _High betweenness centrality (0.117) - this node is a cross-community bridge._
- **Are the 118 inferred relationships involving `ActorContext` (e.g. with `approve_agreement_route()` and `commit_agreement_route()`) actually correct?**
  _`ActorContext` has 118 INFERRED edges - model-reasoned connections that need verification._
- **What connects `syncally`, `PGPASSWORD`, `F1a Curated Repeatable Demo Fixture` to the rest of the system?**
  _48 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Conversations & Test Conversation Use` be split into smaller, more focused modules?**
  _Cohesion score 0.0689551339957844 - nodes in this community are weakly interconnected._
- **Why does `OrganizationId` connect `OrganizationRepositoryTests` to `AIContractError`, `SqlAlchemyAgreementRepository`, `DealId`, `repositories/agreements.py`, `api/agreements.py`, `Test Conversation Routes (ConversationRouteTests)`, `repositories/payments.py`, `bounded_decimal`, `identifiers.py`, `Test Agreement Routes (AgreementRouteTests)`, `ai.py`, `application/deals.py`, `NegotiationTests`, `application/documents.py`, `Test Outbox Dispatcher & Outbox`, `SqlAlchemyCommunicationRepository`, `contracts.py`, `Visibility`, `User`, `commit_agreement`, `SqlAlchemyNegotiationRepository`, `AgreementCommitTests`, `PaymentIntentRepositoryTests`, `build_terms`, `NegotiationMigrationTests`, `OrganizationCapability`, `SqlAlchemyDealRepository`, `Deal`, `ConversationUseCaseTests`, `create_counterparty_invitation`, `repositories/payment_processing.py`, `FulfillmentRouteTests`, `api/organizations.py`, `DealId`, `Money`, `api/negotiation.py`, `AmendmentTests`, `Constraint`, `application/conversations.py`, `AISuggestionProviderTests`, `ConversationContractTests`, `FakeDealRepository`, `AiContextSelectionTests`?**
  _High betweenness centrality (0.068) - this node is a cross-community bridge._
- **Are the 65 inferred relationships involving `OrganizationId` (e.g. with `build_trade_terms_from_request()` and `create_reviewed_agreement_draft_route()`) actually correct?**
  _`OrganizationId` has 65 INFERRED edges - model-reasoned connections that need verification._
- **Should `AIContractError` be split into smaller, more focused modules?**
  _Cohesion score 0.1184939091915836 - nodes in this community are weakly interconnected._