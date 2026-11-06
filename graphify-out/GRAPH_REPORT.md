# Graph Report - SyncAlly  (2026-11-06)

## Corpus Check
- 294 files · ~247,904 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 8 file(s) not represented in the graph (top: (none) 4, .example 1, .ini 1)

## Summary
- 4430 nodes · 14555 edges · 172 communities (111 shown, 61 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 1916 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `5e8452d9`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Conversations & Test Conversation Use
- AIContractError
- BaseModel
- .add
- Test Ai Provider & Ai
- DealId
- Seed Demo & Deals
- PaymentNeedsAction
- PaymentNeedsAction
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
- DomainError
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
- application/agreements.py
- Aisuggestionreview & Suggestionpreview
- SyncAlly Implementation Plan Document
- PaymentProcessingTests
- AgreementCommitTests
- payment_outbox.py
- OrganizationCapability
- Paymentstatuspanel & Paymentstatuspanel.Test
- Test Payment Intent Repository &
- api/fulfillment.py
- ProposedTerms
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
- Organization
- load_deal_workflow_state
- canonical_decimal
- Agreementreview & Client
- _is_duplicate_membership_error
- Test Workflow Activities & Activities
- Test Migration Lock & Env
- Payment Processing & Test Payment
- 01 Commercial Domain Model &
- create_counterparty_invitation
- Test Deal Routes & Identity
- Test Identity Boundary & Config
- Compose.Yaml (volumes)
- InvalidTransition
- AddMessageRequest
- Session
- contracts.py
- Test Payment Reconciliation & Intent
- Money
- PersistentDemoSeedTests
- AgreementVersionId
- Createdealpage & Createdealpage.Test
- Negotiation (BaseRequest)
- SqlAlchemyAgreementRepository
- ConversationUseCaseTests
- 13 Postgres Temporal & 14
- Tsconfig (tsconfig.json)
- Test Paypal Webhooks (FakeWebhookVerifier)
- Test Counterparty Onboarding Migration &
- Test Communication Repositories (MessageIdempotencyPostgresTests)
- Test Operations & Test Outbox
- create_worker
- ExtractedFact
- Main & Test Identity Boundary
- demo_lifecycle.py
- Human Bilateral Amendment Workflow
- react
- Test Organization Index Migration (OrganizationIndexPostgresMigrationTests)
- Server-Enforced Capability Matrix
- vitest
- Test Negotiation (NegotiationRouteTests)
- Constraint
- api/deals.py
- application/conversations.py
- Test Database (DatabasePersistenceTests)
- Master Execution Contract
- 0005 Conversation Party Unique (Enforce
- Main (Request)
- Safe Operations and Recovery Guide
- authorize_payment_intent
- openai.py
- Test Negotiation Migration (NegotiationMigrationTests)
- Test Payment Mode Migration (PaymentModeMigrationTests)
- OnboardingWizard.tsx
- Test Communication Migration (ConversationPartyUniquenessMigrationTests)
- .test_rejected_closure_keeps_approved_agreement_committable
- ConversationContractTests
- queue_simulated_reconciliation
- _is_one_active_per_milestone_violation
- InvalidTransition
- TradeTerms
- create_refresh_token
- AiContextSelectionTests
- Final Gates and Truthful Completion Specification
- Skill (Repo Idea Thinker Skill)
- login
- Vite Env.D (ImportMeta)
- simulate_payment
- FakeCommunicationRepository
- Index (Frontend HTML Root Document)
- Pyproject (syncally)
- auth.py
- InvariantViolation
- sqlalchemy
- _to_domain
- DealWorkflowInput
- _domain_deal
- .__call__
- AI Provider Boundary Specification
- _register_shutdown_handlers
- Four-Dimension Profile Collections
- Two-Party Judge Journey
- .list_for_agreement
- WorkflowWorkerIntegrationTests
- authorize_payment_route
- FulfillmentMigrationTests
- ProviderInvoiceUniqueMigrationTests
- FakeDealRepository
- NegotiationCommand
- MigrationConfigTests
- CollectionSchemaMigrationTests
- .test_refresh_rotates_token_and_revokes_previous_token
- HealthRouteTests
- 0004_communication_sources_and_scope_indexes.py
- repositories/paypal_webhooks.py
- database_health
- get_optional_actor
- _require_demo_admin
- PostgresDispatcherTests

## God Nodes (most connected - your core abstractions)
1. `ActorContext` - 253 edges
2. `OrganizationId` - 174 edges
3. `InvariantViolation` - 130 edges
4. `Deal` - 108 edges
5. `Money` - 105 edges
6. `DealId` - 95 edges
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

## Communities (172 total, 61 thin omitted)

### Community 0 - "Conversations & Test Conversation Use"
Cohesion: 0.07
Nodes (43): add_message_route(), AISuggestionRequest, clarify_fact_route(), confirm_fact_route(), ConstraintResponse, correct_fact_route(), CorrectFactRequest, create_fact_route() (+35 more)

### Community 1 - "AIContractError"
Cohesion: 0.13
Nodes (12): AIContractError, AIValidationClaim, _check_keys(), _decimal(), _required_string(), scope_extracted_facts(), _validate_decimal(), _validate_fact_value() (+4 more)

### Community 2 - "BaseModel"
Cohesion: 0.11
Nodes (9): AcceptInvitationResponse, ContactPayload, ContactResponse, CounterpartyInvitationResponse, InvitationResponse, OrganizationDirectoryItem, OrganizationMemberResponse, ProfileResponse (+1 more)

### Community 3 - ".add"
Cohesion: 0.12
Nodes (7): AuthorizePaymentRequest, AuthorizePaymentResponse, PaymentPreviewResponse, AuthorizePaymentIntentCommand, PaymentIntentAuthorizationOutcome, PaymentIntentCommandMismatch, PaymentExecutionMode

### Community 4 - "Test Ai Provider & Ai"
Cohesion: 0.09
Nodes (13): extract_facts_from_context(), ConfiguredAIProvider, AISuggestionProviderTests, respond(), respond(), respond(), respond(), respond() (+5 more)

### Community 5 - "DealId"
Cohesion: 0.07
Nodes (15): can_view_message(), Conversation, ConversationId, DealId, MessageId, OrganizationId, UserId, constraint() (+7 more)

### Community 6 - "Seed Demo & Deals"
Cohesion: 0.06
Nodes (38): _accept_invitation(), PaymentMilestoneNotFound, _clear_fixture(), _create_fixture(), _delete_scoped(), DemoCollisionError, DemoIdentity, _normalized_index_predicate() (+30 more)

### Community 7 - "PaymentNeedsAction"
Cohesion: 0.09
Nodes (11): receive_paypal_invoice_webhook(), PaymentNeedsAction, PaymentOutcomeUnknown, PaymentRetryableError, _has_excess_currency_precision(), PayPalSandboxInvoiceProvider, _provider_request_id(), _send_request() (+3 more)

### Community 8 - "PaymentNeedsAction"
Cohesion: 0.13
Nodes (8): get_paypal_webhook_configuration(), PaymentInvoiceLookup, PaymentInvoiceRequest, PaymentWorkItem, GmailSettings, PayPalSettings, OfflineDemoInvoiceProvider, PaymentProviderResolver

### Community 9 - "api/agreements.py"
Cohesion: 0.08
Nodes (27): AgreementVersionResponse, ApprovalResponse, approve_agreement_route(), commit_agreement_route(), CommitAgreementRequest, compare_agreements_route(), create_agreement_draft_route(), create_reviewed_agreement_draft_route() (+19 more)

### Community 10 - "Test Conversation Routes (ConversationRouteTests)"
Cohesion: 0.10
Nodes (3): ConversationRouteTests, respond(), send()

### Community 11 - "create_deal"
Cohesion: 0.15
Nodes (5): _both_organizations_active(), create_deal(), CreateDealCommand, DealUseCaseTests, FakeDealRepository

### Community 13 - "get_current_actor"
Cohesion: 0.15
Nodes (5): _decode_token(), _development_actor(), development_login(), get_current_actor(), _unauthorized()

### Community 14 - "process_payment_intent"
Cohesion: 0.08
Nodes (14): PaymentInvoiceNotifier, PaymentInvoiceProvider, PaymentProcessingRepository, process_payment_intent(), reconcile_payment_intent(), _request_id_retry_window_expired(), require_payment_provider(), claim_next_payment_event() (+6 more)

### Community 15 - "ai.py"
Cohesion: 0.07
Nodes (17): get_ai_suggestion_provider(), AIConfigurationError, AIProvenance, AIRetryPolicy, AISuggestionProvider, call_with_bounded_retry(), draft_proposal(), draft_proposal_from_context() (+9 more)

### Community 16 - "NegotiationTests"
Cohesion: 0.20
Nodes (4): EvidenceReference, ProposalBase, negotiate_in_transaction(), NegotiationTests

### Community 17 - "Types & Client"
Cohesion: 0.06
Nodes (62): describeDetail(), getDealFulfillment(), getDealMessageExistence(), isAbortError(), isRecord(), readErrorDetail(), recordDealFulfillment(), AgreementApproval (+54 more)

### Community 18 - "listOrganizations"
Cohesion: 0.06
Nodes (53): dependencies, react@^19.3.0, react-dom@^19.3.0, three@^0.186.1, getCommercialDocumentDraft(), listOrganizations(), login(), clearAccessToken() (+45 more)

### Community 19 - "Money"
Cohesion: 0.11
Nodes (11): PaymentInvoiceReconciliation, PaymentMilestone, VerifiedProviderPaymentState, PaymentIntentId, PaymentMilestoneId, _restore_domain_intent(), transition(), FakePayPalInvoiceProvider (+3 more)

### Community 20 - "DomainError"
Cohesion: 0.07
Nodes (21): CommercialDocumentDraftResponse, get_commercial_document_draft_route(), get_trade_pack_route(), DuplicateApproval, ProposalNotFound, AgreementNotCommitted, CommercialDocumentDraft, _display() (+13 more)

### Community 21 - "Test Outbox Dispatcher & Outbox"
Cohesion: 0.11
Nodes (12): build_deal_workflow_id(), dispatch_outbox_event(), OutboxDispatchResult, PendingOutboxEvent, apply_dispatch_result(), claim_next_pending_event(), _claim_statement(), dispatch_one_pending_event() (+4 more)

### Community 22 - "Simulate Deal Flow & Test"
Cohesion: 0.07
Nodes (8): ci_deal_flow_hook(), DealFlowContext, DealFlowSimulator, run_simulation(), SimulationError, StepRecord, TerminalFormatter, DemoLifecycleTests

### Community 23 - "Test Organization Invitations & Organizations"
Cohesion: 0.16
Nodes (5): accept_invitation(), AcceptInvitationRequest, create_organization_invitation(), CreateInvitationRequest, OrganizationInvitationTests

### Community 24 - "SqlAlchemyCommunicationRepository"
Cohesion: 0.09
Nodes (10): ConcurrentConstraintUpdate, message_fingerprint(), Message, CommunicationScopeError, _conversation_to_domain(), _is_unique_violation(), _message_to_domain(), _page_bounds() (+2 more)

### Community 25 - "Package & Vite.Config"
Cohesion: 0.06
Nodes (47): devDependencies, eslint@^10.13.0, @eslint/js@^10.0.1, eslint-plugin-react-hooks@^7.1.1, eslint-plugin-react-refresh@^0.4.20, globals@^17.13.0, happy-dom@^21.0.3, @testing-library/dom@^10.4.1 (+39 more)

### Community 26 - "client.test.ts"
Cohesion: 0.10
Nodes (22): API_REQUEST_TIMEOUT_MS, compareAgreementVersions(), listOrganizationMembers(), revokeOrganizationMember(), CREATED_MESSAGE, fetchMock, lastRequest(), sentBody() (+14 more)

### Community 27 - "Dealconversationreview & Dealconversationreview.Test"
Cohesion: 0.07
Nodes (40): createDealMessage(), importDealThread(), listDealFacts(), listDealMessages(), previewDealThreadImport(), reviewDealFact(), updateFactVisibility(), areFactsEqual() (+32 more)

### Community 28 - "Skill & Skill.Md"
Cohesion: 0.04
Nodes (43): API and Database Engineer Skill, API Design and Contract Semantics, Data Integrity and Invariant Enforcement, Query Performance and Projection Optimization, Schema Migration and Backward Compatibility, Transaction Boundaries and Atomicity, Archify Diagrammer Skill, Archify CLI Global Tool (+35 more)

### Community 29 - "sqlalchemy"
Cohesion: 0.06
Nodes (5): PaymentInvoiceLineItem, VerifiedProviderPaymentStatus, _provider_error_code(), simulation_state(), DomainDependencyTests

### Community 30 - "User"
Cohesion: 0.15
Nodes (4): _compute_effective_capabilities(), update_member_permissions(), UpdateMemberPermissionsRequest, OrganizationPermissionsTests

### Community 31 - "DealDetailPage.test.tsx"
Cohesion: 0.06
Nodes (41): ApiError, getCurrentAgreement(), getDeal(), getNegotiation(), getOrganization(), negotiateDeal(), Deal, NegotiationView (+33 more)

### Community 32 - "application/agreements.py"
Cohesion: 0.06
Nodes (25): AgreementRepository, AuditEventDraft, AuditRepository, commit_agreement(), create_agreement_draft(), create_reviewed_agreement_draft(), CreateAgreementDraftCommand, CreateReviewedAgreementDraftCommand (+17 more)

### Community 33 - "Aisuggestionreview & Suggestionpreview"
Cohesion: 0.09
Nodes (36): correctDealFact(), createDealFact(), draftDealProposal(), suggestDealFacts(), AIProvenance, DealFact, FactReviewAction, isPaymentTrigger() (+28 more)

### Community 34 - "SyncAlly Implementation Plan Document"
Cohesion: 0.16
Nodes (13): SyncAlly Architecture Document, System Topology and Ownership Boundaries, Temporal Worker and Outbox Architecture, Acceptance Criteria Verification Matrix, SyncAlly Implementation Plan Document, Issue #77 Architecture Contracts, Stage Lifecycle Roadmap, Frontend API Client and Authoritative State (+5 more)

### Community 35 - "PaymentProcessingTests"
Cohesion: 0.13
Nodes (6): payment_invoice_number(), FakeInvoiceProvider, FakeProcessingRepository, PaymentProcessingTests, _request(), _work_item()

### Community 36 - "AgreementCommitTests"
Cohesion: 0.07
Nodes (10): CommitAgreementCommand, RecordApprovalCommand, commit_agreement_in_transaction(), record_approval_in_transaction(), AgreementCommitTests, LocalWorkflowSmokeTests, commit_once(), NegotiationPostgresRaceTests (+2 more)

### Community 37 - "payment_outbox.py"
Cohesion: 0.05
Nodes (19): NotificationKind, _connect_with_retry(), main(), run_forever(), main(), run_forever(), _is_live_backend_healthy(), main() (+11 more)

### Community 38 - "OrganizationCapability"
Cohesion: 0.06
Nodes (21): ContactVisibility, _normalize_string(), Organization, OrganizationCapability, OrganizationContact, OrganizationMember, OrganizationMemberRole, OrganizationMemberStatus (+13 more)

### Community 39 - "Paymentstatuspanel & Paymentstatuspanel.Test"
Cohesion: 0.10
Nodes (29): authorizeDealPayment(), listPaymentStatuses(), previewDealPayment(), PaymentIntentStatus, describeStatus(), displayAmount(), extractInvoiceNumber(), firstMilestoneAmount() (+21 more)

### Community 41 - "api/fulfillment.py"
Cohesion: 0.05
Nodes (35): _event_response(), FulfillmentEventResponse, FulfillmentSnapshotResponse, get_fulfillment_repository(), _raise_fulfillment_error(), read_fulfillment_route(), record_fulfillment_route(), RecordFulfillmentRequest (+27 more)

### Community 42 - "ProposedTerms"
Cohesion: 0.09
Nodes (7): AIProviderError, FactExtractionRequest, ProposalDraftRequest, ProposedTerms, DeterministicFakeAIProvider, extract_facts(), FakeWebhookVerifier

### Community 43 - "build_terms"
Cohesion: 0.22
Nodes (9): compare_agreement_terms(), NegotiationSession, NegotiationSubmissionOutcome, ProposalStatus, NegotiationSessionId, build_proposal(), build_terms(), HumanNegotiationTests (+1 more)

### Community 44 - "DealWorkflow"
Cohesion: 0.18
Nodes (3): DealWorkflow, DealWorkflowUnitTests, run()

### Community 47 - "DealWorkflow"
Cohesion: 0.29
Nodes (3): DealWorkflowResult, DealWorkflowTests, new_notification()

### Community 48 - "Test Organization Directory & Organizations"
Cohesion: 0.13
Nodes (4): _case_insensitive_prefix(), _escape_like(), value(), OrganizationDirectoryTests

### Community 49 - "repositories/negotiation.py"
Cohesion: 0.19
Nodes (6): NegotiationConflict, NegotiationNotFound, NegotiationOrganizationRequired, ProposalId, SqlAlchemyNegotiationRepository, projection()

### Community 50 - "DealWorkflowNotification"
Cohesion: 0.11
Nodes (8): DealWorkflowStarter, WorkflowStartError, WorkflowStartOutcome, WorkflowStartPermanentError, WorkflowStartTransientError, DealWorkflowNotification, TemporalDealWorkflowStarter, TemporalAdapterTests

### Community 51 - "Deal"
Cohesion: 0.13
Nodes (4): Deal, DealStatus, _deal_to_domain(), FakeDealRepository

### Community 52 - "PaymentOutboxWorkerTests"
Cohesion: 0.10
Nodes (5): FakeRepository, NoCallProvider, PaymentOutboxWorkerTests, resolve(), _utc()

### Community 53 - "Organization"
Cohesion: 0.12
Nodes (13): getOrganizationProfile(), updateOrganizationProfile(), ContactVisibility, Organization, OrganizationContact, Props, describeError(), OrganizationProfileSection() (+5 more)

### Community 54 - "load_deal_workflow_state"
Cohesion: 0.11
Nodes (7): DealWorkflowState, load_deal_workflow_state(), parse_workflow_uuid(), WorkflowAgreementRepository, WorkflowDealNotFound, WorkflowDealRepository, _workflow_input_value()

### Community 55 - "canonical_decimal"
Cohesion: 0.08
Nodes (5): PaymentInvoiceNotice, main(), GmailSMTPInvoiceNotifier, _FakeSMTP, GmailSMTPInvoiceNotifierTests

### Community 56 - "Agreementreview & Client"
Cohesion: 0.10
Nodes (33): commitAgreementVersion(), getAgreementHistory(), getAgreementVersion(), getTradePack(), recordAgreementDecision(), TradePackFormat, AgreementVersion, paymentTimingLabel() (+25 more)

### Community 58 - "Test Workflow Activities & Activities"
Cohesion: 0.20
Nodes (3): RefreshDealStateActivity, RefreshDealStateActivityTests, factory()

### Community 59 - "Test Migration Lock & Env"
Cohesion: 0.10
Nodes (9): run_migrations_offline(), run_migrations_online(), serialize_migrations(), _make_postgres_connection(), _make_sqlite_connection(), MigrationLockTests, simulated_migration(), PostgresRealAdvisoryLockTests (+1 more)

### Community 60 - "Payment Processing & Test Payment"
Cohesion: 0.13
Nodes (6): _build_in_process_client(), dispatch_payment(), session_factory(), PaymentIntentStatus, SqlAlchemyPaymentProcessingRepository, transition()

### Community 61 - "01 Commercial Domain Model &"
Cohesion: 0.07
Nodes (19): AgreementVersion Aggregate, Append-Only AuditEvent Ledger, Commercial Constraint and Provenance, Deal Aggregate, Organization and Membership Entities, PaymentMilestone and Obligation, Proposal Aggregate and Terms Hash, Temporal Deal Workflow (+11 more)

### Community 62 - "create_counterparty_invitation"
Cohesion: 0.14
Nodes (6): create_counterparty_invitation(), _create_invitation_token(), CreateCounterpartyInvitationRequest, OnboardingConcurrencyCases, OnboardingPostgresConcurrencyTests, OnboardingSQLiteConcurrencyTests

### Community 64 - "Test Identity Boundary & Config"
Cohesion: 0.15
Nodes (3): _is_weak_jwt_secret(), Settings, IdentityBoundaryTests

### Community 65 - "Compose.Yaml (volumes)"
Cohesion: 0.09
Nodes (22): POSTGRES_DB, POSTGRES_PASSWORD, POSTGRES_USER, interval, retries, test, timeout, environment (+14 more)

### Community 66 - "InvalidTransition"
Cohesion: 0.13
Nodes (4): PaymentStatusResponse, PaymentIntent, SqlAlchemyPaymentIntentRepository, PaymentStatusExtendedModelTests

### Community 67 - "AddMessageRequest"
Cohesion: 0.19
Nodes (3): AddMessageRequest, CreateFactRequest, AddMessageRequestTests

### Community 68 - "Session"
Cohesion: 0.08
Nodes (16): _active_admin_membership(), add_organization_member(), AddOrganizationMemberRequest, create_organization(), CreateOrganizationRequest, _deal_awaiting_counterparty(), get_organization_profile_route(), get_organization_route() (+8 more)

### Community 69 - "contracts.py"
Cohesion: 0.37
Nodes (8): _contains_numeric_token(), _contains_token(), _date_value_is_present(), _fact_value_is_supported_by_quote(), _flexible_whitespace_pattern(), _number_with_currency_is_present(), _number_with_unit_is_present(), _numeric_pattern()

### Community 71 - "Money"
Cohesion: 0.23
Nodes (10): PaymentObligationAllocation, PaymentTerm, ShipmentItemAllocation, ShipmentTerm, TradeLineItem, Money, DecimalCanonicalizationTests, TradeTermsTests (+2 more)

### Community 72 - "PersistentDemoSeedTests"
Cohesion: 0.10
Nodes (6): fixture_id(), initialize_offline_database(), main(), PersistentDemoSeedTests, start_deal_workflow(), dispatch()

### Community 73 - "AgreementVersionId"
Cohesion: 0.28
Nodes (3): AgreementVersionId, DealDomainTests, make_deal()

### Community 74 - "Createdealpage & Createdealpage.Test"
Cohesion: 0.13
Nodes (18): acceptInvitation(), apiBaseUrl(), apiRequest(), createAgreementFromReviewedTerms(), createCounterpartyInvitation(), createDeal(), CreateDealPage(), handleSubmit() (+10 more)

### Community 75 - "Negotiation (BaseRequest)"
Cohesion: 0.13
Nodes (12): BaseRequest, CandidateRequest, EvidenceRequest, HistoryResponse, NegotiationRequest, NegotiationResponse, NegotiationResult, ProposalResponse (+4 more)

### Community 76 - "SqlAlchemyAgreementRepository"
Cohesion: 0.11
Nodes (10): AgreementNotFound, AgreementVersionConflict, AmbiguousAgreementOrganization, StaleAgreementVersion, UnauthorizedApproval, WrongTermsHash, is_pending(), lock_deal() (+2 more)

### Community 77 - "ConversationUseCaseTests"
Cohesion: 0.28
Nodes (4): AddMessageCommand, send(), ConversationUseCaseTests, write_message()

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
Cohesion: 0.20
Nodes (3): create_worker(), workflow_activities(), WorkflowWorkerTests

### Community 85 - "ExtractedFact"
Cohesion: 0.16
Nodes (6): ExtractedFact, FactField, SourceReference, DemoAISuggestionProvider, _is_ambiguous_numeric_term(), _is_delivery_date_context()

### Community 87 - "demo_lifecycle.py"
Cohesion: 0.19
Nodes (8): _acquire_lock(), _is_demo_deal(), lock_demo_deal_creation(), lock_demo_payment_processing(), lock_demo_reset(), lock_outbox_dispatch(), DemoLifecycleLockTests, _postgres_session()

### Community 88 - "Human Bilateral Amendment Workflow"
Cohesion: 0.40
Nodes (3): Canonical Hash and Legacy Export Preservation, Human Bilateral Amendment Workflow, Cancellation and Dispute Case State Machine

### Community 89 - "react"
Cohesion: 0.09
Nodes (28): addOrganizationMember(), createOrganization(), useHashRoute(), describeError(), OrganizationsPanel(), handleCreate(), handleInvite(), OrganizationsState (+20 more)

### Community 92 - "vitest"
Cohesion: 0.13
Nodes (13): listDeals(), ViewerRole, DealsPage(), DealsPageProps, DealsState, describeError(), ROLE_LABELS, mockedListDeals (+5 more)

### Community 94 - "Constraint"
Cohesion: 0.07
Nodes (11): persist_fact_candidates(), ScopedFactCandidate, Constraint, ConstraintKind, ConstraintStatus, MessageSourceType, Visibility, ConstraintId (+3 more)

### Community 95 - "api/deals.py"
Cohesion: 0.11
Nodes (12): create_deal_route(), CreateDealRequest, DealResponse, DealSummaryResponse, get_deal_repository(), list_deals_route(), read_deal_route(), _to_response() (+4 more)

### Community 96 - "application/conversations.py"
Cohesion: 0.06
Nodes (20): add_message(), can_view_constraint(), CommunicationRepository, ConstraintRepository, correct_constraint(), create_manual_constraint(), CreateManualConstraintCommand, deal_has_any_message() (+12 more)

### Community 98 - "Master Execution Contract"
Cohesion: 0.14
Nodes (31): Execution Acceptance Gates, Master Execution Contract, Safe Windows PowerShell Runner, Private Contact Channels, Profiles Specification F14, Fresh Authorization Enforcement, Permissions Specification F15a, Append-Only Fulfillment Observations and Confirmations (+23 more)

### Community 99 - "0005 Conversation Party Unique (Enforce"
Cohesion: 0.36
Nodes (5): _create_party_unique_constraint(), _deduplicate_conversations(), downgrade(), _drop_party_unique_constraint(), upgrade()

### Community 101 - "Safe Operations and Recovery Guide"
Cohesion: 0.19
Nodes (15): PayPal Sandbox Invoicing and Reconciliation Flow, Backend README Document, F11a Explicit Payment Modes, F12 Committed Trade Packs, F1a Curated Repeatable Demo Fixture, F4 Invitations and Private Pending Deals, F5 Persisted Human Negotiation, F6 Agreement History and Comparison (+7 more)

### Community 102 - "authorize_payment_intent"
Cohesion: 0.15
Nodes (6): OutboxEventDraft, OutboxRepository, authorize_payment_intent(), PaymentIntentRepository, SellerMembershipRepository, SqlAlchemyOutboxRepository

### Community 104 - "openai.py"
Cohesion: 0.13
Nodes (14): AIPermanentError, AITransientError, parse_extracted_facts(), parse_proposed_terms(), _provider_context(), AiContext, _json(), _object() (+6 more)

### Community 108 - "OnboardingWizard.tsx"
Cohesion: 0.14
Nodes (13): COUNTRY_NAMES, CountryOption, describeError(), isAmbiguousCreateFailure(), OnboardingWizard(), findExistingOrganization(), handleSubmit(), OnboardingWizardProps (+5 more)

### Community 111 - "ConversationContractTests"
Cohesion: 0.11
Nodes (4): confirm_constraint(), ConstraintNotFound, ConversationContractTests, FakeConstraintRepository

### Community 113 - "_is_one_active_per_milestone_violation"
Cohesion: 0.43
Nodes (3): _is_idempotency_key_violation(), _is_one_active_per_milestone_violation(), _violated_constraint_name()

### Community 115 - "TradeTerms"
Cohesion: 0.13
Nodes (5): build_payment_milestones(), _money(), _parse_money(), TradeTerms, with_timing()

### Community 116 - "create_refresh_token"
Cohesion: 0.22
Nodes (7): _as_utc(), create_refresh_token(), _encode_access_token(), _issue_tokens(), _replay_rotation(), _revoke_family(), exercise_api()

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
Cohesion: 0.07
Nodes (11): _require_dev_environment(), OperationalFastAPI, _decode_invitation_token(), PaymentOutboxStatus, hash_password(), verify_password(), DuplicateActivePaymentIntent, IdempotencyKeyReused (+3 more)

### Community 140 - "InvariantViolation"
Cohesion: 0.11
Nodes (5): _normalized_text(), _require_decimal(), InvariantViolation, bounded_decimal(), BoundedDecimalTests

### Community 141 - "sqlalchemy"
Cohesion: 0.04
Nodes (32): upgrade(), uuid_column(), upgrade(), upgrade(), upgrade(), upgrade(), downgrade(), upgrade() (+24 more)

### Community 144 - "DealWorkflowInput"
Cohesion: 0.21
Nodes (5): DealWorkflowInput, _require_uuid(), new_workflow_input(), RefreshActivity, RefreshCall

### Community 145 - "_domain_deal"
Cohesion: 0.36
Nodes (4): _domain_deal(), _FakeAgreementRepository, _FakeDealRepository, WorkflowStateApplicationTests

### Community 147 - "AI Provider Boundary Specification"
Cohesion: 0.53
Nodes (4): F2 AI Configuration and Provider Boundary, AI Provider Boundary Specification, AI Resilience and Retry Policy, AISuggestionProvider Contract

### Community 148 - "_register_shutdown_handlers"
Cohesion: 0.27
Nodes (4): _register_shutdown_handlers(), _remove_shutdown_handlers(), _request_shutdown(), WorkerShutdownSignalTests

### Community 151 - ".list_for_agreement"
Cohesion: 0.20
Nodes (3): _build_invoice_url(), ExtendedPaymentStatusRecord, _utc_timestamp()

### Community 153 - "authorize_payment_route"
Cohesion: 0.10
Nodes (10): authorize_payment_route(), get_payment_status_repository(), list_payment_statuses_route(), preview_payment_route(), list_current_payment_statuses(), PaymentStatusRecord, PaymentStatusRepository, AgreementStatus (+2 more)

### Community 157 - "NegotiationCommand"
Cohesion: 0.42
Nodes (3): negotiate(), NegotiationCommand, NegotiationRepository

### Community 160 - ".test_refresh_rotates_token_and_revokes_previous_token"
Cohesion: 0.13
Nodes (4): _hash_refresh_token(), refresh_access_token(), RefreshRequest, RefreshToken

### Community 162 - "0004_communication_sources_and_scope_indexes.py"
Cohesion: 0.60
Nodes (4): _create_scope_index(), downgrade(), _drop_scope_index(), upgrade()

## Knowledge Gaps
- **47 isolated node(s):** `syncally`, `F1a Curated Repeatable Demo Fixture`, `Editorial Dark Theme Design System`, `ZIP HTML and Print Export Verification`, `Whole-Worktree Independent Review` (+42 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1303 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **61 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ActorContext` connect `Test Deal Routes & Identity` to `Conversations & Test Conversation Use`, `Test Ai Provider & Ai`, `DealId`, `simulate_payment`, `Seed Demo & Deals`, `FakeCommunicationRepository`, `api/agreements.py`, `Test Conversation Routes (ConversationRouteTests)`, `auth.py`, `create_deal`, `get_current_actor`, `Test Agreement Routes (AgreementRouteTests)`, `ai.py`, `DomainError`, `Simulate Deal Flow & Test`, `Test Organization Invitations & Organizations`, `authorize_payment_route`, `FakeDealRepository`, `sqlalchemy`, `User`, `application/agreements.py`, `OrganizationCapability`, `get_optional_actor`, `Test Payment Intent Repository &`, `_require_demo_admin`, `api/fulfillment.py`, `ProposedTerms`, `Test Organization Directory & Organizations`, `create_counterparty_invitation`, `Test Identity Boundary & Config`, `InvalidTransition`, `Session`, `Negotiation (BaseRequest)`, `ConversationUseCaseTests`, `Test Communication Repositories (MessageIdempotencyPostgresTests)`, `Test Negotiation (NegotiationRouteTests)`, `Constraint`, `api/deals.py`, `application/conversations.py`, `ConversationContractTests`, `queue_simulated_reconciliation`, `AiContextSelectionTests`?**
  _High betweenness centrality (0.118) - this node is a cross-community bridge._
- **Are the 113 inferred relationships involving `ActorContext` (e.g. with `approve_agreement_route()` and `commit_agreement_route()`) actually correct?**
  _`ActorContext` has 113 INFERRED edges - model-reasoned connections that need verification._
- **What connects `syncally`, `F1a Curated Repeatable Demo Fixture`, `Editorial Dark Theme Design System` to the rest of the system?**
  _47 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Conversations & Test Conversation Use` be split into smaller, more focused modules?**
  _Cohesion score 0.06975308641975309 - nodes in this community are weakly interconnected._
- **Why does `OrganizationId` connect `DealId` to `AIContractError`, `.add`, `Test Ai Provider & Ai`, `Seed Demo & Deals`, `FakeCommunicationRepository`, `api/agreements.py`, `Test Conversation Routes (ConversationRouteTests)`, `auth.py`, `create_deal`, `Test Agreement Routes (AgreementRouteTests)`, `ai.py`, `_to_domain`, `NegotiationTests`, `_domain_deal`, `Money`, `DomainError`, `Test Outbox Dispatcher & Outbox`, `SqlAlchemyCommunicationRepository`, `sqlalchemy`, `User`, `application/agreements.py`, `AgreementCommitTests`, `OrganizationCapability`, `Test Payment Intent Repository &`, `api/fulfillment.py`, `ProposedTerms`, `build_terms`, `SqlAlchemyDealRepository`, `repositories/negotiation.py`, `Deal`, `create_counterparty_invitation`, `InvalidTransition`, `Session`, `contracts.py`, `Money`, `AgreementVersionId`, `Negotiation (BaseRequest)`, `SqlAlchemyAgreementRepository`, `ConversationUseCaseTests`, `Test Counterparty Onboarding Migration &`, `Constraint`, `application/conversations.py`, `Test Negotiation Migration (NegotiationMigrationTests)`, `ConversationContractTests`, `InvalidTransition`, `TradeTerms`, `AiContextSelectionTests`?**
  _High betweenness centrality (0.073) - this node is a cross-community bridge._
- **Are the 59 inferred relationships involving `OrganizationId` (e.g. with `create_reviewed_agreement_draft_route()` and `write_negotiation()`) actually correct?**
  _`OrganizationId` has 59 INFERRED edges - model-reasoned connections that need verification._
- **Should `AIContractError` be split into smaller, more focused modules?**
  _Cohesion score 0.12682926829268293 - nodes in this community are weakly interconnected._