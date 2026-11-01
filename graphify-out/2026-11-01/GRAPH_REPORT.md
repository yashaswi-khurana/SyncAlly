# Graph Report - SyncAlly  (2026-10-31)

## Corpus Check
- 229 files · ~148,711 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 8 file(s) not represented in the graph (top: (none) 4, .example 1, .ini 1)

## Summary
- 3363 nodes · 10371 edges · 132 communities (84 shown, 48 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 1353 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `ddfee394`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- ExtractedFact
- repositories/payment_processing.py
- SignInPage.tsx
- Db Models Deals
- App Service Payment Proce
- Api Routes Agreements
- App Service Outbox
- Message
- Paymentinvoicelookup
- client.ts
- api/deals.py
- Repository Agreements
- Reconstitute()
- Frontend Paymentstatuspanel
- Conversationroutetests
- Frontend Package
- Agreementroutetests
- Api Database Skill
- Api Routes Conversations
- test_ai_provider.py
- App Service Agreements
- Frontend Aisuggestionreview
- Operational Recovery & Logging
- Domain Conversations
- Repository Communications
- Accept Invitation()
- Build In Process Client(
- Commercial Domain Model
- Frontend Dealconversationreview
- Commitagreementcommand
- gmail.py
- Repository Organizations
- AISuggestionProviderTests
- Case Insensitive Prefix(
- Test Payment Processing P
- application/conversations.py
- react
- serialize_migrations
- listOrganizations
- ai.py
- Paymentworkitem
- Devroutestests
- Repository Payment Processing
- Api Routes Organizations
- create_worker
- sqlalchemy
- ConversationContractTests
- application/payments.py
- Deal
- seed_demo.py
- ConversationUseCaseTests
- Actorcontext
- AIContractError
- Api Routes Auth
- auth.py
- Frontend Agreementreview
- workflow_state.py
- InvariantViolation
- PaymentIntentRepositoryTests
- Compose Yaml
- application/deals.py
- Operational Recovery & Logging
- Money
- Any
- refresh_access_token
- Paymentintentstatus
- .__call__
- Commercialdocumentdraftre
- DealWorkflowNotification
- DealWorkflowInput
- database_health
- payment_outbox.py
- SqlAlchemyDealRepository
- Demo Lifecycle
- Frontend Tsconfig
- AgreementVersionId
- _register_shutdown_handlers
- Agreement
- CreateFactRequest
- PaymentInvoiceRequest
- Fakewebhookverifier
- authorize_payment_route
- AiContextSelectionTests
- _is_one_active_per_milestone_violation
- workflows/deal.py
- FakeDealRepository
- Api Routes Auth
- Settings
- Api Routes Main
- get_optional_actor
- _deal_awaiting_counterparty
- CreateDealPage.tsx
- Credentialsrequest
- contracts.py
- receive_paypal_invoice_webhook
- OrganizationIndexPostgresMigrationTests
- HealthRouteTests
- DomainDependencyTests
- Databasepersistencetests
- Demolifecycletests
- Implementation Roadmap
- 0005 Conversation Party U
- Api Routes Main
- Commercial Invariants
- Migrationsettings
- DealDetailPage.test.tsx
- Conversationpartyuniquene
- Providerinvoiceuniquemigr
- Repo Idea Thinker Skill
- Frontend Readme
- Frontend Vite-Env D
- Jwt Authentication And Re
- Syncally

## God Nodes (most connected - your core abstractions)
1. `ActorContext` - 180 edges
2. `OrganizationId` - 142 edges
3. `Deal` - 93 edges
4. `Money` - 89 edges
5. `DealId` - 83 edges
6. `InvariantViolation` - 80 edges
7. `UserId` - 78 edges
8. `Constraint` - 73 edges
9. `SqlAlchemyAgreementRepository` - 64 edges
10. `AISuggestionProviderTests` - 63 edges

## Surprising Connections (you probably didn't know these)
- `PayPal Payment Worker Process` --conceptually_related_to--> `PaymentIntent State Machine`  [INFERRED]
  backend/README.md → docs/architecture/03-paypal-payment-intent-lifecycle.md
- `Temporal Worker Restart Smoke Test` --conceptually_related_to--> `Temporal Deal Workflow`  [INFERRED]
  infra/README.md → docs/architecture/02-temporal-deal-workflow-contract.md
- `Outbox to Workflow Start Consistency` --conceptually_related_to--> `Outbox Relay Worker Process`  [INFERRED]
  docs/architecture/02-temporal-deal-workflow-contract.md → backend/README.md
- `_to_agreement_response()` --uses--> `Agreement`  [INFERRED]
  backend/src/syncally/api/agreements.py → backend/src/syncally/domain/agreements/agreement.py
- `_to_approval_response()` --uses--> `Approval`  [INFERRED]
  backend/src/syncally/api/agreements.py → backend/src/syncally/domain/agreements/agreement.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Repository Architecture, Visualization, and Ideation Framework** — github_skills_repo_architect_skill, github_skills_archify_diagrammer_skill, github_skills_repo_idea_thinker_skill, github_skills_api_database_skill [INFERRED 0.85]
- **Code Implementation, Review, Debugging, and QA Loop** — github_skills_senior_engineer_skill, github_skills_code_reviewer_skill, github_skills_debugger_skill, github_skills_testing_qa_skill [INFERRED 0.85]
- **Production Readiness and Quality Gate Lifecycle** — github_skills_devops_production_skill, github_skills_performance_reliability_skill, github_skills_security_analyst_skill, github_skills_testing_qa_skill [INFERRED 0.85]
- **Bilateral Agreement Approval and Commitment Flow** — docs_architecture_01_commercial_domain_model_atomic_bilateral_approval, docs_architecture_01_commercial_domain_model_agreement_version, docs_architecture_05_domain_layer_agreement_commitment_flow, docs_implementation_plan_stage_5_agreement_approvals [INFERRED 0.95]
- **PayPal Payment Intent and Reconciliation Lifecycle** — docs_architecture_03_paypal_payment_intent_lifecycle_payment_intent, docs_architecture_03_paypal_payment_intent_lifecycle_create_unknown_state, docs_architecture_03_paypal_payment_intent_lifecycle_payment_reconciliation, backend_readme_payment_worker_process, docs_operations_unknown_payment_recovery [INFERRED 0.95]
- **Temporal Outbox Relay and Workflow Orchestration** — docs_architecture_02_temporal_deal_workflow_contract_deal_workflow, docs_architecture_02_temporal_deal_workflow_contract_outbox_workflow_start, docs_architecture_02_temporal_deal_workflow_contract_refresh_deal_state, backend_readme_outbox_worker_process, infra_readme_restart_smoke_test [INFERRED 0.95]

## Communities (132 total, 48 thin omitted)

### Community 0 - "ExtractedFact"
Cohesion: 0.11
Nodes (10): get_ai_suggestion_provider(), AIPermanentError, AIProviderError, FactExtractionRequest, ProposalDraftRequest, ExtractedFact, FactField, DemoAISuggestionProvider (+2 more)

### Community 1 - "repositories/payment_processing.py"
Cohesion: 0.11
Nodes (13): PaymentStatusRecord, AgreementStatus, PaymentIntent, PaymentIntentStatus, PaymentMilestone, PaymentIntentId, PaymentMilestoneId, OutboxEvent (+5 more)

### Community 3 - "SignInPage.tsx"
Cohesion: 0.11
Nodes (23): dependencies, react@^19.3.0, react-dom@^19.3.0, three@^0.186.1, apiBaseUrl(), apiRequest(), login(), demoQuickFillEnabled() (+15 more)

### Community 4 - "Db Models Deals"
Cohesion: 0.08
Nodes (27): _aggregate_scope(), _delete_scoped(), _demo_organization_ids(), DevResetResponse, DevRoleSwitchRequest, _missing_demo_emails(), _related_ids(), _require_dev_environment() (+19 more)

### Community 5 - "App Service Payment Proce"
Cohesion: 0.11
Nodes (5): payment_invoice_number(), PaymentProcessingRepository, process_payment_intent(), reconcile_payment_intent(), _request_id_retry_window_expired()

### Community 6 - "Api Routes Agreements"
Cohesion: 0.09
Nodes (22): AgreementVersionResponse, ApprovalResponse, approve_agreement_route(), commit_agreement_route(), CommitAgreementRequest, create_agreement_draft_route(), create_reviewed_agreement_draft_route(), CreateAgreementDraftRequest (+14 more)

### Community 7 - "App Service Outbox"
Cohesion: 0.10
Nodes (13): build_deal_workflow_id(), dispatch_outbox_event(), OutboxDispatchResult, PendingOutboxEvent, WorkflowStartTransientError, apply_dispatch_result(), claim_next_pending_event(), _claim_statement() (+5 more)

### Community 8 - "Message"
Cohesion: 0.07
Nodes (9): add_message(), ConstraintRepository, create_manual_constraint(), review_constraint(), Message, MessageId, create_database_engine(), _message_to_domain() (+1 more)

### Community 9 - "Paymentinvoicelookup"
Cohesion: 0.09
Nodes (11): PaymentNeedsAction, PaymentOutcomeUnknown, PaymentRetryableError, _has_excess_currency_precision(), PayPalSandboxInvoiceProvider, _provider_error_code(), _provider_request_id(), _send_request() (+3 more)

### Community 10 - "client.ts"
Cohesion: 0.07
Nodes (44): API_REQUEST_TIMEOUT_MS, describeDetail(), getDealMessageExistence(), getOrganization(), isAbortError(), isRecord(), listDeals(), readErrorDetail() (+36 more)

### Community 11 - "api/deals.py"
Cohesion: 0.11
Nodes (12): create_deal_route(), CreateDealRequest, DealResponse, DealSummaryResponse, get_deal_repository(), list_deals_route(), read_deal_route(), _to_response() (+4 more)

### Community 12 - "Repository Agreements"
Cohesion: 0.11
Nodes (12): AgreementAccessDenied, AgreementAlreadyCommitted, AgreementNotFound, AgreementVersionConflict, DuplicateApproval, ProposalNotFound, StaleAgreementVersion, UnauthorizedApproval (+4 more)

### Community 13 - "Reconstitute()"
Cohesion: 0.13
Nodes (9): ConstraintId, ConversationId, DealId, OrganizationId, constraint(), message(), CommunicationRepositoryTests, _domain_deal() (+1 more)

### Community 14 - "Frontend Paymentstatuspanel"
Cohesion: 0.10
Nodes (26): authorizeDealPayment(), listPaymentStatuses(), PaymentStatus, describeStatus(), displayAmount(), ExtendedPaymentStatus, extractInvoiceNumber(), firstMilestoneAmount() (+18 more)

### Community 16 - "Frontend Package"
Cohesion: 0.06
Nodes (44): devDependencies, eslint@^10.13.0, @eslint/js@^10.0.1, eslint-plugin-react-hooks@^7.1.1, eslint-plugin-react-refresh@^0.4.20, globals@^17.13.0, happy-dom@^21.0.3, @testing-library/dom@^10.4.1 (+36 more)

### Community 18 - "Api Database Skill"
Cohesion: 0.04
Nodes (43): API and Database Engineer Skill, API Design and Contract Semantics, Data Integrity and Invariant Enforcement, Query Performance and Projection Optimization, Schema Migration and Backward Compatibility, Transaction Boundaries and Atomicity, Archify Diagrammer Skill, Archify CLI Global Tool (+35 more)

### Community 19 - "Api Routes Conversations"
Cohesion: 0.07
Nodes (38): add_message_route(), AISuggestionRequest, clarify_fact_route(), confirm_fact_route(), ConstraintResponse, correct_fact_route(), CorrectFactRequest, create_fact_route() (+30 more)

### Community 20 - "test_ai_provider.py"
Cohesion: 0.07
Nodes (4): run_migrations_offline(), CommunicationMigrationTests, OrganizationIndexMigrationTests, PaymentCreateStartedMigrationTests

### Community 21 - "App Service Agreements"
Cohesion: 0.06
Nodes (23): AgreementRepository, AuditEventDraft, AuditRepository, commit_agreement(), create_agreement_draft(), create_reviewed_agreement_draft(), CreateAgreementDraftCommand, CreateReviewedAgreementDraftCommand (+15 more)

### Community 22 - "Frontend Aisuggestionreview"
Cohesion: 0.09
Nodes (36): correctDealFact(), createAgreementFromReviewedTerms(), createDealFact(), draftDealProposal(), reviewDealFact(), suggestDealFacts(), DealFact, FactReviewAction (+28 more)

### Community 23 - "Operational Recovery & Logging"
Cohesion: 0.10
Nodes (16): _connect_with_retry(), main(), run_forever(), main(), run_forever(), is_permanent_rpc_error(), configure_logging(), log_operation() (+8 more)

### Community 24 - "Domain Conversations"
Cohesion: 0.07
Nodes (4): Constraint, FakeCommunicationRepository, FakeCommunicationRepository, FakeCommunicationRepository

### Community 25 - "Repository Communications"
Cohesion: 0.15
Nodes (4): Conversation, _conversation_to_domain(), _page_bounds(), SqlAlchemyCommunicationRepository

### Community 26 - "Accept Invitation()"
Cohesion: 0.21
Nodes (5): accept_invitation(), AcceptInvitationRequest, create_organization_invitation(), CreateInvitationRequest, OrganizationInvitationTests

### Community 27 - "Build In Process Client("
Cohesion: 0.08
Nodes (10): _build_in_process_client(), ci_deal_flow_hook(), DealFlowContext, DealFlowSimulator, _is_live_backend_healthy(), main(), run_simulation(), SimulationError (+2 more)

### Community 28 - "Commercial Domain Model"
Cohesion: 0.06
Nodes (26): Outbox Relay Worker Process, PayPal Payment Worker Process, PayPal Invoicing Webhook Endpoint, AgreementVersion Aggregate, Append-Only AuditEvent Ledger, Commercial Constraint and Provenance, Deal Aggregate, Organization and Membership Entities (+18 more)

### Community 29 - "Frontend Dealconversationreview"
Cohesion: 0.08
Nodes (34): createDealMessage(), listDealFacts(), listDealMessages(), updateFactVisibility(), areFactsEqual(), ConversationState, DealConversationReview(), addSuggestedFact() (+26 more)

### Community 30 - "Commitagreementcommand"
Cohesion: 0.10
Nodes (8): CommitAgreementCommand, RecordApprovalCommand, AgreementVersion, commit_agreement_in_transaction(), record_approval_in_transaction(), AgreementCommitTests, LocalWorkflowSmokeTests, commit_once()

### Community 31 - "gmail.py"
Cohesion: 0.08
Nodes (8): get_paypal_webhook_configuration(), PaymentInvoiceNotice, main(), GmailSettings, PayPalSettings, GmailSMTPInvoiceNotifier, _FakeSMTP, GmailSMTPInvoiceNotifierTests

### Community 32 - "Repository Organizations"
Cohesion: 0.10
Nodes (11): Organization, OrganizationMember, OrganizationMemberRole, OrganizationMemberStatus, OrganizationStatus, _membership_to_domain(), _organization_to_domain(), SqlAlchemyOrganizationMemberRepository (+3 more)

### Community 33 - "AISuggestionProviderTests"
Cohesion: 0.12
Nodes (6): parse_extracted_facts(), DeterministicFakeAIProvider, AISuggestionProviderTests, _fact_payload(), _proposal_payload(), extract_facts()

### Community 34 - "Case Insensitive Prefix("
Cohesion: 0.14
Nodes (4): _case_insensitive_prefix(), _escape_like(), value(), OrganizationDirectoryTests

### Community 35 - "Test Payment Processing P"
Cohesion: 0.14
Nodes (6): PaymentWorkItem, FakeInvoiceProvider, FakeProcessingRepository, PaymentProcessingTests, _request(), _work_item()

### Community 36 - "application/conversations.py"
Cohesion: 0.06
Nodes (16): can_view_constraint(), can_view_message(), ConcurrentConstraintUpdate, ConstraintNotFound, correct_constraint(), CreateManualConstraintCommand, visible_to_viewer(), DealParticipation (+8 more)

### Community 37 - "react"
Cohesion: 0.07
Nodes (30): addOrganizationMember(), createOrganization(), Organization, COUNTRY_NAMES, CountryOption, describeError(), isAmbiguousCreateFailure(), OnboardingWizard() (+22 more)

### Community 38 - "serialize_migrations"
Cohesion: 0.12
Nodes (8): run_migrations_online(), serialize_migrations(), _make_postgres_connection(), _make_sqlite_connection(), MigrationLockTests, simulated_migration(), PostgresRealAdvisoryLockTests, worker()

### Community 39 - "listOrganizations"
Cohesion: 0.07
Nodes (46): listOrganizations(), clearAccessToken(), getAccessToken(), setAccessToken(), setTokens(), TokenResponse, App(), handleOrganizationCreated() (+38 more)

### Community 40 - "ai.py"
Cohesion: 0.05
Nodes (21): AIRetryPolicy, AISuggestionProvider, call_with_bounded_retry(), draft_proposal(), draft_proposal_from_context(), extract_facts(), extract_facts_from_context(), FactExtractionResult (+13 more)

### Community 41 - "Paymentworkitem"
Cohesion: 0.11
Nodes (5): dispatch_one_payment_event(), FakeRepository, NoCallProvider, PaymentOutboxWorkerTests, _utc()

### Community 43 - "Repository Payment Processing"
Cohesion: 0.17
Nodes (3): PaymentInvoiceLineItem, SqlAlchemyPaymentProcessingRepository, transition()

### Community 44 - "Api Routes Organizations"
Cohesion: 0.12
Nodes (9): AcceptInvitationResponse, add_organization_member(), AddOrganizationMemberRequest, create_organization(), CreateOrganizationRequest, InvitationResponse, list_my_organizations(), OrganizationDirectoryItem (+1 more)

### Community 45 - "create_worker"
Cohesion: 0.20
Nodes (3): create_worker(), workflow_activities(), WorkflowWorkerTests

### Community 46 - "sqlalchemy"
Cohesion: 0.09
Nodes (14): upgrade(), uuid_column(), upgrade(), upgrade(), _create_scope_index(), downgrade(), _drop_scope_index(), upgrade() (+6 more)

### Community 47 - "ConversationContractTests"
Cohesion: 0.11
Nodes (5): confirm_constraint(), UserId, ConversationContractTests, FakeConstraintRepository, OrganizationMemberDomainTests

### Community 48 - "application/payments.py"
Cohesion: 0.08
Nodes (11): OutboxRepository, authorize_payment_intent(), AuthorizePaymentIntentCommand, DuplicateActivePaymentIntent, IdempotencyKeyReused, PaymentIntentAuthorizationOutcome, PaymentIntentCommandMismatch, PaymentIntentRepository (+3 more)

### Community 49 - "Deal"
Cohesion: 0.10
Nodes (6): Deal, DealStatus, _deal_to_domain(), _active_participation(), _to_domain(), FakeDealRepository

### Community 50 - "seed_demo.py"
Cohesion: 0.17
Nodes (5): DemoIdentity, main(), _password_for(), seed_demo_data(), DemoSeedTests

### Community 52 - "Actorcontext"
Cohesion: 0.21
Nodes (3): ActorContext, DealAuthorizationTests, DealRouteTests

### Community 53 - "AIContractError"
Cohesion: 0.11
Nodes (15): parse_proposed_terms(), AIContractError, AIValidationClaim, _check_keys(), _decimal(), ProposedTerms, _required_string(), scope_extracted_facts() (+7 more)

### Community 54 - "Api Routes Auth"
Cohesion: 0.11
Nodes (7): _decode_token(), _development_actor(), development_login(), get_current_actor(), _unauthorized(), _require_demo_admin(), resolve_actor()

### Community 55 - "auth.py"
Cohesion: 0.08
Nodes (8): OperationalFastAPI, _active_admin_membership(), _create_invitation_token(), _decode_invitation_token(), get_organization_route(), list_organization_directory(), verify_password(), get_db()

### Community 56 - "Frontend Agreementreview"
Cohesion: 0.16
Nodes (21): commitAgreementVersion(), getCurrentAgreement(), recordAgreementDecision(), paymentTimingLabel(), AgreementReview(), commitCurrentAgreement(), decide(), reloadAgreement() (+13 more)

### Community 57 - "workflow_state.py"
Cohesion: 0.10
Nodes (10): DealWorkflowState, load_deal_workflow_state(), parse_workflow_uuid(), WorkflowAgreementRepository, WorkflowDealNotFound, WorkflowDealRepository, _domain_deal(), _FakeAgreementRepository (+2 more)

### Community 58 - "InvariantViolation"
Cohesion: 0.13
Nodes (9): NegotiationSession, NegotiationSubmissionOutcome, Proposal, ProposalStatus, InvalidTransition, NegotiationSessionId, ProposalId, build_proposal() (+1 more)

### Community 60 - "Compose Yaml"
Cohesion: 0.09
Nodes (22): POSTGRES_DB, POSTGRES_PASSWORD, POSTGRES_USER, interval, retries, test, timeout, environment (+14 more)

### Community 61 - "application/deals.py"
Cohesion: 0.14
Nodes (6): _both_organizations_active(), create_deal(), CreateDealCommand, DealAccessDenied, DealUseCaseTests, FakeDealRepository

### Community 62 - "Operational Recovery & Logging"
Cohesion: 0.24
Nodes (4): captured_output(), SafeOperationsTests, exercise(), failed_db()

### Community 63 - "Money"
Cohesion: 0.13
Nodes (10): PaymentInvoiceReconciliation, _money(), _parse_money(), VerifiedProviderPaymentState, Money, transition(), FakePayPalInvoiceProvider, PaymentReconciliationTests (+2 more)

### Community 64 - "Any"
Cohesion: 0.13
Nodes (4): RefreshDealStateActivity, _workflow_input_value(), RefreshDealStateActivityTests, factory()

### Community 65 - "refresh_access_token"
Cohesion: 0.13
Nodes (4): _hash_refresh_token(), refresh_access_token(), RefreshRequest, RefreshToken

### Community 68 - "Commercialdocumentdraftre"
Cohesion: 0.10
Nodes (10): CommercialDocumentDraftResponse, get_commercial_document_draft_route(), AgreementNotCommitted, CommercialDocumentDraft, _display(), generate_commercial_document_draft(), _render(), _decimal() (+2 more)

### Community 69 - "DealWorkflowNotification"
Cohesion: 0.10
Nodes (7): DealWorkflowStarter, WorkflowStartError, WorkflowStartOutcome, WorkflowStartPermanentError, DealWorkflowNotification, TemporalDealWorkflowStarter, TemporalAdapterTests

### Community 70 - "DealWorkflowInput"
Cohesion: 0.09
Nodes (8): DealWorkflow, DealWorkflowInput, _require_uuid(), DealWorkflowUnitTests, new_workflow_input(), RefreshActivity, RefreshCall, WorkflowWorkerIntegrationTests

### Community 72 - "payment_outbox.py"
Cohesion: 0.16
Nodes (8): PaymentInvoiceNotifier, PaymentInvoiceProvider, claim_next_payment_event(), _claim_statement(), _ClaimedPaymentEvent, dispatch_pending_payment_events(), _finish_event(), _process_claimed_payment_event()

### Community 74 - "Demo Lifecycle"
Cohesion: 0.23
Nodes (7): _acquire_lock(), _is_demo_deal(), lock_demo_deal_creation(), lock_demo_payment_processing(), lock_demo_reset(), DemoLifecycleLockTests, _postgres_session()

### Community 75 - "Frontend Tsconfig"
Cohesion: 0.11
Nodes (17): compilerOptions, allowImportingTsExtensions, jsx, lib, module, moduleDetection, moduleResolution, noEmit (+9 more)

### Community 76 - "AgreementVersionId"
Cohesion: 0.31
Nodes (3): AgreementVersionId, DealDomainTests, make_deal()

### Community 77 - "_register_shutdown_handlers"
Cohesion: 0.27
Nodes (4): _register_shutdown_handlers(), _remove_shutdown_handlers(), _request_shutdown(), WorkerShutdownSignalTests

### Community 78 - "Agreement"
Cohesion: 0.07
Nodes (16): Agreement, Approval, _normalized_text(), PaymentTerm, _require_decimal(), ShipmentTerm, TradeLineItem, TradeTerms (+8 more)

### Community 82 - "authorize_payment_route"
Cohesion: 0.11
Nodes (8): authorize_payment_route(), AuthorizePaymentRequest, AuthorizePaymentResponse, get_payment_status_repository(), list_payment_statuses_route(), PaymentStatusResponse, list_current_payment_statuses(), PaymentStatusRepository

### Community 85 - "_is_one_active_per_milestone_violation"
Cohesion: 0.43
Nodes (3): _is_idempotency_key_violation(), _is_one_active_per_milestone_violation(), _violated_constraint_name()

### Community 86 - "workflows/deal.py"
Cohesion: 0.11
Nodes (5): NotificationKind, DealWorkflowResult, DealWorkflowStatus, DealWorkflowTests, new_notification()

### Community 88 - "Api Routes Auth"
Cohesion: 0.24
Nodes (6): _as_utc(), create_refresh_token(), _encode_access_token(), _issue_tokens(), _replay_rotation(), _revoke_family()

### Community 90 - "Settings"
Cohesion: 0.19
Nodes (3): _is_duplicate_membership_error(), Settings, IdentityBoundaryTests

### Community 94 - "CreateDealPage.tsx"
Cohesion: 0.09
Nodes (20): @testing-library/react@^16.3.3, vitest@^5.0.5, createDeal(), CreateDealPage(), handleSubmit(), CreateDealPageProps, describeCreateError(), describeError() (+12 more)

### Community 95 - "Credentialsrequest"
Cohesion: 0.23
Nodes (6): CredentialsRequest, login(), TokenResponse, hash_password(), fail(), scalar()

### Community 96 - "contracts.py"
Cohesion: 0.27
Nodes (9): _is_weak_jwt_secret(), _contains_numeric_token(), _contains_token(), _date_value_is_present(), _fact_value_is_supported_by_quote(), _flexible_whitespace_pattern(), _number_with_currency_is_present(), _number_with_unit_is_present() (+1 more)

### Community 97 - "receive_paypal_invoice_webhook"
Cohesion: 0.22
Nodes (3): _persist_paypal_webhook_event(), receive_paypal_invoice_webhook(), record_paypal_webhook_event()

### Community 106 - "Implementation Roadmap"
Cohesion: 0.22
Nodes (9): SyncAlly Implementation Plan, Stage 1 - Basics and Identity, Stage 2 - Create and View Deals, Stage 3 - Messages and Facts Isolation, Stage 4 - AI Suggestions and Review, Stage 5 - Agreement and Approvals, Stage 6 - Background Deal Workflow, Stage 7 - PayPal Sandbox Payment (+1 more)

### Community 107 - "0005 Conversation Party U"
Cohesion: 0.36
Nodes (5): _create_party_unique_constraint(), _deduplicate_conversations(), downgrade(), _drop_party_unique_constraint(), upgrade()

### Community 110 - "Commercial Invariants"
Cohesion: 0.29
Nodes (4): Modular Monolith System Shape, Workflow Orchestration Rules, MVP Commercial Boundary, SyncAlly Commercial Platform

### Community 114 - "DealDetailPage.test.tsx"
Cohesion: 0.07
Nodes (28): ApiError, getCommercialDocumentDraft(), getDeal(), CommercialDocumentPanel(), CommercialDocumentPanelProps, DocumentState, mockedGetDraft, DealDetailPage() (+20 more)

### Community 124 - "Repo Idea Thinker Skill"
Cohesion: 0.50
Nodes (3): Repo Idea Thinker Skill, Repository-Grounded Ideation Discipline, Idea Quality Standards and Lightweight Validation

### Community 128 - "Frontend Readme"
Cohesion: 0.67
Nodes (3): Frontend HTML Root Document, Frontend API Client and Agreement State, React and TypeScript Vite Web App

## Knowledge Gaps
- **47 isolated node(s):** `syncally`, `Stage 1 - Basics and Identity`, `Stage 2 - Create and View Deals`, `Stage 3 - Messages and Facts Isolation`, `Stage 4 - AI Suggestions and Review` (+42 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1107 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **48 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ActorContext` connect `Actorcontext` to `repositories/payment_processing.py`, `sqlalchemy_orm`, `Db Models Deals`, `Api Routes Agreements`, `Message`, `api/deals.py`, `Reconstitute()`, `Conversationroutetests`, `Agreementroutetests`, `Api Routes Conversations`, `App Service Agreements`, `Accept Invitation()`, `AISuggestionProviderTests`, `Case Insensitive Prefix(`, `application/conversations.py`, `ai.py`, `Api Routes Organizations`, `ConversationContractTests`, `application/payments.py`, `ConversationUseCaseTests`, `Api Routes Auth`, `auth.py`, `application/deals.py`, `Commercialdocumentdraftre`, `Agreement`, `authorize_payment_route`, `AiContextSelectionTests`, `Settings`, `get_optional_actor`, `Databasepersistencetests`, `Demolifecycletests`?**
  _High betweenness centrality (0.096) - this node is a cross-community bridge._
- **Are the 76 inferred relationships involving `ActorContext` (e.g. with `approve_agreement_route()` and `commit_agreement_route()`) actually correct?**
  _`ActorContext` has 76 INFERRED edges - model-reasoned connections that need verification._
- **What connects `syncally`, `Stage 1 - Basics and Identity`, `Stage 2 - Create and View Deals` to the rest of the system?**
  _47 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `ExtractedFact` be split into smaller, more focused modules?**
  _Cohesion score 0.10668563300142248 - nodes in this community are weakly interconnected._
- **Why does `OrganizationId` connect `Reconstitute()` to `repositories/payment_processing.py`, `sqlalchemy_orm`, `Api Routes Agreements`, `App Service Outbox`, `Message`, `Repository Agreements`, `Conversationroutetests`, `Agreementroutetests`, `App Service Agreements`, `Domain Conversations`, `Repository Communications`, `Commitagreementcommand`, `Repository Organizations`, `AISuggestionProviderTests`, `application/conversations.py`, `ai.py`, `ConversationContractTests`, `application/payments.py`, `Deal`, `ConversationUseCaseTests`, `AIContractError`, `workflow_state.py`, `InvariantViolation`, `PaymentIntentRepositoryTests`, `application/deals.py`, `Money`, `Commercialdocumentdraftre`, `SqlAlchemyDealRepository`, `AgreementVersionId`, `Agreement`, `AiContextSelectionTests`, `contracts.py`?**
  _High betweenness centrality (0.054) - this node is a cross-community bridge._
- **Are the 48 inferred relationships involving `OrganizationId` (e.g. with `create_reviewed_agreement_draft_route()` and `Agreement`) actually correct?**
  _`OrganizationId` has 48 INFERRED edges - model-reasoned connections that need verification._
- **Should `repositories/payment_processing.py` be split into smaller, more focused modules?**
  _Cohesion score 0.11282051282051282 - nodes in this community are weakly interconnected._