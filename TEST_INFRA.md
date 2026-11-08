# TEST_INFRA.md — E2E Testing Infrastructure & Specification

## Executive Summary
This document establishes the architecture, test runners, oracles, and test inventory for the **AI-Powered Opening Request Analysis & Seller Suggestion** feature suite in SyncAlly.

The testing architecture follows an **opaque-box end-to-end (E2E)** methodology across four hierarchical tiers:
- **Tier 1 — Feature Coverage**: Happy-path verification for normalization, AI fallback, multi-factor seller suggestion, and deal creation integration (>=5 tests per feature).
- **Tier 2 — Boundary & Corner Cases**: Stress-testing edge inputs, zero/multiple matching sellers, deterministic tie-breakers, self-dealing prevention, and inactive organization disqualification (>=5 tests per feature).
- **Tier 3 — Cross-Feature Combinations**: Pairwise interactions between normalization, seller suggestion, and deal creation with complete and partial parameters.
- **Tier 4 — Real-World Application Scenarios**: Comprehensive end-to-end buyer procurement workflows spanning varied global industries (Aerospace, Agriculture, Healthcare, Multi-currency, Air-gapped offline).

---

## 1. Test Architecture & Runners

### 1.1 Backend Test Runner (`pytest`)
- **Binary**: `/home/yashaswi/Project/SyncAlly/backend/.venv/bin/pytest`
- **Working Directory**: `/home/yashaswi/Project/SyncAlly/backend`
- **Framework**: `pytest 9.1.1` on Python 3.12 with `unittest.TestCase` and `httpx.AsyncClient` ASGI transport.
- **Database Isolation**: In-memory SQLite (`sqlite+pysqlite:///:memory:`) using `StaticPool` and `check_same_thread=False`. Clean schema creation (`Base.metadata.create_all(engine)`) and teardown (`Base.metadata.drop_all(engine)`) per test.
- **Authentication & Dependency Injection**: FastAPI `app.dependency_overrides[get_db]` and `app.dependency_overrides[get_current_actor]`.
- **Primary Suite**: `backend/tests/test_e2e_opening_request_analysis.py`

### 1.2 Frontend Test Runner (`vitest`)
- **Binary**: `npx vitest run` via Node / npm in `/home/yashaswi/Project/SyncAlly/frontend`
- **Framework**: `vitest 5.0.5` with `@testing-library/react`, `@testing-library/jest-dom`, and jsdom environment.
- **Network Boundary**: Mocked API client layer (`vi.mock("../api/client")`) testing end-to-end component rendering, user interactions, debounced queries, form submission, and error recovery.
- **Primary Suite**: `frontend/src/deals/CreateDealPage.e2e.test.tsx`

---

## 2. Oracles & Expected Output Derivation

For each test tier and test case, expected values are derived from canonical specifications:
1. **Normalization Contracts**: Defined in `PROJECT.md` § Interface Contracts (1. Backend Normalization Schema).
   - Extracted trade fields: `item_description`, `category`, `quantity`, `unit`, `target_unit_price`, `budget`, `currency`, `destination_country_code`, `destination_name`, `target_delivery_date`, `capabilities_required`, `raw_text`.
2. **Offline Rule-Based Extractor Oracle**: Defined in `DemoAISuggestionProvider` (`backend/src/syncally/infrastructure/ai/demo.py`).
   - Parses regex patterns for unit prices (`$X` or `X USD`), quantities and units (`X units`, `X boxes`, `X kg`, `X meters`), destinations, and delivery dates.
3. **Multi-Factor Matching Engine Oracle**: Defined in `PROJECT.md` § 2 & `spec_miner_survey_3/handoff.md`:
   $$\text{Score}(S, R) = 0.40 \cdot S_{\text{prod}} + 0.25 \cdot S_{\text{cap}} + 0.20 \cdot S_{\text{reg}} + 0.15 \cdot S_{\text{cat}}$$
   - Strict exclusions: Disqualifies buyer self-match (`candidate.id != buyer_organization_id`) and inactive organizations (`status != 'ACTIVE'`).
   - Deterministic tie-breaking: Score desc $\to$ matched token count desc $\to$ legal name asc $\to$ organization ID asc.
4. **Deal Creation Compatibility Oracle**: Defined in `backend/src/syncally/api/deals.py`:
   - `POST /deals` accepts `buyer_organization_id`, `seller_organization_id`, optional `display_name`, and `initiator_party`. Must return `201 Created` with schema `{id, buyer_organization_id, seller_organization_id, status: 'DRAFT', version: 0, pending_counterparty: false, display_name}`.

---

## 3. Test Suites & Coverage Inventory

### 3.1 Backend E2E Test Suite (`backend/tests/test_e2e_opening_request_analysis.py`)

#### Tier 1: Feature Coverage (>=5 tests per feature)
- **Feature 1.1: Requirement Normalization with Varied Phrasings (Happy Path)**
  - `test_tier1_normalization_industrial_fasteners`: Industrial procurement phrasing (stainless steel bolts, units, USD price, destination Berlin, Germany).
  - `test_tier1_normalization_agricultural_produce`: Commodity bulk order (10,000 kg organic coffee beans, Canada, target price).
  - `test_tier1_normalization_electronics_hardware`: Electronics component RFQ (copper wire harness, units, Tokyo Japan, target price).
  - `test_tier1_normalization_medical_supplies`: Healthcare procurement phrasing (1,500 boxes nitrile gloves, US, FDA compliance capability).
  - `test_tier1_normalization_textile_materials`: Raw textile RFQ (50,000 yards cotton fabric, UK destination, total budget).
- **Feature 1.2: Fallback Behavior when AI is Unconfigured or Offline**
  - `test_tier1_fallback_offline_mode_returns_rule_based_extraction`: Mode `offline` extracts structured requirements and reports `AIProvenance(mode="offline")`.
  - `test_tier1_fallback_missing_credentials_graceful_recovery`: Missing OpenAI API key records `fallback_reason="missing_credentials"` without 500 error.
  - `test_tier1_fallback_transient_error_exhausted`: Simulated network outage falls back with `fallback_reason="transient_exhausted"`.
  - `test_tier1_fallback_minimal_text_graceful_extraction`: Minimal phrase preserves `raw_text` and populates non-null fields without crashing.
  - `test_tier1_fallback_currency_symbols_parsing`: Parses `$`, `USD`, `EUR` currency denominations accurately in fallback.
- **Feature 1.3: Multi-Factor Seller Suggestion Matching**
  - `test_tier1_suggestion_product_exact_match`: Seller with matching product in `OrganizationProfile.products` scores high product weight.
  - `test_tier1_suggestion_capability_match`: Seller with matching capability (e.g., "Precision Machining") receives capability boost.
  - `test_tier1_suggestion_regional_compatibility`: Destination country code matching seller country or `regions` receives regional weight.
  - `test_tier1_suggestion_marketplace_catalog_fit`: Active listing matching category with sufficient quantity and price $\le$ budget boosts catalog weight.
  - `test_tier1_suggestion_multi_factor_composite_scoring`: Evaluates composite formula ($0.40/0.25/0.20/0.15$) and returns match reasons.
- **Feature 1.4: Deal Creation Flow Integration**
  - `test_tier1_deal_creation_standard_without_opening_request`: `POST /deals` succeeds with `201 Created` when no opening request is provided.
  - `test_tier1_deal_creation_with_opening_request_text`: Deal creation succeeds and preserves draft message draft.
  - `test_tier1_deal_creation_with_suggested_seller`: Creates deal using counterparty selected directly from suggestion engine.
  - `test_tier1_deal_creation_seller_initiated`: Initiator party `SELLER` creates draft deal with buyer.
  - `test_tier1_deal_creation_backward_compatibility`: Validates exact `DealResponse` schema compatibility.

#### Tier 2: Boundary & Corner Cases (>=5 tests per feature)
- **Feature 2.1: Extreme Inputs & Adversarial Formats**
  - `test_tier2_input_empty_string_rejected`: Empty string `""` rejected with `422 Unprocessable Entity`.
  - `test_tier2_input_whitespace_only_handled_safely`: Whitespace-only string rejected with 422 or handled cleanly without server error.
  - `test_tier2_input_exact_max_length_8000_chars`: 8,000 character quote processes cleanly.
  - `test_tier2_input_exceeding_max_length_rejected`: 8,001 character quote rejected with `422 Unprocessable Entity`.
  - `test_tier2_input_sql_xss_control_characters_escaped`: Injection payloads (`<script>`, SQL fragments, ANSI control chars) preserved verbatim in `raw_text` without execution.
  - `test_tier2_input_unicode_and_multilingual`: Multi-language inputs (Chinese, Japanese, Cyrillic, Accented characters) normalized cleanly.
  - `test_tier2_input_non_matching_gibberish`: Random nonsense text returns empty suggestions without 500 crash.
- **Feature 2.2: Suggestion Cardinality, Thresholds & Tie-Breaking**
  - `test_tier2_suggestion_zero_matching_sellers`: Non-matching request returns empty `suggested_sellers: []` and 200 OK.
  - `test_tier2_suggestion_multiple_sellers_ranked_descending`: Multiple matches ranked strictly by `match_score` desc.
  - `test_tier2_suggestion_deterministic_tie_breaking`: Identical score broken by matched tokens desc $\to$ `legal_name` asc $\to$ `id` asc.
  - `test_tier2_suggestion_top_n_limit_capping`: Capped at top 10 sellers when >10 candidates match.
  - `test_tier2_suggestion_threshold_filtering`: Candidates scoring below minimum threshold (<0.15) excluded.
- **Feature 2.3: Disqualification & Exclusion Invariants**
  - `test_tier2_exclusion_buyer_self_dealing_prevented`: Buyer organization is NEVER suggested as a seller even with 100% keyword match.
  - `test_tier2_exclusion_inactive_organization_disqualified`: Organizations with `status = "INACTIVE"` excluded from suggestions.
  - `test_tier2_exclusion_suspended_organization_disqualified`: Organizations with `status = "SUSPENDED"` excluded.
  - `test_tier2_exclusion_inactive_listing_ignored`: Inactive listings do not count towards catalog fit score.
  - `test_tier2_exclusion_incompatible_region_penalized`: Sellers whose registered regions explicitly exclude destination receive 0 regional score.

#### Tier 3: Cross-Feature Combinations
- `test_tier3_full_pipeline_normalize_suggest_create_deal`: Full lifecycle: Quote $\to$ Normalization $\to$ Suggestion $\to$ Deal Creation.
- `test_tier3_partial_requirements_quantity_only`: Partial input with quantity but no price matches sellers by product/quantity.
- `test_tier3_partial_requirements_destination_only`: Partial input with destination only matches sellers operating in that region.
- `test_tier3_zero_suggestion_fallback_to_directory_deal`: Zero matches falls back cleanly to directory selection and deal creation.
- `test_tier3_offline_fallback_with_deal_creation`: Offline fallback succeeds and downstream deal creation proceeds seamlessly.
- `test_tier3_unscoped_analysis_without_buyer_id`: Analysis without `buyer_organization_id` returns suggestions without self-exclusion.

#### Tier 4: Real-World Application Scenarios
- `test_tier4_scenario_aerospace_precision_machining`: High-tech manufacturing procurement with tight tolerances and ISO certifications.
- `test_tier4_scenario_agricultural_export_supply_chain`: Bulk agricultural commodity trade across international borders.
- `test_tier4_scenario_medical_device_procurement`: Regulated medical devices with CE mark / FDA compliance requirements.
- `test_tier4_scenario_international_multicurrency_trade`: Cross-border deal with EUR budget and US seller USD catalog.
- `test_tier4_scenario_air_gapped_offline_resilience`: Complete deal initiation performed entirely in offline fallback mode.

---

### 3.2 Frontend E2E Test Suite (`frontend/src/deals/CreateDealPage.e2e.test.tsx`)

#### Tier 1: UI Feature Coverage
- `renders the "Analyze & suggest sellers" trigger button beneath opening request textarea`
- `triggers analysis on button click and renders structured requirements card`
- `renders suggested seller cards with match score badge and match reasons`
- `allows selecting a suggested seller to prefill counterparty`
- `creates deal normally without analysis when opening request is omitted`

#### Tier 2: Boundary & Edge Cases
- `disables or ignores analysis when opening request is empty or whitespace`
- `handles maximum length 8,000 character quote in textarea without crashing`
- `displays friendly empty state when zero sellers match requirements`
- `excludes the active buyer organization from suggested sellers list in UI`
- `renders Unicode and special characters in requirements preview without distortion`

#### Tier 3: Cross-Feature Interactions
- `one-click seller selection updates selected seller and switches counterparty mode`
- `gracefully displays inline error message when analysis API fails`
- `allows editing opening request and re-analyzing`
- `displays partial trade attributes cleanly when some fields are absent`
- `maintains separate state and appropriate labels when switching between Buyer and Seller roles`

#### Tier 4: Real-World Buyer Workflows
- `full buyer workflow: enter complex quote -> analyze -> inspect match reasons -> select seller -> create deal`
- `offline resilience workflow: displays offline extractor provenance badge and creates deal`
- `standard procurement workflow: manual directory selection without using opening request analysis`

---

## 4. Execution Commands

### 4.1 Running Backend E2E Tests
```bash
/home/yashaswi/Project/SyncAlly/backend/.venv/bin/pytest backend/tests/test_e2e_opening_request_analysis.py -v
```

### 4.2 Running Frontend E2E Tests
```bash
(cd frontend && npx vitest run src/deals/CreateDealPage.e2e.test.tsx)
```

### 4.3 Running Full Quality Gate
```bash
# Backend tests & linting
/home/yashaswi/Project/SyncAlly/backend/.venv/bin/pytest backend/tests/test_e2e_opening_request_analysis.py
/home/yashaswi/Project/SyncAlly/backend/.venv/bin/ruff check backend/src backend/tests

# Frontend tests & linting
(cd frontend && npx vitest run src/deals/CreateDealPage.e2e.test.tsx)
(cd frontend && npm run lint)
```
