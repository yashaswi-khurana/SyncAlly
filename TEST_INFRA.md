# TEST_INFRA.md — Production Buyer Sourcing Agent E2E Testing Infrastructure

## 1. Executive Summary

This document establishes the architecture, test runners, oracles, data contracts, and test inventory for the **Production Buyer Sourcing Agent** in SyncAlly, as mandated by `ORIGINAL_REQUEST.md` (R1–R4) and `PROJECT.md` (§ Architecture, § Feature Inventory F1–F22, § Interface Contracts).

The test suite is structured as an **opaque-box end-to-end (E2E)** verification matrix spanning four systematic tiers:
- **Tier 1 — Feature Coverage**: Happy-path verification for requirement interpretation, technical spec parsing, pricing & budget validation, quantity/MOQ compliance, lead time feasibility, commercial terms normalization, multi-factor scoring, attribute matrix generation, gap detection, seller inquiry drafting, REST API routes, and deal handoff (>=5 tests per feature).
- **Tier 2 — Boundary & Corner Cases**: Rigorous edge testing including empty/whitespace inputs, extreme lengths (8,000 chars), zero prices ($0.00), massive quantities (100M units), past delivery dates, missing lead times/warranties, ambiguous phrasing ("standard warranty"), and non-standard Incoterms (>=5 tests per feature).
- **Tier 3 — Cross-Feature Combinations**: Pairwise and multi-attribute commercial trade-offs (e.g. over-budget price + missing lead time, non-compliant MOQ + ambiguous warranty, missing regulatory certs + tight deadline, currency mismatch + restrictive EXW terms).
- **Tier 4 — Real-World Application Scenarios**: Comprehensive end-to-end procurement journeys covering all 5 core B2B industrial sectors (Fasteners, Electronics, Agriculture, Textiles, Medical/PPE).

---

## 2. Test Architecture & Runners

### 2.1 Backend Test Runner (`pytest`)
- **Binary**: `/home/yashaswi/Project/SyncAlly/backend/.venv/bin/pytest`
- **Framework**: `pytest 9.1.1` on Python 3.12 with `unittest.TestCase` and `httpx.AsyncClient` ASGI transport (`httpx.ASGITransport(app=app)`).
- **Primary Suite**: `backend/tests/test_e2e_buyer_sourcing.py` (79 automated test cases).
- **Database Isolation**: In-memory SQLite (`sqlite+pysqlite:///:memory:`) using `StaticPool` with `check_same_thread=False`. Per-test clean schema creation (`Base.metadata.create_all(engine)`) and teardown (`Base.metadata.drop_all(engine)`).
- **Dependency Overrides & Authentication**: FastAPI `app.dependency_overrides[get_db]` and `app.dependency_overrides[get_current_actor]`.
- **Progressive Testability**: Employs `_is_route_available(...)` checks. During pre-implementation milestones (M-E2E), tests compile and are collected cleanly with standard unittest skips (`self.skipTest(...)`), ensuring exit code 0. Once implementation milestones (M1/M2) register the router at `/sourcing/*`, the exact same tests execute full assertions without code modification.
- **Offline Self-Containment**: Zero external API keys, zero remote network egress.

### 2.2 Frontend Test Runner (`vitest`)
- **Binary**: `npm --prefix frontend test -- ... --run` via Vitest 5.0.5.
- **Framework**: Vitest 5.0.5 with `@testing-library/react`, `@testing-library/jest-dom`, and jsdom environment.
- **Primary Suite**: `frontend/src/sourcing/SourcingHub.test.tsx` (23 automated test cases).
- **Component Coverage**: Full mounting and DOM verification of `ReferenceSourcingHub`, testing navigation breadcrumbs, dual-mode requirement input (prompt vs structured fields), candidate listing cards, match score badges, attribute comparison table, gap analysis inspector drawer, seller inquiry modal, clipboard copy, and deal creation bridge (`#/deals/new`).
- **Offline Fallback Simulation**: Validates client-side fallback to bundled listings dataset when network is unavailable or disconnected.

---

## 3. Authoritative Oracles & Output Derivation

All expected values across the 102 test cases are derived strictly from authoritative domain specifications:

### 3.1 Requirement Interpretation Oracle (`ORIGINAL_REQUEST.md:R1`, `spec_miner handoff § 1`)
- **Domain Contract**: `BuyerRequirements` schema composed of:
  - `technical_specs`: Materials list, tolerances, certifications (ISO, CE, RoHS, FDA), standards (DIN, ASTM, JASO, OEKO-TEX).
  - `pricing`: Target unit price, max unit price ceiling, max total budget, currency (ISO 4217).
  - `quantity`: Target quantity, min acceptable quantity, unit, packaging preference.
  - `delivery`: Destination country code (ISO 3166-1 alpha-2), destination port/city, required delivery date, max lead time days.
  - `commercial_terms`: Preferred Incoterm (Incoterms 2020), acceptable Incoterms list, preferred payment term (Net 30, Escrow, etc.), min warranty months, inspection requirement.

### 3.2 Bundled Realistic Dataset Oracle (`PROJECT.md § Architecture`, `spec_miner handoff § 2`)
8 curated candidate listings across 5 industrial sectors intentionally modeling completeness variations:
1. `Listing 101` (DE — Berlin Fastener & Bolt GmbH): DIN 933 M8 Grade 316 Bolts, $11.50/box, MOQ 500, lead time 21d, DDP/CIF/FOB, Net 30/Escrow, 24mo warranty, EN 10204 3.1 QC. (`FULL_COMPLETE`)
2. `Listing 102` (US — Apex Hardware): Precision Bolts M8, $10.80/box, MOQ 200, missing lead time, missing Incoterms. (`PARTIAL_MISSING_LEAD_TIME_OR_TERMS`)
3. `Listing 103` (JP — Tokyo Micro-Conductor): Automotive Wire Harness 28AWG, $7.20/unit, MOQ 500, lead time 28d, ambiguous payment ("negotiable"), ambiguous warranty ("standard"). (`AMBIGUOUS_SPECS_OR_TERMS`)
4. `Listing 104` (PL — Baltic Fastener Works): Marine A4-80 Bolts, $9.50/box, MOQ 5,000 (barrier), lead time 35d. (`NON_COMPLIANT_MOQ`)
5. `Listing 105` (SE — Nordic AeroSpares): Aerospace Fasteners M8, $24.00/box (over budget), MOQ 100, lead time 14d. (`NON_COMPLIANT_PRICE`)
6. `Listing 106` (GB — Lancashire Weaving Mills): Industrial Canvas Fabric 320 GSM, $3.10/yd, MOQ 1,000, missing lead time, EXW only. (`AMBIGUOUS_SPECS_OR_TERMS`)
7. `Listing 107` (CN — Shenzhen Precision Interconnect): Shielded Coaxial Assembly, $5.80/unit, MOQ 1,000, lead time 75d (excessive). (`NON_COMPLIANT_LEAD_TIME`)
8. `Listing 108` (US — MediShield Global Corp): Nitrile Examination Gloves 4 mil, $8.50/box, MOQ 500, lead time 10d, FDA 510(k), ISO 13485, CE. (`FULL_COMPLETE`)

### 3.3 Multi-Factor Commercial Scoring Oracle (`PROJECT.md § 3.1`, `spec_miner handoff § 3`)
- **Formula**:
  $$S = 0.30 \cdot s_{\text{spec}} + 0.25 \cdot s_{\text{price}} + 0.15 \cdot s_{\text{qty}} + 0.15 \cdot s_{\text{lead}} + 0.15 \cdot s_{\text{terms}} \in [0, 100]$$
- **Match Tiers**:
  - **Tier A (90% – 100%)**: Ideal Match (Immediate deal room initiation).
  - **Tier B (75% – 89%)**: Strong Candidate (Minor commercial variance).
  - **Tier C (50% – 74%)**: Conditional Candidate (Moderate gaps requiring inquiry).
  - **Tier D (< 50%)**: Disqualified / Substantial Mismatch (Critical deal blocker).

### 3.4 Gap Taxonomy & Explanation Oracle (`ORIGINAL_REQUEST.md:R2`, `spec_miner handoff § 4`)
- **3 Categories**: `MISSING`, `AMBIGUOUS`, `NON_COMPLIANT`.
- **3 Severities**: `CRITICAL` (deal blockers: price > max budget, MOQ > 1.5x demand, lead time > deadline, missing regulatory certs), `MODERATE` (commercial risks: missing lead time, EXW vs DDP, advance payment vs Net 30), `LOW` (clarifications).
- **Explanations**: Include exact mathematical and commercial deltas (e.g., "$24.00 exceeds $14.00 by 71.4%").

### 3.5 Inquiry Drafting Oracle (`ORIGINAL_REQUEST.md:R2`, `spec_miner handoff § 5`)
- Generates polite B2B letters with structured sections: Subject, Salutation, Order Summary Scope, Targeted Gap Paragraphs with proposed compromises (trial batches, volume discounts, warranty extensions), Counter-terms, and Call-to-Action.

---

## 4. Comprehensive Test Inventory (102 Tests)

### 4.1 Backend Test Cases (`backend/tests/test_e2e_buyer_sourcing.py` — 79 Tests)

| Tier | Category / Feature | Test Identifier | Summary |
|---|---|---|---|
| Tier 1 | F1 & F2 Natural Language & Technical Specs | `test_tier1_interpret_fasteners_material_tolerance_standards` | Fastener prompt -> 316 SS, ISO 965-1 6g, DIN 933, CE/RoHS |
| Tier 1 | F1 & F2 Natural Language & Technical Specs | `test_tier1_interpret_electronics_wire_gauge_jaso` | Wire harness prompt -> 28AWG, JASO D611, RoHS, Tokyo |
| Tier 1 | F1 & F2 Natural Language & Technical Specs | `test_tier1_interpret_agriculture_fair_trade_organic` | Bulk Arabica coffee -> 20,000 kg, Fair Trade, CIF Hamburg |
| Tier 1 | F1 & F2 Natural Language & Technical Specs | `test_tier1_interpret_textiles_oeko_tex_gsm` | Cotton canvas -> 5,000 yd, 320 GSM, OEKO-TEX 100, London |
| Tier 1 | F1 & F2 Natural Language & Technical Specs | `test_tier1_interpret_medical_fda_astm_cleanroom` | Nitrile gloves -> 10,000 boxes, ASTM D6319, FDA 510(k), CE |
| Tier 1 | F3 & F4 Pricing & Volume MOQ | `test_tier1_pricing_unit_price_constraint` | Validates target price and budget ceiling |
| Tier 1 | F3 & F4 Pricing & Volume MOQ | `test_tier1_pricing_total_budget_cap` | Validates ceiling budget cap vs quantity calculation |
| Tier 1 | F3 & F4 Pricing & Volume MOQ | `test_tier1_quantity_target_and_min_acceptable` | Validates target quantity vs min acceptable batches |
| Tier 1 | F3 & F4 Pricing & Volume MOQ | `test_tier1_quantity_moq_compatibility_within_limits` | Seller MOQ <= buyer quantity evaluates to full MOQ score |
| Tier 1 | F3 & F4 Pricing & Volume MOQ | `test_tier1_quantity_unit_packaging_preference` | Preserves units and packaging specifications |
| Tier 1 | F5 & F6 Lead Time & Terms Normalization | `test_tier1_lead_time_days_delivery_feasibility` | Lead time days and arrival date buffer calculation |
| Tier 1 | F5 & F6 Lead Time & Terms Normalization | `test_tier1_commercial_terms_incoterms_normalization` | Normalizes Incoterms 2020 preference (DDP/CIF/FOB) |
| Tier 1 | F5 & F6 Lead Time & Terms Normalization | `test_tier1_commercial_terms_payment_methods` | Normalizes Net 30, Net 60, Escrow, 30/70 split |
| Tier 1 | F5 & F6 Lead Time & Terms Normalization | `test_tier1_commercial_terms_warranty_duration` | Validates minimum warranty duration threshold |
| Tier 1 | F5 & F6 Lead Time & Terms Normalization | `test_tier1_commercial_terms_inspection_preferences` | Validates EN 10204 3.1 mill certificate and third-party QC |
| Tier 1 | F7 & F8 Bundled Dataset & Scoring Engine | `test_tier1_bundled_listings_repository_retrieval` | Bundled repository returns listings across all 5 sectors |
| Tier 1 | F7 & F8 Bundled Dataset & Scoring Engine | `test_tier1_scoring_engine_5_dimension_weights` | Verifies 30% specs, 25% price, 15% qty, 15% lead, 15% terms |
| Tier 1 | F7 & F8 Bundled Dataset & Scoring Engine | `test_tier1_scoring_engine_tier_a_ideal_match` | Fully compliant candidate achieves Tier A (score >= 90%) |
| Tier 1 | F7 & F8 Bundled Dataset & Scoring Engine | `test_tier1_scoring_engine_tier_b_minor_variance` | Candidate with minor variance receives Tier B (75-89%) |
| Tier 1 | F7 & F8 Bundled Dataset & Scoring Engine | `test_tier1_scoring_engine_tier_d_disqualified` | Disqualified candidate with severe mismatch receives Tier D |
| Tier 1 | F9 Attribute-by-Attribute Matrix | `test_tier1_comparison_matrix_exact_match_status` | Exact matching attributes tagged with MATCH status |
| Tier 1 | F9 Attribute-by-Attribute Matrix | `test_tier1_comparison_matrix_acceptable_variance_status` | Minor commercial variance tagged ACCEPTABLE |
| Tier 1 | F9 Attribute-by-Attribute Matrix | `test_tier1_comparison_matrix_gap_status` | Non-compliant / missing attributes tagged GAP |
| Tier 1 | F9 Attribute-by-Attribute Matrix | `test_tier1_comparison_matrix_numerical_delta_formatting` | Numerical deltas for price and lead time canonically formatted |
| Tier 1 | F9 Attribute-by-Attribute Matrix | `test_tier1_comparison_matrix_omitted_attributes_rendered` | Missing listing attributes rendered as 'Not Specified' |
| Tier 1 | F10 & F11 Gap Taxonomy & Explanations | `test_tier1_gap_detection_missing_classification` | Omitted lead time or terms classified as MISSING |
| Tier 1 | F10 & F11 Gap Taxonomy & Explanations | `test_tier1_gap_detection_ambiguous_classification` | Vague phrasing ("standard warranty") classified AMBIGUOUS |
| Tier 1 | F10 & F11 Gap Taxonomy & Explanations | `test_tier1_gap_detection_non_compliant_classification` | High MOQ or over-budget price classified NON_COMPLIANT |
| Tier 1 | F10 & F11 Gap Taxonomy & Explanations | `test_tier1_gap_severity_critical_deal_blocker` | Blocker violations (>1.5x MOQ, > budget) tagged CRITICAL |
| Tier 1 | F10 & F11 Gap Taxonomy & Explanations | `test_tier1_gap_explanation_generator_mathematical_delta` | Explanations detail exact numbers and percentage variance |
| Tier 1 | F12 Targeted Seller Inquiry Drafting | `test_tier1_inquiry_drafting_missing_lead_time` | Inquiry requests explicit calendar day lead time |
| Tier 1 | F12 Targeted Seller Inquiry Drafting | `test_tier1_inquiry_drafting_ambiguous_warranty` | Inquiry clarifies warranty duration and defect claim protocol |
| Tier 1 | F12 Targeted Seller Inquiry Drafting | `test_tier1_inquiry_drafting_non_compliant_moq` | Inquiry proposes pilot lot or volume tiers |
| Tier 1 | F12 Targeted Seller Inquiry Drafting | `test_tier1_inquiry_drafting_non_compliant_price` | Inquiry requests volume discount toward target price |
| Tier 1 | F12 Targeted Seller Inquiry Drafting | `test_tier1_inquiry_drafting_zero_gaps_purchase_intent` | Zero-gap candidate produces formal purchase intent RFQ |
| Tier 1 | F13 & F14 Sourcing REST API & Deal Bridge | `test_tier1_api_interpret_endpoint` | POST /sourcing/interpret schema contract validation |
| Tier 1 | F13 & F14 Sourcing REST API & Deal Bridge | `test_tier1_api_listings_endpoint_filtering` | GET /sourcing/listings category and query filter validation |
| Tier 1 | F13 & F14 Sourcing REST API & Deal Bridge | `test_tier1_api_compare_endpoint` | POST /sourcing/compare ranking and score payload validation |
| Tier 1 | F13 & F14 Sourcing REST API & Deal Bridge | `test_tier1_api_gap_analysis_endpoint` | POST /sourcing/gap-analysis gap taxonomy payload validation |
| Tier 1 | F13 & F14 Sourcing REST API & Deal Bridge | `test_tier1_deal_handoff_bridge_prefilled_terms` | Evaluated terms prefilled into deal initiation bridge |
| Tier 2 | Boundary: Parsing Edge Cases | `test_tier2_parsing_empty_string` | Empty string returns blank requirements without 500 error |
| Tier 2 | Boundary: Parsing Edge Cases | `test_tier2_parsing_whitespace_only` | Whitespace-only string handled cleanly |
| Tier 2 | Boundary: Parsing Edge Cases | `test_tier2_parsing_extreme_long_prompt` | 8,000-character input parsed without timeout or buffer overflow |
| Tier 2 | Boundary: Parsing Edge Cases | `test_tier2_parsing_conflicting_budget_and_unit_price` | Unit price $10 vs $50k budget for 100 units handled cleanly |
| Tier 2 | Boundary: Parsing Edge Cases | `test_tier2_parsing_past_delivery_date` | Date 2020-01-01 in past flagged or nullified safely |
| Tier 2 | Boundary: Parsing Edge Cases | `test_tier2_parsing_unparseable_alphanumeric_quantity` | "a few hundred boxes" handles quantity as None gracefully |
| Tier 2 | Boundary: Pricing Limits | `test_tier2_pricing_zero_unit_price` | $0.00 price flagged as custom quote required |
| Tier 2 | Boundary: Pricing Limits | `test_tier2_pricing_extreme_large_price` | $1,000,000 unit price handled without numeric overflow |
| Tier 2 | Boundary: Pricing Limits | `test_tier2_pricing_zero_max_budget` | $0.00 max budget handled gracefully |
| Tier 2 | Boundary: Pricing Limits | `test_tier2_pricing_currency_mismatch_without_fx` | USD buyer vs EUR seller flagged MODERATE gap without crash |
| Tier 2 | Boundary: Pricing Limits | `test_tier2_pricing_fractional_cent_precision` | $0.0075 unit price compared with Decimal precision |
| Tier 2 | Boundary: Quantity & MOQ Limits | `test_tier2_quantity_extreme_large_volume` | 100,000,000 units compared accurately |
| Tier 2 | Boundary: Quantity & MOQ Limits | `test_tier2_quantity_fractional_decimal_quantity` | 0.25 metric tons handled accurately |
| Tier 2 | Boundary: Quantity & MOQ Limits | `test_tier2_quantity_seller_moq_100x_buyer_demand` | 100x seller MOQ triggers CRITICAL deal blocker |
| Tier 2 | Boundary: Quantity & MOQ Limits | `test_tier2_quantity_missing_seller_moq` | None seller MOQ scored at baseline and flagged MISSING |
| Tier 2 | Boundary: Quantity & MOQ Limits | `test_tier2_quantity_incompatible_unit_types` | Non-convertible units (kg vs liters) handled safely |
| Tier 2 | Boundary: Lead Time & Delivery | `test_tier2_lead_time_zero_days` | Zero lead time days handled as immediate dispatch |
| Tier 2 | Boundary: Lead Time & Delivery | `test_tier2_lead_time_extreme_days` | 730 days lead time flagged as non-compliant blocker |
| Tier 2 | Boundary: Lead Time & Delivery | `test_tier2_lead_time_vague_qualitative_phrase` | "immediate dispatch upon reopening" flagged AMBIGUOUS |
| Tier 2 | Boundary: Lead Time & Delivery | `test_tier2_lead_time_delivery_deadline_tomorrow` | 1-day deadline vs 21-day lead time flags CRITICAL |
| Tier 2 | Boundary: Lead Time & Delivery | `test_tier2_lead_time_missing_in_listing` | None lead time scored at baseline and flagged MISSING |
| Tier 2 | Boundary: Commercial Terms | `test_tier2_commercial_terms_unrecognized_incoterm` | Non-standard Incoterm flagged AMBIGUOUS |
| Tier 2 | Boundary: Commercial Terms | `test_tier2_commercial_terms_missing_warranty` | None warranty scored 0 pts and flagged MISSING |
| Tier 2 | Boundary: Commercial Terms | `test_tier2_commercial_terms_100_percent_advance_demand` | 100% advance payment penalized and flagged NON_COMPLIANT |
| Tier 2 | Boundary: Commercial Terms | `test_tier2_commercial_terms_ambiguous_standard_warranty` | "standard warranty applies" flagged AMBIGUOUS |
| Tier 2 | Boundary: Commercial Terms | `test_tier2_commercial_terms_empty_acceptable_incoterms_list` | Empty acceptable Incoterms list handled cleanly |
| Tier 3 | Cross-Feature Interaction | `test_tier3_combo_high_price_plus_missing_lead_time` | Over-budget price + missing lead time -> 2-point inquiry |
| Tier 3 | Cross-Feature Interaction | `test_tier3_combo_non_compliant_moq_plus_ambiguous_warranty` | High MOQ + vague warranty -> pilot lot + warranty inquiry |
| Tier 3 | Cross-Feature Interaction | `test_tier3_combo_missing_regulatory_cert_plus_tight_deadline` | Missing CE/FDA + 14d deadline -> disqualification score |
| Tier 3 | Cross-Feature Interaction | `test_tier3_combo_currency_mismatch_plus_restrictive_exw` | EUR price + EXW terms -> currency lock + freight inquiry |
| Tier 3 | Cross-Feature Interaction | `test_tier3_combo_category_disqualification_with_attractive_pricing` | Wrong category (Medical Gloves vs Fasteners) receives 0 specs |
| Tier 3 | Cross-Feature Interaction | `test_tier3_combo_partial_material_match_with_high_volume_discount` | 304 vs 316 SS -> material variance clarification inquiry |
| Tier 3 | Cross-Feature Interaction | `test_tier3_combo_100_percent_advance_plus_unverified_seller` | Advance payment demand triggers SyncAlly Escrow proposal |
| Tier 3 | Cross-Feature Interaction | `test_tier3_combo_extreme_lead_time_with_acceptable_price_and_specs` | 75d lead time vs 30d window triggers expedited freight request |
| Tier 4 | Real-World Procurement Journey | `test_tier4_journey_fasteners_automotive_oem` | Fasteners OEM journey: Berlin Tier A match, deal opened |
| Tier 4 | Real-World Procurement Journey | `test_tier4_journey_electronics_iot_cable_harness` | Electronics journey: Tokyo Micro-Conductor warranty inquiry |
| Tier 4 | Real-World Procurement Journey | `test_tier4_journey_agriculture_specialty_coffee` | Agriculture journey: 20t Arabica Fair Trade CIF Hamburg |
| Tier 4 | Real-World Procurement Journey | `test_tier4_journey_textiles_organic_canvas` | Textiles journey: Lancashire Mills missing lead time inquiry |
| Tier 4 | Real-World Procurement Journey | `test_tier4_journey_medical_ppe_hospital_replenishment` | Medical journey: MediShield gloves FDA 510(k) immediate deal |

### 4.2 Frontend Test Cases (`frontend/src/sourcing/SourcingHub.test.tsx` — 23 Tests)

| Tier | Category / Feature | Test Name | Summary |
|---|---|---|---|
| Tier 1 | Navigation & Layout | `1.1 renders Sourcing Hub title, breadcrumbs, and active navigation state` | Verifies header, breadcrumbs, and title |
| Tier 1 | Dual-Mode Input Form | `1.2 switches between natural language mode and structured field controls` | Toggles between prompt textarea and structured fields |
| Tier 1 | Dual-Mode Input Form | `1.3 submits natural language requirement prompt and updates evaluation` | Submits prompt and updates candidate listings |
| Tier 1 | Comparison Cards | `1.4 renders candidate listing comparison cards with match score badges and completeness tier` | Verifies Berlin Tier A and Nordic Tier D badges |
| Tier 1 | Comparison Matrix | `1.5 displays attribute-by-attribute comparison table with MATCH, ACCEPTABLE, and GAP status icons` | Verifies tabular comparison matrix rows |
| Tier 1 | Gap Inspector Drawer | `1.6 opens gap analysis inspector drawer displaying MISSING, AMBIGUOUS, and NON_COMPLIANT items` | Inspects Baltic MOQ gap with CRITICAL badge |
| Tier 1 | Seller Inquiry Modal | `1.7 opens seller inquiry modal and renders customizable letter addressing detected gaps` | Verifies prefilled inquiry addressing MOQ gap |
| Tier 1 | Clipboard Integration | `1.8 copies drafted inquiry to clipboard and triggers user notification toast` | Verifies navigator.clipboard.writeText and toast |
| Tier 1 | Deal Bridge Integration | `1.9 bridges selected candidate and inquiry into Deal Creation form (#/deals/new)` | Verifies hash navigation with deal parameters |
| Tier 2 | Boundary / Validation | `2.1 displays validation error when submitting empty requirement input` | Renders inline validation error alert |
| Tier 2 | Boundary / Incompleteness | `2.2 handles candidate listing with missing lead time gracefully` | Renders "Lead: Missing" badge |
| Tier 2 | Boundary / Non-compliance | `2.3 handles excessive seller MOQ relative to buyer demand with critical badge` | Displays CRITICAL severity and +400% explanation |
| Tier 2 | Boundary / Over-budget | `2.4 handles over-budget candidate listing by assigning Tier D rating` | Displays Tier D rating on Nordic AeroSpares |
| Tier 2 | Boundary / Zero Gaps | `2.5 renders 100% compliant zero-gap listing with immediate purchase intent prompt` | Renders zero-gap purchase confirmation text |
| Tier 3 | Cross-Feature Interaction | `3.1 recalculates candidate tiers dynamically when user modifies max budget` | Changing max budget dynamically upgrades candidate tier |
| Tier 3 | Cross-Feature Interaction | `3.2 clicking candidate card immediately switches comparison matrix and gap list` | Card selection updates table and gap inspector |
| Tier 3 | Cross-Feature Interaction | `3.3 editing inquiry draft in modal retains custom buyer changes upon deal initiation` | Custom edits preserved through deal creation bridge |
| Tier 3 | Cross-Feature Interaction | `3.4 filtering by sector updates candidate cards count and list dynamically` | Sector dropdown dynamically filters candidates |
| Tier 4 | Real-World Journey | `4.1 Industrial Fasteners Journey: OEM engineer evaluates bolts, inspects Baltic MOQ gap, selects Berlin, and initiates deal` | End-to-end fastener procurement walkthrough |
| Tier 4 | Real-World Journey | `4.2 Electronics & Wiring Journey: IoT maker evaluates harness and prepares inquiry clarifying ambiguous warranty` | End-to-end electronics wiring harness walkthrough |
| Tier 4 | Real-World Journey | `4.3 Agricultural Commodities Journey: Coffee buyer verifies organic green coffee with Fair Trade and CIF terms` | End-to-end coffee commodity trade walkthrough |
| Tier 4 | Real-World Journey | `4.4 Textiles & Apparel Journey: Fashion brand evaluates cotton canvas and drafts lead time inquiry` | End-to-end textile sourcing walkthrough |
| Tier 4 | Real-World Journey | `4.5 Medical Supplies & PPE Journey: Hospital replenishes 10,000 boxes nitrile examination gloves with FDA certs` | End-to-end medical PPE replenishment walkthrough |

---

## 5. Execution Commands

### 5.1 Run Backend E2E Sourcing Test Suite
```bash
/home/yashaswi/Project/SyncAlly/backend/.venv/bin/pytest backend/tests/test_e2e_buyer_sourcing.py -v
```

### 5.2 Run Frontend E2E Sourcing Test Suite
```bash
npm --prefix frontend test -- src/sourcing/SourcingHub.test.tsx --run
```

### 5.3 Run Linting & Quality Gates
```bash
# Backend lint check
/home/yashaswi/Project/SyncAlly/backend/.venv/bin/ruff check backend/tests/test_e2e_buyer_sourcing.py

# Frontend lint check
(cd /home/yashaswi/Project/SyncAlly/frontend && npx eslint src/sourcing/SourcingHub.test.tsx)
```

### 5.4 Run Combined Full Sourcing Test Suite
```bash
/home/yashaswi/Project/SyncAlly/backend/.venv/bin/pytest backend/tests/test_e2e_buyer_sourcing.py && \
npm --prefix frontend test -- src/sourcing/SourcingHub.test.tsx --run
```
