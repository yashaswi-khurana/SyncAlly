import importlib.util
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import sqlalchemy as sa
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from test_domain_fixes import build_terms

from alembic import command
from syncally.domain.shared.identifiers import OrganizationId
from syncally.infrastructure.models import Deal, NegotiationSession, Organization, User


class NegotiationMigrationTests(unittest.TestCase):
    def config(self, output=None) -> Config:
        root = Path(__file__).resolve().parents[1]
        config = Config(str(root / "alembic.ini"), output_buffer=output)
        config.set_main_option("script_location", str(root / "alembic"))
        return config

    def test_populated_upgrade_preserves_legacy_values_and_scoped_constraints(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            url = "sqlite:///" + (Path(temporary) / "migration.db").as_posix()
            with patch.dict(os.environ, {"DATABASE_URL": url, "APP_ENV": "test"}), patch("logging.config.fileConfig"):
                path = Path(__file__).resolve().parents[1] / "alembic" / "versions" / "0016_persisted_negotiation_rounds.py"
                spec = importlib.util.spec_from_file_location("negotiation_migration", path)
                migration = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(migration)
                self.assertEqual(migration.down_revision, "0015_counterparty_onboarding")
                engine = create_engine(url)
                try:
                    metadata = sa.MetaData()
                    for model in (Organization, User, Deal):
                        model.__table__.to_metadata(metadata)
                    sa.Table("negotiation_sessions", metadata,
                        sa.Column("id", sa.Uuid(), primary_key=True),
                        sa.Column("deal_id", sa.Uuid(), sa.ForeignKey("deals.id"), nullable=False, unique=True),
                        sa.Column("max_rounds", sa.Integer(), nullable=False),
                        sa.Column("round_count", sa.Integer(), nullable=False, default=0),
                        sa.Column("current_proposal_id", sa.Uuid()),
                        sa.Column("escalated", sa.Boolean(), nullable=False, default=False),
                        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
                        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
                        sa.CheckConstraint("max_rounds > 0", name="ck_negotiation_max_rounds_positive"))
                    sa.Table("proposals", metadata,
                        sa.Column("id", sa.Uuid(), primary_key=True),
                        sa.Column("deal_id", sa.Uuid(), sa.ForeignKey("deals.id"), nullable=False),
                        sa.Column("negotiation_session_id", sa.Uuid(), sa.ForeignKey("negotiation_sessions.id"), nullable=False),
                        sa.Column("proposal_number", sa.Integer(), nullable=False),
                        sa.Column("author_organization_id", sa.Uuid(), sa.ForeignKey("organizations.id"), nullable=False),
                        sa.Column("based_on_proposal_id", sa.Uuid(), sa.ForeignKey("proposals.id")),
                        sa.Column("terms_json", sa.JSON(), nullable=False), sa.Column("terms_hash", sa.String(64), nullable=False),
                        sa.Column("status", sa.String(32), nullable=False, default="DRAFT"),
                        sa.Column("expires_at", sa.DateTime()),
                        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
                        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
                        sa.UniqueConstraint("deal_id", "proposal_number"))
                    sa.Table("agreement_versions", metadata,
                        sa.Column("id", sa.Uuid(), primary_key=True),
                        sa.Column("deal_id", sa.Uuid(), sa.ForeignKey("deals.id"), nullable=False),
                        sa.Column("proposal_id", sa.Uuid(), sa.ForeignKey("proposals.id"), nullable=False),
                        sa.Column("version_number", sa.Integer(), nullable=False),
                        sa.Column("canonical_terms_json", sa.JSON(), nullable=False), sa.Column("terms_hash", sa.String(64), nullable=False),
                        sa.Column("status", sa.String(32), nullable=False),
                        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
                        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()), sa.Column("committed_at", sa.DateTime()),
                        sa.UniqueConstraint("deal_id", "version_number"))
                    metadata.create_all(engine)
                    with Session(engine) as db:
                        buyer, seller = uuid4(), uuid4()
                        db.execute(Organization.__table__.insert(), [{"id": buyer, "legal_name": "Buyer", "country_code": "US"}, {"id": seller, "legal_name": "Seller", "country_code": "CA"}])
                        user, deal, session, proposal = uuid4(), uuid4(), uuid4(), uuid4()
                        db.execute(User.__table__.insert().values(id=user, email="legacy@f5.test", display_name="Legacy", status="ACTIVE"))
                        db.execute(Deal.__table__.insert().values(id=deal, buyer_organization_id=buyer, seller_organization_id=seller, version=0))
                        db.execute(NegotiationSession.__table__.insert().values(id=session, deal_id=deal, max_rounds=3, round_count=0, current_proposal_id=proposal))
                        terms = build_terms(buyer_id=OrganizationId(buyer), seller_id=OrganizationId(seller))
                        db.execute(text("INSERT INTO proposals (id, deal_id, negotiation_session_id, proposal_number, author_organization_id, terms_json, terms_hash, status) VALUES (:id, :deal, :session, 1, :author, :terms, :hash, 'DRAFT')"),
                                   {"id": proposal.hex, "deal": deal.hex, "session": session.hex, "author": buyer.hex, "terms": terms.canonical_json(), "hash": terms.terms_hash})
                        db.commit()
                        original = db.execute(text("SELECT * FROM proposals")).first()
                    with engine.begin() as connection:
                        migration.op = Operations(MigrationContext.configure(connection))
                        migration.upgrade()
                    with engine.connect() as connection:
                        stored = connection.execute(text("SELECT * FROM proposals")).first()
                        self.assertEqual(tuple(stored[:len(original)]), tuple(original))
                        self.assertEqual(connection.scalar(text("SELECT lifecycle_origin FROM proposals")), "LEGACY")
                        self.assertEqual(connection.scalar(text("SELECT max_rounds FROM negotiation_sessions")), 3)
                        self.assertEqual(connection.scalar(text("SELECT round_count FROM negotiation_sessions")), 0)
                        self.assertEqual(connection.scalar(text("SELECT COUNT(*) FROM negotiation_actions")), 0)
                        self.assertIn("fk_proposal_predecessor_scope", {fk["name"] for fk in inspect(connection).get_foreign_keys("proposals")})
                    with engine.begin() as connection:
                        migration.op = Operations(MigrationContext.configure(connection))
                        migration.downgrade()
                        migration.upgrade()
                    with engine.begin() as connection:
                        connection.execute(text("UPDATE proposals SET lifecycle_origin = 'HUMAN_ROUNDS', created_by = :user, status = 'SUBMITTED'"), {"user": user.hex})
                    with engine.begin() as connection:
                        migration.op = Operations(MigrationContext.configure(connection))
                        with self.assertRaisesRegex(RuntimeError, "human negotiation history"):
                            migration.downgrade()
                    with engine.connect() as connection:
                        self.assertIn("negotiation_actions", inspect(connection).get_table_names())
                    with engine.begin() as connection:
                        with self.assertRaises(IntegrityError):
                            connection.execute(text("UPDATE negotiation_sessions SET round_count = -1"))
                finally:
                    engine.dispose()

    def test_postgres_offline_additive_upgrade(self) -> None:
        output = io.StringIO()
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql+psycopg://offline.example/syncally", "APP_ENV": "test"}), patch("logging.config.fileConfig"):
            command.upgrade(self.config(output), "0015_counterparty_onboarding:head", sql=True)
        sql = output.getvalue()
        for expected in ("CREATE TABLE negotiation_actions", "uq_agreement_pending_deal", "fk_action_candidate_scope", "ck_human_proposal_state"):
            self.assertIn(expected, sql)

    @unittest.skipUnless(os.environ.get("TEST_POSTGRES_URL"), "Set TEST_POSTGRES_URL for isolated F5 PostgreSQL migration execution")
    def test_postgres_fresh_upgrade_and_downgrade(self) -> None:
        from sqlalchemy.engine import make_url
        engine = create_engine(os.environ["TEST_POSTGRES_URL"], hide_parameters=True)
        schema = "negotiation_migration_" + uuid4().hex
        try:
            with engine.begin() as connection:
                connection.execute(text(f'CREATE SCHEMA "{schema}"'))
            url = make_url(os.environ["TEST_POSTGRES_URL"]).update_query_dict({"options": f"-csearch_path={schema}"}).render_as_string(hide_password=False)
            with patch.dict(os.environ, {"DATABASE_URL": url, "APP_ENV": "test"}), patch("logging.config.fileConfig"):
                command.upgrade(self.config(), "head")
                with engine.connect() as connection:
                    self.assertIn("negotiation_actions", inspect(connection).get_table_names(schema=schema))
                command.downgrade(self.config(), "0015_counterparty_onboarding")
        finally:
            with engine.begin() as connection:
                connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
            engine.dispose()