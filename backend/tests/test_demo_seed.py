import asyncio
import concurrent.futures
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx
from sqlalchemy import Index, MetaData, create_engine, func, inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from syncally.api.auth import _encode_access_token
from syncally.api.main import app
from syncally.application.outbox import WorkflowStartOutcome, WorkflowStartTransientError
from syncally.application.passwords import verify_password
from syncally.cli.demo_fixture import DEMO_DEAL_ID, FIXTURE_KEY, FIXTURE_TIME, fixture_id
from syncally.cli.seed_demo import (
    DEMO_IDENTITIES,
    DemoCollisionError,
    initialize_offline_database,
    main,
    seed_demo_data,
)
from syncally.config import settings
from syncally.domain.agreements.trade_terms import TradeTerms
from syncally.infrastructure.database import create_database_engine, get_db
from syncally.infrastructure.models import (
    AgreementVersion,
    Approval,
    Base,
    Constraint,
    Conversation,
    Deal,
    DemoFixture,
    Message,
    NegotiationSession,
    Obligation,
    Organization,
    OrganizationMember,
    OutboxEvent,
    PaymentIntent,
    PaymentMilestone,
    User,
)
from syncally.infrastructure.outbox import dispatch_one_pending_event
from syncally.infrastructure.payment_schema import SQLITE_PAYMENT_IDENTITY_TRIGGER


class DemoSeedTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.original_app_env = settings.app_env
        settings.app_env = "test"

    def tearDown(self) -> None:
        settings.app_env = self.original_app_env
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_seed_creates_demo_users_orgs_and_admin_memberships(self) -> None:
        passwords = ("buyer-password-123", "seller-password-456")

        seed_demo_data(self.db, passwords)

        users = list(self.db.scalars(select(User).order_by(User.email)))
        organizations = list(
            self.db.scalars(select(Organization).order_by(Organization.legal_name))
        )
        memberships = list(self.db.scalars(select(OrganizationMember)))
        self.assertEqual(
            [user.email for user in users], [identity.email for identity in DEMO_IDENTITIES]
        )
        self.assertEqual(len(organizations), 2)
        self.assertEqual(len(memberships), 2)
        self.assertEqual({membership.role for membership in memberships}, {"ADMIN"})
        self.assertEqual({membership.status for membership in memberships}, {"ACTIVE"})
        self.assertTrue(
            all(user.password_hash and user.password_hash.startswith("scrypt$") for user in users)
        )
        self.assertTrue(verify_password(passwords[0], users[0].password_hash))
        self.assertTrue(verify_password(passwords[1], users[1].password_hash))

    def test_seed_is_idempotent_and_preserves_existing_passwords(self) -> None:
        passwords = ("buyer-password-123", "seller-password-456")
        seed_demo_data(self.db, passwords)
        existing_hashes = {user.email: user.password_hash for user in self.db.scalars(select(User))}

        seed_demo_data(self.db, ("ignored-new-buyer-password", "ignored-new-seller-password"))

        self.assertEqual(self.db.scalar(select(func.count()).select_from(User)), 2)
        self.assertEqual(self.db.scalar(select(func.count()).select_from(Organization)), 2)
        self.assertEqual(self.db.scalar(select(func.count()).select_from(OrganizationMember)), 2)
        self.assertEqual(
            {user.email: user.password_hash for user in self.db.scalars(select(User))},
            existing_hashes,
        )

    def test_seed_refuses_non_local_environment_and_register_is_not_public(self) -> None:
        settings.app_env = "production"
        with self.assertRaises(RuntimeError):
            seed_demo_data(self.db, ("buyer-password-123", "seller-password-456"))

        self.assertNotIn("/auth/register", app.openapi()["paths"])


class PersistentDemoSeedTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.engine = create_database_engine(f"sqlite:///{Path(self.directory.name) / 'demo.db'}")
        self.env = patch.object(settings, "app_env", "test")
        self.env.start()
        initialize_offline_database(self.engine)
        self.passwords = ("buyer-test-password", "seller-test-password")

    def tearDown(self) -> None:
        self.env.stop()
        self.engine.dispose()
        self.directory.cleanup()

    def _snapshot(self) -> dict:
        with Session(self.engine) as db:
            return {
                table.name: [
                    tuple(row)
                    for row in db.execute(select(table).order_by(*table.primary_key.columns))
                ]
                for table in Base.metadata.sorted_tables
            }

    def _seed(self, *, reset=False) -> None:
        with Session(self.engine) as db:
            seed_demo_data(db, self.passwords, reset=reset)

    def test_setup_twice_reset_twice_preserves_exact_ids_content_and_passwords(self) -> None:
        self._seed()
        original = self._snapshot()
        self._seed()
        self.assertEqual(self._snapshot(), original)
        self._seed(reset=True)
        self.assertEqual(self._snapshot(), original)
        self._seed(reset=True)
        self.assertEqual(self._snapshot(), original)
        initialize_offline_database(self.engine)
        with Session(self.engine) as db:
            self.assertEqual(db.scalar(text("PRAGMA foreign_keys")), 1)
            self.assertEqual(db.scalar(select(func.count()).select_from(Deal)), 1)
            self.assertEqual(db.get(Deal, DEMO_DEAL_ID).updated_at, FIXTURE_TIME.replace(tzinfo=None))
            self.assertEqual(db.scalar(select(NegotiationSession)).updated_at, FIXTURE_TIME.replace(tzinfo=None))
            self.assertEqual(db.scalar(select(func.count()).select_from(Conversation)), 2)
            self.assertEqual(db.scalar(select(func.count()).select_from(Message)), 6)
            self.assertEqual(db.scalar(select(func.count()).select_from(Constraint)), 8)
            agreement = db.scalar(select(AgreementVersion))
            self.assertEqual(agreement.status, "PENDING_APPROVAL")
            self.assertIsNone(agreement.committed_at)
            self.assertEqual(
                TradeTerms.from_canonical_json(agreement.canonical_terms_json).terms_hash,
                agreement.terms_hash,
            )
            for candidate in db.scalars(select(Constraint)):
                self.assertEqual(candidate.status, "EXTRACTED")
                self.assertIsNone(candidate.confirmed_at)
                self.assertIsNone(candidate.confirmed_by)
                source = db.get(Message, candidate.source_message_id)
                self.assertIn(candidate.source_span, source.body)
                self.assertEqual(candidate.visibility, source.visibility)
                self.assertEqual(
                    candidate.owner_organization_id,
                    db.get(Conversation, source.conversation_id).participant_organization_id,
                )
            for model in (Approval, Obligation, PaymentMilestone, PaymentIntent, OutboxEvent):
                self.assertEqual(db.scalar(select(func.count()).select_from(model)), 0)

    def test_reseed_failure_rolls_back_deletion_and_identity_changes(self) -> None:
        self._seed()
        with Session(self.engine) as db:
            db.scalar(
                select(User).where(User.email == DEMO_IDENTITIES[1].email)
            ).status = "SUSPENDED"
            db.commit()
        original = self._snapshot()
        with patch(
            "syncally.cli.seed_demo._create_fixture", side_effect=RuntimeError("scripted failure")
        ):
            with self.assertRaisesRegex(RuntimeError, "scripted failure"):
                self._seed(reset=True)
        self.assertEqual(self._snapshot(), original)

    def test_committed_reset_refuses_and_preserves_all_rows_and_passwords(self) -> None:
        self._seed()
        for status in ("COMMITTED", "AGREED", "EXECUTING", "COMPLETED", "DISPUTED"):
            with self.subTest(status=status):
                with Session(self.engine) as db:
                    db.get(Deal, DEMO_DEAL_ID).status = status
                    db.commit()
                original = self._snapshot()
                with patch("syncally.cli.seed_demo._delete_scoped") as deletion:
                    with self.assertRaisesRegex(DemoCollisionError, "history retained"):
                        self._seed(reset=True)
                    deletion.assert_not_called()
                self.assertEqual(self._snapshot(), original)

    def test_approval_obligation_and_milestone_each_refuse_before_deletion(self) -> None:
        self._seed()
        with Session(self.engine) as db:
            deal = db.get(Deal, DEMO_DEAL_ID)
            agreement = db.get(AgreementVersion, fixture_id("agreement"))
            rows = (
                Approval(
                    deal_id=deal.id, agreement_version_id=agreement.id,
                    organization_id=deal.buyer_organization_id,
                    user_id=agreement.created_by, decision="APPROVED", terms_hash=agreement.terms_hash,
                ),
                Obligation(
                    deal_id=deal.id, agreement_version_id=agreement.id,
                    obligation_type="PAYMENT", owner_organization_id=deal.buyer_organization_id,
                    counterparty_organization_id=deal.seller_organization_id,
                ),
                PaymentMilestone(
                    deal_id=deal.id, agreement_version_id=agreement.id, sequence_number=1,
                    payer_organization_id=deal.buyer_organization_id, amount=25, currency="USD",
                    trigger_type="ON_COMMIT", due_condition="On commit",
                ),
            )
        for row in rows:
            with self.subTest(model=row.__tablename__):
                with Session(self.engine) as db:
                    db.add(row)
                    db.commit()
                original = self._snapshot()
                with patch("syncally.cli.seed_demo._delete_scoped") as deletion:
                    with self.assertRaisesRegex(DemoCollisionError, row.__tablename__):
                        self._seed(reset=True)
                    deletion.assert_not_called()
                self.assertEqual(self._snapshot(), original)
                with Session(self.engine) as db:
                    db.delete(row)
                    db.commit()

    def test_approved_agreement_refuses_without_approval_rows(self) -> None:
        self._seed()
        for status in ("APPROVED", "COMMITTED"):
            with self.subTest(status=status):
                with Session(self.engine) as db:
                    db.get(AgreementVersion, fixture_id("agreement")).status = status
                    db.commit()
                original = self._snapshot()
                with patch("syncally.cli.seed_demo._delete_scoped") as deletion:
                    with self.assertRaisesRegex(DemoCollisionError, "approved work"):
                        self._seed(reset=True)
                    deletion.assert_not_called()
                self.assertEqual(self._snapshot(), original)

    def test_fresh_password_provisioning_failure_rolls_back_both_identities(self) -> None:
        original = self._snapshot()
        with Session(self.engine) as db:
            with self.assertRaises(ValueError):
                seed_demo_data(db, (self.passwords[0], "short"))
        self.assertEqual(self._snapshot(), original)

    def test_cli_committed_reset_refuses_without_prompt_or_mutation(self) -> None:
        self._seed()
        with Session(self.engine) as db:
            db.scalar(select(AgreementVersion)).committed_at = FIXTURE_TIME
            db.commit()
        original = self._snapshot()
        with (
            patch("syncally.cli.seed_demo.SessionLocal", lambda: Session(self.engine)),
            patch("syncally.cli.seed_demo.getpass.getpass", side_effect=AssertionError("unexpected prompt")),
            patch("builtins.print") as output,
        ):
            with self.assertRaisesRegex(SystemExit, "history retained"):
                main(["--reset"])
            output.assert_not_called()
        self.assertEqual(self._snapshot(), original)

    def test_reset_refuses_while_generic_dispatch_is_inside_external_call(self) -> None:
        self._seed()
        with Session(self.engine) as db:
            event = OutboxEvent(
                aggregate_type="deal", aggregate_id=DEMO_DEAL_ID,
                event_type="DEAL_NOTIFICATION",
                payload={"deal_id": str(DEMO_DEAL_ID), "record_id": str(DEMO_DEAL_ID),
                         "kind": "DEAL_CREATED"},
            )
            db.add(event)
            db.commit()
            event_id = event.id
        entered, release = threading.Event(), threading.Event()
        test = self

        class PausedStarter:
            def start_deal_workflow(self, **kwargs):
                with Session(test.engine) as observer:
                    row = observer.get(OutboxEvent, event_id)
                    test.assertIsNotNone(row.dispatch_started_at)
                    test.assertEqual(row.retry_count, 0)
                entered.set()
                if not release.wait(timeout=5):
                    raise AssertionError("reset did not finish during the external call")
                return WorkflowStartOutcome.STARTED

        def dispatch():
            with Session(self.engine) as db:
                return dispatch_one_pending_event(db, PausedStarter())

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(dispatch)
            try:
                self.assertTrue(entered.wait(timeout=5), "starter did not observe a durable claim")
                with Session(self.engine) as competing:
                    self.assertFalse(dispatch_one_pending_event(competing, PausedStarter()))
                original = self._snapshot()
                with self.assertRaisesRegex(DemoCollisionError, "external dispatch work"):
                    self._seed(reset=True)
                self.assertEqual(self._snapshot(), original)
            finally:
                release.set()
            self.assertTrue(future.result(timeout=5))
        with Session(self.engine) as db:
            self.assertEqual(db.get(OutboxEvent, event_id).status, "DELIVERED")

    def test_reset_inside_starter_and_after_interruption_retains_history(self) -> None:
        self._seed()
        with Session(self.engine) as db:
            event = OutboxEvent(
                aggregate_type="deal", aggregate_id=DEMO_DEAL_ID,
                event_type="DEAL_NOTIFICATION",
                payload={"deal_id": str(DEMO_DEAL_ID), "record_id": str(DEMO_DEAL_ID),
                         "kind": "DEAL_CREATED"},
            )
            db.add(event)
            db.commit()
            event_id = event.id
        refusals = []
        test = self

        class InterruptedStarter:
            def start_deal_workflow(self, **kwargs):
                try:
                    test._seed(reset=True)
                except DemoCollisionError:
                    refusals.append(True)
                raise KeyboardInterrupt("interrupted during external dispatch")

        with Session(self.engine) as db:
            with self.assertRaises(KeyboardInterrupt):
                dispatch_one_pending_event(db, InterruptedStarter())
        self.assertEqual(refusals, [True])
        with Session(self.engine) as db:
            row = db.get(OutboxEvent, event_id)
            self.assertIsNotNone(row.dispatch_started_at)
            self.assertEqual(row.retry_count, 0)
            row.next_attempt_at = FIXTURE_TIME
            db.commit()
        original = self._snapshot()
        with self.assertRaisesRegex(DemoCollisionError, "external dispatch work"):
            self._seed(reset=True)
        self.assertEqual(self._snapshot(), original)

    def test_reset_refuses_durable_attempt_after_failed_and_manually_requeued_dispatch(self) -> None:
        self._seed()
        with Session(self.engine) as db:
            event = OutboxEvent(
                aggregate_type="deal", aggregate_id=DEMO_DEAL_ID,
                event_type="DEAL_NOTIFICATION",
                payload={"deal_id": str(DEMO_DEAL_ID), "record_id": str(DEMO_DEAL_ID),
                         "kind": "DEAL_CREATED"},
            )
            db.add(event)
            db.commit()
            event_id = event.id

        class UnavailableStarter:
            def start_deal_workflow(self, **kwargs):
                raise WorkflowStartTransientError("scripted outage")

        with Session(self.engine) as db:
            self.assertTrue(dispatch_one_pending_event(db, UnavailableStarter()))
            row = db.get(OutboxEvent, event_id)
            self.assertEqual(row.retry_count, 1)
            self.assertIsNotNone(row.dispatch_started_at)
        original = self._snapshot()
        with self.assertRaisesRegex(DemoCollisionError, "external dispatch work"):
            self._seed(reset=True)
        self.assertEqual(self._snapshot(), original)
        with Session(self.engine) as db:
            row = db.get(OutboxEvent, event_id)
            row.retry_count = 0
            row.next_attempt_at = None
            row.error_detail = None
            db.commit()
        original = self._snapshot()
        with self.assertRaisesRegex(DemoCollisionError, "external dispatch work"):
            self._seed(reset=True)
        self.assertEqual(self._snapshot(), original)

    def test_reset_refuses_external_outbox_work_and_preserves_all_rows(self) -> None:
        self._seed()
        with Session(self.engine) as db:
            event = OutboxEvent(
                aggregate_type="agreement",
                aggregate_id=fixture_id("agreement"),
                event_type="DEAL_NOTIFICATION",
                payload={"deal_id": str(DEMO_DEAL_ID), "kind": "MESSAGE_RECEIVED"},
            )
            db.add(event)
            db.commit()
            event_id = event.id
        for event_type, status, retry_count, delivered_at in (
            ("DEAL_NOTIFICATION", "PROCESSING", 0, None),
            ("DEAL_NOTIFICATION", "DELIVERED", 0, FIXTURE_TIME),
            ("DEAL_NOTIFICATION", "PENDING", 1, None),
            ("DEAL_NOTIFICATION", "PENDING", 0, FIXTURE_TIME),
            ("PAYMENT_INTENT_AUTHORIZED", "PENDING", 0, None),
            ("PAYPAL_WEBHOOK_RECONCILIATION_REQUESTED", "PENDING", 0, None),
            ("GMAIL_SEND", "PENDING", 0, None),
            ("UNKNOWN_EXTERNAL_WORK", "PENDING", 0, None),
        ):
            with self.subTest(event_type=event_type, status=status, retry_count=retry_count):
                with Session(self.engine) as db:
                    event = db.get(OutboxEvent, event_id)
                    event.event_type, event.status = event_type, status
                    event.retry_count, event.delivered_at = retry_count, delivered_at
                    db.commit()
                original = self._snapshot()
                with patch("syncally.cli.seed_demo._delete_scoped") as deletion:
                    with self.assertRaisesRegex(DemoCollisionError, "external dispatch"):
                        self._seed(reset=True)
                    deletion.assert_not_called()
                self.assertEqual(self._snapshot(), original)

    def test_reset_allows_untouched_queued_workflow_wakeup(self) -> None:
        self._seed()
        original = self._snapshot()
        for kind in ("DEAL_CREATED", "MESSAGE_RECEIVED", "CONSTRAINT_CHANGED", "PROPOSAL_SUBMITTED"):
            with self.subTest(kind=kind):
                with Session(self.engine) as db:
                    db.add(OutboxEvent(
                        aggregate_type="deal",
                        aggregate_id=DEMO_DEAL_ID,
                        event_type="DEAL_NOTIFICATION",
                        payload={"deal_id": str(DEMO_DEAL_ID), "kind": kind, "record_id": str(fixture_id("message:0"))},
                    ))
                    db.commit()
                self._seed(reset=True)
                self.assertEqual(self._snapshot(), original)

    def test_reset_refuses_queued_payment_and_approval_workflow_notifications(self) -> None:
        self._seed()
        with Session(self.engine) as db:
            event = OutboxEvent(
                aggregate_type="deal", aggregate_id=DEMO_DEAL_ID,
                event_type="DEAL_NOTIFICATION", payload={},
            )
            db.add(event)
            db.commit()
            event_id = event.id
        for kind in ("PAYMENT_STATE_CHANGED", "AGREEMENT_APPROVAL_RECORDED", "AGREEMENT_COMMITTED", "UNKNOWN_KIND", None):
            with self.subTest(kind=kind):
                with Session(self.engine) as db:
                    db.get(OutboxEvent, event_id).payload = {"kind": kind}
                    db.commit()
                original = self._snapshot()
                with self.assertRaisesRegex(DemoCollisionError, "external dispatch"):
                    self._seed(reset=True)
                self.assertEqual(self._snapshot(), original)

    def test_production_refuses_before_any_mutation(self) -> None:
        original = self._snapshot()
        with patch.object(settings, "app_env", "production"):
            with self.assertRaises(RuntimeError):
                self._seed(reset=True)
            with self.assertRaises(RuntimeError):
                initialize_offline_database(self.engine)
            with self.assertRaises(SystemExit):
                main(["--offline", "--reset"])
        self.assertEqual(self._snapshot(), original)

    def test_unmarked_legacy_deal_is_not_adopted_or_deleted(self) -> None:
        self._seed()
        with Session(self.engine) as db:
            marker = db.get(DemoFixture, FIXTURE_KEY)
            db.delete(marker)
            db.commit()
        original = self._snapshot()
        for reset in (False, True):
            with self.assertRaises(DemoCollisionError):
                self._seed(reset=reset)
        self.assertEqual(self._snapshot(), original)

    def test_marker_party_collision_refuses_before_cleanup(self) -> None:
        self._seed()
        with Session(self.engine) as db:
            marker = db.get(DemoFixture, FIXTURE_KEY)
            marker.buyer_organization_id, marker.seller_organization_id = (
                marker.seller_organization_id,
                marker.buyer_organization_id,
            )
            db.commit()
        original = self._snapshot()
        with patch("syncally.cli.seed_demo._clear_fixture") as cleanup:
            with self.assertRaises(DemoCollisionError):
                self._seed(reset=True)
            cleanup.assert_not_called()
        self.assertEqual(self._snapshot(), original)

    def test_child_collision_refuses_before_cleanup(self) -> None:
        self._seed()
        with Session(self.engine) as db:
            marked = db.get(Deal, DEMO_DEAL_ID)
            legacy = Deal(
                buyer_organization_id=marked.buyer_organization_id,
                seller_organization_id=marked.seller_organization_id,
            )
            db.add(legacy)
            db.flush()
            db.get(Constraint, fixture_id("candidate:0")).deal_id = legacy.id
            db.commit()
        original = self._snapshot()
        with patch("syncally.cli.seed_demo._clear_fixture") as cleanup:
            with self.assertRaises(DemoCollisionError):
                self._seed(reset=True)
            cleanup.assert_not_called()
        self.assertEqual(self._snapshot(), original)

    def test_unknown_schema_is_not_upgraded(self) -> None:
        with self.engine.begin() as connection:
            connection.execute(text("ALTER TABLE users ADD COLUMN unknown_value TEXT"))
        with self.assertRaisesRegex(RuntimeError, "Unknown SQLite schema"):
            initialize_offline_database(self.engine)

    def test_missing_payment_unique_indexes_are_refused_without_repair(self) -> None:
        self._seed()
        original = self._snapshot()
        for index in sorted(PaymentIntent.__table__.indexes, key=lambda item: item.name):
            with self.subTest(index=index.name):
                with self.engine.begin() as connection:
                    index.drop(connection)
                with self.assertRaisesRegex(RuntimeError, "Unknown SQLite payment indexes"):
                    initialize_offline_database(self.engine)
                with self.engine.connect() as connection:
                    self.assertNotIn(index.name, {item["name"] for item in inspect(connection).get_indexes("payment_intents")})
                self.assertEqual(self._snapshot(), original)
                with self.engine.begin() as connection:
                    index.create(connection)

    def test_orm_sqlite_payment_identity_is_durable_and_normal_updates_succeed(self) -> None:
        self._seed()
        with Session(self.engine) as db:
            deal = db.get(Deal, DEMO_DEAL_ID)
            agreement = db.get(AgreementVersion, fixture_id("agreement"))
            milestone = PaymentMilestone(
                deal_id=deal.id, agreement_version_id=agreement.id, sequence_number=1,
                payer_organization_id=deal.buyer_organization_id, amount=25, currency="USD",
                trigger_type="ON_COMMIT", due_condition="On commit",
            )
            db.add(milestone)
            db.flush()
            intent = PaymentIntent(
                deal_id=deal.id, agreement_version_id=agreement.id,
                payment_milestone_id=milestone.id, seller_organization_id=deal.seller_organization_id,
                payer_organization_id=deal.buyer_organization_id, authorized_by=agreement.created_by,
                amount=25, currency="USD", idempotency_key="durable-offline",
                provider="OFFLINE_DEMO", execution_mode="OFFLINE_DEMO",
            )
            db.add(intent)
            db.commit()
            intent_id = intent.id
        self.engine.dispose()
        initialize_offline_database(self.engine)
        for assignment in (
            "provider='PAYPAL', execution_mode='PAYPAL_SANDBOX'",
            "provider='UNKNOWN', execution_mode='LEGACY_UNRESOLVED'",
        ):
            with self.subTest(assignment=assignment), self.engine.begin() as connection:
                with self.assertRaisesRegex(IntegrityError, "provider and mode are immutable"):
                    connection.exec_driver_sql(f"UPDATE payment_intents SET {assignment}")
        with Session(self.engine) as db:
            intent = db.get(PaymentIntent, intent_id)
            intent.provider = "PAYPAL"
            intent.execution_mode = "PAYPAL_SANDBOX"
            with self.assertRaisesRegex(IntegrityError, "provider and mode are immutable"):
                db.commit()
            db.rollback()
            intent = db.get(PaymentIntent, intent_id)
            intent.status = "SENT"
            intent.reconciled_amount = 5
            intent.reconciliation_source = "OFFLINE_DEMO"
            intent.version += 1
            db.commit()
        with self.engine.begin() as connection:
            connection.exec_driver_sql(
                "UPDATE payment_intents SET status='PARTIALLY_PAID', reconciled_amount=10, "
                "version=version+1, provider=provider, execution_mode=execution_mode"
            )
        self.engine.dispose()
        initialize_offline_database(self.engine)
        with Session(self.engine) as db:
            intent = db.get(PaymentIntent, intent_id)
            self.assertEqual((intent.provider, intent.execution_mode), ("OFFLINE_DEMO", "OFFLINE_DEMO"))
            self.assertEqual((intent.status, intent.reconciled_amount, intent.version), ("PARTIALLY_PAID", 10, 2))

    def test_missing_or_altered_identity_trigger_is_refused_without_repair(self) -> None:
        self._seed()
        original = self._snapshot()
        for replacement in (
            None,
            SQLITE_PAYMENT_IDENTITY_TRIGGER.replace(" OR ", " AND "),
            SQLITE_PAYMENT_IDENTITY_TRIGGER.replace("provider, execution_mode", "provider"),
            SQLITE_PAYMENT_IDENTITY_TRIGGER.replace("RAISE(ABORT, 'payment provider and mode are immutable')", "1"),
        ):
            with self.subTest(replacement=replacement):
                with self.engine.begin() as connection:
                    connection.exec_driver_sql("DROP TRIGGER payment_identity_immutable")
                    if replacement is not None:
                        connection.exec_driver_sql(replacement)
                self.engine.dispose()
                with self.assertRaisesRegex(RuntimeError, "Unknown SQLite payment identity trigger"):
                    initialize_offline_database(self.engine)
                with self.engine.connect() as connection:
                    saved = connection.exec_driver_sql(
                        "SELECT sql FROM sqlite_master WHERE type='trigger' AND name='payment_identity_immutable'"
                    ).scalar()
                self.assertEqual(saved, replacement)
                self.assertEqual(self._snapshot(), original)
                with self.engine.begin() as connection:
                    connection.exec_driver_sql("DROP TRIGGER IF EXISTS payment_identity_immutable")
                    connection.exec_driver_sql(SQLITE_PAYMENT_IDENTITY_TRIGGER)

    def test_altered_payment_unique_indexes_are_refused_without_repair(self) -> None:
        self._seed()
        original = self._snapshot()
        for index in sorted(PaymentIntent.__table__.indexes, key=lambda item: item.name):
            for alteration in ("nonunique", "columns", "predicate", "no_predicate"):
                with self.subTest(index=index.name, alteration=alteration):
                    metadata = MetaData()
                    table = PaymentIntent.__table__.to_metadata(metadata)
                    for copied_index in list(table.indexes):
                        table.indexes.remove(copied_index)
                    replacement = Index(
                        index.name,
                        *[table.c[name] for name in (["deal_id"] if alteration == "columns" else index.columns.keys())],
                        unique=alteration != "nonunique",
                        sqlite_where=(
                            None if alteration == "no_predicate" else text("status = 'AUTHORIZED'")
                            if alteration == "predicate" else index.dialect_options["sqlite"]["where"]
                        ),
                    )
                    with self.engine.begin() as connection:
                        index.drop(connection)
                        replacement.create(connection)
                    before_indexes = inspect(self.engine).get_indexes("payment_intents")
                    with self.assertRaisesRegex(RuntimeError, "Unknown SQLite payment indexes"):
                        initialize_offline_database(self.engine)
                    after_indexes = inspect(self.engine).get_indexes("payment_intents")
                    self.assertEqual(
                        [(item["name"], item["unique"], item["column_names"], {key: str(value) for key, value in item.get("dialect_options", {}).items()}) for item in after_indexes],
                        [(item["name"], item["unique"], item["column_names"], {key: str(value) for key, value in item.get("dialect_options", {}).items()}) for item in before_indexes],
                    )
                    self.assertEqual(self._snapshot(), original)
                    with self.engine.begin() as connection:
                        replacement.drop(connection)
                        index.create(connection)

    def test_payment_index_predicate_whitespace_is_normalized(self) -> None:
        index = next(item for item in PaymentIntent.__table__.indexes if len(item.columns) == 1)
        metadata = MetaData()
        table = PaymentIntent.__table__.to_metadata(metadata)
        replacement = Index(
            index.name,
            table.c.payment_milestone_id,
            unique=True,
            sqlite_where=text("status  NOT  IN ('PAID', 'FAILED', 'CANCELLED')"),
        )
        with self.engine.begin() as connection:
            index.drop(connection)
            replacement.create(connection)
        initialize_offline_database(self.engine)

    def test_old_revision_is_not_silently_upgraded(self) -> None:
        with self.engine.begin() as connection:
            connection.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY)"))
            connection.execute(text("INSERT INTO alembic_version VALUES ('0012_message_idempotency')"))
        with self.assertRaisesRegex(RuntimeError, "revision is not current"):
            initialize_offline_database(self.engine)
        with self.engine.connect() as connection:
            self.assertEqual(connection.scalar(text("SELECT version_num FROM alembic_version")), "0012_message_idempotency")

    def test_cli_prepared_file_is_readable_and_resettable_by_api_in_fresh_sessions(self) -> None:
        with patch("syncally.cli.seed_demo.engine", self.engine), patch(
            "syncally.cli.seed_demo.SessionLocal", lambda: Session(self.engine)
        ), patch.dict("os.environ", {"BUYER_PASSWORD": self.passwords[0], "SELLER_PASSWORD": self.passwords[1]}), patch("builtins.print"):
            main(["--offline", "--reset"])
        original = self._snapshot()

        def database():
            with Session(self.engine) as db:
                yield db

        async def exercise_api():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                with Session(self.engine) as db:
                    buyer_id = db.scalar(select(User.id).where(User.email == DEMO_IDENTITIES[0].email))
                headers = {"Authorization": f"Bearer {_encode_access_token(buyer_id)}"}
                for path in (f"/deals/{DEMO_DEAL_ID}", f"/deals/{DEMO_DEAL_ID}/messages", f"/deals/{DEMO_DEAL_ID}/agreements/current"):
                    response = await client.get(path, headers=headers)
                    self.assertEqual(response.status_code, 200, response.text)
                response = await client.post("/dev/reset-demo", headers=headers)
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.json()["deleted"]["deals"], 1)

        app.dependency_overrides[get_db] = database
        try:
            with patch.object(settings, "jwt_secret", "scripted-test-jwt-key-with-no-real-credentials"), patch("syncally.cli.seed_demo.getpass.getpass", side_effect=AssertionError("API must not prompt")):
                asyncio.run(exercise_api())
        finally:
            app.dependency_overrides.pop(get_db, None)
        self.assertEqual(self._snapshot(), original)

    def test_offline_refuses_memory_database(self) -> None:
        memory = create_database_engine("sqlite://")
        try:
            with self.assertRaisesRegex(RuntimeError, "file-backed"):
                initialize_offline_database(memory)
        finally:
            memory.dispose()

    def test_cli_offline_setup_and_reset_use_same_persistent_database_without_prompt(self) -> None:
        with (
            patch("syncally.cli.seed_demo.engine", self.engine),
            patch("syncally.cli.seed_demo.SessionLocal", lambda: Session(self.engine)),
            patch.dict(
                "os.environ",
                {"BUYER_PASSWORD": self.passwords[0], "SELLER_PASSWORD": self.passwords[1]},
            ),
            patch(
                "syncally.cli.seed_demo.getpass.getpass",
                side_effect=AssertionError("unexpected prompt"),
            ),
            patch("builtins.print"),
        ):
            main(["--offline", "--reset"])
            original = self._snapshot()
            main(["--offline", "--reset"])
            self.assertEqual(self._snapshot(), original)

    def test_fresh_missing_passwords_use_secure_getpass_with_scripted_fake_only(self) -> None:
        with (
            Session(self.engine) as db,
            patch(
                "syncally.cli.seed_demo.getpass.getpass",
                side_effect=[
                    self.passwords[0],
                    self.passwords[0],
                    self.passwords[1],
                    self.passwords[1],
                ],
            ) as prompt,
        ):
            seed_demo_data(db)
        self.assertEqual(prompt.call_count, 4)
        with (
            Session(self.engine) as db,
            patch(
                "syncally.cli.seed_demo.getpass.getpass",
                side_effect=AssertionError("unexpected prompt"),
            ),
        ):
            seed_demo_data(db, reset=True)

    def test_file_sqlite_seed_and_reset_serialize_without_partial_visibility(self) -> None:
        self._seed()
        entered, release, attempted, acquired = (threading.Event() for _ in range(4))
        from syncally.cli import seed_demo

        real_clear = seed_demo._clear_fixture
        real_lock = seed_demo.lock_demo_reset

        def hold_clear(db, marker):
            result = real_clear(db, marker)
            entered.set()
            if not release.wait(5):
                raise RuntimeError("test release timed out")
            return result

        def observed_lock(db):
            if threading.current_thread().name.startswith("seed-contender"):
                attempted.set()
                real_lock(db)
                acquired.set()
            else:
                real_lock(db)

        original = self._snapshot()
        with (
            patch.object(seed_demo, "_clear_fixture", hold_clear),
            patch.object(seed_demo, "lock_demo_reset", observed_lock),
        ):
            with (
                concurrent.futures.ThreadPoolExecutor(max_workers=1) as reset_pool,
                concurrent.futures.ThreadPoolExecutor(
                    max_workers=1, thread_name_prefix="seed-contender"
                ) as seed_pool,
            ):
                reset_future = reset_pool.submit(self._seed, reset=True)
                try:
                    self.assertTrue(entered.wait(5))
                    seed_future = seed_pool.submit(self._seed)
                    self.assertTrue(attempted.wait(5))
                    self.assertFalse(acquired.wait(0.15))
                    self.assertEqual(self._snapshot(), original)
                finally:
                    release.set()
                reset_future.result(timeout=5)
                seed_future.result(timeout=5)
        self.assertTrue(acquired.is_set())
        self.assertEqual(self._snapshot(), original)


if __name__ == "__main__":
    unittest.main()
