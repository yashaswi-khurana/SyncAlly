# Graph Report - SyncAlly  (2026-10-31)

## Corpus Check
- 227 files · ~145,102 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 8 file(s) not represented in the graph (top: (none) 4, .example 1, .ini 1)

## Summary
- 3322 nodes · 10277 edges · 146 communities (98 shown, 48 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 1348 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `a15e4c44`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Ast
- App Service Deals
- Asyncio
- Frontend Organizationssettingspage
- Db Models Deals
- App Service Payment Proce
- Api Routes Agreements
- App Service Outbox
- App Service Conversations
- Paymentinvoicelookup
- ApiError
- Api Routes Deals
- Repository Agreements
- Reconstitute()
- Frontend Paymentstatuspanel
- Conversationroutetests
- Frontend Package
- Agreementroutetests
- Api Database Skill
- Api Routes Conversations
- App Service Workflow Noti
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
- client.ts
- Case Insensitive Prefix(
- Test Payment Processing P
- Frontend Onboardingwizard
- Deterministicfakeaiprovid
- Connect With Retry()
- Frontend App Test
- Aipermanenterror
- Paymentworkitem
- Devroutestests
- Repository Payment Processing
- Api Routes Organizations
- Addmessagecommand
- 0001 Initial Schema
- Concurrentconstraintupdat
- Temporal Deal
- Domain Deal
- Agreementrepository
- Alembic Migration
- Actorcontext
- Domain Contracts
- Api Routes Auth
- seed_demo_data
- Frontend Agreementreview
- Load Deal Workflow State(
- Domain Proposal
- Authorize Payment Intent
- Compose Yaml
- Api Routes Organizations
- Operational Recovery & Logging
- Restore()
- Any
- refresh_access_token
- Paymentintentstatus
- Api Routes Dev
- Commercialdocumentdraftre
- DealWorkflowNotification
- Dealworkflownotification
- Domain Trade Terms
- Session
- Domain Agreement
- Demo Lifecycle
- Frontend Tsconfig
- Paymentstatusresponse
- Authorize Payment Intent(
- Paymentterm
- Domain Trade Terms
- From Mapping()
- Fakewebhookverifier
- Get Payment Status Reposi
- Aicontext
- Repository Payments
- Domain Contracts
- Dealworkflowresult
- Agreementversionid
- Api Routes Auth
- Paymentinvoicereconciliat
- Settings
- Api Routes Main
- Api Routes Paypal Webhooks
- Domain Intent
- CreateDealPage.tsx
- Credentialsrequest
- Api Routes Conversations
- Domain Money
- Repository Deals
- Repository Payments
- Domain Organization
- Dealauthorizationtests
- Operational Recovery & Logging
- Api Routes Payments
- Databasepersistencetests
- Demolifecycletests
- Implementation Roadmap
- 0005 Conversation Party U
- Api Routes Main
- Parse Extracted Facts()
- Commercial Invariants
- Migrationsettings
- DealDetailPage.tsx
- Api Routes Main
- Conversationpartyuniquene
- 0004 Communication Source
- Providerinvoiceuniquemigr
- Api Routes Organizations
- Payment Invoice Number()
- _domain_deal
- Repo Idea Thinker Skill
- .refresh_deal_state
- Frontend Readme
- Frontend Vite-Env D
- Jwt Authentication And Re
- repositories/payments.py
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

## Communities (146 total, 48 thin omitted)

### Community 0 - "Ast"
Cohesion: 0.05
Nodes (34): AISuggestionRequest, _fact_suggestion_guidance(), FactCorrectionResponse, FactSuggestionResponse, get_ai_suggestion_provider(), MessageExistenceResponse, _missing_trade_fields(), ProposalSuggestionResponse (+26 more)

### Community 1 - "App Service Deals"
Cohesion: 0.07
Nodes (3): CommercialDocumentDraft, PaymentIntentId, DomainDependencyTests

### Community 2 - "Asyncio"
Cohesion: 0.09
Nodes (8): OperationalFastAPI, _decode_invitation_token(), hash_password(), verify_password(), DemoIdentity, _password_for(), get_db(), HealthRouteTests

### Community 3 - "Frontend Organizationssettingspage"
Cohesion: 0.08
Nodes (31): dependencies, react@^19.3.0, react-dom@^19.3.0, three@^0.186.1, login(), App(), handleOrganizationCreated(), refreshSessionView() (+23 more)

### Community 4 - "Db Models Deals"
Cohesion: 0.09
Nodes (23): _require_dev_environment(), NotificationKind, AgreementVersion, Approval, Obligation, Base, Constraint, Conversation (+15 more)

### Community 5 - "App Service Payment Proce"
Cohesion: 0.07
Nodes (13): PaymentInvoiceNotifier, PaymentInvoiceProvider, PaymentProcessingRepository, process_payment_intent(), reconcile_payment_intent(), _request_id_retry_window_expired(), claim_next_payment_event(), _claim_statement() (+5 more)

### Community 6 - "Api Routes Agreements"
Cohesion: 0.08
Nodes (23): AgreementVersionResponse, ApprovalResponse, approve_agreement_route(), commit_agreement_route(), CommitAgreementRequest, create_agreement_draft_route(), create_reviewed_agreement_draft_route(), CreateAgreementDraftRequest (+15 more)

### Community 7 - "App Service Outbox"
Cohesion: 0.11
Nodes (12): build_deal_workflow_id(), dispatch_outbox_event(), OutboxDispatchResult, PendingOutboxEvent, apply_dispatch_result(), claim_next_pending_event(), _claim_statement(), dispatch_one_pending_event() (+4 more)

### Community 8 - "App Service Conversations"
Cohesion: 0.08
Nodes (19): add_message(), can_view_constraint(), can_view_message(), CommunicationRepository, correct_constraint(), create_manual_constraint(), CreateManualConstraintCommand, deal_has_any_message() (+11 more)

### Community 9 - "Paymentinvoicelookup"
Cohesion: 0.09
Nodes (12): PaymentInvoiceLookup, PaymentInvoiceRequest, PaymentNeedsAction, PaymentOutcomeUnknown, PaymentRetryableError, _has_excess_currency_precision(), PayPalSandboxInvoiceProvider, _provider_error_code() (+4 more)

### Community 10 - "ApiError"
Cohesion: 0.07
Nodes (30): addOrganizationMember(), ApiError, Organization, ViewerRole, DealsPage(), DealsPageProps, DealsState, describeError() (+22 more)

### Community 11 - "Api Routes Deals"
Cohesion: 0.07
Nodes (17): create_deal_route(), CreateDealRequest, DealResponse, DealSummaryResponse, get_deal_repository(), list_deals_route(), read_deal_route(), _to_response() (+9 more)

### Community 12 - "Repository Agreements"
Cohesion: 0.09
Nodes (16): AgreementAccessDenied, AgreementAlreadyCommitted, AgreementNotFound, AgreementVersionConflict, CreateAgreementDraftCommand, DuplicateApproval, ProposalNotFound, StaleAgreementVersion (+8 more)

### Community 13 - "Reconstitute()"
Cohesion: 0.11
Nodes (12): Conversation, ConstraintId, ConversationId, DealId, OrganizationId, UserId, constraint(), message() (+4 more)

### Community 14 - "Frontend Paymentstatuspanel"
Cohesion: 0.10
Nodes (26): authorizeDealPayment(), OrganizationDirectoryItem, PaymentStatus, describeStatus(), displayAmount(), ExtendedPaymentStatus, extractInvoiceNumber(), firstMilestoneAmount() (+18 more)

### Community 16 - "Frontend Package"
Cohesion: 0.06
Nodes (47): devDependencies, eslint@^10.13.0, @eslint/js@^10.0.1, eslint-plugin-react-hooks@^7.1.1, eslint-plugin-react-refresh@^0.4.20, globals@^17.13.0, happy-dom@^21.0.3, @testing-library/dom@^10.4.1 (+39 more)

### Community 18 - "Api Database Skill"
Cohesion: 0.04
Nodes (43): API and Database Engineer Skill, API Design and Contract Semantics, Data Integrity and Invariant Enforcement, Query Performance and Projection Optimization, Schema Migration and Backward Compatibility, Transaction Boundaries and Atomicity, Archify Diagrammer Skill, Archify CLI Global Tool (+35 more)

### Community 19 - "Api Routes Conversations"
Cohesion: 0.09
Nodes (20): add_message_route(), clarify_fact_route(), confirm_fact_route(), ConstraintResponse, correct_fact_route(), create_fact_route(), get_communication_repository(), _list_all_visible_constraints() (+12 more)

### Community 21 - "App Service Agreements"
Cohesion: 0.08
Nodes (15): AuditEventDraft, AuditRepository, commit_agreement(), get_current_agreement(), ObligationRepository, OutboxEventDraft, OutboxRepository, PaymentMilestoneRepository (+7 more)

### Community 22 - "Frontend Aisuggestionreview"
Cohesion: 0.07
Nodes (49): correctDealFact(), createAgreementFromReviewedTerms(), createDealFact(), draftDealProposal(), reviewDealFact(), suggestDealFacts(), AgreementLineItem, AgreementStatus (+41 more)

### Community 23 - "Operational Recovery & Logging"
Cohesion: 0.13
Nodes (12): _connect_with_retry(), main(), run_forever(), main(), run_forever(), is_permanent_rpc_error(), configure_logging(), log_operation() (+4 more)

### Community 24 - "Domain Conversations"
Cohesion: 0.08
Nodes (4): Constraint, FakeCommunicationRepository, FakeCommunicationRepository, FakeCommunicationRepository

### Community 25 - "Repository Communications"
Cohesion: 0.10
Nodes (6): Visibility, CommunicationScopeError, _constraint_to_domain(), _conversation_to_domain(), _page_bounds(), SqlAlchemyCommunicationRepository

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
Cohesion: 0.07
Nodes (35): createDealMessage(), Deal, DealMessage, DealSummary, Visibility, areFactsEqual(), ConversationState, DealConversationReview() (+27 more)

### Community 30 - "Commitagreementcommand"
Cohesion: 0.10
Nodes (5): CommitAgreementCommand, commit_agreement_in_transaction(), AgreementCommitTests, LocalWorkflowSmokeTests, commit_once()

### Community 31 - "Argparse"
Cohesion: 0.08
Nodes (8): get_paypal_webhook_configuration(), PaymentInvoiceNotice, main(), GmailSettings, PayPalSettings, GmailSMTPInvoiceNotifier, _FakeSMTP, GmailSMTPInvoiceNotifierTests

### Community 32 - "Repository Organizations"
Cohesion: 0.09
Nodes (8): Organization, OrganizationMember, create_database_engine(), _membership_to_domain(), _organization_to_domain(), SqlAlchemyOrganizationMemberRepository, SqlAlchemyOrganizationRepository, OrganizationRepositoryTests

### Community 33 - "client.ts"
Cohesion: 0.08
Nodes (40): apiBaseUrl(), apiRequest(), createDeal(), describeDetail(), getDeal(), getDealMessageExistence(), getOrganization(), isAbortError() (+32 more)

### Community 34 - "Case Insensitive Prefix("
Cohesion: 0.14
Nodes (4): _case_insensitive_prefix(), _escape_like(), value(), OrganizationDirectoryTests

### Community 35 - "Test Payment Processing P"
Cohesion: 0.14
Nodes (5): FakeInvoiceProvider, FakeProcessingRepository, PaymentProcessingTests, _request(), _work_item()

### Community 36 - "Frontend Onboardingwizard"
Cohesion: 0.14
Nodes (15): createOrganization(), CreateOrganizationInput, COUNTRY_NAMES, CountryOption, describeError(), isAmbiguousCreateFailure(), OnboardingWizard(), findExistingOrganization() (+7 more)

### Community 37 - "Deterministicfakeaiprovid"
Cohesion: 0.13
Nodes (3): DeterministicFakeAIProvider, AISuggestionProviderTests, extract_facts()

### Community 38 - "Connect With Retry()"
Cohesion: 0.09
Nodes (11): _connect_with_retry(), create_worker(), _register_shutdown_handlers(), _remove_shutdown_handlers(), _request_shutdown(), run_worker(), workflow_activities(), ConnectWithRetryTests (+3 more)

### Community 39 - "Frontend App Test"
Cohesion: 0.14
Nodes (21): API_REQUEST_TIMEOUT_MS, listOrganizations(), CREATED_MESSAGE, fetchMock, lastRequest(), sentBody(), clearAccessToken(), getAccessToken() (+13 more)

### Community 40 - "Aipermanenterror"
Cohesion: 0.10
Nodes (9): AIPermanentError, AIProviderError, FactExtractionRequest, ProposalDraftRequest, ExtractedFact, FactField, DemoAISuggestionProvider, _is_ambiguous_numeric_term() (+1 more)

### Community 41 - "Paymentworkitem"
Cohesion: 0.11
Nodes (5): PaymentWorkItem, FakeRepository, NoCallProvider, PaymentOutboxWorkerTests, _utc()

### Community 43 - "Repository Payment Processing"
Cohesion: 0.16
Nodes (5): PaymentInvoiceLineItem, _restore_domain_intent(), SqlAlchemyPaymentProcessingRepository, transition(), transition()

### Community 44 - "Api Routes Organizations"
Cohesion: 0.13
Nodes (8): AcceptInvitationResponse, add_organization_member(), AddOrganizationMemberRequest, create_organization(), CreateOrganizationRequest, InvitationResponse, OrganizationDirectoryItem, OrganizationOnboardingTests

### Community 45 - "Addmessagecommand"
Cohesion: 0.11
Nodes (4): AddMessageCommand, ConstraintRepository, review_constraint(), ConversationUseCaseTests

### Community 46 - "0001 Initial Schema"
Cohesion: 0.10
Nodes (10): upgrade(), uuid_column(), upgrade(), upgrade(), upgrade(), upgrade(), downgrade(), upgrade() (+2 more)

### Community 47 - "Concurrentconstraintupdat"
Cohesion: 0.13
Nodes (5): ConcurrentConstraintUpdate, confirm_constraint(), ConstraintNotFound, ConversationContractTests, FakeConstraintRepository

### Community 49 - "Domain Deal"
Cohesion: 0.13
Nodes (4): Deal, DealStatus, _deal_to_domain(), FakeDealRepository

### Community 50 - "Agreementrepository"
Cohesion: 0.13
Nodes (8): AgreementRepository, create_agreement_draft(), create_reviewed_agreement_draft(), CreateReviewedAgreementDraftCommand, record_approval(), RecordApprovalCommand, Approval, record_approval_in_transaction()

### Community 51 - "Alembic Migration"
Cohesion: 0.10
Nodes (4): run_migrations_offline(), run_migrations_online(), CommunicationMigrationTests, PaymentCreateStartedMigrationTests

### Community 53 - "Domain Contracts"
Cohesion: 0.19
Nodes (10): AIContractError, _check_keys(), _decimal(), _required_string(), SourceReference, _validate_decimal(), _validate_fact_value(), _validate_schema_version() (+2 more)

### Community 54 - "Api Routes Auth"
Cohesion: 0.11
Nodes (7): _decode_token(), _development_actor(), development_login(), get_current_actor(), _unauthorized(), _require_demo_admin(), resolve_actor()

### Community 55 - "seed_demo_data"
Cohesion: 0.22
Nodes (3): main(), seed_demo_data(), DemoSeedTests

### Community 56 - "Frontend Agreementreview"
Cohesion: 0.14
Nodes (23): commitAgreementVersion(), getCurrentAgreement(), recordAgreementDecision(), AgreementApproval, AgreementVersion, paymentTimingLabel(), AgreementReview(), commitCurrentAgreement() (+15 more)

### Community 57 - "Load Deal Workflow State("
Cohesion: 0.14
Nodes (6): DealWorkflowState, load_deal_workflow_state(), parse_workflow_uuid(), WorkflowAgreementRepository, WorkflowDealNotFound, WorkflowDealRepository

### Community 58 - "Domain Proposal"
Cohesion: 0.21
Nodes (8): NegotiationSession, NegotiationSubmissionOutcome, Proposal, ProposalStatus, NegotiationSessionId, ProposalId, build_proposal(), NegotiationTests

### Community 60 - "Compose Yaml"
Cohesion: 0.09
Nodes (22): POSTGRES_DB, POSTGRES_PASSWORD, POSTGRES_USER, interval, retries, test, timeout, environment (+14 more)

### Community 61 - "Api Routes Organizations"
Cohesion: 0.12
Nodes (7): _active_admin_membership(), _create_invitation_token(), _deal_awaiting_counterparty(), get_optional_actor(), get_organization_route(), list_my_organizations(), list_organization_directory()

### Community 62 - "Operational Recovery & Logging"
Cohesion: 0.22
Nodes (4): captured_output(), SafeOperationsTests, exercise(), failed_db()

### Community 63 - "Restore()"
Cohesion: 0.21
Nodes (7): PaymentMilestone, VerifiedProviderPaymentState, PaymentMilestoneId, Money, transition(), DecimalCanonicalizationTests, PaymentReconciliationTests

### Community 64 - "Any"
Cohesion: 0.11
Nodes (8): RefreshDealStateActivity, DealWorkflowInput, _require_uuid(), new_workflow_input(), RefreshActivity, RefreshCall, RefreshDealStateActivityTests, factory()

### Community 65 - "refresh_access_token"
Cohesion: 0.19
Nodes (4): _hash_refresh_token(), refresh_access_token(), RefreshRequest, RefreshToken

### Community 66 - "Paymentintentstatus"
Cohesion: 0.21
Nodes (3): PaymentIntentStatus, VerifiedProviderPaymentStatus, PaymentReconciliationRepositoryTests

### Community 67 - "Api Routes Dev"
Cohesion: 0.17
Nodes (10): _aggregate_scope(), _delete_scoped(), _demo_organization_ids(), DevResetResponse, DevRoleSwitchRequest, _missing_demo_emails(), _related_ids(), _require_seeded_demo_identities() (+2 more)

### Community 68 - "Commercialdocumentdraftre"
Cohesion: 0.13
Nodes (5): CommercialDocumentDraftResponse, get_commercial_document_draft_route(), AgreementNotCommitted, generate_commercial_document_draft(), CommercialDocumentDraftTests

### Community 69 - "DealWorkflowNotification"
Cohesion: 0.11
Nodes (8): DealWorkflowStarter, WorkflowStartError, WorkflowStartOutcome, WorkflowStartPermanentError, WorkflowStartTransientError, DealWorkflowNotification, TemporalDealWorkflowStarter, TemporalAdapterTests

### Community 71 - "Domain Trade Terms"
Cohesion: 0.13
Nodes (3): _normalized_text(), _require_decimal(), InvariantViolation

### Community 73 - "Domain Agreement"
Cohesion: 0.28
Nodes (5): _display(), _render(), Agreement, AgreementId, FakeAgreementRepository

### Community 74 - "Demo Lifecycle"
Cohesion: 0.23
Nodes (7): _acquire_lock(), _is_demo_deal(), lock_demo_deal_creation(), lock_demo_payment_processing(), lock_demo_reset(), DemoLifecycleLockTests, _postgres_session()

### Community 75 - "Frontend Tsconfig"
Cohesion: 0.11
Nodes (17): compilerOptions, allowImportingTsExtensions, jsx, lib, module, moduleDetection, moduleResolution, noEmit (+9 more)

### Community 76 - "Paymentstatusresponse"
Cohesion: 0.17
Nodes (3): PaymentStatusResponse, SqlAlchemyPaymentIntentRepository, PaymentStatusExtendedModelTests

### Community 77 - "Authorize Payment Intent("
Cohesion: 0.16
Nodes (5): authorize_payment_intent(), AuthorizePaymentIntentCommand, PaymentIntentAuthorizationOutcome, PaymentIntentRepository, SellerMembershipRepository

### Community 78 - "Paymentterm"
Cohesion: 0.29
Nodes (6): PaymentTerm, ShipmentTerm, TradeLineItem, build_terms(), TradeTermsTests, _agreement()

### Community 80 - "From Mapping()"
Cohesion: 0.15
Nodes (5): parse_proposed_terms(), ProposedTerms, scope_extracted_facts(), AIContractTests, FakeWebhookVerifier

### Community 82 - "Get Payment Status Reposi"
Cohesion: 0.16
Nodes (4): get_payment_status_repository(), list_payment_statuses_route(), list_current_payment_statuses(), PaymentStatusRepository

### Community 83 - "Aicontext"
Cohesion: 0.24
Nodes (3): AiContext, select_ai_context(), AiContextSelectionTests

### Community 84 - "Repository Payments"
Cohesion: 0.18
Nodes (4): DuplicateActivePaymentIntent, _is_idempotency_key_violation(), _is_one_active_per_milestone_violation(), _violated_constraint_name()

### Community 85 - "Domain Contracts"
Cohesion: 0.23
Nodes (9): AIValidationClaim, _contains_numeric_token(), _contains_token(), _date_value_is_present(), _fact_value_is_supported_by_quote(), _flexible_whitespace_pattern(), _number_with_currency_is_present(), _number_with_unit_is_present() (+1 more)

### Community 86 - "Dealworkflowresult"
Cohesion: 0.29
Nodes (3): DealWorkflowResult, DealWorkflowTests, new_notification()

### Community 87 - "Agreementversionid"
Cohesion: 0.29
Nodes (3): AgreementVersionId, DealDomainTests, make_deal()

### Community 88 - "Api Routes Auth"
Cohesion: 0.24
Nodes (6): _as_utc(), create_refresh_token(), _encode_access_token(), _issue_tokens(), _replay_rotation(), _revoke_family()

### Community 89 - "Paymentinvoicereconciliat"
Cohesion: 0.21
Nodes (4): PaymentInvoiceReconciliation, FakePayPalInvoiceProvider, get_invoice_reconciliation(), get_invoice_reconciliation()

### Community 90 - "Settings"
Cohesion: 0.19
Nodes (3): _is_weak_jwt_secret(), Settings, IdentityBoundaryTests

### Community 92 - "Api Routes Paypal Webhooks"
Cohesion: 0.20
Nodes (3): _persist_paypal_webhook_event(), receive_paypal_invoice_webhook(), record_paypal_webhook_event()

### Community 94 - "CreateDealPage.tsx"
Cohesion: 0.09
Nodes (18): CreateDealPage(), handleSubmit(), CreateDealPageProps, describeCreateError(), describeError(), DirectoryItem, FieldErrors, OrganizationsState (+10 more)

### Community 95 - "Credentialsrequest"
Cohesion: 0.24
Nodes (5): CredentialsRequest, login(), TokenResponse, fail(), scalar()

### Community 96 - "Api Routes Conversations"
Cohesion: 0.22
Nodes (3): AddMessageRequest, CorrectFactRequest, CreateFactRequest

### Community 97 - "Domain Money"
Cohesion: 0.18
Nodes (4): _decimal(), _money(), _parse_money(), canonical_decimal()

### Community 99 - "Repository Payments"
Cohesion: 0.22
Nodes (3): PaymentStatusRecord, _build_invoice_url(), ExtendedPaymentStatusRecord

### Community 100 - "Domain Organization"
Cohesion: 0.38
Nodes (3): OrganizationMemberRole, OrganizationMemberStatus, OrganizationStatus

### Community 103 - "Api Routes Payments"
Cohesion: 0.25
Nodes (4): authorize_payment_route(), AuthorizePaymentRequest, AuthorizePaymentResponse, UnauthorizedPaymentAuthorization

### Community 106 - "Implementation Roadmap"
Cohesion: 0.22
Nodes (9): SyncAlly Implementation Plan, Stage 1 - Basics and Identity, Stage 2 - Create and View Deals, Stage 3 - Messages and Facts Isolation, Stage 4 - AI Suggestions and Review, Stage 5 - Agreement and Approvals, Stage 6 - Background Deal Workflow, Stage 7 - PayPal Sandbox Payment (+1 more)

### Community 107 - "0005 Conversation Party U"
Cohesion: 0.36
Nodes (5): _create_party_unique_constraint(), _deduplicate_conversations(), downgrade(), _drop_party_unique_constraint(), upgrade()

### Community 109 - "Parse Extracted Facts()"
Cohesion: 0.40
Nodes (3): parse_extracted_facts(), _fact_payload(), _proposal_payload()

### Community 110 - "Commercial Invariants"
Cohesion: 0.29
Nodes (4): Modular Monolith System Shape, Workflow Orchestration Rules, MVP Commercial Boundary, SyncAlly Commercial Platform

### Community 114 - "DealDetailPage.tsx"
Cohesion: 0.11
Nodes (16): getCommercialDocumentDraft(), CommercialDocumentDraft, CommercialDocumentPanel(), CommercialDocumentPanelProps, DocumentState, mockedGetDraft, DealConstellation(), DealConstellationProps (+8 more)

### Community 117 - "0004 Communication Source"
Cohesion: 0.60
Nodes (4): _create_scope_index(), downgrade(), _drop_scope_index(), upgrade()

### Community 122 - "_domain_deal"
Cohesion: 0.36
Nodes (4): _domain_deal(), _FakeAgreementRepository, _FakeDealRepository, WorkflowStateApplicationTests

### Community 124 - "Repo Idea Thinker Skill"
Cohesion: 0.50
Nodes (3): Repo Idea Thinker Skill, Repository-Grounded Ideation Discipline, Idea Quality Standards and Lightweight Validation

### Community 128 - "Frontend Readme"
Cohesion: 0.67
Nodes (3): Frontend HTML Root Document, Frontend API Client and Agreement State, React and TypeScript Vite Web App

### Community 132 - "repositories/payments.py"
Cohesion: 0.24
Nodes (4): IdempotencyKeyReused, PaymentIntentCommandMismatch, PaymentMilestoneNotFound, AgreementStatus

## Knowledge Gaps
- **47 isolated node(s):** `syncally`, `Stage 1 - Basics and Identity`, `Stage 2 - Create and View Deals`, `Stage 3 - Messages and Facts Isolation`, `Stage 4 - AI Suggestions and Review` (+42 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1093 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **48 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ActorContext` connect `Actorcontext` to `Ast`, `App Service Deals`, `Asyncio`, `repositories/payments.py`, `Db Models Deals`, `Api Routes Agreements`, `App Service Conversations`, `Api Routes Deals`, `Reconstitute()`, `Conversationroutetests`, `Agreementroutetests`, `Api Routes Conversations`, `App Service Agreements`, `Accept Invitation()`, `Case Insensitive Prefix(`, `Deterministicfakeaiprovid`, `Api Routes Organizations`, `Addmessagecommand`, `Concurrentconstraintupdat`, `Api Routes Auth`, `Api Routes Organizations`, `Commercialdocumentdraftre`, `Paymentstatusresponse`, `From Mapping()`, `Get Payment Status Reposi`, `Aicontext`, `Settings`, `Dealauthorizationtests`, `Api Routes Payments`, `Demolifecycletests`?**
  _High betweenness centrality (0.084) - this node is a cross-community bridge._
- **Are the 76 inferred relationships involving `ActorContext` (e.g. with `approve_agreement_route()` and `commit_agreement_route()`) actually correct?**
  _`ActorContext` has 76 INFERRED edges - model-reasoned connections that need verification._
- **What connects `syncally`, `Stage 1 - Basics and Identity`, `Stage 2 - Create and View Deals` to the rest of the system?**
  _47 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Ast` be split into smaller, more focused modules?**
  _Cohesion score 0.0526006464883926 - nodes in this community are weakly interconnected._
- **Why does `OrganizationId` connect `Reconstitute()` to `Ast`, `App Service Deals`, `Db Models Deals`, `repositories/payments.py`, `Api Routes Agreements`, `App Service Outbox`, `App Service Conversations`, `Api Routes Deals`, `Repository Agreements`, `Conversationroutetests`, `Agreementroutetests`, `App Service Agreements`, `Domain Conversations`, `Repository Communications`, `Commitagreementcommand`, `Repository Organizations`, `Deterministicfakeaiprovid`, `Repository Payment Processing`, `Addmessagecommand`, `Concurrentconstraintupdat`, `Domain Deal`, `Agreementrepository`, `Domain Proposal`, `Authorize Payment Intent`, `Restore()`, `Commercialdocumentdraftre`, `Session`, `Domain Agreement`, `Paymentstatusresponse`, `Paymentterm`, `Domain Trade Terms`, `From Mapping()`, `Aicontext`, `Repository Payments`, `Domain Contracts`, `Agreementversionid`, `Domain Intent`, `Repository Deals`, `Domain Organization`, `_domain_deal`?**
  _High betweenness centrality (0.053) - this node is a cross-community bridge._
- **Are the 48 inferred relationships involving `OrganizationId` (e.g. with `create_reviewed_agreement_draft_route()` and `Agreement`) actually correct?**
  _`OrganizationId` has 48 INFERRED edges - model-reasoned connections that need verification._
- **Should `App Service Deals` be split into smaller, more focused modules?**
  _Cohesion score 0.07250341997264022 - nodes in this community are weakly interconnected._