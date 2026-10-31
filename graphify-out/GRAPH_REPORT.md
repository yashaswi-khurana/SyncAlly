# Graph Report - SyncAlly  (2026-10-31)

## Corpus Check
- 231 files · ~148,286 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 8 file(s) not represented in the graph (top: (none) 4, .example 1, .ini 1)

## Summary
- 3351 nodes · 10327 edges · 125 communities (78 shown, 47 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 1372 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `a15e4c44`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- TradeFlowScene.tsx
- App Service Deals
- Asyncio
- App.tsx
- Db Models Deals
- App Service Payment Proce
- Api Routes Agreements
- App Service Outbox
- App Service Conversations
- Paymentinvoicelookup
- client.ts
- Api Routes Deals
- Repository Agreements
- Reconstitute()
- Frontend Paymentstatuspanel
- Conversationroutetests
- Frontend Package
- Agreementroutetests
- Api Database Skill
- Api Routes Conversations
- simulate_deal_flow.py
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
- App.test.tsx
- Case Insensitive Prefix(
- Test Payment Processing P
- Frontend Onboardingwizard
- get_commercial_document_draft_route
- Connect With Retry()
- Frontend App Test
- AISuggestionProviderTests
- Paymentworkitem
- Devroutestests
- Repository Payment Processing
- Api Routes Organizations
- ConversationUseCaseTests
- 0001 Initial Schema
- ActorContext
- Temporal Deal
- Domain Deal
- ADR-001: <short decision title>
- Alembic Migration
- Actorcontext
- contracts.py
- Api Routes Auth
- seed_demo_data
- Frontend Agreementreview
- repositories/deals.py
- Domain Proposal
- PaymentIntentRepositoryTests
- Compose Yaml
- create_database_engine
- Operational Recovery & Logging
- InvalidTransition
- Any
- RefreshRequest
- Paymentintentstatus
- Api Routes Dev
- Commercialdocumentdraftre
- DealWorkflowNotification
- Dealworkflownotification
- _decode_token
- Session
- DealParticipation
- Demo Lifecycle
- Frontend Tsconfig
- HealthRouteTests
- Money
- Fakewebhookverifier
- repositories/payment_processing.py
- Dealworkflowresult
- Agreementversionid
- Api Routes Auth
- Paymentinvoicereconciliat
- Settings
- Api Routes Main
- CreateDealPage.tsx
- Credentialsrequest
- get_deal
- Operational Recovery & Logging
- authorize_payment_route
- Databasepersistencetests
- Demolifecycletests
- Implementation Roadmap
- 0005 Conversation Party U
- Api Routes Main
- Commercial Invariants
- Migrationsettings
- apiRequest
- Api Routes Main
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
- `Assumptions` --references--> `CreateReviewedAgreementDraftRequest`  [INFERRED]
  docs/engineering/plan.md → backend/src/syncally/api/agreements.py
- `Testing strategy` --references--> `listDealFacts()`  [INFERRED]
  docs/engineering/plan.md → frontend/src/api/client.ts
- `Plan challenge log` --references--> `AISuggestionReview()`  [INFERRED]
  docs/engineering/plan.md → frontend/src/deals/AISuggestionReview.tsx
- `2. Guard against revoked fact reappearance and stale poll drops` --references--> `mergeFact()`  [INFERRED]
  docs/engineering/log.md → frontend/src/deals/DealConversationReview.tsx
- `Implementation blueprint` --references--> `createAgreementFromReviewedTerms()`  [INFERRED]
  docs/engineering/plan.md → frontend/src/api/client.ts

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Repository Architecture, Visualization, and Ideation Framework** — github_skills_repo_architect_skill, github_skills_archify_diagrammer_skill, github_skills_repo_idea_thinker_skill, github_skills_api_database_skill [INFERRED 0.85]
- **Code Implementation, Review, Debugging, and QA Loop** — github_skills_senior_engineer_skill, github_skills_code_reviewer_skill, github_skills_debugger_skill, github_skills_testing_qa_skill [INFERRED 0.85]
- **Production Readiness and Quality Gate Lifecycle** — github_skills_devops_production_skill, github_skills_performance_reliability_skill, github_skills_security_analyst_skill, github_skills_testing_qa_skill [INFERRED 0.85]
- **Bilateral Agreement Approval and Commitment Flow** — docs_architecture_01_commercial_domain_model_atomic_bilateral_approval, docs_architecture_01_commercial_domain_model_agreement_version, docs_architecture_05_domain_layer_agreement_commitment_flow, docs_implementation_plan_stage_5_agreement_approvals [INFERRED 0.95]
- **PayPal Payment Intent and Reconciliation Lifecycle** — docs_architecture_03_paypal_payment_intent_lifecycle_payment_intent, docs_architecture_03_paypal_payment_intent_lifecycle_create_unknown_state, docs_architecture_03_paypal_payment_intent_lifecycle_payment_reconciliation, backend_readme_payment_worker_process, docs_operations_unknown_payment_recovery [INFERRED 0.95]
- **Temporal Outbox Relay and Workflow Orchestration** — docs_architecture_02_temporal_deal_workflow_contract_deal_workflow, docs_architecture_02_temporal_deal_workflow_contract_outbox_workflow_start, docs_architecture_02_temporal_deal_workflow_contract_refresh_deal_state, backend_readme_outbox_worker_process, infra_readme_restart_smoke_test [INFERRED 0.95]

## Communities (125 total, 47 thin omitted)

### Community 0 - "TradeFlowScene.tsx"
Cohesion: 0.21
Nodes (9): dependencies, react@^19.3.0, react-dom@^19.3.0, three@^0.186.1, DealConstellation(), DealConstellationProps, TradeFlowScene(), react-dom (+1 more)

### Community 2 - "Asyncio"
Cohesion: 0.07
Nodes (12): _as_utc(), OperationalFastAPI, _active_admin_membership(), _create_invitation_token(), _deal_awaiting_counterparty(), _decode_invitation_token(), get_organization_route(), list_my_organizations() (+4 more)

### Community 3 - "App.tsx"
Cohesion: 0.05
Nodes (48): listDeals(), login(), ViewerRole, App(), handleOrganizationCreated(), refreshSessionView(), useHashRoute(), demoQuickFillEnabled() (+40 more)

### Community 4 - "Db Models Deals"
Cohesion: 0.12
Nodes (18): _require_dev_environment(), Approval, Obligation, Base, Constraint, Conversation, Deal, Message (+10 more)

### Community 5 - "App Service Payment Proce"
Cohesion: 0.09
Nodes (5): PaymentInvoiceProvider, PaymentProcessingRepository, process_payment_intent(), reconcile_payment_intent(), _request_id_retry_window_expired()

### Community 6 - "Api Routes Agreements"
Cohesion: 0.10
Nodes (20): AgreementVersionResponse, ApprovalResponse, approve_agreement_route(), commit_agreement_route(), CommitAgreementRequest, create_agreement_draft_route(), create_reviewed_agreement_draft_route(), CreateAgreementDraftRequest (+12 more)

### Community 7 - "App Service Outbox"
Cohesion: 0.11
Nodes (12): dispatch_outbox_event(), OutboxDispatchResult, PendingOutboxEvent, OutboxEvent, apply_dispatch_result(), claim_next_pending_event(), _claim_statement(), dispatch_one_pending_event() (+4 more)

### Community 8 - "App Service Conversations"
Cohesion: 0.07
Nodes (17): add_message(), can_view_constraint(), can_view_message(), CommunicationRepository, ConcurrentConstraintUpdate, ConstraintNotFound, ConstraintRepository, correct_constraint() (+9 more)

### Community 9 - "Paymentinvoicelookup"
Cohesion: 0.08
Nodes (11): receive_paypal_invoice_webhook(), PaymentInvoiceLookup, PaymentInvoiceRequest, PaymentNeedsAction, _has_excess_currency_precision(), PayPalSandboxInvoiceProvider, _provider_error_code(), _provider_request_id() (+3 more)

### Community 10 - "client.ts"
Cohesion: 0.09
Nodes (34): API_REQUEST_TIMEOUT_MS, describeDetail(), getDealMessageExistence(), isAbortError(), isRecord(), readErrorDetail(), CREATED_MESSAGE, fetchMock (+26 more)

### Community 11 - "Api Routes Deals"
Cohesion: 0.08
Nodes (17): create_deal_route(), CreateDealRequest, DealResponse, DealSummaryResponse, get_deal_repository(), list_deals_route(), read_deal_route(), _to_response() (+9 more)

### Community 12 - "Repository Agreements"
Cohesion: 0.06
Nodes (24): AgreementAccessDenied, AgreementAlreadyCommitted, AgreementNotFound, AgreementVersionConflict, CreateAgreementDraftCommand, DuplicateApproval, ProposalNotFound, StaleAgreementVersion (+16 more)

### Community 13 - "Reconstitute()"
Cohesion: 0.09
Nodes (14): ConstraintKind, ConstraintStatus, Message, MessageSourceType, Visibility, ConstraintId, ConversationId, MessageId (+6 more)

### Community 14 - "Frontend Paymentstatuspanel"
Cohesion: 0.10
Nodes (26): authorizeDealPayment(), listPaymentStatuses(), PaymentStatus, describeStatus(), displayAmount(), ExtendedPaymentStatus, extractInvoiceNumber(), firstMilestoneAmount() (+18 more)

### Community 16 - "Frontend Package"
Cohesion: 0.06
Nodes (47): devDependencies, eslint@^10.13.0, @eslint/js@^10.0.1, eslint-plugin-react-hooks@^7.1.1, eslint-plugin-react-refresh@^0.4.20, globals@^17.13.0, happy-dom@^21.0.3, @testing-library/dom@^10.4.1 (+39 more)

### Community 18 - "Api Database Skill"
Cohesion: 0.04
Nodes (43): API and Database Engineer Skill, API Design and Contract Semantics, Data Integrity and Invariant Enforcement, Query Performance and Projection Optimization, Schema Migration and Backward Compatibility, Transaction Boundaries and Atomicity, Archify Diagrammer Skill, Archify CLI Global Tool (+35 more)

### Community 19 - "Api Routes Conversations"
Cohesion: 0.06
Nodes (38): add_message_route(), AddMessageRequest, AISuggestionRequest, clarify_fact_route(), confirm_fact_route(), ConstraintResponse, correct_fact_route(), CorrectFactRequest (+30 more)

### Community 20 - "simulate_deal_flow.py"
Cohesion: 0.12
Nodes (4): _persist_paypal_webhook_event(), _is_live_backend_healthy(), main(), record_paypal_webhook_event()

### Community 21 - "App Service Agreements"
Cohesion: 0.08
Nodes (18): AgreementRepository, AuditEventDraft, AuditRepository, commit_agreement(), create_agreement_draft(), create_reviewed_agreement_draft(), CreateReviewedAgreementDraftCommand, get_current_agreement() (+10 more)

### Community 22 - "Frontend Aisuggestionreview"
Cohesion: 0.10
Nodes (33): correctDealFact(), createDealFact(), draftDealProposal(), reviewDealFact(), suggestDealFacts(), DealFact, FactReviewAction, isPaymentTrigger() (+25 more)

### Community 23 - "Operational Recovery & Logging"
Cohesion: 0.09
Nodes (15): get_paypal_webhook_configuration(), _connect_with_retry(), main(), run_forever(), main(), run_forever(), GmailSettings, PayPalSettings (+7 more)

### Community 24 - "Domain Conversations"
Cohesion: 0.07
Nodes (4): Constraint, FakeCommunicationRepository, FakeCommunicationRepository, FakeCommunicationRepository

### Community 25 - "Repository Communications"
Cohesion: 0.09
Nodes (7): Conversation, CommunicationScopeError, _constraint_to_domain(), _conversation_to_domain(), _message_to_domain(), _page_bounds(), SqlAlchemyCommunicationRepository

### Community 26 - "Accept Invitation()"
Cohesion: 0.16
Nodes (5): accept_invitation(), AcceptInvitationRequest, create_organization_invitation(), CreateInvitationRequest, OrganizationInvitationTests

### Community 27 - "Build In Process Client("
Cohesion: 0.10
Nodes (8): _build_in_process_client(), ci_deal_flow_hook(), DealFlowContext, DealFlowSimulator, run_simulation(), SimulationError, StepRecord, TerminalFormatter

### Community 28 - "Commercial Domain Model"
Cohesion: 0.06
Nodes (26): Outbox Relay Worker Process, PayPal Payment Worker Process, PayPal Invoicing Webhook Endpoint, AgreementVersion Aggregate, Append-Only AuditEvent Ledger, Commercial Constraint and Provenance, Deal Aggregate, Organization and Membership Entities (+18 more)

### Community 29 - "Frontend Dealconversationreview"
Cohesion: 0.05
Nodes (54): 1. Paged fact retrieval in client API, 2. Guard against revoked fact reappearance and stale poll drops, 3. Metadata consistency, edit preservation, and agreement race guards, 4. Test hardening and CodeRabbit timing fix, 5. Adversarial verification, Engineering Log, Affected files, Alternatives considered (+46 more)

### Community 30 - "Commitagreementcommand"
Cohesion: 0.10
Nodes (8): CommitAgreementCommand, RecordApprovalCommand, ApprovalDecision, AgreementVersion, commit_agreement_in_transaction(), AgreementCommitTests, LocalWorkflowSmokeTests, commit_once()

### Community 31 - "Argparse"
Cohesion: 0.08
Nodes (6): PaymentInvoiceNotice, PaymentRetryableError, main(), GmailSMTPInvoiceNotifier, _FakeSMTP, GmailSMTPInvoiceNotifierTests

### Community 32 - "Repository Organizations"
Cohesion: 0.11
Nodes (10): Organization, OrganizationMember, OrganizationMemberRole, OrganizationMemberStatus, OrganizationStatus, _membership_to_domain(), _organization_to_domain(), SqlAlchemyOrganizationMemberRepository (+2 more)

### Community 33 - "App.test.tsx"
Cohesion: 0.12
Nodes (16): mockedApiRequest, mockedCreateOrganization, mockedGetCommercialDocumentDraft, mockedGetCurrentAgreement, mockedGetDeal, mockedGetDealMessageExistence, mockedListDealFacts, mockedListDealMessages (+8 more)

### Community 34 - "Case Insensitive Prefix("
Cohesion: 0.14
Nodes (4): _case_insensitive_prefix(), _escape_like(), value(), OrganizationDirectoryTests

### Community 35 - "Test Payment Processing P"
Cohesion: 0.15
Nodes (5): FakeInvoiceProvider, FakeProcessingRepository, PaymentProcessingTests, _request(), _work_item()

### Community 36 - "Frontend Onboardingwizard"
Cohesion: 0.10
Nodes (22): addOrganizationMember(), createOrganization(), Organization, COUNTRY_NAMES, CountryOption, describeError(), isAmbiguousCreateFailure(), OnboardingWizard() (+14 more)

### Community 38 - "Connect With Retry()"
Cohesion: 0.08
Nodes (11): _connect_with_retry(), create_worker(), _register_shutdown_handlers(), _remove_shutdown_handlers(), _request_shutdown(), run_worker(), workflow_activities(), ConnectWithRetryTests (+3 more)

### Community 39 - "Frontend App Test"
Cohesion: 0.23
Nodes (15): listOrganizations(), clearAccessToken(), getAccessToken(), setAccessToken(), setTokens(), TokenResponse, Session, useSession() (+7 more)

### Community 40 - "AISuggestionProviderTests"
Cohesion: 0.04
Nodes (29): get_ai_suggestion_provider(), AIPermanentError, AIProviderError, AIRetryPolicy, AISuggestionProvider, call_with_bounded_retry(), draft_proposal_from_context(), extract_facts_from_context() (+21 more)

### Community 41 - "Paymentworkitem"
Cohesion: 0.09
Nodes (13): PaymentInvoiceNotifier, PaymentWorkItem, claim_next_payment_event(), _claim_statement(), _ClaimedPaymentEvent, dispatch_one_payment_event(), dispatch_pending_payment_events(), _finish_event() (+5 more)

### Community 43 - "Repository Payment Processing"
Cohesion: 0.13
Nodes (6): payment_invoice_number(), PaymentInvoiceLineItem, _restore_domain_intent(), SqlAlchemyPaymentProcessingRepository, transition(), transition()

### Community 44 - "Api Routes Organizations"
Cohesion: 0.14
Nodes (9): AcceptInvitationResponse, add_organization_member(), AddOrganizationMemberRequest, create_organization(), CreateOrganizationRequest, InvitationResponse, _is_duplicate_membership_error(), OrganizationDirectoryItem (+1 more)

### Community 46 - "0001 Initial Schema"
Cohesion: 0.09
Nodes (14): upgrade(), uuid_column(), upgrade(), upgrade(), _create_scope_index(), downgrade(), _drop_scope_index(), upgrade() (+6 more)

### Community 47 - "ActorContext"
Cohesion: 0.10
Nodes (9): draft_proposal(), extract_facts(), _list_all_constraints_for_owner(), persist_fact_candidates(), confirm_constraint(), select_ai_context(), ActorContext, AiContextSelectionTests (+1 more)

### Community 49 - "Domain Deal"
Cohesion: 0.10
Nodes (5): Deal, FakeDealRepository, _domain_deal(), FakeDealRepository, FakeDealRepository

### Community 50 - "ADR-001: <short decision title>"
Cohesion: 0.25
Nodes (7): ADR-001: <short decision title>, Architectural Decision Records, Consequences, Context, Decision, Options considered, Rejected

### Community 51 - "Alembic Migration"
Cohesion: 0.10
Nodes (4): run_migrations_offline(), run_migrations_online(), CommunicationMigrationTests, PaymentCreateStartedMigrationTests

### Community 53 - "contracts.py"
Cohesion: 0.08
Nodes (24): _is_weak_jwt_secret(), AIContractError, AIValidationClaim, _check_keys(), _contains_numeric_token(), _contains_token(), _date_value_is_present(), _decimal() (+16 more)

### Community 54 - "Api Routes Auth"
Cohesion: 0.12
Nodes (5): _development_actor(), development_login(), get_current_actor(), get_optional_actor(), resolve_actor()

### Community 55 - "seed_demo_data"
Cohesion: 0.17
Nodes (5): DemoIdentity, main(), _password_for(), seed_demo_data(), DemoSeedTests

### Community 56 - "Frontend Agreementreview"
Cohesion: 0.16
Nodes (20): commitAgreementVersion(), recordAgreementDecision(), paymentTimingLabel(), AgreementReview(), commitCurrentAgreement(), decide(), reloadAgreement(), AgreementReviewProps (+12 more)

### Community 57 - "repositories/deals.py"
Cohesion: 0.06
Nodes (14): NotificationKind, DealWorkflowState, load_deal_workflow_state(), parse_workflow_uuid(), WorkflowAgreementRepository, WorkflowDealNotFound, WorkflowDealRepository, DealStatus (+6 more)

### Community 58 - "Domain Proposal"
Cohesion: 0.26
Nodes (6): NegotiationSession, Proposal, DealId, NegotiationSessionId, build_proposal(), NegotiationTests

### Community 59 - "PaymentIntentRepositoryTests"
Cohesion: 0.08
Nodes (10): authorize_payment_intent(), AuthorizePaymentIntentCommand, PaymentIntentAuthorizationOutcome, PaymentIntentRepository, SellerMembershipRepository, authorize_payment_intent_in_transaction(), _is_idempotency_key_violation(), _is_one_active_per_milestone_violation() (+2 more)

### Community 60 - "Compose Yaml"
Cohesion: 0.09
Nodes (22): POSTGRES_DB, POSTGRES_PASSWORD, POSTGRES_USER, interval, retries, test, timeout, environment (+14 more)

### Community 62 - "Operational Recovery & Logging"
Cohesion: 0.20
Nodes (4): captured_output(), SafeOperationsTests, exercise(), failed_db()

### Community 63 - "InvalidTransition"
Cohesion: 0.07
Nodes (13): DuplicateActivePaymentIntent, PaymentIntentCommandMismatch, PaymentMilestoneNotFound, PaymentIntent, PaymentMilestone, VerifiedProviderPaymentState, InvalidTransition, PaymentIntentId (+5 more)

### Community 64 - "Any"
Cohesion: 0.09
Nodes (9): RefreshDealStateActivity, _workflow_input_value(), DealWorkflowInput, _require_uuid(), new_workflow_input(), RefreshActivity, RefreshCall, RefreshDealStateActivityTests (+1 more)

### Community 66 - "Paymentintentstatus"
Cohesion: 0.22
Nodes (3): PaymentIntentStatus, VerifiedProviderPaymentStatus, PaymentReconciliationRepositoryTests

### Community 67 - "Api Routes Dev"
Cohesion: 0.17
Nodes (10): _aggregate_scope(), _delete_scoped(), _demo_organization_ids(), DevResetResponse, DevRoleSwitchRequest, _missing_demo_emails(), _related_ids(), _require_seeded_demo_identities() (+2 more)

### Community 68 - "Commercialdocumentdraftre"
Cohesion: 0.21
Nodes (4): AgreementNotCommitted, CommercialDocumentDraft, generate_commercial_document_draft(), CommercialDocumentDraftTests

### Community 69 - "DealWorkflowNotification"
Cohesion: 0.11
Nodes (9): build_deal_workflow_id(), DealWorkflowStarter, WorkflowStartError, WorkflowStartOutcome, WorkflowStartPermanentError, WorkflowStartTransientError, DealWorkflowNotification, TemporalDealWorkflowStarter (+1 more)

### Community 72 - "Session"
Cohesion: 0.16
Nodes (3): _active_participation(), SqlAlchemyDealRepository, DealRepositoryTests

### Community 74 - "Demo Lifecycle"
Cohesion: 0.23
Nodes (7): _acquire_lock(), _is_demo_deal(), lock_demo_deal_creation(), lock_demo_payment_processing(), lock_demo_reset(), DemoLifecycleLockTests, _postgres_session()

### Community 75 - "Frontend Tsconfig"
Cohesion: 0.11
Nodes (17): compilerOptions, allowImportingTsExtensions, jsx, lib, module, moduleDetection, moduleResolution, noEmit (+9 more)

### Community 78 - "Money"
Cohesion: 0.08
Nodes (19): Agreement, Approval, _money(), _normalized_text(), _parse_money(), PaymentTerm, _require_decimal(), ShipmentTerm (+11 more)

### Community 82 - "repositories/payment_processing.py"
Cohesion: 0.07
Nodes (13): _display(), _render(), IdempotencyKeyReused, list_current_payment_statuses(), PaymentStatusRecord, PaymentStatusRepository, UnauthorizedPaymentAuthorization, AgreementStatus (+5 more)

### Community 86 - "Dealworkflowresult"
Cohesion: 0.29
Nodes (3): DealWorkflowResult, DealWorkflowTests, new_notification()

### Community 87 - "Agreementversionid"
Cohesion: 0.15
Nodes (6): AgreementVersionId, OrganizationId, DealDomainTests, make_deal(), OrganizationDomainTests, OrganizationMemberDomainTests

### Community 88 - "Api Routes Auth"
Cohesion: 0.19
Nodes (9): create_refresh_token(), _encode_access_token(), _hash_refresh_token(), _issue_tokens(), refresh_access_token(), _replay_rotation(), _revoke_family(), _unauthorized() (+1 more)

### Community 89 - "Paymentinvoicereconciliat"
Cohesion: 0.18
Nodes (5): PaymentInvoiceReconciliation, PaymentOutcomeUnknown, FakePayPalInvoiceProvider, get_invoice_reconciliation(), get_invoice_reconciliation()

### Community 94 - "CreateDealPage.tsx"
Cohesion: 0.15
Nodes (13): createDeal(), CreateDealPage(), handleSubmit(), CreateDealPageProps, describeCreateError(), describeError(), DirectoryItem, FieldErrors (+5 more)

### Community 95 - "Credentialsrequest"
Cohesion: 0.26
Nodes (5): CredentialsRequest, login(), TokenResponse, fail(), scalar()

### Community 103 - "authorize_payment_route"
Cohesion: 0.13
Nodes (6): authorize_payment_route(), AuthorizePaymentRequest, AuthorizePaymentResponse, get_payment_status_repository(), list_payment_statuses_route(), PaymentStatusResponse

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
Cohesion: 0.08
Nodes (33): apiBaseUrl(), ApiError, apiRequest(), getCommercialDocumentDraft(), getCurrentAgreement(), getDeal(), getOrganization(), listDealMessages() (+25 more)

### Community 124 - "Repo Idea Thinker Skill"
Cohesion: 0.50
Nodes (3): Repo Idea Thinker Skill, Repository-Grounded Ideation Discipline, Idea Quality Standards and Lightweight Validation

### Community 128 - "Frontend Readme"
Cohesion: 0.67
Nodes (3): Frontend HTML Root Document, Frontend API Client and Agreement State, React and TypeScript Vite Web App

## Knowledge Gaps
- **47 isolated node(s):** `syncally`, `Stage 1 - Basics and Identity`, `Stage 2 - Create and View Deals`, `Stage 3 - Messages and Facts Isolation`, `Stage 4 - AI Suggestions and Review` (+42 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1109 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **47 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `CreateReviewedAgreementDraftRequest` connect `Api Routes Agreements` to `Frontend Dealconversationreview`, `Api Routes Agreements`?**
  _High betweenness centrality (0.249) - this node is a cross-community bridge._
- **Are the 76 inferred relationships involving `ActorContext` (e.g. with `approve_agreement_route()` and `commit_agreement_route()`) actually correct?**
  _`ActorContext` has 76 INFERRED edges - model-reasoned connections that need verification._
- **What connects `syncally`, `Stage 1 - Basics and Identity`, `Stage 2 - Create and View Deals` to the rest of the system?**
  _47 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `App Service Deals` be split into smaller, more focused modules?**
  _Cohesion score 0.07438596491228071 - nodes in this community are weakly interconnected._
- **Why does `Assumptions` connect `Frontend Dealconversationreview` to `Api Routes Agreements`?**
  _High betweenness centrality (0.249) - this node is a cross-community bridge._
- **Are the 48 inferred relationships involving `OrganizationId` (e.g. with `create_reviewed_agreement_draft_route()` and `Agreement`) actually correct?**
  _`OrganizationId` has 48 INFERRED edges - model-reasoned connections that need verification._
- **Should `Asyncio` be split into smaller, more focused modules?**
  _Cohesion score 0.07142857142857142 - nodes in this community are weakly interconnected._