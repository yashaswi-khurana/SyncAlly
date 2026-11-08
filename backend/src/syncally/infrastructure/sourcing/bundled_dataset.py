"""Bundled realistic marketplace dataset for buyer sourcing agent evaluation.

Contains 14 curated candidate listings across 5 commercial B2B sectors:
1. Industrial Fasteners
2. Electronics & Electrical
3. Agricultural Commodities
4. Textiles & Fabrics
5. Medical Supplies & PPE

With intentionally varying completeness tiers:
- FULL_COMPLETE: Benchmark candidates with explicit specs, verified lead times, clear Incoterms & payment terms.
- AMBIGUOUS_SPECS_OR_TERMS: Vague or non-binding terms (e.g. "standard warranty", "negotiable payment terms", "prompt shipment").
- PARTIAL_MISSING_LEAD_TIME_OR_TERMS: Crucial terms omitted (missing lead time days, empty Incoterms, missing QC).
- NON_COMPLIANT_MOQ: High MOQ barrier exceeding standard pilot batch demand.
- NON_COMPLIANT_PRICE: Premium tier exceeding typical buyer budget ceilings.
- NON_COMPLIANT_LEAD_TIME: Production delay exceeding typical urgent delivery windows.
"""

from __future__ import annotations

from decimal import Decimal

from syncally.domain.sourcing.contracts import (
    Incoterm,
    MarketplaceListingDetail,
    TechnicalSpecification,
)

BUNDLED_MARKETPLACE_LISTINGS: list[MarketplaceListingDetail] = [
    # -------------------------------------------------------------------------
    # 1. Industrial Fasteners (4 listings)
    # -------------------------------------------------------------------------
    MarketplaceListingDetail(
        id="00000000-0000-4000-8000-000000000101",
        organization_id="11111111-0000-4000-8000-000000000001",
        organization_name="Berlin Fastener & Bolt GmbH",
        country_code="DE",
        title="M8x30 Grade 316 Stainless Steel Hex Cap Bolts",
        category="Industrial Fasteners",
        description="High precision A4-70 marine grade stainless steel hex head bolts, DIN 933 compliant, passivated finish.",
        available_quantity=Decimal("15000"),
        moq=Decimal("500"),
        unit="boxes",
        unit_price=Decimal("11.50"),
        currency="USD",
        lead_time_days=21,
        incoterms=[Incoterm.FOB, Incoterm.CIF, Incoterm.DDP],
        payment_terms="Net 30 for verified accounts; Escrow accepted",
        technical_specs=TechnicalSpecification(
            materials=["316 Stainless Steel", "A4-70"],
            tolerances="ISO 965-1 6g (+/- 0.05mm)",
            certifications=["ISO 9001", "CE", "RoHS"],
            standards=["DIN 933", "ISO 4017"],
            quality_grade="A4-70",
            notes="Full batch traceability with 3.1 mill test certificates.",
        ),
        warranty_months=24,
        warranty_description="24-month replacement warranty against material and manufacturing defects.",
        inspection_terms="EN 10204 3.1 Mill Test Certificate included; Pre-shipment inspection allowed.",
        completeness_tier="FULL_COMPLETE",
    ),
    MarketplaceListingDetail(
        id="00000000-0000-4000-8000-000000000102",
        organization_id="11111111-0000-4000-8000-000000000002",
        organization_name="Apex Hardware Manufacturing",
        country_code="US",
        title="Bulk Precision Stainless Steel Bolts M8",
        category="Industrial Fasteners",
        description="Standard commercial M8 hex bolts for construction and industrial assembly.",
        available_quantity=Decimal("8000"),
        moq=Decimal("200"),
        unit="boxes",
        unit_price=Decimal("10.80"),
        currency="USD",
        lead_time_days=None,  # Missing
        incoterms=[],  # Missing
        payment_terms="50% advance deposit, 50% prior to dispatch",
        technical_specs=TechnicalSpecification(
            materials=["304 Stainless Steel"],
            tolerances="+/- 0.1mm",
            certifications=["ISO 9001"],
            standards=["DIN 933"],
            quality_grade="A2-70",
            notes="General purpose hardware.",
        ),
        warranty_months=12,
        warranty_description="12 months factory warranty.",
        inspection_terms="Factory internal QC report.",
        completeness_tier="PARTIAL_MISSING_LEAD_TIME_OR_TERMS",
    ),
    MarketplaceListingDetail(
        id="00000000-0000-4000-8000-000000000104",
        organization_id="11111111-0000-4000-8000-000000000004",
        organization_name="Baltic Fastener Works",
        country_code="PL",
        title="Industrial Marine-Grade A4-80 Bolts & Studs",
        category="Industrial Fasteners",
        description="Heavy-duty marine grade A4-80 bolts engineered for high-saline and extreme offshore environments.",
        available_quantity=Decimal("50000"),
        moq=Decimal("5000"),  # High MOQ barrier
        unit="boxes",
        unit_price=Decimal("9.50"),
        currency="USD",
        lead_time_days=35,
        incoterms=[Incoterm.FOB, Incoterm.CIF],
        payment_terms="Net 30 or LC at sight",
        technical_specs=TechnicalSpecification(
            materials=["316 Stainless Steel", "A4-80"],
            tolerances="ISO 965-1 6g",
            certifications=["ISO 9001", "CE"],
            standards=["ISO 3506-1", "DIN 933"],
            quality_grade="A4-80",
            notes="High tensile strength > 800 MPa.",
        ),
        warranty_months=36,
        warranty_description="36-month heavy industrial corrosion guarantee.",
        inspection_terms="Third-party Lloyd's Register marine inspection certified.",
        completeness_tier="NON_COMPLIANT_MOQ",
    ),
    MarketplaceListingDetail(
        id="00000000-0000-4000-8000-000000000105",
        organization_id="11111111-0000-4000-8000-000000000005",
        organization_name="Nordic Precision AeroSpares",
        country_code="SE",
        title="Aerospace Grade Ultra-High Tensile Fasteners M8",
        category="Industrial Fasteners",
        description="Ultra-precision titanium-stabilized 316L fasteners manufactured under aerospace quality standards.",
        available_quantity=Decimal("2500"),
        moq=Decimal("100"),
        unit="boxes",
        unit_price=Decimal("24.00"),  # Premium price / over typical budget
        currency="USD",
        lead_time_days=14,
        incoterms=[Incoterm.DDP, Incoterm.CIP],
        payment_terms="Net 45 upon invoice",
        technical_specs=TechnicalSpecification(
            materials=["316L Stainless Steel", "Titanium Alloy"],
            tolerances="+/- 0.005mm",
            certifications=["AS9100D", "ISO 9001", "RoHS"],
            standards=["DIN 933", "EN 2859"],
            quality_grade="Aerospace Grade A4-80",
            notes="100% optical and laser dimensional inspection.",
        ),
        warranty_months=36,
        warranty_description="Comprehensive aerospace quality guarantee covering dimensional accuracy and metallurgical purity.",
        inspection_terms="100% laser CMM dimensional verification report and EN 10204 3.1 inspection certificate.",
        completeness_tier="NON_COMPLIANT_PRICE",
    ),

    # -------------------------------------------------------------------------
    # 2. Electronics & Electrical (3 listings)
    # -------------------------------------------------------------------------
    MarketplaceListingDetail(
        id="00000000-0000-4000-8000-000000000103",
        organization_id="11111111-0000-4000-8000-000000000003",
        organization_name="Tokyo Micro-Conductor Ltd",
        country_code="JP",
        title="Automotive Spec Copper Wire Harness 2m 28AWG",
        category="Electronics & Electrical",
        description="Flame retardant high-flexibility automotive grade copper wire harness with gold-plated terminal connectors.",
        available_quantity=Decimal("5000"),
        moq=Decimal("500"),
        unit="units",
        unit_price=Decimal("7.20"),
        currency="USD",
        lead_time_days=28,
        incoterms=[Incoterm.FOB],
        payment_terms="Negotiable commercial terms upon request",  # Ambiguous
        technical_specs=TechnicalSpecification(
            materials=["Oxygen-free Copper", "PVC Insulation"],
            tolerances="+/- 1mm length",
            certifications=["ISO 9001", "RoHS"],
            standards=["JASO D611", "UL 1007"],
            quality_grade="Automotive Grade",
            notes="Tested for 100,000 cycle flexing.",
        ),
        warranty_months=None,  # Ambiguous
        warranty_description="Standard warranty applies per industry norms.",  # Ambiguous
        inspection_terms="Standard factory check.",  # Ambiguous
        completeness_tier="AMBIGUOUS_SPECS_OR_TERMS",
    ),
    MarketplaceListingDetail(
        id="00000000-0000-4000-8000-000000000107",
        organization_id="11111111-0000-4000-8000-000000000007",
        organization_name="Shenzhen Precision Interconnect Co",
        country_code="CN",
        title="Custom Shielded Micro-Coaxial Cable Assembly",
        category="Electronics & Electrical",
        description="High-frequency low-loss micro coaxial cable assemblies for medical and RF telecommunication equipment.",
        available_quantity=Decimal("20000"),
        moq=Decimal("1000"),
        unit="units",
        unit_price=Decimal("5.80"),
        currency="USD",
        lead_time_days=75,  # Excessive lead time
        incoterms=[Incoterm.FOB],
        payment_terms="30% deposit, 70% before shipment",
        technical_specs=TechnicalSpecification(
            materials=["Silver-Plated Copper", "PTFE Dielectric"],
            tolerances="+/- 0.5mm",
            certifications=["CE", "RoHS", "UL 94V-0"],
            standards=["MIL-DTL-17", "IPC-620"],
            quality_grade="High Frequency Grade",
            notes="Impedance 50 Ohm +/- 2 Ohm.",
        ),
        warranty_months=12,
        warranty_description="12 months manufacturer defect warranty.",
        inspection_terms="Factory batch inspection report.",
        completeness_tier="NON_COMPLIANT_LEAD_TIME",
    ),
    MarketplaceListingDetail(
        id="00000000-0000-4000-8000-000000000109",
        organization_id="11111111-0000-4000-8000-000000000009",
        organization_name="Silicon Valley Sensors Inc",
        country_code="US",
        title="Industrial IoT Temperature & Pressure Transducer 4-20mA",
        category="Electronics & Electrical",
        description="Ruggedized hermetically sealed stainless steel pressure and temperature sensor with analog 4-20mA output.",
        available_quantity=Decimal("3000"),
        moq=Decimal("50"),
        unit="units",
        unit_price=Decimal("42.00"),
        currency="USD",
        lead_time_days=14,
        incoterms=[Incoterm.DDP, Incoterm.FOB],
        payment_terms="Net 30 for verified corporate buyers; Escrow accepted",
        technical_specs=TechnicalSpecification(
            materials=["316L Stainless Steel", "Ceramic Sensor Element"],
            tolerances="0.25% Full Scale Accuracy",
            certifications=["CE", "RoHS", "ISO 9001", "ATEX"],
            standards=["IEC 60770", "IP67"],
            quality_grade="Industrial Harsh Environment",
            notes="Calibrated against NIST traceable standards.",
        ),
        warranty_months=24,
        warranty_description="24-month unconditional calibration and electronics warranty.",
        inspection_terms="NIST traceable individual calibration certificate included.",
        completeness_tier="FULL_COMPLETE",
    ),

    # -------------------------------------------------------------------------
    # 3. Agricultural Commodities (3 listings)
    # -------------------------------------------------------------------------
    MarketplaceListingDetail(
        id="00000000-0000-4000-8000-000000000110",
        organization_id="11111111-0000-4000-8000-000000000010",
        organization_name="São Paulo Agri-Exports Ltd",
        country_code="BR",
        title="Non-GMO Soybeans Bulk Grade 1 Food & Feed",
        category="Agricultural Commodities",
        description="Cleaned, graded, high-protein non-GMO soybeans for food processing and high-grade feed formulation.",
        available_quantity=Decimal("10000"),
        moq=Decimal("500"),
        unit="metric tons",
        unit_price=Decimal("480.00"),
        currency="USD",
        lead_time_days=25,
        incoterms=[Incoterm.FOB, Incoterm.CIF],
        payment_terms="Irrevocable LC at sight or Escrow",
        technical_specs=TechnicalSpecification(
            materials=["Non-GMO Yellow Soybeans"],
            tolerances="Moisture max 13%, Foreign matter max 1%",
            certifications=["ISO 22000", "HACCP", "Non-GMO Project Verified"],
            standards=["USDA Grade 1", "GAFTA 100"],
            quality_grade="Grade 1 Food Quality",
            notes="Protein content min 36% dry basis.",
        ),
        warranty_months=6,
        warranty_description="Quality guaranteed upon arrival at port of discharge per SGS report.",
        inspection_terms="SGS pre-shipment quality and weight inspection certificate included.",
        completeness_tier="FULL_COMPLETE",
    ),
    MarketplaceListingDetail(
        id="00000000-0000-4000-8000-000000000111",
        organization_id="11111111-0000-4000-8000-000000000011",
        organization_name="Danubian Grains Trading Co",
        country_code="RO",
        title="High Protein Milling Wheat Grade A",
        category="Agricultural Commodities",
        description="Premium European milling wheat with high test weight and stable falling number for commercial bakeries.",
        available_quantity=Decimal("8000"),
        moq=Decimal("300"),
        unit="metric tons",
        unit_price=Decimal("265.00"),
        currency="USD",
        lead_time_days=None,  # Missing
        incoterms=[Incoterm.FOB, Incoterm.CIF],
        payment_terms="Negotiable letter of credit or cash against documents",  # Ambiguous
        technical_specs=TechnicalSpecification(
            materials=["Milling Wheat"],
            tolerances="Moisture max 14%, Protein min 13.5%",
            certifications=["ISO 9001"],
            standards=["EU Grain Standards"],
            quality_grade="Grade A Milling",
            notes="Hagberg Falling Number min 280 sec.",
        ),
        warranty_months=None,  # Missing
        warranty_description="Standard agricultural commodity delivery terms.",  # Ambiguous
        inspection_terms="Port terminal grain elevator inspection.",
        completeness_tier="AMBIGUOUS_SPECS_OR_TERMS",
    ),
    MarketplaceListingDetail(
        id="00000000-0000-4000-8000-000000000112",
        organization_id="11111111-0000-4000-8000-000000000012",
        organization_name="Valley Organic Farms Cooperative",
        country_code="US",
        title="Certified Organic Arabica Green Coffee Beans",
        category="Agricultural Commodities",
        description="Single-origin specialty washed green arabica coffee beans, screen size 17/18, specialty grade 84+ SCA.",
        available_quantity=Decimal("1200"),
        moq=Decimal("50"),
        unit="bags",
        unit_price=Decimal("210.00"),
        currency="USD",
        lead_time_days=30,
        incoterms=[Incoterm.FOB],
        payment_terms="50% deposit, balance upon Bill of Lading",
        technical_specs=TechnicalSpecification(
            materials=["100% Arabica Green Coffee"],
            tolerances="Moisture 10.5% - 11.5%",
            certifications=["USDA Organic", "Fair Trade Certified", "Rainforest Alliance"],
            standards=["SCA Specialty Coffee Standards"],
            quality_grade="Strictly High Grown (SHG) EP",
            notes="GrainPro hermetic bag packaging included.",
        ),
        warranty_months=12,
        warranty_description="Guaranteed green coffee freshness and cupping score integrity in unopened GrainPro bags.",
        inspection_terms=None,  # Missing
        completeness_tier="PARTIAL_MISSING_LEAD_TIME_OR_TERMS",
    ),

    # -------------------------------------------------------------------------
    # 4. Textiles & Fabrics (2 listings)
    # -------------------------------------------------------------------------
    MarketplaceListingDetail(
        id="00000000-0000-4000-8000-000000000106",
        organization_id="11111111-0000-4000-8000-000000000006",
        organization_name="Lancashire Weaving Mills",
        country_code="GB",
        title="Heavy Industrial Canvas & Poplin Fabric",
        category="Textiles & Fabrics",
        description="High durability industrial woven cotton canvas suitable for protective gear, workwear, and heavy tote bags.",
        available_quantity=Decimal("40000"),
        moq=Decimal("1000"),
        unit="yards",
        unit_price=Decimal("3.10"),
        currency="USD",
        lead_time_days=None,  # Missing
        incoterms=[Incoterm.EXW],  # Restrictive
        payment_terms="Net 30 for UK; export terms subject to approval",  # Ambiguous
        technical_specs=TechnicalSpecification(
            materials=["100% Cotton", "Ring Spun Yarn"],
            tolerances="Weight 320 GSM +/- 5%",
            certifications=["OEKO-TEX Standard 100"],
            standards=["BS EN 14419"],
            quality_grade="Heavy Industrial Duck",
            notes="Water repellent fluorocarbon free finish available.",
        ),
        warranty_months=None,  # Missing
        warranty_description=None,  # Missing
        inspection_terms=None,  # Missing
        completeness_tier="AMBIGUOUS_SPECS_OR_TERMS",
    ),
    MarketplaceListingDetail(
        id="00000000-0000-4000-8000-000000000113",
        organization_id="11111111-0000-4000-8000-000000000013",
        organization_name="Istanbul Technical Textiles A.S.",
        country_code="TR",
        title="Flame Retardant Nomex Aramid Protective Fabric",
        category="Textiles & Fabrics",
        description="Inherent flame retardant woven aramid fabric with anti-static carbon grid for petrochemical and electrical arc flash PPE.",
        available_quantity=Decimal("15000"),
        moq=Decimal("250"),
        unit="meters",
        unit_price=Decimal("14.50"),
        currency="USD",
        lead_time_days=18,
        incoterms=[Incoterm.DDP, Incoterm.CIF, Incoterm.FOB],
        payment_terms="Net 30 with trade credit insurance or Escrow",
        technical_specs=TechnicalSpecification(
            materials=["93% Meta-Aramid", "5% Para-Aramid", "2% Antistatic Fiber"],
            tolerances="Weight 220 GSM +/- 3%",
            certifications=["ISO 9001", "CE", "OEKO-TEX Standard 100"],
            standards=["EN ISO 11612", "NFPA 2112", "EN 1149-5"],
            quality_grade="PPE Level 2 Arc Flash",
            notes="Wash durability 50+ industrial launderings.",
        ),
        warranty_months=36,
        warranty_description="36-month flame retardant property guarantee under recommended laundering conditions.",
        inspection_terms="Pre-shipment batch flammability test report per EN ISO 15025.",
        completeness_tier="FULL_COMPLETE",
    ),

    # -------------------------------------------------------------------------
    # 5. Medical Supplies & PPE (2 listings)
    # -------------------------------------------------------------------------
    MarketplaceListingDetail(
        id="00000000-0000-4000-8000-000000000108",
        organization_id="11111111-0000-4000-8000-000000000008",
        organization_name="MediShield Global Corp",
        country_code="US",
        title="Nitrile Examination Gloves Powder-Free Medical Grade",
        category="Medical Supplies & PPE",
        description="Premium powder-free medical examination gloves with textured fingertips for superior grip and barrier protection.",
        available_quantity=Decimal("25000"),
        moq=Decimal("500"),
        unit="boxes",
        unit_price=Decimal("8.50"),
        currency="USD",
        lead_time_days=10,
        incoterms=[Incoterm.FOB, Incoterm.DDP],
        payment_terms="Net 30 upon credit approval; Escrow accepted",
        technical_specs=TechnicalSpecification(
            materials=["Medical Nitrile", "Nitrile Butadiene Rubber"],
            tolerances="Thickness 4.0 mil +/- 0.5 mil",
            certifications=["FDA 510(k)", "ISO 13485", "CE"],
            standards=["ASTM D6319", "EN 455 Parts 1-4"],
            quality_grade="Medical Examination Grade",
            notes="Chemotherapy drug tested per ASTM D6978.",
        ),
        warranty_months=60,
        warranty_description="60-month shelf-life sterility and integrity guarantee.",
        inspection_terms="AQL 1.5 pinhole water leak inspection lot release certificate.",
        completeness_tier="FULL_COMPLETE",
    ),
    MarketplaceListingDetail(
        id="00000000-0000-4000-8000-000000000115",
        organization_id="11111111-0000-4000-8000-000000000015",
        organization_name="Bavarian MedTech Instruments GmbH",
        country_code="DE",
        title="Reusable Surgical Grade Stainless Steel Scalpel Handles",
        category="Medical Supplies & PPE",
        description="Precision machined German surgical stainless steel scalpel handles (#3 & #4) for hospital operating rooms.",
        available_quantity=Decimal("1000"),
        moq=Decimal("20"),
        unit="units",
        unit_price=Decimal("45.00"),  # Premium medical instrument price
        currency="USD",
        lead_time_days=12,
        incoterms=[Incoterm.DDP, Incoterm.FOB],
        payment_terms="Net 30 upon delivery",
        technical_specs=TechnicalSpecification(
            materials=["Martensitic Stainless Steel 420"],
            tolerances="+/- 0.02mm fit to surgical blades",
            certifications=["ISO 13485", "CE Mark Class I", "FDA Registered"],
            standards=["ISO 7153-1", "EN ISO 14971"],
            quality_grade="Surgical Grade 420",
            notes="Autoclavable up to 134 deg C.",
        ),
        warranty_months=60,
        warranty_description="5-year corrosion and defect warranty under hospital autoclave sterilization cycles.",
        inspection_terms="Individual passivation and corrosion resistance boil test certificate.",
        completeness_tier="NON_COMPLIANT_PRICE",
    ),
]


def get_bundled_listings(
    category: str | None = None,
    completeness: str | None = None,
    query: str | None = None,
) -> list[MarketplaceListingDetail]:
    """Retrieve bundled marketplace listings filtered by category, completeness tier, or search text."""
    results = list(BUNDLED_MARKETPLACE_LISTINGS)

    if category:
        cat_lower = category.strip().lower()
        results = [
            item for item in results
            if cat_lower in item.category.lower() or item.category.lower() in cat_lower
        ]

    if completeness:
        comp_lower = completeness.strip().lower()
        results = [
            item for item in results
            if comp_lower in item.completeness_tier.lower()
        ]

    if query:
        q_lower = query.strip().lower()
        results = [
            item for item in results
            if (
                q_lower in item.title.lower()
                or q_lower in item.description.lower()
                or q_lower in item.organization_name.lower()
                or any(q_lower in m.lower() for m in item.technical_specs.materials)
                or any(q_lower in c.lower() for c in item.technical_specs.certifications)
                or any(q_lower in s.lower() for s in item.technical_specs.standards)
            )
        ]

    return results


def get_bundled_listing_by_id(listing_id: str) -> MarketplaceListingDetail | None:
    """Find a bundled marketplace listing by its stable ID."""
    clean_id = listing_id.strip().lower()
    for listing in BUNDLED_MARKETPLACE_LISTINGS:
        if listing.id.lower() == clean_id:
            return listing
    return None
