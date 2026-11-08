"""Local requirement interpreter for buyer sourcing prompts and structured criteria.

Operates 100% locally with zero external network or LLM dependencies.
Extracts structured parameters from natural language prompts using regex and heuristics,
and composes with structured field overrides.
"""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, InvalidOperation, Overflow
from typing import Any

from syncally.domain.sourcing.contracts import (
    BuyerRequirements,
    CommercialTermsRequirement,
    DeliveryConstraint,
    Incoterm,
    InspectionPreference,
    PaymentMethodPreference,
    PricingConstraint,
    QuantityRequirement,
    TechnicalSpecification,
)

# -----------------------------------------------------------------------------
# Regular Expressions for Local NLP Extraction
# -----------------------------------------------------------------------------

_QUANTITY_RE = re.compile(
    r"\b(?:need|require|order|buy|procure|purchasing|quantity|volume|target\s+quantity|rfq\s+for|for)?\s*"
    r"(?P<qty>\d{1,3}(?:,\d{3})*|\d+)\s*"
    r"(?P<unit>boxes|box|units|unit|pieces|pcs|pc|metric\s+tons?|tonnes?|tons?|mt|kg|kilograms?|yards?|yd|meters?|m|bags?|rolls?|sets?)\b",
    re.IGNORECASE,
)

_CURRENCY_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("USD", re.compile(r"(\$|USD\b|US\s+Dollars?)", re.IGNORECASE)),
    ("EUR", re.compile(r"(€|EUR\b|Euros?)", re.IGNORECASE)),
    ("GBP", re.compile(r"(£|GBP\b|Pounds?|Sterling)", re.IGNORECASE)),
    ("JPY", re.compile(r"(¥|JPY\b|Yen)", re.IGNORECASE)),
]

_UNIT_PRICE_RE = re.compile(
    r"\b(?:target\s+(?:unit\s+)?price|unit\s+price|target\s+price|price|price\s+per\s+unit|target\s+of|target)\s*[:=]?\s*"
    r"[$€£¥]?\s*(?P<price>\d+(?:\.\d{1,4})?)\s*"
    r"(?:[$€£¥]|USD|EUR|GBP)?\s*"
    r"(?:(?:\s*(?:per|\/)\s*(?:box|unit|piece|pc|boxe?s?|kg|metric\s+ton|mt|meter|yard|bag|each))|\b)",
    re.IGNORECASE,
)

_MAX_PRICE_RE = re.compile(
    r"\b(?:max(?:imum)?\s+(?:unit\s+)?price|ceiling\s+(?:unit\s+)?price|budget\s+ceiling|price\s+ceiling|ceiling|not\s+exceeding|under|max|cap)\s*[:=]?\s*"
    r"[$€£¥]?\s*(?P<max_price>\d+(?:\.\d{1,4})?)\s*(?:USD|EUR|GBP)?(?:\s*(?:per|\/)\s*[a-z]+)?\b",
    re.IGNORECASE,
)

_MAX_BUDGET_RE = re.compile(
    r"\b(?:total\s+budget|total\s+order\s+budget|max\s+total\s+budget|overall\s+budget|total\s+spend|budget\s+of)\s*[:=]?\s*"
    r"[$€£¥]?\s*(?P<budget>\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)\s*(?:USD|EUR|GBP)?\b",
    re.IGNORECASE,
)

_LEAD_TIME_DAYS_RE = re.compile(
    r"\b(?:within|max(?:imum)?\s+lead\s+time|lead\s+time|leadtime|delivery\s+within|in|delivery\s+time)\s*[:=]?\s*"
    r"(?P<days>\d+)\s*(?P<scale>days?|calendar\s+days?|business\s+days?|weeks?|months?)\b",
    re.IGNORECASE,
)

_DELIVERY_DATE_RE = re.compile(
    r"\b(?:deliver\s+by|delivery\s+by|by|before|required\s+by)\s*(?P<year>20\d\d)-(?P<month>0[1-9]|1[0-2])-(?P<day>0[1-9]|[12]\d|3[01])\b",
    re.IGNORECASE,
)

_WARRANTY_MONTHS_RE = re.compile(
    r"\b(?P<duration>\d+)\s*(?P<scale>months?|years?)\s*(?:warranty|guarantee)\b",
    re.IGNORECASE,
)

_TOLERANCE_RE = re.compile(
    r"(\+/-\s*\d+(?:\.\d+)?\s*(?:mm|cm|mil|%|\b)|iso\s*965[^\n,;.]*|\d+(?:\.\d+)?%\s*(?:full\s+scale\s+accuracy|accuracy))",
    re.IGNORECASE,
)

_CATEGORY_KEYWORDS: list[tuple[str, list[str]]] = [
    (
        "Industrial Fasteners",
        ["fastener", "bolt", "bolts", "screw", "screws", "hex cap", "hex head", "studs", "washers"],
    ),
    (
        "Electronics & Electrical",
        [
            "wire harness",
            "harness",
            "cable",
            "coaxial",
            "sensor",
            "transducer",
            "semiconductor",
            "connector",
            "electrical",
        ],
    ),
    (
        "Agricultural Commodities",
        ["soybean", "soybeans", "wheat", "coffee", "grain", "grains", "corn", "seed"],
    ),
    (
        "Textiles & Fabrics",
        [
            "fabric",
            "fabrics",
            "canvas",
            "poplin",
            "cotton",
            "textile",
            "textiles",
            "aramid",
            "nomex",
            "yarn",
        ],
    ),
    (
        "Medical Supplies & PPE",
        [
            "glove",
            "gloves",
            "nitrile",
            "medical",
            "surgical",
            "scalpel",
            "ppe",
            "hospital",
            "examination gloves",
        ],
    ),
]

_KNOWN_MATERIALS: list[str] = [
    "316 Stainless Steel",
    "316L Stainless Steel",
    "304 Stainless Steel",
    "A4-70",
    "A4-80",
    "Titanium Alloy",
    "Oxygen-free Copper",
    "Silver-Plated Copper",
    "Non-GMO Yellow Soybeans",
    "Milling Wheat",
    "Arabica Green Coffee",
    "100% Cotton",
    "Meta-Aramid",
    "Para-Aramid",
    "Medical Nitrile",
    "Nitrile",
    "Martensitic Stainless Steel 420",
]

_KNOWN_CERTIFICATIONS: list[str] = [
    "ISO 9001",
    "ISO 13485",
    "ISO 22000",
    "AS9100D",
    "CE",
    "RoHS",
    "FDA 510(k)",
    "FDA",
    "OEKO-TEX Standard 100",
    "OEKO-TEX",
    "UL 94V-0",
    "UL",
    "HACCP",
    "Non-GMO Project Verified",
    "USDA Organic",
    "Fair Trade Certified",
    "Rainforest Alliance",
    "ATEX",
]

_KNOWN_STANDARDS: list[str] = [
    "DIN 933",
    "ISO 4017",
    "ISO 3506-1",
    "ASTM D6319",
    "EN 455",
    "JASO D611",
    "UL 1007",
    "EN ISO 11612",
    "NFPA 2112",
    "USDA Grade 1",
    "GAFTA 100",
    "BS EN 14419",
    "IEC 60770",
    "ISO 7153-1",
]

_KNOWN_GRADES: list[str] = [
    "A4-70",
    "A4-80",
    "A2-70",
    "Grade 8.8",
    "Grade 10.9",
    "Medical Grade",
    "Automotive Grade",
    "Aerospace Grade",
    "Grade 1 Food Quality",
    "Grade A Milling",
    "Surgical Grade 420",
]

_INCOTERM_LOOKUP: dict[str, Incoterm] = {
    "DDP": Incoterm.DDP,
    "CIF": Incoterm.CIF,
    "FOB": Incoterm.FOB,
    "EXW": Incoterm.EXW,
    "FCA": Incoterm.FCA,
    "CIP": Incoterm.CIP,
    "DAP": Incoterm.DAP,
    "CFR": Incoterm.CFR,
    "CPT": Incoterm.CPT,
    "DPU": Incoterm.DPU,
    "FAS": Incoterm.FAS,
}

_COUNTRY_NAME_TO_CODE: dict[str, str] = {
    "germany": "DE",
    "deutschland": "DE",
    "united states": "US",
    "usa": "US",
    "us": "US",
    "america": "US",
    "united kingdom": "GB",
    "uk": "GB",
    "britain": "GB",
    "great britain": "GB",
    "japan": "JP",
    "poland": "PL",
    "polska": "PL",
    "sweden": "SE",
    "turkey": "TR",
    "türkiye": "TR",
    "brazil": "BR",
    "brasil": "BR",
    "china": "CN",
    "romania": "RO",
    "france": "FR",
    "netherlands": "NL",
    "india": "IN",
    "canada": "CA",
    "mexico": "MX",
    "italy": "IT",
    "spain": "ES",
}

_KNOWN_PORTS_CITIES: list[tuple[str, str]] = [
    ("Hamburg", "DE"),
    ("Bremen", "DE"),
    ("Rotterdam", "NL"),
    ("Antwerp", "BE"),
    ("Chicago", "US"),
    ("Long Beach", "US"),
    ("Los Angeles", "US"),
    ("New York", "US"),
    ("Tokyo", "JP"),
    ("Yokohama", "JP"),
    ("London", "GB"),
    ("Southampton", "GB"),
    ("Gdansk", "PL"),
    ("Stockholm", "SE"),
    ("Gothenburg", "SE"),
    ("Istanbul", "TR"),
    ("Santos", "BR"),
    ("Shanghai", "CN"),
    ("Constanta", "RO"),
]


class RequirementInterpreter:
    """Interprets free-text buyer sourcing requests and merges structured criteria overrides."""

    @classmethod
    def _extract_pricing(
        cls,
        text: str,
        parsed_fields: list[str],
        default_currency: str = "USD",
    ) -> tuple[str, Decimal | None, Decimal | None, Decimal | None]:
        """Extract pricing parameters from text prompt with safe overflow and bounds protection."""
        currency = default_currency
        target_unit_price: Decimal | None = None
        max_unit_price: Decimal | None = None
        max_total_budget: Decimal | None = None

        # Currency
        for curr_code, curr_pattern in _CURRENCY_PATTERNS:
            if curr_pattern.search(text):
                currency = curr_code
                parsed_fields.append("currency")
                break

        # Unit Price
        price_match = _UNIT_PRICE_RE.search(text)
        if price_match:
            try:
                target_unit_price = Decimal(price_match.group("price"))
                parsed_fields.append("target_unit_price")
            except (ValueError, ArithmeticError, InvalidOperation, Overflow):
                pass

        # Max Price
        max_p_match = _MAX_PRICE_RE.search(text)
        if max_p_match:
            try:
                max_unit_price = Decimal(max_p_match.group("max_price"))
                parsed_fields.append("max_unit_price")
            except (ValueError, ArithmeticError, InvalidOperation, Overflow):
                pass

        # Total Budget
        budget_match = _MAX_BUDGET_RE.search(text)
        if budget_match:
            try:
                max_total_budget = Decimal(budget_match.group("budget").replace(",", ""))
                parsed_fields.append("max_total_budget")
            except (ValueError, ArithmeticError, InvalidOperation, Overflow):
                pass

        # If target price exists but max price doesn't, derive or set max price if budget allows
        if target_unit_price is not None and max_unit_price is None:
            try:
                max_unit_price = (target_unit_price * Decimal("1.20")).quantize(Decimal("0.01"))
            except (InvalidOperation, Overflow, ArithmeticError):
                # Fallback for huge numbers exceeding Decimal context precision (>28 digits)
                max_unit_price = target_unit_price

        return currency, target_unit_price, max_unit_price, max_total_budget

    @classmethod
    def interpret(
        cls,
        prompt: str | None = None,
        structured_overrides: dict[str, Any] | None = None,
    ) -> tuple[BuyerRequirements, list[str]]:
        """Extract structured parameters from prompt and compose with structured overrides.

        Returns (BuyerRequirements, list_of_parsed_field_names).
        """
        parsed_fields: list[str] = []
        text = (prompt or "").strip()

        # 1. Defaults
        title = "Buyer Sourcing Request"
        category = "Industrial Fasteners"
        description = text[:4000]
        materials: list[str] = []
        tolerances: str | None = None
        certifications: list[str] = []
        standards: list[str] = []
        quality_grade: str | None = None
        target_quantity = Decimal("1000")
        min_acceptable_quantity: Decimal | None = None
        unit = "units"
        packaging_preference: str | None = None
        target_unit_price: Decimal | None = None
        max_unit_price: Decimal | None = None
        max_total_budget: Decimal | None = None
        currency = "USD"
        destination_country_code = "DE"
        destination_port_or_city: str | None = None
        required_delivery_date: date | None = None
        max_lead_time_days: int | None = 30
        preferred_incoterm: Incoterm | str | None = Incoterm.DDP
        acceptable_incoterms: list[Incoterm | str] = [Incoterm.DDP, Incoterm.CIF]
        preferred_payment_term: PaymentMethodPreference | str | None = (
            PaymentMethodPreference.NET_30
        )
        min_warranty_months = 12
        inspection_requirement: InspectionPreference | str = (
            InspectionPreference.FACTORY_MILL_CERTIFICATE
        )

        # 2. Extract from Natural Language Text if provided
        if text:
            # Category
            for cat_name, keywords in _CATEGORY_KEYWORDS:
                for kw in keywords:
                    if re.search(rf"\b{re.escape(kw)}\b", text, re.IGNORECASE):
                        category = cat_name
                        parsed_fields.append("category")
                        break
                if "category" in parsed_fields:
                    break

            # Title
            first_sentence = re.split(r"[.\n]", text)[0].strip()
            if 5 <= len(first_sentence) <= 200:
                title = first_sentence
                parsed_fields.append("title")
            elif len(first_sentence) > 200:
                title = first_sentence[:197] + "..."
                parsed_fields.append("title")
            elif 5 <= len(text.split("\n")[0].strip()) <= 200:
                title = text.split("\n")[0].strip()
                parsed_fields.append("title")

            # Quantity and Unit
            qty_match = _QUANTITY_RE.search(text)
            if qty_match:
                try:
                    raw_qty = qty_match.group("qty").replace(",", "")
                    target_quantity = Decimal(raw_qty)
                    raw_unit = qty_match.group("unit").lower().strip()
                    # Normalize plural units
                    if raw_unit in ("boxes", "box"):
                        unit = "boxes"
                    elif raw_unit in ("pieces", "pcs", "pc"):
                        unit = "units"
                    elif raw_unit in ("metric tons", "tonnes", "tons", "mt"):
                        unit = "metric tons"
                    elif raw_unit in ("kilograms", "kg"):
                        unit = "kg"
                    elif raw_unit in ("yards", "yd"):
                        unit = "yards"
                    elif raw_unit in ("meters", "m"):
                        unit = "meters"
                    elif raw_unit in ("bags", "bag"):
                        unit = "bags"
                    else:
                        unit = raw_unit
                    parsed_fields.append("quantity")
                except (ValueError, ArithmeticError):
                    pass

            # Pricing
            currency, target_unit_price, max_unit_price, max_total_budget = cls._extract_pricing(
                text=text,
                parsed_fields=parsed_fields,
                default_currency=currency,
            )

            # Materials
            for mat in _KNOWN_MATERIALS:
                if re.search(rf"\b{re.escape(mat)}\b", text, re.IGNORECASE):
                    if mat not in materials:
                        materials.append(mat)
                        if "materials" not in parsed_fields:
                            parsed_fields.append("materials")

            # Tolerances
            tol_match = _TOLERANCE_RE.search(text)
            if tol_match:
                tolerances = tol_match.group(1).strip()
                parsed_fields.append("tolerances")

            # Certifications
            for cert in _KNOWN_CERTIFICATIONS:
                if re.search(rf"\b{re.escape(cert)}\b", text, re.IGNORECASE):
                    if cert not in certifications:
                        certifications.append(cert)
                        if "certifications" not in parsed_fields:
                            parsed_fields.append("certifications")

            # Standards
            for std in _KNOWN_STANDARDS:
                if re.search(rf"\b{re.escape(std)}\b", text, re.IGNORECASE):
                    if std not in standards:
                        standards.append(std)
                        if "standards" not in parsed_fields:
                            parsed_fields.append("standards")

            # Quality Grade
            for grade in _KNOWN_GRADES:
                if re.search(rf"\b{re.escape(grade)}\b", text, re.IGNORECASE):
                    quality_grade = grade
                    parsed_fields.append("quality_grade")
                    break

            # Lead Time Days
            lt_match = _LEAD_TIME_DAYS_RE.search(text)
            if lt_match:
                try:
                    num = int(lt_match.group("days"))
                    scale = lt_match.group("scale").lower()
                    if "week" in scale:
                        max_lead_time_days = num * 7
                    elif "month" in scale:
                        max_lead_time_days = num * 30
                    else:
                        max_lead_time_days = num
                    parsed_fields.append("max_lead_time_days")
                except ValueError:
                    pass

            # Delivery Date
            date_match = _DELIVERY_DATE_RE.search(text)
            if date_match:
                try:
                    y, m, d = (
                        int(date_match.group("year")),
                        int(date_match.group("month")),
                        int(date_match.group("day")),
                    )
                    parsed_date = date(y, m, d)
                    today = date.today()
                    if parsed_date >= today:
                        required_delivery_date = parsed_date
                        parsed_fields.append("required_delivery_date")
                except ValueError:
                    pass

            # Destination City / Port
            for port, code in _KNOWN_PORTS_CITIES:
                if re.search(rf"\b{re.escape(port)}\b", text, re.IGNORECASE):
                    destination_port_or_city = port
                    destination_country_code = code
                    parsed_fields.append("destination_port_or_city")
                    parsed_fields.append("destination_country_code")
                    break

            # Destination Country (if not resolved from city)
            if "destination_country_code" not in parsed_fields:
                for c_name, c_code in _COUNTRY_NAME_TO_CODE.items():
                    if re.search(rf"\b{re.escape(c_name)}\b", text, re.IGNORECASE):
                        destination_country_code = c_code
                        parsed_fields.append("destination_country_code")
                        break

            # Incoterms
            for incoterm_str, incoterm_enum in _INCOTERM_LOOKUP.items():
                if re.search(rf"\b{incoterm_str}\b", text, re.IGNORECASE):
                    preferred_incoterm = incoterm_enum
                    if incoterm_enum not in acceptable_incoterms:
                        acceptable_incoterms.append(incoterm_enum)
                    parsed_fields.append("preferred_incoterm")
                    break

            # Payment Terms
            if re.search(r"\b(net\s*30|30\s*days?\s*credit)\b", text, re.IGNORECASE):
                preferred_payment_term = PaymentMethodPreference.NET_30
                parsed_fields.append("preferred_payment_term")
            elif re.search(r"\b(net\s*60|60\s*days?\s*credit)\b", text, re.IGNORECASE):
                preferred_payment_term = PaymentMethodPreference.NET_60
                parsed_fields.append("preferred_payment_term")
            elif re.search(r"\b(escrow)\b", text, re.IGNORECASE):
                preferred_payment_term = PaymentMethodPreference.ESCROW
                parsed_fields.append("preferred_payment_term")
            elif re.search(r"\b(letter\s+of\s+credit|lc\s+at\s+sight|l\/c)\b", text, re.IGNORECASE):
                preferred_payment_term = PaymentMethodPreference.LC
                parsed_fields.append("preferred_payment_term")
            elif re.search(r"\b(30\/70|split)\b", text, re.IGNORECASE):
                preferred_payment_term = PaymentMethodPreference.SPLIT_30_70
                parsed_fields.append("preferred_payment_term")

            # Warranty
            w_match = _WARRANTY_MONTHS_RE.search(text)
            if w_match:
                try:
                    duration = int(w_match.group("duration"))
                    scale = w_match.group("scale").lower()
                    if "year" in scale:
                        min_warranty_months = duration * 12
                    else:
                        min_warranty_months = duration
                    parsed_fields.append("min_warranty_months")
                except ValueError:
                    pass

            # Inspection
            if re.search(
                r"\b(en\s*10204|mill\s+test|mill\s+certificate|3\.1\s+cert)\b", text, re.IGNORECASE
            ):
                inspection_requirement = InspectionPreference.FACTORY_MILL_CERTIFICATE
                parsed_fields.append("inspection_requirement")
            elif re.search(
                r"\b(third\s*party|sgs|tuv|bureau\s*veritas|pre-shipment\s+inspection)\b",
                text,
                re.IGNORECASE,
            ):
                inspection_requirement = InspectionPreference.PRE_SHIPMENT_THIRD_PARTY
                parsed_fields.append("inspection_requirement")
            elif re.search(r"\b(receiving\s+inspection|buyer\s+inspection)\b", text, re.IGNORECASE):
                inspection_requirement = InspectionPreference.BUYER_RECEIVING_INSPECTION
                parsed_fields.append("inspection_requirement")

        # 3. Apply Structured Overrides
        if structured_overrides:
            if isinstance(structured_overrides, dict):
                so = structured_overrides
            elif hasattr(structured_overrides, "model_dump"):
                so = structured_overrides.model_dump(exclude_unset=True)
            else:
                so = dict(structured_overrides)

            if "title" in so and so["title"]:
                title = str(so["title"])
                parsed_fields.append("title")
            if "category" in so and so["category"]:
                category = str(so["category"])
                parsed_fields.append("category")
            if "description" in so and so["description"]:
                description = str(so["description"])

            # Nested technical_specs
            if "technical_specs" in so and isinstance(so["technical_specs"], dict):
                ts = so["technical_specs"]
                if "materials" in ts and ts["materials"]:
                    materials = list(ts["materials"])
                    parsed_fields.append("materials")
                if "tolerances" in ts and ts["tolerances"] is not None:
                    tolerances = str(ts["tolerances"])
                    parsed_fields.append("tolerances")
                if "certifications" in ts and ts["certifications"]:
                    certifications = list(ts["certifications"])
                    parsed_fields.append("certifications")
                if "standards" in ts and ts["standards"]:
                    standards = list(ts["standards"])
                    parsed_fields.append("standards")
                if "quality_grade" in ts and ts["quality_grade"] is not None:
                    quality_grade = str(ts["quality_grade"])
                    parsed_fields.append("quality_grade")

            # Nested pricing
            if "pricing" in so and isinstance(so["pricing"], dict):
                pr = so["pricing"]
                if "target_unit_price" in pr and pr["target_unit_price"] is not None:
                    try:
                        target_unit_price = Decimal(str(pr["target_unit_price"]))
                    except (InvalidOperation, ValueError, TypeError) as exc:
                        raise ValueError(
                            f"Invalid target_unit_price: {pr['target_unit_price']}"
                        ) from exc
                    parsed_fields.append("target_unit_price")
                if "max_unit_price" in pr and pr["max_unit_price"] is not None:
                    try:
                        max_unit_price = Decimal(str(pr["max_unit_price"]))
                    except (InvalidOperation, ValueError, TypeError) as exc:
                        raise ValueError(f"Invalid max_unit_price: {pr['max_unit_price']}") from exc
                    parsed_fields.append("max_unit_price")
                if "max_total_budget" in pr and pr["max_total_budget"] is not None:
                    try:
                        max_total_budget = Decimal(str(pr["max_total_budget"]))
                    except (InvalidOperation, ValueError, TypeError) as exc:
                        raise ValueError(
                            f"Invalid max_total_budget: {pr['max_total_budget']}"
                        ) from exc
                    parsed_fields.append("max_total_budget")
                if "currency" in pr and pr["currency"]:
                    currency = str(pr["currency"]).upper()
                    parsed_fields.append("currency")

            # Nested quantity
            if "quantity" in so and isinstance(so["quantity"], dict):
                qr = so["quantity"]
                if "target_quantity" in qr and qr["target_quantity"] is not None:
                    try:
                        target_quantity = Decimal(str(qr["target_quantity"]))
                    except (InvalidOperation, ValueError, TypeError) as exc:
                        raise ValueError(
                            f"Invalid target_quantity: {qr['target_quantity']}"
                        ) from exc
                    parsed_fields.append("quantity")
                if "min_acceptable_quantity" in qr and qr["min_acceptable_quantity"] is not None:
                    try:
                        min_acceptable_quantity = Decimal(str(qr["min_acceptable_quantity"]))
                    except (InvalidOperation, ValueError, TypeError) as exc:
                        raise ValueError(
                            f"Invalid min_acceptable_quantity: {qr['min_acceptable_quantity']}"
                        ) from exc
                if "unit" in qr and qr["unit"]:
                    unit = str(qr["unit"])
                if "packaging_preference" in qr and qr["packaging_preference"] is not None:
                    packaging_preference = str(qr["packaging_preference"])

            # Nested delivery
            if "delivery" in so and isinstance(so["delivery"], dict):
                deliv = so["delivery"]
                if "destination_country_code" in deliv and deliv["destination_country_code"]:
                    destination_country_code = str(deliv["destination_country_code"]).upper()
                    parsed_fields.append("destination_country_code")
                if (
                    "destination_port_or_city" in deliv
                    and deliv["destination_port_or_city"] is not None
                ):
                    destination_port_or_city = str(deliv["destination_port_or_city"])
                    parsed_fields.append("destination_port_or_city")
                if (
                    "required_delivery_date" in deliv
                    and deliv["required_delivery_date"] is not None
                ):
                    rdd = deliv["required_delivery_date"]
                    if isinstance(rdd, str):
                        try:
                            parts = [int(p) for p in rdd.split("-")]
                            required_delivery_date = date(parts[0], parts[1], parts[2])
                        except (ValueError, TypeError, IndexError) as exc:
                            raise ValueError(f"Invalid required_delivery_date: {rdd}") from exc
                    elif isinstance(rdd, date):
                        required_delivery_date = rdd
                    parsed_fields.append("required_delivery_date")
                if "max_lead_time_days" in deliv and deliv["max_lead_time_days"] is not None:
                    try:
                        max_lead_time_days = int(deliv["max_lead_time_days"])
                    except (ValueError, TypeError) as exc:
                        raise ValueError(
                            f"Invalid max_lead_time_days: {deliv['max_lead_time_days']}"
                        ) from exc
                    parsed_fields.append("max_lead_time_days")

            # Nested commercial_terms
            if "commercial_terms" in so and isinstance(so["commercial_terms"], dict):
                ct = so["commercial_terms"]
                if "preferred_incoterm" in ct and ct["preferred_incoterm"]:
                    preferred_incoterm = ct["preferred_incoterm"]
                    parsed_fields.append("preferred_incoterm")
                if "acceptable_incoterms" in ct and ct["acceptable_incoterms"]:
                    acceptable_incoterms = list(ct["acceptable_incoterms"])
                if "preferred_payment_term" in ct and ct["preferred_payment_term"]:
                    preferred_payment_term = ct["preferred_payment_term"]
                    parsed_fields.append("preferred_payment_term")
                if "min_warranty_months" in ct and ct["min_warranty_months"] is not None:
                    try:
                        min_warranty_months = int(ct["min_warranty_months"])
                    except (ValueError, TypeError) as exc:
                        raise ValueError(
                            f"Invalid min_warranty_months: {ct['min_warranty_months']}"
                        ) from exc
                    parsed_fields.append("min_warranty_months")
                if "inspection_requirement" in ct and ct["inspection_requirement"]:
                    inspection_requirement = ct["inspection_requirement"]
                    parsed_fields.append("inspection_requirement")

        # 4. Fallback calculation if target price / budget is not provided
        if target_unit_price is None and max_total_budget is not None and target_quantity > 0:
            try:
                calculated = (max_total_budget / target_quantity).quantize(Decimal("0.01"))
                if calculated >= Decimal("0.05"):
                    target_unit_price = calculated
                    if max_unit_price is None:
                        max_unit_price = target_unit_price
            except (InvalidOperation, Overflow, ArithmeticError, ZeroDivisionError):
                if max_total_budget > 0:
                    target_unit_price = max_total_budget
                    if max_unit_price is None:
                        max_unit_price = target_unit_price

        # Build domain models
        tech_spec = TechnicalSpecification(
            materials=materials,
            tolerances=tolerances,
            certifications=certifications,
            standards=standards,
            quality_grade=quality_grade,
            notes=None,
        )

        pricing = PricingConstraint(
            target_unit_price=target_unit_price,
            max_unit_price=max_unit_price,
            max_total_budget=max_total_budget,
            currency=currency,
        )

        quantity = QuantityRequirement(
            target_quantity=target_quantity,
            min_acceptable_quantity=min_acceptable_quantity,
            unit=unit,
            packaging_preference=packaging_preference,
        )

        delivery = DeliveryConstraint(
            destination_country_code=destination_country_code,
            destination_port_or_city=destination_port_or_city,
            required_delivery_date=required_delivery_date,
            max_lead_time_days=max_lead_time_days,
        )

        comm_terms = CommercialTermsRequirement(
            preferred_incoterm=preferred_incoterm,
            acceptable_incoterms=acceptable_incoterms,
            preferred_payment_term=preferred_payment_term,
            min_warranty_months=min_warranty_months,
            inspection_requirement=inspection_requirement,
        )

        requirements = BuyerRequirements(
            title=title,
            category=category,
            description=description,
            technical_specs=tech_spec,
            pricing=pricing,
            quantity=quantity,
            delivery=delivery,
            commercial_terms=comm_terms,
            raw_prompt=prompt,
        )

        # Deduplicate parsed_fields while preserving order
        unique_parsed = list(dict.fromkeys(parsed_fields))
        return requirements, unique_parsed
