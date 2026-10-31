"""Versioned synthetic human choices and source text; no provider calls."""

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid5

from syncally.domain.ai.contracts import ProposedTerms

FIXTURE_KEY = "curated-buyer-seller"
FIXTURE_VERSION = 1
FIXTURE_TIME = datetime(2026, 10, 30, 9, 0, tzinfo=UTC)
_NAMESPACE = UUID("ce438e74-91b0-46b8-af75-86ac1f41fbd1")


def fixture_id(name: str) -> UUID:
    return uuid5(_NAMESPACE, f"{FIXTURE_KEY}:v{FIXTURE_VERSION}:{name}")


DEMO_DEAL_ID = fixture_id("deal")
CURATED_HUMAN_CHOICES = ProposedTerms(
    schema_version=1,
    description="Stainless steel bolts",
    quantity=Decimal("120"),
    unit="box",
    unit_price=Decimal("25.00"),
    currency="USD",
    delivery_destination="Toronto warehouse",
    delivery_date=date(2026, 12, 1),
)

MESSAGES = (
    (
        "buyer",
        "SHAREABLE",
        "We need stainless steel bolts for our winter assembly run: 120 boxes. Can you deliver to Toronto warehouse by 2026-12-01?",
    ),
    (
        "seller",
        "SHAREABLE",
        "We can supply 120 boxes of stainless steel bolts at USD 25.00 per box. Delivery to Toronto warehouse by 2026-12-01 is feasible. Payment is due when seller invoices; please review before approving.",
    ),
    (
        "buyer",
        "SHAREABLE",
        "Thanks. Please prepare a draft for 120 boxes at USD 25.00 per box, delivered to Toronto warehouse by 2026-12-01. This is not an approval; our procurement team still needs to review.",
    ),
    (
        "seller",
        "SHAREABLE",
        "Draft only. We will wait for both parties to approve the same version before any shipment or invoice action.",
    ),
    (
        "buyer",
        "PRIVATE",
        "Buyer internal note: our reserve ceiling is USD 28.00 per box. Do not share the reserve with the supplier.",
    ),
    (
        "seller",
        "PRIVATE",
        "Seller internal note: our floor is USD 22.00 per box. Keep the margin private and do not invoice an unapproved draft.",
    ),
)

CANDIDATES = (
    (0, "item_description", "stainless steel bolts", None, "stainless steel bolts"),
    (0, "quantity", "120", "box", "120 boxes"),
    (0, "delivery_destination", "Toronto warehouse", None, "Toronto warehouse"),
    (0, "delivery_date", "2026-12-01", None, "2026-12-01"),
    (1, "unit_price", "25.00", "USD", "USD 25.00 per box"),
    (1, "payment_obligation", "when seller invoices", None, "Payment is due when seller invoices"),
    (4, "unit_price", "28.00", "USD", "USD 28.00 per box"),
    (5, "unit_price", "22.00", "USD", "USD 22.00 per box"),
)
