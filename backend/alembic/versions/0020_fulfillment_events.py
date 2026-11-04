"""Persist version-bound shipment observations and confirmations."""

from alembic import op
import sqlalchemy as sa


revision = "0020_fulfillment_events"
down_revision = "0019_organization_permissions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    sqlite = bind.dialect.name == "sqlite"
    op.add_column(
        "obligations",
        sa.Column("fulfillment_version", sa.Integer(), nullable=False, server_default="0"),
    )
    if sqlite:
        # SQLite rebuilds for ALTER TABLE constraints; rebuilding either referenced
        # table can cascade-delete existing obligations and dependent milestone rows.
        # Unique indexes provide the composite parent keys without copying history.
        op.create_index(
            "uq_obligation_fulfillment_scope",
            "obligations",
            ["id", "deal_id", "agreement_version_id"],
            unique=True,
        )
        op.create_index(
            "uq_agreement_scope_hash",
            "agreement_versions",
            ["id", "deal_id", "terms_hash"],
            unique=True,
        )
        op.execute(
            "CREATE TRIGGER ck_obligation_fulfillment_version_insert "
            "BEFORE INSERT ON obligations WHEN NEW.fulfillment_version < 0 "
            "BEGIN SELECT RAISE(ABORT, 'fulfillment_version must be nonnegative'); END"
        )
        op.execute(
            "CREATE TRIGGER ck_obligation_fulfillment_version_update "
            "BEFORE UPDATE OF fulfillment_version ON obligations "
            "WHEN NEW.fulfillment_version < 0 "
            "BEGIN SELECT RAISE(ABORT, 'fulfillment_version must be nonnegative'); END"
        )
    else:
        op.create_check_constraint(
            "ck_obligation_fulfillment_version_nonnegative",
            "obligations",
            "fulfillment_version >= 0",
        )
        op.create_unique_constraint(
            "uq_obligation_fulfillment_scope",
            "obligations",
            ["id", "deal_id", "agreement_version_id"],
        )
        op.create_unique_constraint(
            "uq_agreement_scope_hash",
            "agreement_versions",
            ["id", "deal_id", "terms_hash"],
        )
    op.create_table(
        "fulfillment_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("deal_id", sa.Uuid(), nullable=False),
        sa.Column("agreement_version_id", sa.Uuid(), nullable=False),
        sa.Column("terms_hash", sa.String(length=64), nullable=False),
        sa.Column("obligation_id", sa.Uuid(), nullable=False),
        sa.Column("actor_organization_id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=16), nullable=False),
        sa.Column("quantity", sa.Text(), nullable=False),
        sa.Column("unit", sa.String(length=100), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "event_type IN ('SHIPPED', 'OBSERVED', 'CONFIRMED')",
            name="ck_fulfillment_event_type",
        ),
        sa.CheckConstraint(
            "source_type = 'USER_ATTESTATION'", name="ck_fulfillment_source_type"
        ),
        sa.CheckConstraint("version > 0", name="ck_fulfillment_version_positive"),
        sa.ForeignKeyConstraint(
            ["deal_id"], ["deals.id"], name="fk_fulfillment_events_deal_id_deals", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["actor_organization_id"], ["organizations.id"],
            name="fk_fulfillment_events_actor_organization_id_organizations",
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"], ["users.id"], name="fk_fulfillment_events_actor_user_id_users"
        ),
        sa.ForeignKeyConstraint(
            ["agreement_version_id", "deal_id", "terms_hash"],
            ["agreement_versions.id", "agreement_versions.deal_id", "agreement_versions.terms_hash"],
            name="fk_fulfillment_agreement_scope",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["obligation_id", "deal_id", "agreement_version_id"],
            ["obligations.id", "obligations.deal_id", "obligations.agreement_version_id"],
            name="fk_fulfillment_obligation_scope",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "deal_id", "actor_user_id", "idempotency_key", name="uq_fulfillment_idempotency"
        ),
        sa.UniqueConstraint(
            "obligation_id", "version", name="uq_fulfillment_obligation_version"
        ),
    )
    op.create_index(
        "ix_fulfillment_events_version_obligation_recorded",
        "fulfillment_events",
        ["agreement_version_id", "obligation_id", "recorded_at"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    event_count = bind.scalar(sa.text("SELECT COUNT(*) FROM fulfillment_events"))
    version_count = bind.scalar(
        sa.text("SELECT COUNT(*) FROM obligations WHERE fulfillment_version <> 0")
    )
    if event_count or version_count:
        raise RuntimeError("Cannot downgrade fulfillment state with recorded delivery history")
    sqlite = bind.dialect.name == "sqlite"
    if sqlite:
        version = tuple(
            int(part)
            for part in bind.exec_driver_sql("SELECT sqlite_version()").scalar().split(".")
        )
        if version < (3, 35, 0):
            raise RuntimeError("Cannot safely drop fulfillment_version on SQLite older than 3.35")
    op.drop_index(
        "ix_fulfillment_events_version_obligation_recorded", table_name="fulfillment_events"
    )
    op.drop_table("fulfillment_events")
    if sqlite:
        op.execute("DROP TRIGGER ck_obligation_fulfillment_version_insert")
        op.execute("DROP TRIGGER ck_obligation_fulfillment_version_update")
        op.drop_index("uq_agreement_scope_hash", table_name="agreement_versions")
        op.drop_index("uq_obligation_fulfillment_scope", table_name="obligations")
        op.drop_column("obligations", "fulfillment_version")
    else:
        op.drop_constraint("uq_agreement_scope_hash", "agreement_versions", type_="unique")
        op.drop_constraint("uq_obligation_fulfillment_scope", "obligations", type_="unique")
        op.drop_constraint(
            "ck_obligation_fulfillment_version_nonnegative", "obligations", type_="check"
        )
        op.drop_column("obligations", "fulfillment_version")
