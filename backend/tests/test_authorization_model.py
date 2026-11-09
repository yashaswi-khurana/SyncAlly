"""Closed permission bundles and deal scope remain separate decisions."""

import unittest
from uuid import uuid4

from syncally.application.identity import ActorContext
from syncally.domain.organizations.authorization import expand_grants, validate_grants


class Deal:
    def __init__(self, buyer_organization_id, seller_organization_id):
        self.id = uuid4()
        self.buyer_organization_id = buyer_organization_id
        self.seller_organization_id = seller_organization_id


class AuthorizationModelTests(unittest.TestCase):
    def test_bundle_permissions_do_not_grant_deal_scope(self) -> None:
        organization_id = uuid4()
        deal = Deal(organization_id, uuid4())
        actor = ActorContext(
            user_id=uuid4(), organization_ids=frozenset({organization_id}),
            permissions_by_organization={organization_id: expand_grants(["DEAL_MEMBER"], [])},
        )
        self.assertFalse(actor.can_read_deal(deal))
        actor = ActorContext(
            user_id=actor.user_id, organization_ids=actor.organization_ids,
            permissions_by_organization=actor.permissions_by_organization,
            assigned_deals=frozenset({(organization_id, deal.id)}),
        )
        self.assertTrue(actor.has_deal_authority(deal, organization_id, "deal.edit_assigned"))
        self.assertFalse(actor.has_deal_authority(deal, organization_id, "payments.authorize"))

    def test_owner_has_full_org_scope_and_unknown_grants_are_rejected(self) -> None:
        organization_id = uuid4()
        deal = Deal(organization_id, uuid4())
        actor = ActorContext(user_id=uuid4(), organization_ids=frozenset({organization_id}), owned_organization_ids=frozenset({organization_id}))
        self.assertTrue(actor.has_deal_authority(deal, organization_id, "payments.authorize"))
        self.assertTrue(actor.can_read_deal(deal))
        with self.assertRaises(ValueError):
            validate_grants(["SUPERUSER"], [])


if __name__ == "__main__":
    unittest.main()
