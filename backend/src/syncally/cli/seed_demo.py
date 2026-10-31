"""Create the fixed buyer/seller accounts used by the local demo."""

from __future__ import annotations

import argparse
import getpass
import os
from dataclasses import dataclass
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    MetaData,
    Table,
    UniqueConstraint,
    and_,
    delete,
    func,
    inspect,
    or_,
    select,
    update,
)
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session

from syncally.application.passwords import hash_password
from syncally.cli.demo_fixture import (
    CANDIDATES,
    CURATED_HUMAN_CHOICES,
    DEMO_DEAL_ID,
    FIXTURE_KEY,
    FIXTURE_TIME,
    FIXTURE_VERSION,
    MESSAGES,
    fixture_id,
)
from syncally.config import settings
from syncally.infrastructure.database import SessionLocal, engine
from syncally.infrastructure.demo_lifecycle import lock_demo_reset
from syncally.infrastructure.models import (
    AgreementVersion,
    Approval,
    AuditEvent,
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
    Proposal,
    User,
    WebhookEvent,
)
from syncally.infrastructure.payment_schema import SQLITE_PAYMENT_IDENTITY_TRIGGER


@dataclass(frozen=True)
class DemoIdentity:
    email: str
    display_name: str
    organization_name: str


DEMO_IDENTITIES = (
    DemoIdentity("buyer@syncally.demo", "Demo Buyer", "Demo Buyer Co"),
    DemoIdentity("seller@syncally.demo", "Demo Seller", "Demo Seller Co"),
)


def _password_for(identity: DemoIdentity, supplied_password: str | None) -> str:
    if supplied_password is not None:
        password = supplied_password
    else:
        password = getpass.getpass(f"Set password for {identity.email} (12+ characters): ")
        confirmation = getpass.getpass("Confirm password: ")
        if password != confirmation:
            raise ValueError("Passwords do not match")
    if len(password) < 12 or len(password) > 128:
        raise ValueError("Passwords must be between 12 and 128 characters")
    return password


def _seed_identities(
    db: Session,
    passwords: tuple[str | None, str | None],
) -> tuple[list[User], list[Organization]]:
    users, organizations = [], []
    for identity, supplied_password in zip(DEMO_IDENTITIES, passwords, strict=True):
        user = db.scalar(select(User).where(User.email == identity.email))
        if user is None:
            user = User(
                id=fixture_id(identity.email),
                email=identity.email,
                display_name=identity.display_name,
                password_hash=hash_password(_password_for(identity, supplied_password)),
                status="ACTIVE",
            )
            db.add(user)
            db.flush()
        else:
            if user.status != "ACTIVE":
                user.status = "ACTIVE"
            if user.password_hash is None:
                user.password_hash = hash_password(_password_for(identity, supplied_password))

        organization = db.scalar(
            select(Organization).where(
                Organization.legal_name == identity.organization_name,
                Organization.country_code == "US",
            )
        )
        if organization is None:
            organization = Organization(
                id=fixture_id(identity.organization_name),
                legal_name=identity.organization_name,
                country_code="US",
                status="ACTIVE",
            )
            db.add(organization)
            db.flush()

        membership = db.scalar(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == organization.id,
                OrganizationMember.user_id == user.id,
            )
        )
        if membership is None:
            db.add(
                OrganizationMember(
                    organization_id=organization.id,
                    user_id=user.id,
                    role="ADMIN",
                    status="ACTIVE",
                )
            )
        else:
            membership.role = "ADMIN"
            membership.status = "ACTIVE"
        users.append(user)
        organizations.append(organization)
    db.flush()
    return users, organizations


class DemoCollisionError(RuntimeError):
    """Reserved fixture identity or ownership conflicts with existing data."""


def _preflight(db: Session) -> DemoFixture | None:
    party_ids = []
    for identity in DEMO_IDENTITIES:
        organizations = list(
            db.scalars(
                select(Organization).where(
                    Organization.legal_name == identity.organization_name,
                    Organization.country_code == "US",
                )
            )
        )
        if len(organizations) > 1:
            raise DemoCollisionError("Demo organization identity is ambiguous")
        party_ids.append(
            organizations[0].id if organizations else fixture_id(identity.organization_name)
        )
        reserved_org = db.get(Organization, fixture_id(identity.organization_name))
        if reserved_org is not None and (
            reserved_org.id != party_ids[-1]
            or reserved_org.legal_name != identity.organization_name
            or reserved_org.country_code != "US"
        ):
            raise DemoCollisionError("Reserved demo organization ID is occupied")
        reserved_user = db.get(User, fixture_id(identity.email))
        if reserved_user is not None and reserved_user.email != identity.email:
            raise DemoCollisionError("Reserved demo user ID is occupied")

    marker = db.get(DemoFixture, FIXTURE_KEY)
    other_markers = list(
        db.scalars(select(DemoFixture).where(DemoFixture.fixture_key != FIXTURE_KEY))
    )
    if any(row.deal_id == DEMO_DEAL_ID for row in other_markers):
        raise DemoCollisionError("Reserved demo deal is owned by another fixture")
    if marker is not None and (
        marker.fixture_version != FIXTURE_VERSION
        or marker.deal_id != DEMO_DEAL_ID
        or marker.buyer_organization_id != party_ids[0]
        or marker.seller_organization_id != party_ids[1]
    ):
        raise DemoCollisionError("Demo fixture marker does not match its version or parties")
    deal = db.get(Deal, DEMO_DEAL_ID)
    if deal is not None and (
        marker is None
        or (
            deal.buyer_organization_id != party_ids[0]
            or deal.seller_organization_id != party_ids[1]
        )
    ):
        raise DemoCollisionError("Reserved demo deal ID is occupied or has different parties")
    if marker is not None and deal is None:
        raise DemoCollisionError("Marked demo deal is missing")
    reserved = (
        [
            (Conversation, fixture_id(f"conversation:{side}"), "deal_id", DEMO_DEAL_ID)
            for side in ("buyer", "seller")
        ]
        + [
            (
                Message,
                fixture_id(f"message:{index}"),
                "conversation_id",
                fixture_id(f"conversation:{side}"),
            )
            for index, (side, _visibility, _body) in enumerate(MESSAGES)
        ]
        + [
            (Constraint, fixture_id(f"candidate:{index}"), "deal_id", DEMO_DEAL_ID)
            for index in range(len(CANDIDATES))
        ]
        + [
            (NegotiationSession, fixture_id("negotiation"), "deal_id", DEMO_DEAL_ID),
            (Proposal, fixture_id("proposal"), "deal_id", DEMO_DEAL_ID),
            (AgreementVersion, fixture_id("agreement"), "deal_id", DEMO_DEAL_ID),
        ]
    )
    for model, identifier, owner_field, expected_owner in reserved:
        row = db.get(model, identifier)
        if row is not None and (marker is None or getattr(row, owner_field) != expected_owner):
            raise DemoCollisionError(
                "Reserved fixture child ID is occupied outside the marked deal"
            )
    return marker


def _delete_scoped(db: Session, model: Any, *criteria: Any) -> int:
    count = int(db.scalar(select(func.count()).select_from(model).where(*criteria)) or 0)
    if count:
        db.execute(delete(model).where(*criteria).execution_options(synchronize_session="fetch"))
    return count


def _clear_fixture(db: Session, marker: DemoFixture) -> dict[str, int]:
    deal_ids = [marker.deal_id]
    if db.scalar(
        select(Deal.id).where(
            Deal.id == marker.deal_id,
            Deal.status.not_in(("DRAFT", "NEGOTIATING", "PENDING_APPROVALS")),
        )
    ) is not None or db.scalar(
        select(AgreementVersion.id).where(
            AgreementVersion.deal_id == marker.deal_id,
            or_(
                AgreementVersion.status.in_(("APPROVED", "COMMITTED")),
                AgreementVersion.committed_at.is_not(None),
            ),
        ).limit(1)
    ) is not None:
        raise DemoCollisionError("Demo has committed or approved work; history retained")
    for model in (PaymentIntent, Approval, Obligation, PaymentMilestone):
        if db.scalar(select(model.id).where(model.deal_id == marker.deal_id).limit(1)) is not None:
            raise DemoCollisionError(f"Demo has {model.__tablename__} work; history retained")
    agreement_ids = list(
        db.scalars(select(AgreementVersion.id).where(AgreementVersion.deal_id.in_(deal_ids)))
    )
    conversation_ids = list(
        db.scalars(select(Conversation.id).where(Conversation.deal_id.in_(deal_ids)))
    )
    intent_ids = list(
        db.scalars(select(PaymentIntent.id).where(PaymentIntent.deal_id.in_(deal_ids)))
    )
    outbox_scope = or_(
        and_(OutboxEvent.aggregate_type == "deal", OutboxEvent.aggregate_id.in_(deal_ids)),
        and_(OutboxEvent.aggregate_type == "agreement", OutboxEvent.aggregate_id.in_(agreement_ids)),
        and_(OutboxEvent.aggregate_type == "payment_intent", OutboxEvent.aggregate_id.in_(intent_ids)),
    )
    for event in db.scalars(select(OutboxEvent).where(outbox_scope)):
        if (
            event.event_type != "DEAL_NOTIFICATION"
            or event.status != "PENDING"
            or event.retry_count != 0
            or event.delivered_at is not None
            or event.dispatch_started_at is not None
            or event.next_attempt_at is not None
            or event.error_detail is not None
            or not isinstance(event.payload, dict)
            or event.payload.get("kind") not in (
                "DEAL_CREATED", "MESSAGE_RECEIVED", "CONSTRAINT_CHANGED", "PROPOSAL_SUBMITTED"
            )
        ):
            raise DemoCollisionError("Demo has external dispatch work; history retained")
    deleted = {}
    for model, criterion in (
        (WebhookEvent, WebhookEvent.payment_intent_id.in_(intent_ids)),
        (PaymentIntent, PaymentIntent.deal_id.in_(deal_ids)),
        (PaymentMilestone, PaymentMilestone.deal_id.in_(deal_ids)),
        (Obligation, Obligation.deal_id.in_(deal_ids)),
        (Approval, Approval.deal_id.in_(deal_ids)),
        (AgreementVersion, AgreementVersion.deal_id.in_(deal_ids)),
    ):
        deleted[model.__tablename__] = _delete_scoped(db, model, criterion)
    db.execute(
        update(Proposal).where(Proposal.deal_id.in_(deal_ids)).values(based_on_proposal_id=None)
    )
    for model, criterion in (
        (Proposal, Proposal.deal_id.in_(deal_ids)),
        (NegotiationSession, NegotiationSession.deal_id.in_(deal_ids)),
        (Constraint, Constraint.deal_id.in_(deal_ids)),
        (Message, Message.conversation_id.in_(conversation_ids)),
        (Conversation, Conversation.deal_id.in_(deal_ids)),
    ):
        deleted[model.__tablename__] = _delete_scoped(db, model, criterion)
    for model in (OutboxEvent, AuditEvent):
        scope = or_(
            and_(model.aggregate_type == "deal", model.aggregate_id.in_(deal_ids)),
            and_(model.aggregate_type == "agreement", model.aggregate_id.in_(agreement_ids)),
            and_(model.aggregate_type == "payment_intent", model.aggregate_id.in_(intent_ids)),
        )
        deleted[model.__tablename__] = _delete_scoped(db, model, scope)
    db.delete(marker)
    db.flush()
    deleted["deals"] = _delete_scoped(db, Deal, Deal.id.in_(deal_ids))
    return deleted


def _create_fixture(db: Session, users: list[User], organizations: list[Organization]) -> None:
    buyer, seller = organizations
    deal = Deal(
        id=DEMO_DEAL_ID,
        buyer_organization_id=buyer.id,
        seller_organization_id=seller.id,
        current_proposal_id=fixture_id("proposal"),
        current_agreement_version_id=fixture_id("agreement"),
        status="DRAFT",
        version=0,
        created_at=FIXTURE_TIME,
        updated_at=FIXTURE_TIME,
    )
    db.add(deal)
    db.flush()
    sides = {"buyer": (users[0], buyer), "seller": (users[1], seller)}
    for side, (_user, organization) in sides.items():
        db.add(
            Conversation(
                id=fixture_id(f"conversation:{side}"),
                deal_id=deal.id,
                participant_organization_id=organization.id,
                created_at=FIXTURE_TIME,
            )
        )
    db.flush()
    for index, (side, visibility, body) in enumerate(MESSAGES):
        db.add(
            Message(
                id=fixture_id(f"message:{index}"),
                conversation_id=fixture_id(f"conversation:{side}"),
                author_user_id=sides[side][0].id,
                body=body,
                visibility=visibility,
                source_type="USER",
                source_reference=f"curated-demo:v{FIXTURE_VERSION}:message:{index}",
                created_at=FIXTURE_TIME,
            )
        )
    db.flush()
    for index, (source_index, field, value, unit, quote) in enumerate(CANDIDATES):
        side, visibility, body = MESSAGES[source_index]
        if quote not in body:
            raise ValueError("Curated candidate quote is not present in source")
        db.add(
            Constraint(
                id=fixture_id(f"candidate:{index}"),
                deal_id=deal.id,
                owner_organization_id=sides[side][1].id,
                field=field,
                typed_value=value,
                currency_or_unit=unit,
                kind="INFORMATIONAL",
                status="EXTRACTED",
                visibility=visibility,
                source_message_id=fixture_id(f"message:{source_index}"),
                source_span=quote,
                version=0,
                created_at=FIXTURE_TIME,
                updated_at=FIXTURE_TIME,
            )
        )
    negotiation = NegotiationSession(
        id=fixture_id("negotiation"),
        deal_id=deal.id,
        current_proposal_id=fixture_id("proposal"),
        max_rounds=3,
        round_count=0,
        escalated=False,
        created_at=FIXTURE_TIME,
        updated_at=FIXTURE_TIME,
    )
    db.add(negotiation)
    db.flush()
    terms = CURATED_HUMAN_CHOICES.to_trade_terms(buyer_id=buyer.id, seller_id=seller.id)
    terms.validate_for_commit()
    db.add(
        Proposal(
            id=fixture_id("proposal"),
            deal_id=deal.id,
            negotiation_session_id=negotiation.id,
            proposal_number=1,
            author_organization_id=buyer.id,
            terms_json=terms.to_storage_dict(),
            terms_hash=terms.terms_hash,
            status="DRAFT",
            created_at=FIXTURE_TIME,
            updated_at=FIXTURE_TIME,
        )
    )
    db.flush()
    db.add(
        AgreementVersion(
            id=fixture_id("agreement"),
            deal_id=deal.id,
            proposal_id=fixture_id("proposal"),
            version_number=1,
            canonical_terms_json=terms.to_storage_dict(),
            terms_hash=terms.terms_hash,
            status="PENDING_APPROVAL",
            created_by=users[0].id,
            created_at=FIXTURE_TIME,
        )
    )
    db.add(
        DemoFixture(
            fixture_key=FIXTURE_KEY,
            fixture_version=FIXTURE_VERSION,
            buyer_organization_id=buyer.id,
            seller_organization_id=seller.id,
            deal_id=deal.id,
        )
    )
    db.flush()


def seed_demo_data(
    db: Session,
    passwords: tuple[str | None, str | None] = (None, None),
    *,
    reset: bool = False,
    require_existing_passwords: bool = False,
) -> dict[str, int]:
    """Own one locked transaction for curated setup/reset and identity provisioning."""
    if settings.app_env.strip().lower() not in {"development", "test"}:
        raise RuntimeError("Demo seeding is only allowed in development or test")
    try:
        lock_demo_reset(db)
        marker = _preflight(db)
        if require_existing_passwords:
            for identity in DEMO_IDENTITIES:
                user = db.scalar(select(User).where(User.email == identity.email))
                if user is None or not user.password_hash:
                    raise DemoCollisionError(
                        "Demo identities are not seeded. Run python -m syncally.cli.seed_demo first."
                    )
        deleted = {
            model.__tablename__: 0
            for model in (
                Deal,
                Conversation,
                Message,
                Constraint,
                NegotiationSession,
                Proposal,
                AgreementVersion,
                Approval,
                Obligation,
                PaymentMilestone,
                PaymentIntent,
                WebhookEvent,
                OutboxEvent,
                AuditEvent,
            )
        }
        if reset and marker is not None:
            deleted = _clear_fixture(db, marker)
        users, organizations = _seed_identities(db, passwords)
        if marker is None or reset:
            _create_fixture(db, users, organizations)
        db.commit()
        return deleted
    except Exception:
        db.rollback()
        raise


def initialize_offline_database(db_engine: Engine) -> None:
    """Initialize only an empty persistent SQLite DB; never upgrade existing schemas."""
    if settings.app_env.strip().lower() not in {"development", "test"}:
        raise RuntimeError("Offline demo initialization is only allowed in development or test")
    url = make_url(str(db_engine.url))
    if (
        url.get_backend_name() != "sqlite"
        or not url.database
        or url.database == ":memory:"
        or url.database.startswith("file:")
        or url.query.get("mode") == "memory"
    ):
        raise RuntimeError("--offline requires DATABASE_URL pointing to file-backed SQLite")
    with Session(db_engine) as db:
        lock_demo_reset(db)
        connection = db.connection()
        schema = inspect(connection)
        tables = set(schema.get_table_names())
        if not tables:
            Base.metadata.create_all(connection)
        else:
            expected = set(Base.metadata.tables)
            if tables - {"alembic_version"} != expected:
                raise RuntimeError(
                    "Unknown SQLite schema; refusing initialization or automatic upgrade"
                )
            for table in Base.metadata.sorted_tables:
                columns = schema.get_columns(table.name)
                if {column["name"] for column in columns} != set(table.columns.keys()):
                    raise RuntimeError(
                        "Unknown SQLite schema; refusing initialization or automatic upgrade"
                    )
                for column in columns:
                    model_column = table.columns[column["name"]]
                    if (
                        column["nullable"] != model_column.nullable
                        or str(column["type"].compile(dialect=connection.dialect)).upper()
                        != str(model_column.type.compile(dialect=connection.dialect)).upper()
                    ):
                        raise RuntimeError(
                            "Unknown SQLite schema; refusing initialization or automatic upgrade"
                        )
                expected_uniques = {
                    tuple(column.name for column in constraint.columns)
                    for constraint in table.constraints
                    if isinstance(constraint, UniqueConstraint)
                }
                actual_uniques = {
                    tuple(item["column_names"])
                    for item in schema.get_unique_constraints(table.name)
                }
                if not expected_uniques.issubset(actual_uniques):
                    raise RuntimeError("Unknown SQLite uniqueness; refusing automatic upgrade")
                if table.name == PaymentIntent.__tablename__:
                    actual_indexes = {
                        item["name"]: item for item in schema.get_indexes(table.name)
                    }
                    for index in table.indexes:
                        actual = actual_indexes.get(index.name)
                        expected_where = index.dialect_options[connection.dialect.name].get("where")
                        actual_where = (
                            actual.get("dialect_options", {}).get(f"{connection.dialect.name}_where")
                            if actual is not None else None
                        )
                        if (
                            actual is None
                            or bool(actual["unique"]) != bool(index.unique)
                            or actual["column_names"] != [column.name for column in index.columns]
                            or _normalized_index_predicate(actual_where, connection.dialect)
                            != _normalized_index_predicate(expected_where, connection.dialect)
                        ):
                            raise RuntimeError(
                                "Unknown SQLite payment indexes; refusing automatic upgrade"
                            )
                    trigger_sql = connection.exec_driver_sql(
                        "SELECT sql FROM sqlite_master WHERE type = 'trigger' "
                        "AND name = 'payment_identity_immutable' AND tbl_name = 'payment_intents'"
                    ).scalar()
                    if (
                        trigger_sql is None
                        or " ".join(trigger_sql.split())
                        != " ".join(SQLITE_PAYMENT_IDENTITY_TRIGGER.split())
                    ):
                        raise RuntimeError(
                            "Unknown SQLite payment identity trigger; refusing automatic upgrade"
                        )
                expected_fks = {
                    (
                        tuple(element.parent.name for element in constraint.elements),
                        tuple(element.column.name for element in constraint.elements),
                        constraint.referred_table.name,
                        constraint.ondelete,
                    )
                    for constraint in table.foreign_key_constraints
                }
                actual_fks = {
                    (
                        tuple(item["constrained_columns"]),
                        tuple(item["referred_columns"]),
                        item["referred_table"],
                        item.get("options", {}).get("ondelete"),
                    )
                    for item in schema.get_foreign_keys(table.name)
                }
                expected_checks = {
                    str(constraint.sqltext)
                    for constraint in table.constraints
                    if isinstance(constraint, CheckConstraint)
                }
                actual_checks = {
                    item["sqltext"] for item in schema.get_check_constraints(table.name)
                }
                if (
                    expected_fks != actual_fks
                    or expected_checks != actual_checks
                    or schema.get_pk_constraint(table.name)["constrained_columns"]
                    != [column.name for column in table.primary_key.columns]
                ):
                    raise RuntimeError("Unknown SQLite constraints; refusing automatic upgrade")
            if "alembic_version" in tables:
                revision_table = Table("alembic_version", MetaData(), autoload_with=connection)
                revisions = list(connection.scalars(select(revision_table.c.version_num)))
                if revisions != ["0013_curated_demo_fixture"]:
                    raise RuntimeError(
                        "SQLite migration revision is not current; refusing automatic upgrade"
                    )
        db.commit()


def _normalized_index_predicate(expression: Any, dialect: Any) -> str | None:
    if expression is None:
        return None
    return " ".join(str(expression.compile(dialect=dialect, compile_kwargs={"literal_binds": True})).split())


def main(argv: list[str] | None = None) -> None:
    """Prepare or reset the configured persistent demo, without provider operations."""
    parser = argparse.ArgumentParser(description="Prepare the curated, unapproved local demo")
    parser.add_argument(
        "--offline", action="store_true", help="Initialize fresh file-backed SQLite metadata"
    )
    parser.add_argument("--reset", action="store_true", help="Restore only the marked fixture")
    args = parser.parse_args(argv)
    if settings.app_env.strip().lower() not in {"development", "test"}:
        raise SystemExit("Demo seeding is only allowed in development or test")
    if args.offline:
        initialize_offline_database(engine)
    with SessionLocal() as db:
        try:
            seed_demo_data(
                db,
                (os.environ.get("BUYER_PASSWORD"), os.environ.get("SELLER_PASSWORD")),
                reset=args.reset,
            )
        except DemoCollisionError as exc:
            raise SystemExit(str(exc)) from exc
    print(f"Curated unapproved demo is ready. Deal: {DEMO_DEAL_ID}")
    print("Sign in with buyer@syncally.demo or seller@syncally.demo and the password you set.")


if __name__ == "__main__":
    main()
