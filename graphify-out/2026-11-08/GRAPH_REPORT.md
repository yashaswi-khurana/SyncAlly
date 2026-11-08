# Graph Report - SyncAlly  (2026-11-07)

## Corpus Check
- 369 files · ~334,845 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 14 file(s) not represented in the graph (top: (none) 8, .example 2, .ini 1)

## Summary
- 5653 nodes · 18555 edges · 185 communities (134 shown, 51 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 2462 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `53018ee0`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Conversations & Test Conversation Use
- AIContractError
- BaseModel
- repositories/agreements.py
- Test Ai Provider & Ai
- api/reminders.py
- repositories/agreements.py
- PaymentNeedsAction
- canonical_decimal
- api/agreements.py
- Test Conversation Routes (ConversationRouteTests)
- SqlAlchemyPaymentIntentRepository
- Test Agreement Routes (AgreementRouteTests)
- FulfillmentRouteTests
- process_payment_intent
- AISuggestionProviderTests
- NegotiationTests
- Types & Client
- listOrganizations
- OrganizationPermissionsTests
- CommunicationRepositoryTests
- Test Outbox Dispatcher & Outbox
- Simulate Deal Flow & Test
- Test Organization Invitations & Organizations
- SqlAlchemyCommunicationRepository
- Package & Vite.Config
- Organization
- Dealconversationreview & Dealconversationreview.Test
- Skill & Skill.Md
- identifiers.py
- User
- repositories/negotiation.py
- demo_lifecycle.py
- Aisuggestionreview & Suggestionpreview
- SyncAlly Implementation Plan Document
- PaymentProcessingTests
- application/deal_cases.py
- log_operation
- ApprovalRoutingTestCase
- Paymentstatuspanel & Paymentstatuspanel.Test
- PaymentIntentRepositoryTests
- services
- api/deals.py
- repositories/agreements.py
- DealWorkflow
- Test Dev Routes (DevRoutesTests)
- _case_insensitive_prefix
- DealWorkflow
- Test Organization Directory & Organizations
- create_deal
- .test_generates_draft_from_schema_2_committed_terms
- Deal
- PaymentOutboxWorkerTests
- api/payments.py
- gmail.py
- DealDetailPage.test.tsx
- RemindersPanel.tsx
- _active_admin_membership
- CommercialDocumentDraftTests
- Test Migration Lock & Env
- Payment Processing & Test Payment
- 01 Commercial Domain Model &
- create_counterparty_invitation
- Test Deal Routes & Identity
- api/negotiation.py
- Compose.Yaml (volumes)
- Architectural & Implementation Plan: Step 08 Cancel Disputes (F8)
- react
- AmendmentTests
- OrganizationId
- ExtractedFact
- Money
- PersistentDemoSeedTests
- AgreementReview.tsx
- refresh_access_token
- Visibility
- commit_agreement
- IdentityBoundaryTests
- Optional AI Specification
- Tsconfig (tsconfig.json)
- Test Paypal Webhooks (FakeWebhookVerifier)
- NegotiationPostgresRaceTests
- contracts.py
- repositories/__init__.py
- SafeOperationsTests
- environment
- Main & Test Identity Boundary
- Deploying SyncAlly's Temporal workers on AWS
- Collections API and UI Specification F10b
- ApiError
- Test Organization Index Migration (OrganizationIndexPostgresMigrationTests)
- Server-Enforced Capability Matrix
- 0024_deal_display_name.py
- NegotiationRouteTests
- InvalidTransition
- amendment.py
- application/conversations.py
- DatabasePersistenceTests
- Master Execution Contract
- 0005 Conversation Party Unique (Enforce
- Main (Request)
- Safe Operations and Recovery Guide
- temporal-namespace
- ai.py
- openai.py
- .__call__
- x-app-environment
- Test Payment Mode Migration (PaymentModeMigrationTests)
- environment
- Test Communication Migration (ConversationPartyUniquenessMigrationTests)
- create_worker
- ConversationContractTests
- ApprovalRoutingRouteTests
- NegotiationCommand
- healthcheck
- AddMessageRequest
- DealWorkflowInput
- AiContextSelectionTests
- DealCasesTests
- Final Gates and Truthful Completion Specification
- Skill (Repo Idea Thinker Skill)
- OrganizationRegistrationRequest
- Vite Env.D (ImportMeta)
- temporal-schema
- VerifiedProviderPaymentState
- Index (Frontend HTML Root Document)
- Pyproject (syncally)
- Customer journey: buyer and seller
- InvariantViolation
- sqlalchemy
- scaling
- Deal
- SyncAlly deployment
- Code Review: Step 08 Cancel Disputes (F8) — Work Package RV1
- DealDetailPage.test.tsx
- ProposalComparison.tsx
- api/fulfillment.py
- OnboardingWizard.tsx
- AIConfigurationError
- volumes
- MASTER BOARD
- setup-temporal-postgres.sh
- FulfillmentMigrationTests
- ProviderInvoiceUniqueMigrationTests
- database_health
- activities.py
- MigrationConfigTests
- CollectionSchemaMigrationTests
- create-temporal-namespace.sh
- postgres-init.sh
- get_commercial_document_draft_route
- ConversationUseCaseTests
- .test_remote_currency_evidence_controls_routes_without_retry_or_fallback
- get_optional_actor
- STATE LOG: developer
- HealthRouteTests
- 0004_communication_sources_and_scope_indexes.py
- send
- MilestonePaymentsMigrationTests
- STATE LOG: planner
- NegotiationMigrationTests
- STATE LOG: reviewer
- CONTRACT: cancel-disputes-contract v1   status: FROZEN
- organization.py
- auth.py
- Constraint
- hostless-start.sh
- main.py
- SyncAlly: Confirmed Bugs and Feature Roadmap
- Frontend product review
- NotificationKind

## God Nodes (most connected - your core abstractions)
1. `ActorContext` - 313 edges
2. `OrganizationId` - 241 edges
3. `InvariantViolation` - 150 edges
4. `UserId` - 139 edges
5. `Money` - 127 edges
6. `DealId` - 122 edges
7. `Deal` - 114 edges
8. `SqlAlchemyAgreementRepository` - 113 edges
9. `TradeTerms` - 87 edges
10. `AISuggestionProviderTests` - 87 edges

## Surprising Connections (you probably didn't know these)
- `1. Executive Summary & Change Stack Digest` --references--> `_resolve_deal_party_organization()`  [INFERRED]
  .orchestrator/reviews/RV1/review.md → backend/src/syncally/api/deals.py
- `5. Audit Checklist Verification` --references--> `_resolve_deal_party_organization()`  [INFERRED]
  .orchestrator/reviews/RV1/review.md → backend/src/syncally/api/deals.py
- `AST Metrics Table` --references--> `_raise_case_impl()`  [INFERRED]
  .orchestrator/reviews/RV1/review.md → backend/src/syncally/api/deals.py
- `AST Metrics Table` --references--> `_respond_case_impl()`  [INFERRED]
  .orchestrator/reviews/RV1/review.md → backend/src/syncally/api/deals.py
- `Existing Codebase Behavior` --references--> `InvalidTransition`  [INFERRED]
  .orchestrator/plans/cancel_disputes_plan.md → backend/src/syncally/domain/shared/errors.py

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

## Communities (185 total, 51 thin omitted)

### Community 0 - "Conversations & Test Conversation Use"
Cohesion: 0.07
Nodes (44): add_message_route(), AISuggestionRequest, clarify_fact_route(), confirm_fact_route(), ConstraintResponse, correct_fact_route(), CorrectFactRequest, create_fact_route() (+36 more)

### Community 1 - "AIContractError"
Cohesion: 0.13
Nodes (13): parse_extracted_facts(), AIContractError, AIValidationClaim, _check_keys(), _decimal(), _required_string(), scope_extracted_facts(), _validate_decimal() (+5 more)

### Community 2 - "BaseModel"
Cohesion: 0.10
Nodes (9): AcceptInvitationResponse, ApprovalRoutingPolicyRequest, ApprovalRoutingPolicyResponse, ContactPayload, ContactResponse, OrganizationDirectoryItem, OrganizationMemberResponse, ProfileResponse (+1 more)

### Community 3 - "repositories/agreements.py"
Cohesion: 0.09
Nodes (17): AgreementAccessDenied, AgreementNotFound, AgreementVersionConflict, CreateAgreementDraftCommand, UnauthorizedApproval, WrongTermsHash, AmendmentConflict, AmendmentError (+9 more)

### Community 4 - "Test Ai Provider & Ai"
Cohesion: 0.08
Nodes (14): AIRetryPolicy, call_with_bounded_retry(), extract_facts_from_context(), ConfiguredAIProvider, respond(), respond(), respond(), respond() (+6 more)

### Community 5 - "api/reminders.py"
Cohesion: 0.04
Nodes (25): get_deal_reminders(), ReminderResponse, _resolve_actor_deal_org(), suppress_reminder(), sync_reminders(), _to_response(), trigger_dispatch(), dispatch_due_reminders() (+17 more)

### Community 6 - "repositories/agreements.py"
Cohesion: 0.05
Nodes (37): _accept_invitation(), CounterpartyInvitationResponse, InvitationResponse, _clear_fixture(), _create_fixture(), _delete_scoped(), DemoCollisionError, DemoIdentity (+29 more)

### Community 7 - "PaymentNeedsAction"
Cohesion: 0.09
Nodes (11): receive_paypal_invoice_webhook(), PaymentNeedsAction, PaymentOutcomeUnknown, PaymentRetryableError, _has_excess_currency_precision(), PayPalSandboxInvoiceProvider, _provider_error_code(), _provider_request_id() (+3 more)

### Community 8 - "canonical_decimal"
Cohesion: 0.10
Nodes (11): get_paypal_webhook_configuration(), PaymentInvoiceLookup, PaymentInvoiceRequest, PaymentWorkItem, main(), run_forever(), GmailSettings, PayPalSettings (+3 more)

### Community 9 - "api/agreements.py"
Cohesion: 0.05
Nodes (45): AgreementVersionResponse, AmendmentImpactResponse, ApprovalResponse, approve_agreement_route(), commit_agreement_route(), CommitAgreementRequest, compare_agreements_route(), create_agreement_draft_route() (+37 more)

### Community 11 - "SqlAlchemyPaymentIntentRepository"
Cohesion: 0.14
Nodes (3): PaymentStatusResponse, PaymentIntent, PaymentStatusExtendedModelTests

### Community 13 - "FulfillmentRouteTests"
Cohesion: 0.17
Nodes (5): build_obligations(), build_payment_milestones(), ObligationDraft, PaymentMilestoneDraft, FulfillmentRouteTests

### Community 14 - "process_payment_intent"
Cohesion: 0.08
Nodes (7): payment_invoice_number(), PaymentInvoiceProvider, PaymentProcessingRepository, process_payment_intent(), reconcile_payment_intent(), _request_id_retry_window_expired(), require_payment_provider()

### Community 15 - "AISuggestionProviderTests"
Cohesion: 0.11
Nodes (4): DeterministicFakeAIProvider, AISuggestionProviderTests, extract_facts(), FakeWebhookVerifier

### Community 16 - "NegotiationTests"
Cohesion: 0.20
Nodes (4): EvidenceReference, ProposalBase, negotiate_in_transaction(), NegotiationTests

### Community 17 - "Types & Client"
Cohesion: 0.04
Nodes (98): closeMarketplaceRFQ(), createMarketplaceListing(), createMarketplaceRFQ(), deactivateMarketplaceListing(), describeDetail(), getDealMessageExistence(), isAbortError(), isRecord() (+90 more)

### Community 18 - "listOrganizations"
Cohesion: 0.05
Nodes (67): dependencies, react@^19.3.0, react-dom@^19.3.0, three@^0.186.1, getCurrentUser(), listOrganizations(), login(), registerOrganization() (+59 more)

### Community 19 - "OrganizationPermissionsTests"
Cohesion: 0.07
Nodes (18): _active_admin_membership(), _compute_effective_capabilities(), _deal_awaiting_counterparty(), delete_approval_routing_policy_route(), get_approval_routing_policy_route(), get_organization_profile_route(), get_organization_route(), list_my_organizations() (+10 more)

### Community 20 - "CommunicationRepositoryTests"
Cohesion: 0.11
Nodes (6): ConstraintId, ConversationId, MessageId, constraint(), message(), CommunicationRepositoryTests

### Community 21 - "Test Outbox Dispatcher & Outbox"
Cohesion: 0.09
Nodes (14): build_deal_workflow_id(), DealWorkflowStarter, dispatch_outbox_event(), OutboxDispatchResult, PendingOutboxEvent, apply_dispatch_result(), claim_next_pending_event(), _claim_statement() (+6 more)

### Community 22 - "Simulate Deal Flow & Test"
Cohesion: 0.07
Nodes (11): _build_in_process_client(), dispatch_payment(), session_factory(), ci_deal_flow_hook(), DealFlowContext, DealFlowSimulator, run_simulation(), SimulationError (+3 more)

### Community 23 - "Test Organization Invitations & Organizations"
Cohesion: 0.15
Nodes (6): accept_invitation(), AcceptInvitationRequest, create_organization_invitation(), CreateInvitationRequest, _decode_invitation_token(), OrganizationInvitationTests

### Community 24 - "SqlAlchemyCommunicationRepository"
Cohesion: 0.08
Nodes (10): can_view_message(), message_fingerprint(), Conversation, Message, CommunicationScopeError, _conversation_to_domain(), _is_unique_violation(), _message_to_domain() (+2 more)

### Community 25 - "Package & Vite.Config"
Cohesion: 0.06
Nodes (47): devDependencies, eslint@^10.13.0, @eslint/js@^10.0.1, eslint-plugin-react-hooks@^7.1.1, eslint-plugin-react-refresh@^0.4.20, globals@^17.13.0, happy-dom@^21.0.3, @testing-library/dom@^10.4.1 (+39 more)

### Community 26 - "Organization"
Cohesion: 0.04
Nodes (59): API_REQUEST_TIMEOUT_MS, deleteApprovalRoutingPolicy(), getApprovalRoutingPolicy(), getCommercialDocumentDraft(), listOrganizationMembers(), putApprovalRoutingPolicy(), revokeOrganizationMember(), CREATED_MESSAGE (+51 more)

### Community 27 - "Dealconversationreview & Dealconversationreview.Test"
Cohesion: 0.07
Nodes (45): createDealMessage(), importDealThread(), listDealFacts(), listDealMessages(), previewDealThreadImport(), reviewDealFact(), updateFactVisibility(), Visibility (+37 more)

### Community 28 - "Skill & Skill.Md"
Cohesion: 0.04
Nodes (43): API and Database Engineer Skill, API Design and Contract Semantics, Data Integrity and Invariant Enforcement, Query Performance and Projection Optimization, Schema Migration and Backward Compatibility, Transaction Boundaries and Atomicity, Archify Diagrammer Skill, Archify CLI Global Tool (+35 more)

### Community 30 - "User"
Cohesion: 0.19
Nodes (5): add_organization_member(), AddOrganizationMemberRequest, create_organization(), CreateOrganizationRequest, OrganizationOnboardingTests

### Community 31 - "repositories/negotiation.py"
Cohesion: 0.18
Nodes (7): NegotiationConflict, NegotiationNotFound, NegotiationOrganizationRequired, ProposalId, NegotiationAction, SqlAlchemyNegotiationRepository, projection()

### Community 32 - "demo_lifecycle.py"
Cohesion: 0.19
Nodes (8): _acquire_lock(), _is_demo_deal(), lock_demo_deal_creation(), lock_demo_payment_processing(), lock_demo_reset(), lock_outbox_dispatch(), DemoLifecycleLockTests, _postgres_session()

### Community 33 - "Aisuggestionreview & Suggestionpreview"
Cohesion: 0.09
Nodes (38): correctDealFact(), createDealFact(), draftDealProposal(), getNegotiation(), suggestDealFacts(), AIProvenance, DealFact, FactReviewAction (+30 more)

### Community 34 - "SyncAlly Implementation Plan Document"
Cohesion: 0.13
Nodes (16): SyncAlly Architecture Document, System Topology and Ownership Boundaries, Temporal Worker and Outbox Architecture, AI Provider Boundary Specification, AI Resilience and Retry Policy, AISuggestionProvider Contract, Acceptance Criteria Verification Matrix, SyncAlly Implementation Plan Document (+8 more)

### Community 35 - "PaymentProcessingTests"
Cohesion: 0.14
Nodes (5): FakeInvoiceProvider, FakeProcessingRepository, PaymentProcessingTests, _request(), _work_item()

### Community 36 - "application/deal_cases.py"
Cohesion: 0.09
Nodes (27): add_case_evidence(), AddCaseEvidenceCommand, assess_deal_case_blockers(), DealCaseRepository, DealNotFound, list_deal_cases(), raise_deal_case(), RaiseDealCaseCommand (+19 more)

### Community 37 - "log_operation"
Cohesion: 0.14
Nodes (14): _connect_with_retry(), main(), run_forever(), main(), is_permanent_rpc_error(), configure_logging(), log_operation(), Operation (+6 more)

### Community 38 - "ApprovalRoutingTestCase"
Cohesion: 0.12
Nodes (7): ApprovalRoutingMode, ApprovalRoutingPolicy, UserId, routing_policy_to_domain(), SqlAlchemyApprovalRoutingPolicyRepository, ApprovalRoutingTestCase, OrganizationMemberDomainTests

### Community 39 - "Paymentstatuspanel & Paymentstatuspanel.Test"
Cohesion: 0.09
Nodes (31): authorizeDealPayment(), listDealPaymentMilestones(), listPaymentStatuses(), previewDealPayment(), PaymentIntentStatus, formatCountdown(), parseTimestamp(), describeStatus() (+23 more)

### Community 40 - "PaymentIntentRepositoryTests"
Cohesion: 0.11
Nodes (4): _persist_paypal_webhook_event(), authorize_payment_intent_in_transaction(), record_paypal_webhook_event(), PaymentIntentRepositoryTests

### Community 41 - "services"
Cohesion: 0.09
Nodes (29): build, depends_on, restart, context, dockerfile, migrate, temporal-namespace, build (+21 more)

### Community 42 - "api/deals.py"
Cohesion: 0.11
Nodes (33): add_evidence_deals_route(), _add_evidence_impl(), add_evidence_v1_route(), AddEvidenceRequest, CaseEvidenceResponse, CaseResponse, create_deal_route(), CreateDealRequest (+25 more)

### Community 43 - "repositories/agreements.py"
Cohesion: 0.05
Nodes (35): AgreementAlreadyCommitted, AgreementRepository, create_agreement_draft(), create_reviewed_agreement_draft(), CreateReviewedAgreementDraftCommand, DuplicateApproval, NotEligibleApprover, OutOfSequenceApproval (+27 more)

### Community 44 - "DealWorkflow"
Cohesion: 0.13
Nodes (7): DealWorkflowInput, DealWorkflowStatus, _require_uuid(), new_workflow_input(), RefreshActivity, RefreshCall, WorkflowWorkerIntegrationTests

### Community 46 - "_case_insensitive_prefix"
Cohesion: 0.29
Nodes (3): _case_insensitive_prefix(), _escape_like(), value()

### Community 47 - "DealWorkflow"
Cohesion: 0.12
Nodes (6): DealWorkflow, DealWorkflowResult, DealWorkflowTests, DealWorkflowUnitTests, new_notification(), run()

### Community 49 - "create_deal"
Cohesion: 0.15
Nodes (6): _both_organizations_active(), create_deal(), CreateDealCommand, DealAccessDenied, DealUseCaseTests, FakeDealRepository

### Community 50 - ".test_generates_draft_from_schema_2_committed_terms"
Cohesion: 0.14
Nodes (8): _display(), _render(), Agreement, AgreementId, FakeAgreementRepository, _FakeAgreementRepository, _FakeDealRepository, WorkflowStateApplicationTests

### Community 52 - "PaymentOutboxWorkerTests"
Cohesion: 0.09
Nodes (13): PaymentInvoiceNotifier, claim_next_payment_event(), _claim_statement(), _ClaimedPaymentEvent, dispatch_one_payment_event(), dispatch_pending_payment_events(), _finish_event(), _process_claimed_payment_event() (+5 more)

### Community 53 - "api/payments.py"
Cohesion: 0.04
Nodes (43): authorize_payment_route(), AuthorizePaymentRequest, AuthorizePaymentResponse, _check_milestone_delivery_confirmed(), get_payment_status_repository(), list_payment_milestones_route(), list_payment_statuses_route(), MilestoneAllocationResponse (+35 more)

### Community 54 - "gmail.py"
Cohesion: 0.09
Nodes (3): PaymentInvoiceNotice, _FakeSMTP, GmailSMTPInvoiceNotifierTests

### Community 55 - "DealDetailPage.test.tsx"
Cohesion: 0.05
Nodes (49): getDeal(), getOrganization(), negotiateDeal(), Deal, NegotiationView, AgreementReviewProps, DealCasesPanelProps, DealConstellation() (+41 more)

### Community 56 - "RemindersPanel.tsx"
Cohesion: 0.21
Nodes (14): listDealReminders(), suppressDealReminder(), syncDealReminders(), ReminderScope, ReminderStatus, formatUtc(), RemindersPanel(), scopeBadgeLabel() (+6 more)

### Community 57 - "_active_admin_membership"
Cohesion: 0.11
Nodes (15): close_marketplace_rfq(), create_marketplace_listing(), create_marketplace_rfq(), deactivate_marketplace_listing(), get_marketplace_listing(), get_marketplace_rfq(), MarketplaceListingRequest, MarketplaceListingResponse (+7 more)

### Community 58 - "CommercialDocumentDraftTests"
Cohesion: 0.14
Nodes (11): export_display_terms(), generate_commercial_document_draft(), generate_trade_pack(), InvalidTradePack, _json_bytes(), _shape(), _trade_pack_html(), section() (+3 more)

### Community 59 - "Test Migration Lock & Env"
Cohesion: 0.12
Nodes (8): run_migrations_online(), serialize_migrations(), _make_postgres_connection(), _make_sqlite_connection(), MigrationLockTests, simulated_migration(), PostgresRealAdvisoryLockTests, worker()

### Community 60 - "Payment Processing & Test Payment"
Cohesion: 0.17
Nodes (4): PaymentInvoiceLineItem, SqlAlchemyPaymentProcessingRepository, transition(), transition()

### Community 61 - "01 Commercial Domain Model &"
Cohesion: 0.07
Nodes (19): AgreementVersion Aggregate, Append-Only AuditEvent Ledger, Commercial Constraint and Provenance, Deal Aggregate, Organization and Membership Entities, PaymentMilestone and Obligation, Proposal Aggregate and Terms Hash, Temporal Deal Workflow (+11 more)

### Community 62 - "create_counterparty_invitation"
Cohesion: 0.14
Nodes (6): create_counterparty_invitation(), _create_invitation_token(), CreateCounterpartyInvitationRequest, OnboardingConcurrencyCases, OnboardingPostgresConcurrencyTests, OnboardingSQLiteConcurrencyTests

### Community 63 - "Test Deal Routes & Identity"
Cohesion: 0.20
Nodes (3): ActorContext, DealAuthorizationTests, DealRouteTests

### Community 64 - "api/negotiation.py"
Cohesion: 0.13
Nodes (12): BaseRequest, CandidateRequest, EvidenceRequest, HistoryResponse, NegotiationRequest, NegotiationResponse, NegotiationResult, ProposalResponse (+4 more)

### Community 65 - "Compose.Yaml (volumes)"
Cohesion: 0.09
Nodes (22): POSTGRES_DB, POSTGRES_PASSWORD, POSTGRES_USER, interval, retries, test, timeout, environment (+14 more)

### Community 66 - "Architectural & Implementation Plan: Step 08 Cancel Disputes (F8)"
Cohesion: 0.10
Nodes (19): 1. Executive Summary & Existing vs. Required Behavior, 2. Domain Entities & Value Objects, 3. Deal Aggregate Coordination, 4. Persistence Models & Alembic Migration 0025, 5. Application Layer: Use Cases & Operational Impact Assessment, 6. HTTP API Layer, 7. Frontend Integration, 9. Verification & Test Plan (+11 more)

### Community 67 - "react"
Cohesion: 0.07
Nodes (31): createCounterpartyInvitation(), createDeal(), getMarketplaceListing(), getMarketplaceRFQ(), listDeals(), ViewerRole, counterpartyInvitePreview(), counterpartyInviteUrl() (+23 more)

### Community 68 - "AmendmentTests"
Cohesion: 0.07
Nodes (10): CommitAgreementCommand, ProposeAmendmentCommand, RecordApprovalCommand, commit_agreement_in_transaction(), propose_amendment_in_transaction(), record_approval_in_transaction(), AgreementCommitTests, AmendmentTests (+2 more)

### Community 69 - "OrganizationId"
Cohesion: 0.08
Nodes (15): PaymentMilestone, AgreementVersionId, DealId, OrganizationId, PaymentIntentId, PaymentMilestoneId, AgreementVersion, _restore_domain_intent() (+7 more)

### Community 70 - "ExtractedFact"
Cohesion: 0.16
Nodes (6): ExtractedFact, FactField, SourceReference, DemoAISuggestionProvider, _is_ambiguous_numeric_term(), _is_delivery_date_context()

### Community 71 - "Money"
Cohesion: 0.13
Nodes (16): build_trade_terms_from_request(), PaymentObligationAllocation, PaymentTerm, ShipmentItemAllocation, ShipmentTerm, TradeLineItem, TradeTerms, Money (+8 more)

### Community 72 - "PersistentDemoSeedTests"
Cohesion: 0.10
Nodes (7): fixture_id(), initialize_offline_database(), main(), OutboxEvent, PersistentDemoSeedTests, exercise_api(), dispatch()

### Community 73 - "AgreementReview.tsx"
Cohesion: 0.08
Nodes (53): acceptInvitation(), apiBaseUrl(), ApiError, apiRequest(), commitAgreementVersion(), compareAgreementVersions(), createAgreementFromReviewedTerms(), getAgreementHistory() (+45 more)

### Community 74 - "refresh_access_token"
Cohesion: 0.06
Nodes (4): _hash_refresh_token(), refresh_access_token(), RefreshRequest, RefreshToken

### Community 75 - "Visibility"
Cohesion: 0.17
Nodes (8): persist_fact_candidates(), CreateManualConstraintCommand, ConstraintKind, ConstraintStatus, MessageSourceType, Visibility, _constraint_to_domain(), DatabaseEngineTests

### Community 76 - "commit_agreement"
Cohesion: 0.16
Nodes (6): assess_amendment_impact(), AuditEventDraft, AuditRepository, commit_agreement(), ObligationRepository, PaymentMilestoneRepository

### Community 77 - "IdentityBoundaryTests"
Cohesion: 0.07
Nodes (8): CredentialsRequest, _is_duplicate_membership_error(), _is_loopback_temporal_address(), _is_weak_jwt_secret(), Settings, IdentityBoundaryTests, fail(), scalar()

### Community 78 - "Optional AI Specification"
Cohesion: 0.29
Nodes (4): PayPal Sandbox Lifecycle Verification, Optional AI Specification, Human-Grounded AI Suggestion Evaluation, No AI Approval or Legal Authority Boundary

### Community 79 - "Tsconfig (tsconfig.json)"
Cohesion: 0.11
Nodes (17): compilerOptions, allowImportingTsExtensions, jsx, lib, module, moduleDetection, moduleResolution, noEmit (+9 more)

### Community 81 - "NegotiationPostgresRaceTests"
Cohesion: 0.08
Nodes (7): create_database_engine(), CounterpartyOnboardingMigrationTests, DemoFixtureMigrationTests, NegotiationPostgresRaceTests, failing(), succeed(), NegotiationSqliteRaceTests

### Community 82 - "contracts.py"
Cohesion: 0.22
Nodes (9): _contains_numeric_token(), _contains_token(), _date_value_is_present(), _fact_value_is_supported_by_quote(), _flexible_whitespace_pattern(), _number_with_currency_is_present(), _number_with_unit_is_present(), _numeric_pattern() (+1 more)

### Community 83 - "repositories/__init__.py"
Cohesion: 0.15
Nodes (4): SqlAlchemyAuditRepository, SqlAlchemyObligationRepository, SqlAlchemyOutboxRepository, SqlAlchemyPaymentMilestoneRepository

### Community 84 - "SafeOperationsTests"
Cohesion: 0.22
Nodes (4): captured_output(), SafeOperationsTests, exercise(), failed_db()

### Community 85 - "environment"
Cohesion: 0.28
Nodes (28): environment, AI_PROVIDER, APP_ENV, DATABASE_URL, DEBUG, DEFAULT_NAMESPACE, GMAIL_APP_PASSWORD, GMAIL_FROM_EMAIL (+20 more)

### Community 87 - "Deploying SyncAlly's Temporal workers on AWS"
Cohesion: 0.09
Nodes (21): AWS layout, Build and deploy the worker services, Configure Temporal Cloud, Current deployment placement, Database and security boundaries, Deploying SyncAlly's Temporal workers on AWS, If Temporal itself must run in AWS, Provisioned so far (+13 more)

### Community 88 - "Collections API and UI Specification F10b"
Cohesion: 0.14
Nodes (12): Append-Only Fulfillment Observations and Confirmations, Canonical Hash and Legacy Export Preservation, Collection Schema Specification F10a, Versioned Item Shipment Payment Collections, Collections API and UI Specification F10b, Deterministic Version-Aware Export Downloads, Structured Collection Authoring and Review, Milestone Payment Intent State Machine (+4 more)

### Community 89 - "ApiError"
Cohesion: 0.09
Nodes (20): addOrganizationMember(), getOrganizationProfile(), updateOrganizationProfile(), ContactVisibility, Organization, OrganizationContact, MarketplacePageProps, Props (+12 more)

### Community 92 - "0024_deal_display_name.py"
Cohesion: 0.36
Nodes (4): _deal_names_table(), downgrade(), _rollback_backup_table(), upgrade()

### Community 94 - "InvalidTransition"
Cohesion: 0.12
Nodes (9): NegotiationSession, NegotiationSubmissionOutcome, Proposal, ProposalStatus, InvalidTransition, NegotiationSessionId, build_proposal(), HumanNegotiationTests (+1 more)

### Community 95 - "amendment.py"
Cohesion: 0.19
Nodes (6): compare_agreement_terms(), AmendmentAlreadyCommitted, AmendmentImpact, assess_amendment_impact(), FulfillmentObligationImpact, PaymentMilestoneImpact

### Community 96 - "application/conversations.py"
Cohesion: 0.06
Nodes (20): _list_all_constraints_for_owner(), add_message(), can_view_constraint(), CommunicationRepository, ConstraintRepository, correct_constraint(), create_manual_constraint(), deal_has_any_message() (+12 more)

### Community 98 - "Master Execution Contract"
Cohesion: 0.11
Nodes (30): Execution Acceptance Gates, Master Execution Contract, Safe Windows PowerShell Runner, Four-Dimension Profile Collections, Private Contact Channels, Profiles Specification F14, Fresh Authorization Enforcement, Permissions Specification F15a (+22 more)

### Community 99 - "0005 Conversation Party Unique (Enforce"
Cohesion: 0.36
Nodes (5): _create_party_unique_constraint(), _deduplicate_conversations(), downgrade(), _drop_party_unique_constraint(), upgrade()

### Community 101 - "Safe Operations and Recovery Guide"
Cohesion: 0.18
Nodes (16): PayPal Sandbox Invoicing and Reconciliation Flow, Backend README Document, F11a Explicit Payment Modes, F12 Committed Trade Packs, F1a Curated Repeatable Demo Fixture, F2 AI Configuration and Provider Boundary, F4 Invitations and Private Pending Deals, F5 Persisted Human Negotiation (+8 more)

### Community 102 - "temporal-namespace"
Cohesion: 0.09
Nodes (22): condition, aliases, api, temporal, APP_DOMAIN, TEMPORAL_DOMAIN, default, temporal-namespace (+14 more)

### Community 103 - "ai.py"
Cohesion: 0.09
Nodes (21): AIProvenance, AISuggestionProvider, draft_proposal(), draft_proposal_from_context(), extract_facts(), fact_suggestion_guidance(), FactExtractionResult, missing_trade_fields() (+13 more)

### Community 104 - "openai.py"
Cohesion: 0.09
Nodes (16): AIPermanentError, AIProviderError, AITransientError, FactExtractionRequest, parse_proposed_terms(), ProposalDraftRequest, AiContext, ProposedTerms (+8 more)

### Community 106 - "x-app-environment"
Cohesion: 0.09
Nodes (22): x-app-environment, AI_PROVIDER, APP_ENV, DATABASE_URL, DEBUG, GMAIL_APP_PASSWORD, GMAIL_FROM_EMAIL, GMAIL_SMTP_USERNAME (+14 more)

### Community 108 - "environment"
Cohesion: 0.12
Nodes (20): environment, BIND_ON_IP, DB, DB_PORT, DBNAME, POSTGRES_DB, POSTGRES_PASSWORD, POSTGRES_PWD (+12 more)

### Community 110 - "create_worker"
Cohesion: 0.11
Nodes (7): create_worker(), _register_shutdown_handlers(), _remove_shutdown_handlers(), _request_shutdown(), workflow_activities(), WorkerShutdownSignalTests, WorkflowWorkerTests

### Community 111 - "ConversationContractTests"
Cohesion: 0.12
Nodes (4): confirm_constraint(), ConstraintNotFound, ConversationContractTests, FakeConstraintRepository

### Community 113 - "NegotiationCommand"
Cohesion: 0.42
Nodes (3): negotiate(), NegotiationCommand, NegotiationRepository

### Community 114 - "healthcheck"
Cohesion: 0.16
Nodes (18): healthcheck, healthcheck, image, restart, volumes, temporal-schema, interval, retries (+10 more)

### Community 115 - "AddMessageRequest"
Cohesion: 0.19
Nodes (3): AddMessageRequest, CreateFactRequest, AddMessageRequestTests

### Community 116 - "DealWorkflowInput"
Cohesion: 0.13
Nodes (4): RefreshDealStateActivity, _workflow_input_value(), RefreshDealStateActivityTests, factory()

### Community 119 - "Final Gates and Truthful Completion Specification"
Cohesion: 0.20
Nodes (9): Evidence-Free Projection and Safety Bounds, F12 Trade Pack Handoff Document, Trade Pack Export Contract, Browser Verification Specification, ZIP HTML and Print Export Verification, Two-Party Isolated Browser Testing, Final Gates and Truthful Completion Specification, Full Gate Verification Suite (+1 more)

### Community 120 - "Skill (Repo Idea Thinker Skill)"
Cohesion: 0.50
Nodes (3): Repo Idea Thinker Skill, Repository-Grounded Ideation Discipline, Idea Quality Standards and Lightweight Validation

### Community 122 - "OrganizationRegistrationRequest"
Cohesion: 0.29
Nodes (3): CurrentUserResponse, OrganizationRegistrationRequest, SystemAdminBootstrapRequest

### Community 134 - "temporal-schema"
Cohesion: 0.15
Nodes (13): condition, db, command, depends_on, restart, migrate, temporal-schema, command (+5 more)

### Community 135 - "VerifiedProviderPaymentState"
Cohesion: 0.07
Nodes (13): PaymentInvoiceReconciliation, VerifiedProviderPaymentState, VerifiedProviderPaymentStatus, WebhookEvent, queue_simulated_reconciliation(), require_simulation_scope(), simulation_state(), transition() (+5 more)

### Community 139 - "Customer journey: buyer and seller"
Cohesion: 0.29
Nodes (6): Customer contract, Customer journey: buyer and seller, Evidence and limits, Implementation constraints discovered during task mapping, Outcome, Task graph

### Community 140 - "InvariantViolation"
Cohesion: 0.06
Nodes (19): bounded_quantity(), quantity_text(), _decimal(), _money(), _normalized_text(), _parse_money(), _require_decimal(), InvariantViolation (+11 more)

### Community 141 - "sqlalchemy"
Cohesion: 0.03
Nodes (53): run_migrations_offline(), upgrade(), uuid_column(), upgrade(), upgrade(), upgrade(), upgrade(), downgrade() (+45 more)

### Community 142 - "scaling"
Cohesion: 0.10
Nodes (20): build, build_context_directory, max_cpu, max_memory, min_cpu, min_memory, system, dockerfile_path (+12 more)

### Community 143 - "Deal"
Cohesion: 0.08
Nodes (8): Deal, DealStatus, _active_participation(), _to_domain(), FakeDealRepository, FakeDealRepository, 1. Executive Summary & Change Stack Digest, Blast-Radius & File Risk Table

### Community 144 - "SyncAlly deployment"
Cohesion: 0.20
Nodes (9): 1. Provision the VM and DNS, 2. Configure secrets, 3. Start the stack, Configure the Hostless App, Connect the Render frontend, Current $0 demo: Render + Hostless, OCI single-VM deployment, SyncAlly deployment (+1 more)

### Community 145 - "Code Review: Step 08 Cancel Disputes (F8) — Work Package RV1"
Cohesion: 0.22
Nodes (8): 1. Medium (P2) — Parallel Alembic Migration Heads Branching From 0024_amendments, 2. Reviewer's Guide, 3. Merge Gate, 4. Findings, 6. Empirical Verification Summary, 7. Review Verdict, Code Review: Step 08 Cancel Disputes (F8) — Work Package RV1, Control-flow diagram

### Community 146 - "DealDetailPage.test.tsx"
Cohesion: 0.05
Nodes (51): addCaseEvidence(), getDealFulfillment(), listDealCases(), raiseDealCase(), recordDealFulfillment(), respondToDealCase(), BilateralDecision, CaseStatus (+43 more)

### Community 147 - "ProposalComparison.tsx"
Cohesion: 0.19
Nodes (20): paymentTimingLabel(), allocations(), Change, compareEntries(), comparisonChanges(), entries(), Entry, entrySignature() (+12 more)

### Community 148 - "api/fulfillment.py"
Cohesion: 0.08
Nodes (27): _event_response(), FulfillmentEventResponse, FulfillmentSnapshotResponse, get_fulfillment_repository(), _raise_fulfillment_error(), read_fulfillment_route(), _record_fulfillment_event(), record_fulfillment_route() (+19 more)

### Community 149 - "OnboardingWizard.tsx"
Cohesion: 0.15
Nodes (14): createOrganization(), COUNTRY_NAMES, CountryOption, describeError(), isAmbiguousCreateFailure(), OnboardingWizard(), findExistingOrganization(), handleSubmit() (+6 more)

### Community 151 - "volumes"
Cohesion: 0.50
Nodes (4): volumes, caddy_config, caddy_data, postgres_data

### Community 152 - "MASTER BOARD"
Cohesion: 0.18
Nodes (10): ARBITRATION LOG, CAPABILITY MATRIX, CONSTRAINTS, CONTRACTS, DIRECTIVES, MASTER BOARD, OBJECTIVE, REQUIREMENTS (+2 more)

### Community 153 - "setup-temporal-postgres.sh"
Cohesion: 0.67
Nodes (3): PGPASSWORD, setup-temporal-postgres.sh script, update_database_schema()

### Community 157 - "activities.py"
Cohesion: 0.05
Nodes (10): NotificationKind, DealWorkflowState, load_deal_workflow_state(), parse_workflow_uuid(), WorkflowAgreementRepository, WorkflowDealNotFound, WorkflowDealRepository, _is_live_backend_healthy() (+2 more)

### Community 162 - "get_commercial_document_draft_route"
Cohesion: 0.24
Nodes (3): CommercialDocumentDraftResponse, get_commercial_document_draft_route(), get_trade_pack_route()

### Community 163 - "ConversationUseCaseTests"
Cohesion: 0.12
Nodes (9): AddMessageCommand, MessageIdempotencyPostgresTests, _find_conversation(), _find_keyed_message(), rendezvous(), send(), wait_for(), ConversationUseCaseTests (+1 more)

### Community 166 - "STATE LOG: developer"
Cohesion: 0.25
Nodes (7): BLOCKERS & ESCALATIONS, CURRENT_STATE, ENVIRONMENT_SNAPSHOT (ENV), GOAL & ACCEPTANCE CRITERIA, IDENTITY & ROLE, IMPLEMENTATION_LEDGER, STATE LOG: developer

### Community 168 - "0004_communication_sources_and_scope_indexes.py"
Cohesion: 0.60
Nodes (4): _create_scope_index(), downgrade(), _drop_scope_index(), upgrade()

### Community 171 - "STATE LOG: planner"
Cohesion: 0.25
Nodes (7): BLOCKERS & ESCALATIONS, CURRENT_STATE, ENVIRONMENT_SNAPSHOT (ENV), GOAL & ACCEPTANCE CRITERIA, IDENTITY & ROLE, IMPLEMENTATION_LEDGER, STATE LOG: planner

### Community 173 - "STATE LOG: reviewer"
Cohesion: 0.25
Nodes (7): BLOCKERS & ESCALATIONS, CURRENT_STATE, ENVIRONMENT_SNAPSHOT (ENV), GOAL & ACCEPTANCE CRITERIA, IDENTITY & ROLE, IMPLEMENTATION_LEDGER, STATE LOG: reviewer

### Community 174 - "CONTRACT: cancel-disputes-contract v1   status: FROZEN"
Cohesion: 0.29
Nodes (6): Change rule, CONTRACT: cancel-disputes-contract v1   status: FROZEN, Domain / Models, Endpoints (under /api/v1/deals/{deal_id}/cases), Errors and edge cases, Interface

### Community 175 - "organization.py"
Cohesion: 0.06
Nodes (24): ContactVisibility, _normalize_string(), Organization, OrganizationCapability, OrganizationContact, OrganizationMember, OrganizationMemberRole, OrganizationMemberStatus (+16 more)

### Community 177 - "auth.py"
Cohesion: 0.06
Nodes (27): _as_utc(), bootstrap_system_admin(), create_refresh_token(), current_user(), _decode_token(), _development_actor(), development_login(), _encode_access_token() (+19 more)

### Community 179 - "Constraint"
Cohesion: 0.07
Nodes (4): Constraint, FakeCommunicationRepository, FakeCommunicationRepository, FakeCommunicationRepository

### Community 188 - "main.py"
Cohesion: 0.06
Nodes (8): OperationalFastAPI, list_platform_organizations(), _organization_summary(), OrganizationStatusUpdate, update_platform_organization_status(), AgreementNotCommitted, CommercialDocumentDraft, get_db()

### Community 189 - "SyncAlly: Confirmed Bugs and Feature Roadmap"
Cohesion: 0.25
Nodes (7): Confirmed bugs, Core product capabilities, Feature roadmap, Hackathon-focused vertical slice, Scope and safeguards, Suggested sequencing, SyncAlly: Confirmed Bugs and Feature Roadmap

### Community 200 - "Frontend product review"
Cohesion: 0.50
Nodes (3): Findings and fixes, Frontend product review, Walkthrough coverage

### Community 202 - "NotificationKind"
Cohesion: 0.12
Nodes (8): WorkflowStartError, WorkflowStartOutcome, WorkflowStartPermanentError, WorkflowStartTransientError, DealWorkflowNotification, TemporalDealWorkflowStarter, start_deal_workflow(), TemporalAdapterTests

## Knowledge Gaps
- **48 isolated node(s):** `syncally`, `PGPASSWORD`, `F1a Curated Repeatable Demo Fixture`, `Editorial Dark Theme Design System`, `ZIP HTML and Print Export Verification` (+43 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1761 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **51 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ActorContext` connect `Test Deal Routes & Identity` to `Conversations & Test Conversation Use`, `api/reminders.py`, `repositories/agreements.py`, `api/agreements.py`, `Test Conversation Routes (ConversationRouteTests)`, `SqlAlchemyPaymentIntentRepository`, `Test Agreement Routes (AgreementRouteTests)`, `FulfillmentRouteTests`, `AISuggestionProviderTests`, `OrganizationPermissionsTests`, `api/fulfillment.py`, `CommunicationRepositoryTests`, `Simulate Deal Flow & Test`, `Test Organization Invitations & Organizations`, `SqlAlchemyCommunicationRepository`, `identifiers.py`, `User`, `get_commercial_document_draft_route`, `ConversationUseCaseTests`, `.test_remote_currency_evidence_controls_routes_without_retry_or_fallback`, `get_optional_actor`, `PaymentIntentRepositoryTests`, `api/deals.py`, `repositories/agreements.py`, `organization.py`, `Test Organization Directory & Organizations`, `auth.py`, `create_deal`, `.test_generates_draft_from_schema_2_committed_terms`, `Constraint`, `api/payments.py`, `_active_admin_membership`, `CommercialDocumentDraftTests`, `main.py`, `create_counterparty_invitation`, `api/negotiation.py`, `AmendmentTests`, `OrganizationId`, `Visibility`, `IdentityBoundaryTests`, `NegotiationRouteTests`, `application/conversations.py`, `ai.py`, `ConversationContractTests`, `ApprovalRoutingRouteTests`, `AiContextSelectionTests`, `DealCasesTests`?**
  _High betweenness centrality (0.119) - this node is a cross-community bridge._
- **Are the 157 inferred relationships involving `ActorContext` (e.g. with `approve_agreement_route()` and `commit_agreement_route()`) actually correct?**
  _`ActorContext` has 157 INFERRED edges - model-reasoned connections that need verification._
- **What connects `syncally`, `PGPASSWORD`, `F1a Curated Repeatable Demo Fixture` to the rest of the system?**
  _48 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Conversations & Test Conversation Use` be split into smaller, more focused modules?**
  _Cohesion score 0.06788128122245078 - nodes in this community are weakly interconnected._
- **Why does `OrganizationId` connect `OrganizationId` to `AIContractError`, `repositories/agreements.py`, `api/reminders.py`, `repositories/agreements.py`, `VerifiedProviderPaymentState`, `api/agreements.py`, `Test Conversation Routes (ConversationRouteTests)`, `SqlAlchemyPaymentIntentRepository`, `InvariantViolation`, `FulfillmentRouteTests`, `Test Agreement Routes (AgreementRouteTests)`, `Deal`, `AISuggestionProviderTests`, `NegotiationTests`, `OrganizationPermissionsTests`, `CommunicationRepositoryTests`, `Test Outbox Dispatcher & Outbox`, `SqlAlchemyCommunicationRepository`, `identifiers.py`, `repositories/negotiation.py`, `ConversationUseCaseTests`, `application/deal_cases.py`, `ApprovalRoutingTestCase`, `PaymentIntentRepositoryTests`, `repositories/agreements.py`, `NegotiationMigrationTests`, `organization.py`, `create_deal`, `.test_generates_draft_from_schema_2_committed_terms`, `Constraint`, `Deal`, `api/payments.py`, `CommercialDocumentDraftTests`, `create_counterparty_invitation`, `api/negotiation.py`, `AmendmentTests`, `Money`, `Visibility`, `contracts.py`, `InvalidTransition`, `application/conversations.py`, `ai.py`, `openai.py`, `ConversationContractTests`, `ApprovalRoutingRouteTests`, `AiContextSelectionTests`, `DealCasesTests`?**
  _High betweenness centrality (0.066) - this node is a cross-community bridge._
- **Are the 74 inferred relationships involving `OrganizationId` (e.g. with `build_trade_terms_from_request()` and `create_reviewed_agreement_draft_route()`) actually correct?**
  _`OrganizationId` has 74 INFERRED edges - model-reasoned connections that need verification._
- **Should `AIContractError` be split into smaller, more focused modules?**
  _Cohesion score 0.12682926829268293 - nodes in this community are weakly interconnected._