# Graph Report - SyncAlly  (2026-10-31)

## Corpus Check
- 228 files · ~148,005 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 8 file(s) not represented in the graph (top: (none) 4, .example 1, .ini 1)

## Summary
- 3339 nodes · 10318 edges · 142 communities (89 shown, 53 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 1349 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `09f3e8e1`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- ExtractedFact
- identifiers.py
- sqlalchemy_orm
- SignInPage.tsx
- Db Models Deals
- App Service Payment Proce
- Api Routes Agreements
- App Service Outbox
- App Service Conversations
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
- test_outbox_dispatcher.py
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
- Argparse
- Repository Organizations
- AISuggestionProviderTests
- Case Insensitive Prefix(
- Test Payment Processing P
- Frontend Onboardingwizard
- react
- create_worker
- listOrganizations
- ai.py
- Paymentworkitem
- Devroutestests
- Repository Payment Processing
- Api Routes Organizations
- ConversationUseCaseTests
- 0001 Initial Schema
- ConversationContractTests
- Temporal Deal
- Domain Deal
- infrastructure/outbox.py
- Alembic Migration
- Actorcontext
- AIContractError
- Api Routes Auth
- seed_demo.py
- Frontend Agreementreview
- workflow_state.py
- Domain Proposal
- PaymentIntentRepositoryTests
- Compose Yaml
- application/deals.py
- Operational Recovery & Logging
- InvalidTransition
- Any
- refresh_access_token
- Paymentintentstatus
- Api Routes Dev
- Commercialdocumentdraftre
- DealWorkflowNotification
- DealWorkflowInput
- Session
- Session
- InvariantViolation
- Demo Lifecycle
- Frontend Tsconfig
- fake.py
- Agreement
- Money
- SqlAlchemyPaymentIntentRepository
- authorize_payment_intent
- Fakewebhookverifier
- api/payments.py
- repositories/__init__.py
- AiContextSelectionTests
- .add
- Dealworkflowresult
- DealRepository
- Api Routes Auth
- Paymentinvoicereconciliat
- Settings
- Api Routes Main
- AIContractTests
- IdempotencyKeyReused
- CreateDealPage.tsx
- Credentialsrequest
- contracts.py
- api/paypal_webhooks.py
- OrganizationIndexPostgresMigrationTests
- test_ai_provider.py
- simulate_deal_flow.py
- FakeDealRepository
- HealthRouteTests
- Databasepersistencetests
- Demolifecycletests
- Implementation Roadmap
- 0005 Conversation Party U
- Api Routes Main
- _to_domain
- Commercial Invariants
- Migrationsettings
- apiRequest
- Api Routes Main
- Conversationpartyuniquene
- PaymentStatusRecord
- Providerinvoiceuniquemigr
- 0004_communication_sources_and_scope_indexes.py
- Repo Idea Thinker Skill
- Frontend Readme
- Frontend Vite-Env D
- Jwt Authentication And Re
- Syncally
- _is_duplicate_membership_error

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
- `get_deal_repository()` --uses--> `DealRepository`  [INFERRED]
  backend/src/syncally/api/agreements.py → backend/src/syncally/application/deals.py
- `_to_agreement_response()` --uses--> `Agreement`  [INFERRED]
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

## Communities (142 total, 53 thin omitted)

### Community 0 - "ExtractedFact"
Cohesion: 0.19
Nodes (6): get_ai_suggestion_provider(), ExtractedFact, FactField, DemoAISuggestionProvider, _is_ambiguous_numeric_term(), _is_delivery_date_context()

### Community 1 - "identifiers.py"
Cohesion: 0.10
Nodes (5): _display(), _render(), _decimal(), canonical_decimal(), DomainDependencyTests

### Community 3 - "SignInPage.tsx"
Cohesion: 0.09
Nodes (30): dependencies, react@^19.3.0, react-dom@^19.3.0, three@^0.186.1, login(), handleOrganizationCreated(), refreshSessionView(), useHashRoute() (+22 more)

### Community 4 - "Db Models Deals"
Cohesion: 0.10
Nodes (21): _require_dev_environment(), AgreementVersion, Approval, Obligation, Base, Constraint, Conversation, Deal (+13 more)

### Community 5 - "App Service Payment Proce"
Cohesion: 0.09
Nodes (5): payment_invoice_number(), PaymentProcessingRepository, process_payment_intent(), reconcile_payment_intent(), _request_id_retry_window_expired()

### Community 6 - "Api Routes Agreements"
Cohesion: 0.10
Nodes (21): AgreementVersionResponse, ApprovalResponse, approve_agreement_route(), commit_agreement_route(), CommitAgreementRequest, create_agreement_draft_route(), create_reviewed_agreement_draft_route(), CreateAgreementDraftRequest (+13 more)

### Community 7 - "App Service Outbox"
Cohesion: 0.15
Nodes (6): build_deal_workflow_id(), dispatch_outbox_event(), PendingOutboxEvent, WorkflowStartTransientError, FakeDealWorkflowStarter, OutboxDispatcherTests

### Community 8 - "App Service Conversations"
Cohesion: 0.06
Nodes (18): _list_all_constraints_for_owner(), add_message(), can_view_constraint(), CommunicationRepository, ConcurrentConstraintUpdate, ConstraintNotFound, ConstraintRepository, correct_constraint() (+10 more)

### Community 9 - "Paymentinvoicelookup"
Cohesion: 0.07
Nodes (14): receive_paypal_invoice_webhook(), PaymentInvoiceLookup, PaymentInvoiceRequest, PaymentNeedsAction, PaymentOutcomeUnknown, PaymentRetryableError, VerifiedProviderPaymentStatus, _has_excess_currency_precision() (+6 more)

### Community 10 - "client.ts"
Cohesion: 0.06
Nodes (46): API_REQUEST_TIMEOUT_MS, apiBaseUrl(), apiRequest(), createDeal(), describeDetail(), getDeal(), getDealMessageExistence(), isAbortError() (+38 more)

### Community 11 - "api/deals.py"
Cohesion: 0.11
Nodes (12): create_deal_route(), CreateDealRequest, DealResponse, DealSummaryResponse, get_deal_repository(), list_deals_route(), read_deal_route(), _to_response() (+4 more)

### Community 12 - "Repository Agreements"
Cohesion: 0.09
Nodes (16): AgreementAccessDenied, AgreementAlreadyCommitted, AgreementNotFound, AgreementVersionConflict, CreateAgreementDraftCommand, CreateReviewedAgreementDraftCommand, DuplicateApproval, ProposalNotFound (+8 more)

### Community 13 - "Reconstitute()"
Cohesion: 0.08
Nodes (13): can_view_message(), ConstraintId, ConversationId, DealId, OrganizationId, UserId, constraint(), message() (+5 more)

### Community 14 - "Frontend Paymentstatuspanel"
Cohesion: 0.07
Nodes (39): authorizeDealPayment(), getCurrentAgreement(), getOrganization(), listPaymentStatuses(), OrganizationDirectoryItem, PaymentStatus, DealConstellation(), DealConstellationProps (+31 more)

### Community 16 - "Frontend Package"
Cohesion: 0.06
Nodes (47): devDependencies, eslint@^10.13.0, @eslint/js@^10.0.1, eslint-plugin-react-hooks@^7.1.1, eslint-plugin-react-refresh@^0.4.20, globals@^17.13.0, happy-dom@^21.0.3, @testing-library/dom@^10.4.1 (+39 more)

### Community 18 - "Api Database Skill"
Cohesion: 0.04
Nodes (43): API and Database Engineer Skill, API Design and Contract Semantics, Data Integrity and Invariant Enforcement, Query Performance and Projection Optimization, Schema Migration and Backward Compatibility, Transaction Boundaries and Atomicity, Archify Diagrammer Skill, Archify CLI Global Tool (+35 more)

### Community 19 - "Api Routes Conversations"
Cohesion: 0.06
Nodes (39): add_message_route(), AddMessageRequest, AISuggestionRequest, clarify_fact_route(), confirm_fact_route(), ConstraintResponse, correct_fact_route(), CorrectFactRequest (+31 more)

### Community 20 - "test_outbox_dispatcher.py"
Cohesion: 0.10
Nodes (4): _register_shutdown_handlers(), _remove_shutdown_handlers(), _request_shutdown(), WorkerShutdownSignalTests

### Community 21 - "App Service Agreements"
Cohesion: 0.09
Nodes (15): AgreementRepository, AuditEventDraft, AuditRepository, commit_agreement(), create_agreement_draft(), create_reviewed_agreement_draft(), get_current_agreement(), ObligationRepository (+7 more)

### Community 22 - "Frontend Aisuggestionreview"
Cohesion: 0.10
Nodes (34): correctDealFact(), createAgreementFromReviewedTerms(), createDealFact(), draftDealProposal(), reviewDealFact(), suggestDealFacts(), DealFact, FactReviewAction (+26 more)

### Community 23 - "Operational Recovery & Logging"
Cohesion: 0.07
Nodes (19): OperationalFastAPI, OperationalRequestMiddleware, _connect_with_retry(), main(), run_forever(), main(), run_forever(), GmailSettings (+11 more)

### Community 24 - "Domain Conversations"
Cohesion: 0.09
Nodes (5): Constraint, Message, FakeCommunicationRepository, FakeCommunicationRepository, FakeCommunicationRepository

### Community 25 - "Repository Communications"
Cohesion: 0.08
Nodes (14): ConstraintKind, ConstraintStatus, Conversation, MessageSourceType, Visibility, MessageId, CommunicationScopeError, _constraint_to_domain() (+6 more)

### Community 26 - "Accept Invitation()"
Cohesion: 0.21
Nodes (5): accept_invitation(), AcceptInvitationRequest, create_organization_invitation(), CreateInvitationRequest, OrganizationInvitationTests

### Community 27 - "Build In Process Client("
Cohesion: 0.10
Nodes (8): _build_in_process_client(), ci_deal_flow_hook(), DealFlowContext, DealFlowSimulator, run_simulation(), SimulationError, StepRecord, TerminalFormatter

### Community 28 - "Commercial Domain Model"
Cohesion: 0.06
Nodes (26): Outbox Relay Worker Process, PayPal Payment Worker Process, PayPal Invoicing Webhook Endpoint, AgreementVersion Aggregate, Append-Only AuditEvent Ledger, Commercial Constraint and Provenance, Deal Aggregate, Organization and Membership Entities (+18 more)

### Community 29 - "Frontend Dealconversationreview"
Cohesion: 0.08
Nodes (32): createDealMessage(), Visibility, areFactsEqual(), ConversationState, DealConversationReview(), addSuggestedFact(), replaceSuggestedFact(), reviewFact() (+24 more)

### Community 30 - "Commitagreementcommand"
Cohesion: 0.09
Nodes (7): CommitAgreementCommand, RecordApprovalCommand, commit_agreement_in_transaction(), record_approval_in_transaction(), AgreementCommitTests, LocalWorkflowSmokeTests, commit_once()

### Community 31 - "Argparse"
Cohesion: 0.09
Nodes (5): PaymentInvoiceNotice, main(), GmailSMTPInvoiceNotifier, _FakeSMTP, GmailSMTPInvoiceNotifierTests

### Community 32 - "Repository Organizations"
Cohesion: 0.09
Nodes (11): Organization, OrganizationMember, OrganizationMemberRole, OrganizationMemberStatus, OrganizationStatus, create_database_engine(), _membership_to_domain(), _organization_to_domain() (+3 more)

### Community 33 - "AISuggestionProviderTests"
Cohesion: 0.16
Nodes (3): DeterministicFakeAIProvider, AISuggestionProviderTests, extract_facts()

### Community 35 - "Test Payment Processing P"
Cohesion: 0.15
Nodes (5): FakeInvoiceProvider, FakeProcessingRepository, PaymentProcessingTests, _request(), _work_item()

### Community 36 - "Frontend Onboardingwizard"
Cohesion: 0.13
Nodes (13): CreateOrganizationInput, Organization, COUNTRY_NAMES, CountryOption, describeError(), isAmbiguousCreateFailure(), handleSubmit(), OnboardingWizardProps (+5 more)

### Community 37 - "react"
Cohesion: 0.10
Nodes (22): addOrganizationMember(), createOrganization(), describeError(), OrganizationsPanel(), handleCreate(), handleInvite(), OrganizationsState, AcceptInvitationResponse (+14 more)

### Community 38 - "create_worker"
Cohesion: 0.20
Nodes (3): create_worker(), workflow_activities(), WorkflowWorkerTests

### Community 39 - "listOrganizations"
Cohesion: 0.10
Nodes (30): listOrganizations(), clearAccessToken(), getAccessToken(), setAccessToken(), setTokens(), TokenResponse, App(), mockedApiRequest (+22 more)

### Community 40 - "ai.py"
Cohesion: 0.07
Nodes (14): AIRetryPolicy, AISuggestionProvider, call_with_bounded_retry(), draft_proposal(), draft_proposal_from_context(), extract_facts(), extract_facts_from_context(), FactExtractionResult (+6 more)

### Community 41 - "Paymentworkitem"
Cohesion: 0.08
Nodes (13): PaymentInvoiceNotifier, PaymentInvoiceProvider, claim_next_payment_event(), _claim_statement(), _ClaimedPaymentEvent, dispatch_one_payment_event(), dispatch_pending_payment_events(), _finish_event() (+5 more)

### Community 43 - "Repository Payment Processing"
Cohesion: 0.14
Nodes (6): PaymentInvoiceLineItem, PaymentWorkItem, _restore_domain_intent(), SqlAlchemyPaymentProcessingRepository, transition(), transition()

### Community 44 - "Api Routes Organizations"
Cohesion: 0.13
Nodes (8): AcceptInvitationResponse, add_organization_member(), AddOrganizationMemberRequest, create_organization(), CreateOrganizationRequest, InvitationResponse, OrganizationDirectoryItem, OrganizationOnboardingTests

### Community 46 - "0001 Initial Schema"
Cohesion: 0.10
Nodes (10): upgrade(), uuid_column(), upgrade(), upgrade(), upgrade(), upgrade(), downgrade(), upgrade() (+2 more)

### Community 49 - "Domain Deal"
Cohesion: 0.12
Nodes (4): Deal, DealStatus, _deal_to_domain(), FakeDealRepository

### Community 50 - "infrastructure/outbox.py"
Cohesion: 0.16
Nodes (8): DealWorkflowStarter, OutboxDispatchResult, apply_dispatch_result(), claim_next_pending_event(), _claim_statement(), dispatch_one_pending_event(), dispatch_pending_outbox_events(), PostgresDispatcherTests

### Community 51 - "Alembic Migration"
Cohesion: 0.08
Nodes (5): run_migrations_offline(), run_migrations_online(), CommunicationMigrationTests, OrganizationIndexMigrationTests, PaymentCreateStartedMigrationTests

### Community 53 - "AIContractError"
Cohesion: 0.25
Nodes (9): AIContractError, _check_keys(), _decimal(), _required_string(), _validate_decimal(), _validate_fact_value(), _validate_schema_version(), _validate_unit() (+1 more)

### Community 54 - "Api Routes Auth"
Cohesion: 0.11
Nodes (7): _decode_token(), _development_actor(), development_login(), get_current_actor(), _unauthorized(), _require_demo_admin(), resolve_actor()

### Community 55 - "seed_demo.py"
Cohesion: 0.12
Nodes (7): hash_password(), verify_password(), DemoIdentity, main(), _password_for(), seed_demo_data(), DemoSeedTests

### Community 56 - "Frontend Agreementreview"
Cohesion: 0.14
Nodes (22): commitAgreementVersion(), recordAgreementDecision(), AgreementApproval, AgreementVersion, paymentTimingLabel(), AgreementReview(), commitCurrentAgreement(), decide() (+14 more)

### Community 57 - "workflow_state.py"
Cohesion: 0.10
Nodes (10): DealWorkflowState, load_deal_workflow_state(), parse_workflow_uuid(), WorkflowAgreementRepository, WorkflowDealNotFound, WorkflowDealRepository, _domain_deal(), _FakeAgreementRepository (+2 more)

### Community 58 - "Domain Proposal"
Cohesion: 0.20
Nodes (8): NegotiationSession, NegotiationSubmissionOutcome, Proposal, ProposalStatus, NegotiationSessionId, ProposalId, build_proposal(), NegotiationTests

### Community 60 - "Compose Yaml"
Cohesion: 0.09
Nodes (22): POSTGRES_DB, POSTGRES_PASSWORD, POSTGRES_USER, interval, retries, test, timeout, environment (+14 more)

### Community 61 - "application/deals.py"
Cohesion: 0.16
Nodes (6): _both_organizations_active(), create_deal(), CreateDealCommand, DealAccessDenied, DealUseCaseTests, FakeDealRepository

### Community 62 - "Operational Recovery & Logging"
Cohesion: 0.20
Nodes (4): captured_output(), SafeOperationsTests, exercise(), failed_db()

### Community 63 - "InvalidTransition"
Cohesion: 0.14
Nodes (9): PaymentIntent, PaymentIntentStatus, PaymentMilestone, VerifiedProviderPaymentState, InvalidTransition, PaymentIntentId, PaymentMilestoneId, transition() (+1 more)

### Community 64 - "Any"
Cohesion: 0.13
Nodes (4): RefreshDealStateActivity, _workflow_input_value(), RefreshDealStateActivityTests, factory()

### Community 65 - "refresh_access_token"
Cohesion: 0.19
Nodes (4): _hash_refresh_token(), refresh_access_token(), RefreshRequest, RefreshToken

### Community 67 - "Api Routes Dev"
Cohesion: 0.17
Nodes (10): _aggregate_scope(), _delete_scoped(), _demo_organization_ids(), DevResetResponse, DevRoleSwitchRequest, _missing_demo_emails(), _related_ids(), _require_seeded_demo_identities() (+2 more)

### Community 68 - "Commercialdocumentdraftre"
Cohesion: 0.12
Nodes (6): CommercialDocumentDraftResponse, get_commercial_document_draft_route(), AgreementNotCommitted, CommercialDocumentDraft, generate_commercial_document_draft(), CommercialDocumentDraftTests

### Community 69 - "DealWorkflowNotification"
Cohesion: 0.12
Nodes (7): WorkflowStartError, WorkflowStartOutcome, WorkflowStartPermanentError, DealWorkflowNotification, NotificationKind, TemporalDealWorkflowStarter, TemporalAdapterTests

### Community 70 - "DealWorkflowInput"
Cohesion: 0.12
Nodes (7): DealWorkflowInput, DealWorkflowStatus, _require_uuid(), new_workflow_input(), RefreshActivity, RefreshCall, WorkflowWorkerIntegrationTests

### Community 71 - "Session"
Cohesion: 0.09
Nodes (10): _active_admin_membership(), _case_insensitive_prefix(), _create_invitation_token(), _deal_awaiting_counterparty(), _escape_like(), get_optional_actor(), get_organization_route(), list_my_organizations() (+2 more)

### Community 73 - "InvariantViolation"
Cohesion: 0.14
Nodes (3): _normalized_text(), _require_decimal(), InvariantViolation

### Community 74 - "Demo Lifecycle"
Cohesion: 0.21
Nodes (7): _acquire_lock(), _is_demo_deal(), lock_demo_deal_creation(), lock_demo_payment_processing(), lock_demo_reset(), DemoLifecycleLockTests, _postgres_session()

### Community 75 - "Frontend Tsconfig"
Cohesion: 0.11
Nodes (17): compilerOptions, allowImportingTsExtensions, jsx, lib, module, moduleDetection, moduleResolution, noEmit (+9 more)

### Community 76 - "fake.py"
Cohesion: 0.16
Nodes (4): AIPermanentError, AIProviderError, FactExtractionRequest, ProposalDraftRequest

### Community 77 - "Agreement"
Cohesion: 0.17
Nodes (6): Agreement, AgreementId, AgreementVersionId, FakeAgreementRepository, DealDomainTests, make_deal()

### Community 78 - "Money"
Cohesion: 0.12
Nodes (12): _money(), _parse_money(), PaymentTerm, ShipmentTerm, TradeLineItem, TradeTerms, Money, with_timing() (+4 more)

### Community 79 - "SqlAlchemyPaymentIntentRepository"
Cohesion: 0.17
Nodes (3): PaymentStatusResponse, SqlAlchemyPaymentIntentRepository, PaymentStatusExtendedModelTests

### Community 80 - "authorize_payment_intent"
Cohesion: 0.14
Nodes (8): OutboxEventDraft, OutboxRepository, authorize_payment_intent(), AuthorizePaymentIntentCommand, PaymentIntentAuthorizationOutcome, PaymentIntentRepository, SellerMembershipRepository, UnauthorizedPaymentAuthorization

### Community 82 - "api/payments.py"
Cohesion: 0.11
Nodes (10): authorize_payment_route(), AuthorizePaymentRequest, AuthorizePaymentResponse, get_payment_status_repository(), list_payment_statuses_route(), DuplicateActivePaymentIntent, list_current_payment_statuses(), PaymentStatusRecord (+2 more)

### Community 83 - "repositories/__init__.py"
Cohesion: 0.15
Nodes (4): SqlAlchemyAuditRepository, SqlAlchemyObligationRepository, SqlAlchemyOutboxRepository, SqlAlchemyPaymentMilestoneRepository

### Community 85 - ".add"
Cohesion: 0.16
Nodes (5): PaymentIntentCommandMismatch, PaymentMilestoneNotFound, _is_idempotency_key_violation(), _is_one_active_per_milestone_violation(), _violated_constraint_name()

### Community 86 - "Dealworkflowresult"
Cohesion: 0.29
Nodes (3): DealWorkflowResult, DealWorkflowTests, new_notification()

### Community 88 - "Api Routes Auth"
Cohesion: 0.24
Nodes (6): _as_utc(), create_refresh_token(), _encode_access_token(), _issue_tokens(), _replay_rotation(), _revoke_family()

### Community 89 - "Paymentinvoicereconciliat"
Cohesion: 0.15
Nodes (4): PaymentInvoiceReconciliation, FakePayPalInvoiceProvider, get_invoice_reconciliation(), get_invoice_reconciliation()

### Community 90 - "Settings"
Cohesion: 0.19
Nodes (3): _is_weak_jwt_secret(), Settings, IdentityBoundaryTests

### Community 92 - "AIContractTests"
Cohesion: 0.21
Nodes (4): parse_proposed_terms(), ProposedTerms, scope_extracted_facts(), AIContractTests

### Community 94 - "CreateDealPage.tsx"
Cohesion: 0.14
Nodes (12): CreateDealPage(), handleSubmit(), CreateDealPageProps, describeCreateError(), describeError(), DirectoryItem, FieldErrors, OrganizationsState (+4 more)

### Community 95 - "Credentialsrequest"
Cohesion: 0.24
Nodes (5): CredentialsRequest, login(), TokenResponse, fail(), scalar()

### Community 96 - "contracts.py"
Cohesion: 0.14
Nodes (11): AIValidationClaim, _contains_numeric_token(), _contains_token(), _date_value_is_present(), _fact_value_is_supported_by_quote(), _flexible_whitespace_pattern(), _number_with_currency_is_present(), _number_with_unit_is_present() (+3 more)

### Community 97 - "api/paypal_webhooks.py"
Cohesion: 0.18
Nodes (4): get_paypal_webhook_configuration(), _persist_paypal_webhook_event(), PayPalSettings, record_paypal_webhook_event()

### Community 99 - "test_ai_provider.py"
Cohesion: 0.28
Nodes (3): parse_extracted_facts(), _fact_payload(), _proposal_payload()

### Community 106 - "Implementation Roadmap"
Cohesion: 0.22
Nodes (9): SyncAlly Implementation Plan, Stage 1 - Basics and Identity, Stage 2 - Create and View Deals, Stage 3 - Messages and Facts Isolation, Stage 4 - AI Suggestions and Review, Stage 5 - Agreement and Approvals, Stage 6 - Background Deal Workflow, Stage 7 - PayPal Sandbox Payment (+1 more)

### Community 107 - "0005 Conversation Party U"
Cohesion: 0.36
Nodes (5): _create_party_unique_constraint(), _deduplicate_conversations(), downgrade(), _drop_party_unique_constraint(), upgrade()

### Community 110 - "Commercial Invariants"
Cohesion: 0.29
Nodes (4): Modular Monolith System Shape, Workflow Orchestration Rules, MVP Commercial Boundary, SyncAlly Commercial Platform

### Community 114 - "apiRequest"
Cohesion: 0.07
Nodes (25): ApiError, getCommercialDocumentDraft(), CommercialDocumentDraft, CommercialDocumentPanel(), CommercialDocumentPanelProps, DocumentState, mockedGetDraft, DEAL (+17 more)

### Community 122 - "0004_communication_sources_and_scope_indexes.py"
Cohesion: 0.60
Nodes (4): _create_scope_index(), downgrade(), _drop_scope_index(), upgrade()

### Community 124 - "Repo Idea Thinker Skill"
Cohesion: 0.50
Nodes (3): Repo Idea Thinker Skill, Repository-Grounded Ideation Discipline, Idea Quality Standards and Lightweight Validation

### Community 128 - "Frontend Readme"
Cohesion: 0.67
Nodes (3): Frontend HTML Root Document, Frontend API Client and Agreement State, React and TypeScript Vite Web App

## Knowledge Gaps
- **47 isolated node(s):** `syncally`, `Stage 1 - Basics and Identity`, `Stage 2 - Create and View Deals`, `Stage 3 - Messages and Facts Isolation`, `Stage 4 - AI Suggestions and Review` (+42 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1100 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **53 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ActorContext` connect `Actorcontext` to `identifiers.py`, `sqlalchemy_orm`, `Db Models Deals`, `Api Routes Agreements`, `App Service Conversations`, `api/deals.py`, `Reconstitute()`, `Conversationroutetests`, `Agreementroutetests`, `Api Routes Conversations`, `App Service Agreements`, `Accept Invitation()`, `AISuggestionProviderTests`, `Case Insensitive Prefix(`, `ai.py`, `Api Routes Organizations`, `ConversationUseCaseTests`, `ConversationContractTests`, `Api Routes Auth`, `application/deals.py`, `Commercialdocumentdraftre`, `Session`, `SqlAlchemyPaymentIntentRepository`, `authorize_payment_intent`, `api/payments.py`, `AiContextSelectionTests`, `DealRepository`, `Settings`, `Demolifecycletests`?**
  _High betweenness centrality (0.087) - this node is a cross-community bridge._
- **Are the 76 inferred relationships involving `ActorContext` (e.g. with `approve_agreement_route()` and `commit_agreement_route()`) actually correct?**
  _`ActorContext` has 76 INFERRED edges - model-reasoned connections that need verification._
- **What connects `syncally`, `Stage 1 - Basics and Identity`, `Stage 2 - Create and View Deals` to the rest of the system?**
  _47 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `identifiers.py` be split into smaller, more focused modules?**
  _Cohesion score 0.10101010101010101 - nodes in this community are weakly interconnected._
- **Why does `OrganizationId` connect `Reconstitute()` to `identifiers.py`, `Db Models Deals`, `Api Routes Agreements`, `App Service Outbox`, `App Service Conversations`, `Repository Agreements`, `Conversationroutetests`, `Agreementroutetests`, `Api Routes Conversations`, `App Service Agreements`, `Domain Conversations`, `Repository Communications`, `Commitagreementcommand`, `Repository Organizations`, `AISuggestionProviderTests`, `ai.py`, `Repository Payment Processing`, `ConversationUseCaseTests`, `ConversationContractTests`, `Domain Deal`, `workflow_state.py`, `Domain Proposal`, `PaymentIntentRepositoryTests`, `application/deals.py`, `InvalidTransition`, `Commercialdocumentdraftre`, `Session`, `Agreement`, `Money`, `SqlAlchemyPaymentIntentRepository`, `AiContextSelectionTests`, `.add`, `AIContractTests`, `contracts.py`, `_to_domain`?**
  _High betweenness centrality (0.058) - this node is a cross-community bridge._
- **Are the 48 inferred relationships involving `OrganizationId` (e.g. with `create_reviewed_agreement_draft_route()` and `Agreement`) actually correct?**
  _`OrganizationId` has 48 INFERRED edges - model-reasoned connections that need verification._
- **Should `sqlalchemy_orm` be split into smaller, more focused modules?**
  _Cohesion score 0.0867283950617284 - nodes in this community are weakly interconnected._