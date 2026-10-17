import unittest
from uuid import uuid4

from fastapi import HTTPException

from syncally.api.deals import get_authorized_deal
from syncally.application.identity import ActorContext
from syncally.infrastructure.models import Deal


class DealAuthorizationTests(unittest.TestCase):
    def test_unknown_and_unauthorized_deals_have_the_same_response(self) -> None:
        actor = ActorContext(user_id=uuid4(), organization_ids=frozenset())
        existing_deal = Deal(
            id=uuid4(),
            buyer_organization_id=uuid4(),
            seller_organization_id=uuid4(),
            status="DRAFT",
        )

        class FakeSession:
            def __init__(self, deal: Deal | None) -> None:
                self.deal = deal

            def scalar(self, _query: object) -> Deal | None:
                return self.deal

        responses = []
        for deal in (None, existing_deal):
            with self.assertRaises(HTTPException) as raised:
                get_authorized_deal(uuid4(), actor, FakeSession(deal))
            responses.append((raised.exception.status_code, raised.exception.detail))

        self.assertEqual(responses[0], responses[1])
        self.assertEqual(responses[0], (404, "Deal not found"))