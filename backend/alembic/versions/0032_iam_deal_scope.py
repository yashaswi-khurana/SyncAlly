"""Add canonical organization grants, explicit deal assignments, and owner state."""

import json
from uuid import UUID

import sqlalchemy as sa
from alembic import op
from syncally.infrastructure.models.base import JSON_TYPE, UUID_TYPE

revision = "0032_iam_deal_scope"
down_revision = "0031_reminders"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("organization_members", sa.Column("role_bundles", JSON_TYPE, nullable=False, server_default="[]"))
    op.add_column("organization_members", sa.Column("permissions", JSON_TYPE, nullable=False, server_default="[]"))
    op.add_column("organization_members", sa.Column("is_owner", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_table(
        "deal_assignments",
        sa.Column("id", UUID_TYPE, nullable=False),
        sa.Column("organization_id", UUID_TYPE, nullable=False),
        sa.Column("deal_id", UUID_TYPE, nullable=False),
        sa.Column("user_id", UUID_TYPE, nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["deal_id"], ["deals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "deal_id", "user_id", name="uq_deal_assignment_org_deal_user"),
    )
    op.create_index("ix_deal_assignments_user_org", "deal_assignments", ["user_id", "organization_id"])
    op.create_index("ix_deal_assignments_org_deal", "deal_assignments", ["organization_id", "deal_id"])

    # Preserve org profile/member administration for existing administrators,
    # but deliberately do not infer deal assignments or read_all for anyone.
    bind = op.get_bind()
    bind.execute(sa.text("UPDATE organization_members SET role_bundles = '[]' WHERE role_bundles IS NULL"))
    bind.execute(sa.text("UPDATE organization_members SET role_bundles = '[\"ORG_ADMIN\"]' WHERE role = 'ADMIN'"))
    member_table = sa.table(
        "organization_members",
        sa.column("organization_id", UUID_TYPE),
        sa.column("user_id", UUID_TYPE),
        sa.column("status", sa.String()),
        sa.column("capabilities", JSON_TYPE),
        sa.column("is_owner", sa.Boolean()),
        sa.column("role_bundles", JSON_TYPE),
        sa.column("permissions", JSON_TYPE),
    )
    legacy_permissions = {
        "DRAFTING": ["deal.read_assigned", "deal.edit_assigned"],
        "AGREEMENT_APPROVAL": ["deal.read_assigned", "agreement.approve"],
        "FINANCE": ["deal.read_assigned", "payments.read", "payments.authorize"],
        "FULFILLMENT": ["deal.read_assigned", "fulfillment.read", "fulfillment.record"],
    }
    rows = bind.execute(sa.select(member_table.c.organization_id, member_table.c.user_id, member_table.c.capabilities)
                        .where(member_table.c.status == "ACTIVE")).all()
    for organization_id, user_id, capabilities in rows:
        values = capabilities if isinstance(capabilities, list) else json.loads(capabilities or "[]")
        permissions = sorted({permission for capability in values for permission in legacy_permissions.get(capability, [])})
        if permissions:
            bind.execute(sa.update(member_table).where(
                member_table.c.organization_id == organization_id,
                member_table.c.user_id == user_id,
            ).values(permissions=permissions))
    audit_table = sa.table(
        "audit_events",
        sa.column("aggregate_type", sa.String()),
        sa.column("event_type", sa.String()),
        sa.column("aggregate_id", UUID_TYPE),
        sa.column("actor_id", UUID_TYPE),
        sa.column("payload", JSON_TYPE),
        sa.column("occurred_at", sa.DateTime()),
    )
    owner_events = bind.execute(
        sa.select(audit_table.c.aggregate_id, audit_table.c.actor_id, audit_table.c.payload)
        .where(
            audit_table.c.aggregate_type == "organization",
            audit_table.c.event_type == "organization.owner_registered",
        )
        .order_by(audit_table.c.occurred_at)
    ).mappings().all()
    for event in owner_events:
        payload = event["payload"]
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except (TypeError, ValueError):
                payload = {}
        user_id = UUID(str((payload or {}).get("user_id"))) if (payload or {}).get("user_id") else event["actor_id"]
        bind.execute(sa.update(member_table).where(
            member_table.c.organization_id == event["aggregate_id"],
            member_table.c.user_id == user_id,
            member_table.c.status == "ACTIVE",
        ).values(is_owner=True, role_bundles=[], permissions=[]))


def downgrade() -> None:
    bind = op.get_bind()
    if bind.execute(sa.text("SELECT 1 FROM deal_assignments LIMIT 1")).first():
        raise RuntimeError("Cannot downgrade IAM deal scope migration with assignments present")
    op.drop_index("ix_deal_assignments_org_deal", table_name="deal_assignments")
    op.drop_index("ix_deal_assignments_user_org", table_name="deal_assignments")
    op.drop_table("deal_assignments")
    op.drop_column("organization_members", "is_owner")
    op.drop_column("organization_members", "permissions")
    op.drop_column("organization_members", "role_bundles")
