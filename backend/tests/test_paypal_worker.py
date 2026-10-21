import os
import unittest
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from threading import Event
from uuid import uuid4

import test_payment_intent_repository as fixtures
from sqlalchemy import create_engine, event, select, text
from sqlalchemy.orm import Session, sessionmaker

from syncally.application.invoicing import InvoiceFailure
from syncally.infrastructure.models import AgreementVersion, Base, OutboxEvent, PaymentIntent, User
from syncally.infrastructure.paypal.fake import FakeInvoiceClient
from syncally.infrastructure.paypal.worker import (
    ACTION_REQUIRED,
    SandboxMerchant,
    authorize_sandbox_issuance,
    dispatch_one_payment,
    operation_id,
)
from syncally.infrastructure.repositories.payments import authorize_payment_intent_in_transaction


class PaymentWorkerTests(unittest.TestCase):
    # Reuse the real committed-agreement fixture, without inheriting its tests.
    _seed_committed_agreement_with_milestone = (
        fixtures.PaymentIntentRepositoryTests._seed_committed_agreement_with_milestone
    )
    _command = fixtures.PaymentIntentRepositoryTests._command

    def setUp(self):
        fixtures.PaymentIntentRepositoryTests.setUp(self)
        self.factory = sessionmaker(self.engine)
        self.seller_user_id = self.session.scalar(
            select(User.id).where(User.email == "seller@example.com")
        )
        self.merchant = SandboxMerchant(
            self.seller_org_id, self.buyer_org_id, "seller@sandbox.example", "buyer@sandbox.example"
        )
        self.command = self._command()
        authorize_payment_intent_in_transaction(self.session, self.command)
        self.session.close()
        self.client = FakeInvoiceClient()
        self.now = datetime.now(UTC)
        self.transactions = 0
        event.listen(self.engine, "begin", self._begin)
        event.listen(self.engine, "commit", self._end)
        event.listen(self.engine, "rollback", self._end)
        self.client.before_call = lambda: self.assertEqual(
            self.transactions, 0, "HTTP inside DB transaction"
        )

    def _begin(self, *args):
        self.transactions += 1

    def _end(self, *args):
        self.transactions -= 1

    def tearDown(self):
        event.remove(self.engine, "begin", self._begin)
        event.remove(self.engine, "commit", self._end)
        event.remove(self.engine, "rollback", self._end)
        fixtures.PaymentIntentRepositoryTests.tearDown(self)

    def authorize(self):
        authorize_sandbox_issuance(
            self.factory, self.command.id, self.seller_user_id, self.merchant
        )

    def tick(self, seconds=600):
        self.now += timedelta(seconds=seconds)
        return dispatch_one_payment(self.factory, self.client, self.merchant, now=self.now)

    def state(self):
        with self.factory() as db:
            row = db.get(PaymentIntent, self.command.id)
            return row.status, row.provider_invoice_id, row.failure_code

    def test_create_send_and_get_are_separate_and_repeated_delivery_is_safe(self):
        self.authorize()
        self.tick()
        self.assertEqual(self.state()[0], "PROVIDER_CREATED")
        self.assertEqual([c[0] for c in self.client.calls], ["create"])
        self.tick()
        self.assertEqual(self.state()[0], "SEND_UNKNOWN")
        self.tick()
        self.assertEqual(self.state()[0], "SENT")
        self.assertFalse(self.tick())
        self.assertEqual([c[0] for c in self.client.calls], ["create", "get", "send", "get"])
        self.assertNotEqual(
            operation_id(self.command.id, "create"), operation_id(self.command.id, "send")
        )
        self.assertEqual(len(self.client.invoices), 1)

    def test_create_timeout_after_side_effect_finds_existing_invoice(self):
        self.authorize()
        self.client.after_mutation["create"] = InvoiceFailure("TIMEOUT", ambiguous=True)
        self.tick()
        self.assertEqual(self.state()[0], "CREATE_UNKNOWN")
        self.tick()
        self.assertEqual(self.state()[0], "PROVIDER_CREATED")
        self.tick()
        self.tick()
        self.assertEqual(
            [c[0] for c in self.client.calls], ["create", "find", "get", "send", "get"]
        )
        self.assertEqual(self.state()[0], "SENT")

    def test_send_timeout_reconciles_before_any_resend(self):
        self.authorize()
        self.tick()
        self.client.after_mutation["send"] = InvoiceFailure("TIMEOUT", ambiguous=True)
        self.tick()
        self.assertEqual(self.state()[0], "SEND_UNKNOWN")
        self.tick()
        self.assertEqual(self.state()[0], "SENT")
        self.assertEqual(len([c for c in self.client.calls if c[0] == "send"]), 1)

    def test_crash_after_provider_create_recovers_after_lease(self):
        self.authorize()
        self.client.after_mutation["create"] = RuntimeError("process died")
        with self.assertRaises(RuntimeError):
            self.tick()
        self.assertEqual(self.state()[0], "CREATE_UNKNOWN")
        self.assertFalse(self.tick(seconds=1))
        self.tick()
        self.assertEqual([c[0] for c in self.client.calls], ["create", "find"])
        self.assertEqual(self.state()[0], "PROVIDER_CREATED")

    def test_unresolved_create_never_recreates_and_exhausts_budget(self):
        self.authorize()
        self.client.failures["create"] = InvoiceFailure("TIMEOUT", ambiguous=True)
        self.tick()
        for _ in range(9):
            self.tick()
        self.assertEqual(self.state()[0], ACTION_REQUIRED)
        self.assertEqual(len([c for c in self.client.calls if c[0] == "create"]), 1)

    def test_explicit_transient_rejection_retries_with_identical_identity(self):
        self.authorize()
        self.client.failures["create"] = InvoiceFailure("RATE_LIMIT")
        self.tick()
        self.assertEqual(self.state()[0], "AUTHORIZED")
        self.assertFalse(self.tick(seconds=0))
        self.tick()
        self.assertEqual(self.client.calls[0], self.client.calls[1])

    def test_permanent_failure_stops_with_manual_path(self):
        self.authorize()
        self.client.failures["create"] = InvoiceFailure("INVALID_MERCHANT", permanent=True)
        self.tick()
        self.assertEqual(self.state()[0], ACTION_REQUIRED)
        self.assertFalse(self.tick())

    def test_no_seller_authorization_never_calls_provider(self):
        self.tick()
        self.assertEqual(self.state()[0], ACTION_REQUIRED)
        self.assertEqual(self.client.calls, [])

    def test_buyer_cannot_authorize_seller_issuance(self):
        with self.assertRaises(InvoiceFailure):
            authorize_sandbox_issuance(
                self.factory, self.command.id, self.buyer_user_id, self.merchant
            )
        self.assertEqual(self.client.calls, [])

    def test_changed_committed_data_fails_closed(self):
        self.authorize()
        with self.factory() as db, db.begin():
            db.get(AgreementVersion, self.agreement_version_id).status = "SUPERSEDED"
        self.tick()
        self.assertEqual(self.state()[0], ACTION_REQUIRED)
        self.assertEqual(self.client.calls, [])

    def test_changed_recipient_or_merchant_binding_fails_closed(self):
        self.authorize()
        self.merchant = replace(self.merchant, buyer_email="other@sandbox.example")
        self.tick()
        self.assertEqual(self.state()[0], ACTION_REQUIRED)
        self.assertEqual(self.client.calls, [])

    def _reject_provider_change(self, change):
        self.authorize()
        self.tick()
        key = next(iter(self.client.invoices))
        self.client.invoices[key] = replace(self.client.invoices[key], **change)
        self.tick()
        self.assertEqual(self.state()[0], ACTION_REQUIRED)
        self.assertFalse(any(c[0] == "send" for c in self.client.calls))

    def test_wrong_provider_amount_never_sends(self):
        self._reject_provider_change({"amount": Decimal("11")})

    def test_wrong_provider_currency_never_sends(self):
        self._reject_provider_change({"currency": "EUR"})

    def test_wrong_provider_reference_never_sends(self):
        self._reject_provider_change({"reference": str(uuid4())})

    def test_wrong_provider_recipient_never_sends(self):
        self._reject_provider_change({"recipient_email": "other@example.com"})

    def test_unknown_provider_status_never_marks_paid(self):
        self.authorize()
        self.tick()
        key = next(iter(self.client.invoices))
        self.client.invoices[key] = replace(self.client.invoices[key], status="SURPRISE")
        self.tick()
        self.assertEqual(self.state()[0], ACTION_REQUIRED)

    def test_provider_paid_is_left_for_settlement_reconciler(self):
        self.authorize()
        self.tick()
        key = next(iter(self.client.invoices))
        self.client.invoices[key] = replace(self.client.invoices[key], status="PAID")
        self.tick()
        self.assertEqual(self.state()[0], "SENT")

    def test_seller_authorization_is_idempotent_and_contains_no_credentials(self):
        self.authorize()
        self.authorize()
        with self.factory() as db:
            row = db.scalar(select(OutboxEvent).where(OutboxEvent.aggregate_id == self.command.id))
            self.assertEqual(
                row.payload["issuance"]["create_operation_id"],
                operation_id(self.command.id, "create"),
            )
            self.assertNotIn("secret", str(row.payload).lower())

    def test_revoked_seller_membership_stops_issuance(self):
        self.authorize()
        from syncally.infrastructure.models import OrganizationMember

        with self.factory() as db, db.begin():
            member = db.scalar(
                select(OrganizationMember).where(OrganizationMember.user_id == self.seller_user_id)
            )
            member.status = "REVOKED"
        self.tick()
        self.assertEqual(self.state()[0], ACTION_REQUIRED)
        self.assertEqual(self.client.calls, [])

    def test_stale_worker_result_cannot_overwrite_newer_command(self):
        self.authorize()

        def newer_command():
            self.assertEqual(self.transactions, 0)
            with self.factory() as db, db.begin():
                intent = db.get(PaymentIntent, self.command.id)
                intent.status = "CANCELLED"
                intent.version += 1

        self.client.before_call = newer_command
        self.tick()
        self.assertEqual(self.state()[0], "CANCELLED")

    def test_crash_after_send_reconciles_instead_of_resending(self):
        self.authorize()
        self.tick()
        self.client.after_mutation["send"] = RuntimeError("crashed")
        with self.assertRaises(RuntimeError):
            self.tick()
        self.tick()
        self.assertEqual(self.state()[0], "SENT")
        self.assertEqual(len([c for c in self.client.calls if c[0] == "send"]), 1)

    def test_transient_get_failure_does_not_repeat_create(self):
        self.authorize()
        self.tick()
        self.client.failures["get"] = InvoiceFailure("UNAVAILABLE")
        self.tick()
        self.tick()
        self.assertEqual([c[0] for c in self.client.calls], ["create", "get", "get", "send"])

    def test_send_failure_before_mutation_gets_draft_again_before_retry(self):
        self.authorize()
        self.tick()
        self.client.failures["send"] = InvoiceFailure("TIMEOUT", ambiguous=True)
        self.tick()
        self.tick()
        self.tick()
        self.assertEqual(self.state()[0], "SENT")
        self.assertEqual(
            [c[0] for c in self.client.calls], ["create", "get", "send", "get", "send", "get"]
        )

    def test_replayed_event_never_downgrades_settled_intent(self):
        with self.factory() as db, db.begin():
            db.get(PaymentIntent, self.command.id).status = "PAID"
        self.tick()
        self.assertEqual(self.state()[0], "PAID")
        self.assertEqual(self.client.calls, [])

    def test_cancelled_deal_stops_new_invoice(self):
        self.authorize()
        from syncally.infrastructure.models import Deal

        with self.factory() as db, db.begin():
            db.get(Deal, self.command.deal_id).status = "CANCELLED"
        self.tick()
        self.assertEqual(self.state()[0], ACTION_REQUIRED)
        self.assertEqual(self.client.calls, [])


@unittest.skipUnless(
    os.environ.get("TEST_POSTGRES_URL"), "Set TEST_POSTGRES_URL for PostgreSQL locking tests"
)
class PostgresPaymentWorkerTests(unittest.TestCase):
    _seed_committed_agreement_with_milestone = (
        fixtures.PaymentIntentRepositoryTests._seed_committed_agreement_with_milestone
    )
    _command = fixtures.PaymentIntentRepositoryTests._command

    def setUp(self):
        self.engine = create_engine(
            os.environ["TEST_POSTGRES_URL"], connect_args={"options": "-c statement_timeout=5000"}
        )
        self.schema = "paypal_test_" + uuid4().hex
        with self.engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{self.schema}"'))
        self.scoped = self.engine.execution_options(schema_translate_map={None: self.schema})
        Base.metadata.create_all(self.scoped)
        self.session = Session(self.scoped)
        self._seed_committed_agreement_with_milestone()
        self.command = self._command()
        self.seller_user_id = self.session.scalar(
            select(User.id).where(User.email == "seller@example.com")
        )
        authorize_payment_intent_in_transaction(self.session, self.command)
        self.session.close()
        self.factory = sessionmaker(self.scoped)
        self.merchant = SandboxMerchant(
            self.seller_org_id, self.buyer_org_id, "seller@sandbox.example", "buyer@sandbox.example"
        )
        authorize_sandbox_issuance(
            self.factory, self.command.id, self.seller_user_id, self.merchant
        )
        self.client = FakeInvoiceClient()
        self.now = datetime.now(UTC)

    def tearDown(self):
        self.session.close()
        with self.engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{self.schema}" CASCADE'))
        self.engine.dispose()

    def test_locked_event_is_skipped_and_rollback_releases_it(self):
        with self.factory() as holder:
            holder.scalar(
                select(OutboxEvent)
                .where(OutboxEvent.aggregate_id == self.command.id)
                .with_for_update()
            )
            self.assertFalse(
                dispatch_one_payment(self.factory, self.client, self.merchant, now=self.now)
            )
            self.assertEqual(self.client.calls, [])
            holder.rollback()
        self.assertTrue(
            dispatch_one_payment(self.factory, self.client, self.merchant, now=self.now)
        )
        self.assertEqual([call[0] for call in self.client.calls], ["create"])

    def test_second_worker_cannot_create_while_first_is_in_http(self):
        entered, release = Event(), Event()
        original_create = self.client.create

        def blocked_create(payload, operation_id):
            result = original_create(payload, operation_id)
            entered.set()
            if not release.wait(10):
                raise RuntimeError("test wait timed out")
            return result

        self.client.create = blocked_create
        with ThreadPoolExecutor(max_workers=1) as executor:
            first = executor.submit(
                dispatch_one_payment, self.factory, self.client, self.merchant, now=self.now
            )
            try:
                self.assertTrue(entered.wait(5))
                self.assertFalse(
                    dispatch_one_payment(self.factory, self.client, self.merchant, now=self.now)
                )
                with self.factory() as db:
                    self.assertEqual(
                        db.get(PaymentIntent, self.command.id).status, "CREATE_UNKNOWN"
                    )
            finally:
                release.set()
            self.assertTrue(first.result(timeout=5))
        self.assertEqual(len(self.client.invoices), 1)
        self.assertEqual([call[0] for call in self.client.calls], ["create"])

    def test_expired_claim_fences_late_result_and_reconciles_existing_invoice(self):
        entered, release = Event(), Event()
        original_create = self.client.create

        def blocked_create(payload, operation_id):
            result = original_create(payload, operation_id)
            entered.set()
            if not release.wait(10):
                raise RuntimeError("test wait timed out")
            return result

        self.client.create = blocked_create
        with ThreadPoolExecutor(max_workers=1) as executor:
            first = executor.submit(
                dispatch_one_payment, self.factory, self.client, self.merchant, now=self.now
            )
            try:
                self.assertTrue(entered.wait(5))
                self.assertTrue(
                    dispatch_one_payment(
                        self.factory,
                        self.client,
                        self.merchant,
                        now=self.now + timedelta(seconds=601),
                    )
                )
            finally:
                release.set()
            self.assertTrue(first.result(timeout=5))
        with self.factory() as db:
            self.assertEqual(db.get(PaymentIntent, self.command.id).status, "PROVIDER_CREATED")
            self.assertEqual(db.get(PaymentIntent, self.command.id).version, 4)
        self.assertEqual([call[0] for call in self.client.calls], ["create", "find"])
        self.assertEqual(len(self.client.invoices), 1)
