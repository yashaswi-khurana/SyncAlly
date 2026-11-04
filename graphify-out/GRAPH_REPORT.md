# Graph Report - SyncAlly  (2026-11-04)

## Corpus Check
- 291 files · ~244,088 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 8 file(s) not represented in the graph (top: (none) 4, .example 1, .ini 1)

## Summary
- 4389 nodes · 14385 edges · 168 communities (109 shown, 59 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 1893 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `bf3f8cf0`
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
- DealDetailPage.test.tsx
- application/agreements.py
- Aisuggestionreview & Suggestionpreview
- SyncAlly Implementation Plan Document
- PaymentProcessingTests
- AgreementCommitTests
- worker.py
- repositories/organizations.py
- Paymentstatuspanel & Paymentstatuspanel.Test
- Test Payment Intent Repository &
- repositories/fulfillment.py
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
- PaymentOutboxWorkerTests
- Organization
- load_deal_workflow_state
- canonical_decimal
- Agreementreview & Client
- Organizations & Test Organization Onboarding
- Test Workflow Activities & Activities
- Test Migration Lock & Env
- Payment Processing & Test Payment
- 01 Commercial Domain Model &
- api/fulfillment.py
- Test Deal Routes & Identity
- Test Identity Boundary & Config
- Compose.Yaml (volumes)
- InvalidTransition
- AddMessageRequest
- api/organizations.py
- contracts.py
- Test Payment Reconciliation & Intent
- build_terms
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
- _connect_with_retry
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
- create_deal_route
- review_constraint
- Test Database (DatabasePersistenceTests)
- Master Execution Contract
- 0005 Conversation Party Unique (Enforce
- Main (Request)
- Safe Operations and Recovery Guide
- OrganizationRepositoryTests
- openai.py
- Test Negotiation Migration (NegotiationMigrationTests)
- Test Payment Mode Migration (PaymentModeMigrationTests)
- OnboardingWizard.tsx
- Test Communication Migration (ConversationPartyUniquenessMigrationTests)
- .test_rejected_closure_keeps_approved_agreement_committable
- ActorContext
- FulfillmentRouteTests
- _is_one_active_per_milestone_violation
- InvalidTransition
- TradeTerms
- create_refresh_token
- NegotiationPostgresRaceTests
- Final Gates and Truthful Completion Specification
- Skill (Repo Idea Thinker Skill)
- login
- Vite Env.D (ImportMeta)
- simulate_payment
- simulate_deal_flow.py
- Index (Frontend HTML Root Document)
- Pyproject (syncally)
- auth.py
- InvariantViolation
- sqlalchemy
- get_commercial_document_draft_route
- generate_trade_pack
- _domain_deal
- .__call__
- AI Provider Boundary Specification
- read_deal_route
- Four-Dimension Profile Collections
- Two-Party Judge Journey
- AIConfigurationError
- main
- verify_member_capability
- FulfillmentMigrationTests
- ProviderInvoiceUniqueMigrationTests
- MigrationConfigTests
- .test_reset_refuses_while_generic_dispatch_is_inside_external_call
- .test_refresh_rotates_token_and_revokes_previous_token
- HealthRouteTests
- 0004_communication_sources_and_scope_indexes.py
- OrganizationIndexMigrationTests
- CommunicationMigrationTests
- MessageIdempotencyMigrationTests
- OutboxDispatchMigrationTests
- PaymentCreateStartedMigrationTests

## God Nodes (most connected - your core abstractions)
1. `ActorContext` - 253 edges
2. `OrganizationId` - 172 edges
3. `InvariantViolation` - 124 edges
4. `Deal` - 108 edges
5. `DealId` - 95 edges
6. `Money` - 95 edges
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

## Communities (168 total, 59 thin omitted)

### Community 0 - "Conversations & Test Conversation Use"
Cohesion: 0.05
Nodes (58): add_message_route(), AISuggestionRequest, clarify_fact_route(), confirm_fact_route(), ConstraintResponse, correct_fact_route(), CorrectFactRequest, create_fact_route() (+50 more)

### Community 1 - "AIContractError"
Cohesion: 0.13
Nodes (12): AIContractError, _check_keys(), _decimal(), _required_string(), scope_extracted_facts(), _validate_decimal(), _validate_fact_value(), _validate_schema_version() (+4 more)

### Community 3 - "api/payments.py"
Cohesion: 0.05
Nodes (32): authorize_payment_route(), AuthorizePaymentRequest, AuthorizePaymentResponse, get_payment_status_repository(), list_payment_statuses_route(), PaymentOutboxStatus, PaymentPreviewResponse, preview_payment_route() (+24 more)

### Community 4 - "Test Ai Provider & Ai"
Cohesion: 0.10
Nodes (12): extract_facts_from_context(), ConfiguredAIProvider, respond(), respond(), respond(), respond(), respond(), respond() (+4 more)

### Community 5 - "DealId"
Cohesion: 0.07
Nodes (16): Approval, ConstraintId, ConversationId, DealId, MessageId, OrganizationId, UserId, _agreement_to_domain() (+8 more)

### Community 6 - "Seed Demo & Deals"
Cohesion: 0.07
Nodes (35): _accept_invitation(), NotificationKind, _create_fixture(), DemoIdentity, _password_for(), _seed_identities(), is_pending(), lock_deal() (+27 more)

### Community 7 - "PaymentNeedsAction"
Cohesion: 0.10
Nodes (9): receive_paypal_invoice_webhook(), PaymentOutcomeUnknown, PaymentRetryableError, _has_excess_currency_precision(), PayPalSandboxInvoiceProvider, _provider_request_id(), _send_request(), PayPalSandboxAdapterTests (+1 more)

### Community 8 - "PaymentNeedsAction"
Cohesion: 0.09
Nodes (11): get_paypal_webhook_configuration(), PaymentInvoiceLookup, PaymentInvoiceRequest, PaymentNeedsAction, PaymentWorkItem, main(), GmailSettings, PayPalSettings (+3 more)

### Community 9 - "api/agreements.py"
Cohesion: 0.07
Nodes (27): AgreementVersionResponse, ApprovalResponse, approve_agreement_route(), commit_agreement_route(), CommitAgreementRequest, compare_agreements_route(), create_agreement_draft_route(), create_reviewed_agreement_draft_route() (+19 more)

### Community 10 - "Test Conversation Routes (ConversationRouteTests)"
Cohesion: 0.10
Nodes (3): ConversationRouteTests, respond(), send()

### Community 11 - "create_deal"
Cohesion: 0.15
Nodes (6): _both_organizations_active(), create_deal(), CreateDealCommand, DealAccessDenied, DealUseCaseTests, FakeDealRepository

### Community 13 - "get_current_actor"
Cohesion: 0.12
Nodes (7): _decode_token(), _development_actor(), development_login(), get_current_actor(), _unauthorized(), _require_demo_admin(), resolve_actor()

### Community 14 - "process_payment_intent"
Cohesion: 0.08
Nodes (15): payment_invoice_number(), PaymentInvoiceNotifier, PaymentInvoiceProvider, PaymentProcessingRepository, process_payment_intent(), reconcile_payment_intent(), _request_id_retry_window_expired(), require_payment_provider() (+7 more)

### Community 15 - "ai.py"
Cohesion: 0.11
Nodes (15): get_ai_suggestion_provider(), AIProvenance, AISuggestionProvider, draft_proposal(), draft_proposal_from_context(), extract_facts(), FactExtractionResult, _list_all_constraints_for_owner() (+7 more)

### Community 16 - "NegotiationTests"
Cohesion: 0.14
Nodes (8): CandidateAcknowledgement, EvidenceReference, negotiate(), NegotiationCommand, NegotiationRepository, ProposalBase, negotiate_in_transaction(), NegotiationTests

### Community 17 - "Types & Client"
Cohesion: 0.06
Nodes (62): describeDetail(), getDealFulfillment(), getDealMessageExistence(), isAbortError(), isRecord(), readErrorDetail(), recordDealFulfillment(), AgreementApproval (+54 more)

### Community 18 - "listOrganizations"
Cohesion: 0.06
Nodes (53): dependencies, react@^19.3.0, react-dom@^19.3.0, three@^0.186.1, getCommercialDocumentDraft(), listOrganizations(), login(), clearAccessToken() (+45 more)

### Community 19 - "Money"
Cohesion: 0.08
Nodes (16): PaymentInvoiceReconciliation, _money(), _parse_money(), PaymentIntentStatus, PaymentMilestone, VerifiedProviderPaymentState, VerifiedProviderPaymentStatus, PaymentIntentId (+8 more)

### Community 20 - "CommercialDocumentDraftTests"
Cohesion: 0.20
Nodes (3): AgreementNotCommitted, generate_commercial_document_draft(), CommercialDocumentDraftTests

### Community 21 - "Test Outbox Dispatcher & Outbox"
Cohesion: 0.08
Nodes (15): build_deal_workflow_id(), DealWorkflowStarter, dispatch_outbox_event(), OutboxDispatchResult, PendingOutboxEvent, WorkflowStartTransientError, apply_dispatch_result(), claim_next_pending_event() (+7 more)

### Community 22 - "Simulate Deal Flow & Test"
Cohesion: 0.07
Nodes (11): _build_in_process_client(), dispatch_payment(), session_factory(), ci_deal_flow_hook(), DealFlowContext, DealFlowSimulator, run_simulation(), SimulationError (+3 more)

### Community 23 - "Test Organization Invitations & Organizations"
Cohesion: 0.07
Nodes (13): accept_invitation(), AcceptInvitationRequest, ContactPayload, create_counterparty_invitation(), create_organization_invitation(), CreateCounterpartyInvitationRequest, CreateInvitationRequest, _decode_invitation_token() (+5 more)

### Community 24 - "SqlAlchemyCommunicationRepository"
Cohesion: 0.11
Nodes (9): message_fingerprint(), Conversation, Message, CommunicationScopeError, _conversation_to_domain(), _is_unique_violation(), _message_to_domain(), _page_bounds() (+1 more)

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

### Community 31 - "DealDetailPage.test.tsx"
Cohesion: 0.06
Nodes (41): ApiError, getCurrentAgreement(), getDeal(), getNegotiation(), getOrganization(), negotiateDeal(), Deal, NegotiationView (+33 more)

### Community 32 - "application/agreements.py"
Cohesion: 0.09
Nodes (14): AgreementRepository, AuditEventDraft, AuditRepository, commit_agreement(), ObligationRepository, OutboxRepository, PaymentMilestoneRepository, build_obligations() (+6 more)

### Community 33 - "Aisuggestionreview & Suggestionpreview"
Cohesion: 0.09
Nodes (36): correctDealFact(), createDealFact(), draftDealProposal(), suggestDealFacts(), AIProvenance, DealFact, FactReviewAction, isPaymentTrigger() (+28 more)

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
Cohesion: 0.12
Nodes (12): _connect_with_retry(), main(), run_forever(), main(), run_forever(), is_permanent_rpc_error(), configure_logging(), log_operation() (+4 more)

### Community 38 - "repositories/organizations.py"
Cohesion: 0.13
Nodes (14): ContactVisibility, OrganizationCapability, OrganizationMember, OrganizationMemberRole, OrganizationMemberStatus, OrganizationProfile, OrganizationStatus, OrganizationVerificationStatus (+6 more)

### Community 39 - "Paymentstatuspanel & Paymentstatuspanel.Test"
Cohesion: 0.10
Nodes (29): authorizeDealPayment(), listPaymentStatuses(), previewDealPayment(), PaymentIntentStatus, describeStatus(), displayAmount(), extractInvoiceNumber(), firstMilestoneAmount() (+21 more)

### Community 40 - "Test Payment Intent Repository &"
Cohesion: 0.12
Nodes (4): queue_simulated_reconciliation(), require_simulation_scope(), authorize_payment_intent_in_transaction(), PaymentIntentRepositoryTests

### Community 41 - "repositories/fulfillment.py"
Cohesion: 0.10
Nodes (17): FulfillmentEventRecord, FulfillmentUnavailable, RecordFulfillmentCommand, bounded_quantity(), FulfillmentStage, quantity_text(), delivery_obligation_fulfilled(), _event_total() (+9 more)

### Community 42 - "AISuggestionProviderTests"
Cohesion: 0.10
Nodes (6): AIRetryPolicy, call_with_bounded_retry(), DeterministicFakeAIProvider, AISuggestionProviderTests, extract_facts(), FakeWebhookVerifier

### Community 43 - "seed_demo.py"
Cohesion: 0.15
Nodes (7): _clear_fixture(), _delete_scoped(), DemoCollisionError, _normalized_index_predicate(), _preflight(), seed_demo_data(), DemoSeedTests

### Community 44 - "DealWorkflow"
Cohesion: 0.11
Nodes (5): DealWorkflow, DealWorkflowInput, _require_uuid(), DealWorkflowUnitTests, WorkflowWorkerIntegrationTests

### Community 46 - "SqlAlchemyDealRepository"
Cohesion: 0.14
Nodes (4): _active_participation(), SqlAlchemyDealRepository, _to_domain(), DealRepositoryTests

### Community 47 - "DealWorkflow"
Cohesion: 0.14
Nodes (6): DealWorkflowResult, DealWorkflowTests, new_notification(), new_workflow_input(), RefreshActivity, RefreshCall

### Community 49 - "repositories/negotiation.py"
Cohesion: 0.19
Nodes (6): NegotiationConflict, NegotiationNotFound, NegotiationOrganizationRequired, ProposalId, SqlAlchemyNegotiationRepository, projection()

### Community 50 - "DealWorkflowNotification"
Cohesion: 0.13
Nodes (6): WorkflowStartError, WorkflowStartOutcome, WorkflowStartPermanentError, DealWorkflowNotification, TemporalDealWorkflowStarter, TemporalAdapterTests

### Community 51 - "Deal"
Cohesion: 0.09
Nodes (6): Deal, DealStatus, _deal_to_domain(), FakeDealRepository, DealAuthorizationTests, FakeDealRepository

### Community 52 - "PaymentOutboxWorkerTests"
Cohesion: 0.10
Nodes (5): FakeRepository, NoCallProvider, PaymentOutboxWorkerTests, resolve(), _utc()

### Community 53 - "Organization"
Cohesion: 0.12
Nodes (13): getOrganizationProfile(), updateOrganizationProfile(), ContactVisibility, Organization, OrganizationContact, Props, describeError(), OrganizationProfileSection() (+5 more)

### Community 54 - "load_deal_workflow_state"
Cohesion: 0.08
Nodes (8): DealWorkflowState, load_deal_workflow_state(), parse_workflow_uuid(), WorkflowAgreementRepository, WorkflowDealNotFound, WorkflowDealRepository, _workflow_input_value(), DealWorkflowStatus

### Community 55 - "canonical_decimal"
Cohesion: 0.12
Nodes (3): PaymentInvoiceNotice, _FakeSMTP, GmailSMTPInvoiceNotifierTests

### Community 56 - "Agreementreview & Client"
Cohesion: 0.10
Nodes (33): commitAgreementVersion(), getAgreementHistory(), getAgreementVersion(), getTradePack(), recordAgreementDecision(), TradePackFormat, AgreementVersion, paymentTimingLabel() (+25 more)

### Community 57 - "Organizations & Test Organization Onboarding"
Cohesion: 0.16
Nodes (6): add_organization_member(), AddOrganizationMemberRequest, create_organization(), CreateOrganizationRequest, _is_duplicate_membership_error(), OrganizationOnboardingTests

### Community 58 - "Test Workflow Activities & Activities"
Cohesion: 0.18
Nodes (3): RefreshDealStateActivity, RefreshDealStateActivityTests, factory()

### Community 59 - "Test Migration Lock & Env"
Cohesion: 0.10
Nodes (9): run_migrations_offline(), run_migrations_online(), serialize_migrations(), _make_postgres_connection(), _make_sqlite_connection(), MigrationLockTests, simulated_migration(), PostgresRealAdvisoryLockTests (+1 more)

### Community 60 - "Payment Processing & Test Payment"
Cohesion: 0.17
Nodes (4): PaymentInvoiceLineItem, SqlAlchemyPaymentProcessingRepository, transition(), transition()

### Community 61 - "01 Commercial Domain Model &"
Cohesion: 0.07
Nodes (19): AgreementVersion Aggregate, Append-Only AuditEvent Ledger, Commercial Constraint and Provenance, Deal Aggregate, Organization and Membership Entities, PaymentMilestone and Obligation, Proposal Aggregate and Terms Hash, Temporal Deal Workflow (+11 more)

### Community 62 - "api/fulfillment.py"
Cohesion: 0.12
Nodes (16): _event_response(), FulfillmentEventResponse, FulfillmentSnapshotResponse, get_fulfillment_repository(), _raise_fulfillment_error(), read_fulfillment_route(), record_fulfillment_route(), _snapshot_response() (+8 more)

### Community 64 - "Test Identity Boundary & Config"
Cohesion: 0.18
Nodes (3): _is_weak_jwt_secret(), Settings, IdentityBoundaryTests

### Community 65 - "Compose.Yaml (volumes)"
Cohesion: 0.09
Nodes (22): POSTGRES_DB, POSTGRES_PASSWORD, POSTGRES_USER, interval, retries, test, timeout, environment (+14 more)

### Community 67 - "AddMessageRequest"
Cohesion: 0.19
Nodes (3): AddMessageRequest, CreateFactRequest, AddMessageRequestTests

### Community 68 - "api/organizations.py"
Cohesion: 0.07
Nodes (23): AcceptInvitationResponse, _active_admin_membership(), _case_insensitive_prefix(), _compute_effective_capabilities(), ContactResponse, CounterpartyInvitationResponse, _create_invitation_token(), _deal_awaiting_counterparty() (+15 more)

### Community 69 - "contracts.py"
Cohesion: 0.13
Nodes (12): AIValidationClaim, _contains_numeric_token(), _contains_token(), _date_value_is_present(), _fact_value_is_supported_by_quote(), _flexible_whitespace_pattern(), _number_with_currency_is_present(), _number_with_unit_is_present() (+4 more)

### Community 71 - "build_terms"
Cohesion: 0.24
Nodes (6): PaymentTerm, ShipmentTerm, TradeLineItem, DecimalCanonicalizationTests, TradeTermsTests, _agreement()

### Community 72 - "PersistentDemoSeedTests"
Cohesion: 0.15
Nodes (4): fixture_id(), initialize_offline_database(), PersistentDemoSeedTests, start_deal_workflow()

### Community 73 - "AgreementVersionId"
Cohesion: 0.28
Nodes (3): AgreementVersionId, DealDomainTests, make_deal()

### Community 74 - "Createdealpage & Createdealpage.Test"
Cohesion: 0.13
Nodes (18): acceptInvitation(), apiBaseUrl(), apiRequest(), createAgreementFromReviewedTerms(), createCounterpartyInvitation(), createDeal(), CreateDealPage(), handleSubmit() (+10 more)

### Community 75 - "Negotiation (BaseRequest)"
Cohesion: 0.11
Nodes (12): CreateReviewedAgreementDraftRequest, BaseRequest, CandidateRequest, EvidenceRequest, HistoryResponse, NegotiationRequest, NegotiationResponse, NegotiationResult (+4 more)

### Community 76 - "SqlAlchemyAgreementRepository"
Cohesion: 0.13
Nodes (8): AgreementAccessDenied, AgreementNotFound, AgreementVersionConflict, ProposalNotFound, StaleAgreementVersion, UnauthorizedApproval, WrongTermsHash, SqlAlchemyAgreementRepository

### Community 77 - "ConversationUseCaseTests"
Cohesion: 0.19
Nodes (6): AddMessageCommand, import_thread(), preview_thread_import(), send(), ConversationUseCaseTests, write_message()

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

### Community 84 - "_connect_with_retry"
Cohesion: 0.09
Nodes (11): _connect_with_retry(), create_worker(), _register_shutdown_handlers(), _remove_shutdown_handlers(), _request_shutdown(), run_worker(), workflow_activities(), ConnectWithRetryTests (+3 more)

### Community 85 - "ExtractedFact"
Cohesion: 0.18
Nodes (5): ExtractedFact, FactField, DemoAISuggestionProvider, _is_ambiguous_numeric_term(), _is_delivery_date_context()

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
Cohesion: 0.06
Nodes (10): _missing_trade_fields(), Constraint, ConstraintKind, ConstraintStatus, MessageSourceType, Visibility, _constraint_to_domain(), FakeCommunicationRepository (+2 more)

### Community 95 - "create_deal_route"
Cohesion: 0.20
Nodes (5): create_deal_route(), CreateDealRequest, DealResponse, DealSummaryResponse, _to_response()

### Community 98 - "Master Execution Contract"
Cohesion: 0.14
Nodes (31): Execution Acceptance Gates, Master Execution Contract, Safe Windows PowerShell Runner, Private Contact Channels, Profiles Specification F14, Fresh Authorization Enforcement, Permissions Specification F15a, Append-Only Fulfillment Observations and Confirmations (+23 more)

### Community 99 - "0005 Conversation Party Unique (Enforce"
Cohesion: 0.36
Nodes (5): _create_party_unique_constraint(), _deduplicate_conversations(), downgrade(), _drop_party_unique_constraint(), upgrade()

### Community 101 - "Safe Operations and Recovery Guide"
Cohesion: 0.19
Nodes (15): PayPal Sandbox Invoicing and Reconciliation Flow, Backend README Document, F11a Explicit Payment Modes, F12 Committed Trade Packs, F1a Curated Repeatable Demo Fixture, F4 Invitations and Private Pending Deals, F5 Persisted Human Negotiation, F6 Agreement History and Comparison (+7 more)

### Community 102 - "OrganizationRepositoryTests"
Cohesion: 0.20
Nodes (4): Organization, _organization_to_domain(), SqlAlchemyOrganizationRepository, OrganizationRepositoryTests

### Community 104 - "openai.py"
Cohesion: 0.09
Nodes (16): AIPermanentError, AITransientError, FactExtractionRequest, parse_extracted_facts(), parse_proposed_terms(), ProposalDraftRequest, AiContext, ProposedTerms (+8 more)

### Community 108 - "OnboardingWizard.tsx"
Cohesion: 0.14
Nodes (13): COUNTRY_NAMES, CountryOption, describeError(), isAmbiguousCreateFailure(), OnboardingWizard(), findExistingOrganization(), handleSubmit(), OnboardingWizardProps (+5 more)

### Community 110 - ".test_rejected_closure_keeps_approved_agreement_committable"
Cohesion: 0.26
Nodes (5): _display(), _render(), Agreement, AgreementId, FakeAgreementRepository

### Community 111 - "ActorContext"
Cohesion: 0.08
Nodes (10): can_view_constraint(), can_view_message(), confirm_constraint(), select_ai_context(), visible_to_viewer(), ActorContext, DealParticipation, AiContextSelectionTests (+2 more)

### Community 113 - "_is_one_active_per_milestone_violation"
Cohesion: 0.43
Nodes (3): _is_idempotency_key_violation(), _is_one_active_per_milestone_violation(), _violated_constraint_name()

### Community 114 - "InvalidTransition"
Cohesion: 0.11
Nodes (10): NegotiationSession, NegotiationSubmissionOutcome, Proposal, ProposalStatus, PaymentIntent, InvalidTransition, NegotiationSessionId, build_proposal() (+2 more)

### Community 115 - "TradeTerms"
Cohesion: 0.18
Nodes (4): _decimal(), TradeTerms, value(), with_timing()

### Community 116 - "create_refresh_token"
Cohesion: 0.24
Nodes (6): _as_utc(), create_refresh_token(), _encode_access_token(), _issue_tokens(), _replay_rotation(), _revoke_family()

### Community 117 - "NegotiationPostgresRaceTests"
Cohesion: 0.08
Nodes (12): create_agreement_draft(), create_reviewed_agreement_draft(), CreateAgreementDraftCommand, CreateReviewedAgreementDraftCommand, create_agreement_draft_in_transaction(), create_reviewed_agreement_draft_in_transaction(), NegotiationPostgresRaceTests, run() (+4 more)

### Community 119 - "Final Gates and Truthful Completion Specification"
Cohesion: 0.20
Nodes (9): Evidence-Free Projection and Safety Bounds, F12 Trade Pack Handoff Document, Trade Pack Export Contract, Browser Verification Specification, ZIP HTML and Print Export Verification, Two-Party Isolated Browser Testing, Final Gates and Truthful Completion Specification, Full Gate Verification Suite (+1 more)

### Community 120 - "Skill (Repo Idea Thinker Skill)"
Cohesion: 0.50
Nodes (3): Repo Idea Thinker Skill, Repository-Grounded Ideation Discipline, Idea Quality Standards and Lightweight Validation

### Community 122 - "login"
Cohesion: 0.23
Nodes (6): CredentialsRequest, login(), TokenResponse, hash_password(), fail(), scalar()

### Community 134 - "simulate_payment"
Cohesion: 0.19
Nodes (6): DevResetResponse, DevRoleSwitchRequest, reset_demo(), simulate_payment(), SimulatePaymentRequest, switch_role()

### Community 139 - "auth.py"
Cohesion: 0.06
Nodes (9): get_deal_repository(), _require_dev_environment(), database_health(), health(), OperationalFastAPI, _persist_paypal_webhook_event(), list_deals(), verify_password() (+1 more)

### Community 140 - "InvariantViolation"
Cohesion: 0.13
Nodes (6): _normalized_text(), _require_decimal(), _normalize_string(), OrganizationContact, InvariantViolation, OrganizationContactDomainTests

### Community 141 - "sqlalchemy"
Cohesion: 0.05
Nodes (25): upgrade(), uuid_column(), upgrade(), upgrade(), upgrade(), upgrade(), downgrade(), upgrade() (+17 more)

### Community 143 - "get_commercial_document_draft_route"
Cohesion: 0.20
Nodes (4): CommercialDocumentDraftResponse, get_commercial_document_draft_route(), get_trade_pack_route(), CommercialDocumentDraft

### Community 144 - "generate_trade_pack"
Cohesion: 0.32
Nodes (9): export_display_terms(), generate_trade_pack(), InvalidTradePack, _json_bytes(), _shape(), _trade_pack_html(), section(), TradePack (+1 more)

### Community 145 - "_domain_deal"
Cohesion: 0.36
Nodes (4): _domain_deal(), _FakeAgreementRepository, _FakeDealRepository, WorkflowStateApplicationTests

### Community 147 - "AI Provider Boundary Specification"
Cohesion: 0.53
Nodes (4): F2 AI Configuration and Provider Boundary, AI Provider Boundary Specification, AI Resilience and Retry Policy, AISuggestionProvider Contract

### Community 148 - "read_deal_route"
Cohesion: 0.25
Nodes (3): list_deals_route(), read_deal_route(), _viewer_role()

### Community 160 - ".test_refresh_rotates_token_and_revokes_previous_token"
Cohesion: 0.10
Nodes (4): _hash_refresh_token(), refresh_access_token(), RefreshRequest, RefreshToken

### Community 162 - "0004_communication_sources_and_scope_indexes.py"
Cohesion: 0.60
Nodes (4): _create_scope_index(), downgrade(), _drop_scope_index(), upgrade()

## Knowledge Gaps
- **47 isolated node(s):** `syncally`, `F1a Curated Repeatable Demo Fixture`, `Editorial Dark Theme Design System`, `ZIP HTML and Print Export Verification`, `Whole-Worktree Independent Review` (+42 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1300 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **59 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ActorContext` connect `ActorContext` to `Conversations & Test Conversation Use`, `api/payments.py`, `DealId`, `simulate_payment`, `Seed Demo & Deals`, `api/agreements.py`, `Test Conversation Routes (ConversationRouteTests)`, `auth.py`, `create_deal`, `get_current_actor`, `Test Agreement Routes (AgreementRouteTests)`, `get_commercial_document_draft_route`, `ai.py`, `read_deal_route`, `CommercialDocumentDraftTests`, `Simulate Deal Flow & Test`, `Test Organization Invitations & Organizations`, `.has_capability`, `sqlalchemy`, `User`, `application/agreements.py`, `repositories/organizations.py`, `Test Payment Intent Repository &`, `repositories/fulfillment.py`, `AISuggestionProviderTests`, `Test Organization Directory & Organizations`, `Deal`, `Organizations & Test Organization Onboarding`, `api/fulfillment.py`, `Test Deal Routes & Identity`, `Test Identity Boundary & Config`, `InvalidTransition`, `api/organizations.py`, `Negotiation (BaseRequest)`, `ConversationUseCaseTests`, `Test Communication Repositories (MessageIdempotencyPostgresTests)`, `Test Negotiation (NegotiationRouteTests)`, `create_deal_route`, `review_constraint`, `FulfillmentRouteTests`?**
  _High betweenness centrality (0.137) - this node is a cross-community bridge._
- **Are the 113 inferred relationships involving `ActorContext` (e.g. with `approve_agreement_route()` and `commit_agreement_route()`) actually correct?**
  _`ActorContext` has 113 INFERRED edges - model-reasoned connections that need verification._
- **What connects `syncally`, `F1a Curated Repeatable Demo Fixture`, `Editorial Dark Theme Design System` to the rest of the system?**
  _47 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Conversations & Test Conversation Use` be split into smaller, more focused modules?**
  _Cohesion score 0.04812698412698413 - nodes in this community are weakly interconnected._
- **Why does `OrganizationId` connect `DealId` to `Conversations & Test Conversation Use`, `AIContractError`, `api/payments.py`, `Seed Demo & Deals`, `api/agreements.py`, `Test Conversation Routes (ConversationRouteTests)`, `create_deal`, `Test Agreement Routes (AgreementRouteTests)`, `ai.py`, `NegotiationTests`, `_domain_deal`, `Money`, `CommercialDocumentDraftTests`, `Test Outbox Dispatcher & Outbox`, `Test Organization Invitations & Organizations`, `SqlAlchemyCommunicationRepository`, `sqlalchemy`, `User`, `application/agreements.py`, `AgreementCommitTests`, `repositories/organizations.py`, `Test Payment Intent Repository &`, `repositories/fulfillment.py`, `AISuggestionProviderTests`, `SqlAlchemyDealRepository`, `repositories/negotiation.py`, `Deal`, `InvalidTransition`, `api/organizations.py`, `contracts.py`, `build_terms`, `AgreementVersionId`, `Negotiation (BaseRequest)`, `SqlAlchemyAgreementRepository`, `ConversationUseCaseTests`, `Test Counterparty Onboarding Migration &`, `Constraint`, `OrganizationRepositoryTests`, `openai.py`, `Test Negotiation Migration (NegotiationMigrationTests)`, `.test_rejected_closure_keeps_approved_agreement_committable`, `ActorContext`, `FulfillmentRouteTests`, `InvalidTransition`, `TradeTerms`?**
  _High betweenness centrality (0.090) - this node is a cross-community bridge._
- **Are the 58 inferred relationships involving `OrganizationId` (e.g. with `create_reviewed_agreement_draft_route()` and `write_negotiation()`) actually correct?**
  _`OrganizationId` has 58 INFERRED edges - model-reasoned connections that need verification._
- **Should `AIContractError` be split into smaller, more focused modules?**
  _Cohesion score 0.12560975609756098 - nodes in this community are weakly interconnected._