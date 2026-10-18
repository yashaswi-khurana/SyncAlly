"""Add message source references and organization-scoped query indexes.

Revision ID: 0004_communication_sources
Revises: 0003_user_password_hash
"""

import sqlalchemy as sa

from alembic import op

revision = "0004_communication_sources"
down_revision = "0003_user_password_hash"
branch_labels = None
depends_on = None


def _create_scope_index(name: str, table: str, columns: list[str]) -> None:
    context = op.get_context()
    if context.dialect.name == "postgresql":
        with context.autocommit_block():
            op.create_index(
                name,
                table,
                columns,
                postgresql_concurrently=True,
            )
    else:
        op.create_index(name, table, columns)


def _drop_scope_index(name: str, table: str) -> None:
    context = op.get_context()
    if context.dialect.name == "postgresql":
        with context.autocommit_block():
            op.drop_index(name, table_name=table, postgresql_concurrently=True)
    else:
        op.drop_index(name, table_name=table)


def upgrade() -> None:
    op.add_column("messages", sa.Column("source_reference", sa.Text(), nullable=True))
    with op.batch_alter_table("messages") as batch_op:
        batch_op.create_check_constraint(
            "ck_message_visibility",
            "visibility IN ('PRIVATE', 'SHAREABLE', 'INTERNAL')",
        )
    with op.batch_alter_table("constraints") as batch_op:
        batch_op.create_check_constraint(
            "ck_constraint_kind",
            "kind IN ('HARD_LIMIT', 'PREFERENCE', 'FLEXIBLE_OPTION', 'INFORMATIONAL')",
        )
        batch_op.create_check_constraint(
            "ck_constraint_status",
            "status IN ('EXTRACTED', 'NEEDS_CLARIFICATION', 'CONFIRMED', 'SUPERSEDED')",
        )
        batch_op.create_check_constraint(
            "ck_constraint_visibility",
            "visibility IN ('PRIVATE', 'SHAREABLE', 'INTERNAL')",
        )
    _create_scope_index(
        "ix_conversations_deal_participant_created",
        "conversations",
        ["deal_id", "participant_organization_id", "created_at"],
    )
    _create_scope_index(
        "ix_messages_conversation_visibility_created",
        "messages",
        ["conversation_id", "visibility", "created_at"],
    )
    _create_scope_index(
        "ix_constraints_deal_owner_visibility_created",
        "constraints",
        ["deal_id", "owner_organization_id", "visibility", "created_at"],
    )


def downgrade() -> None:
    _drop_scope_index("ix_constraints_deal_owner_visibility_created", "constraints")
    _drop_scope_index("ix_messages_conversation_visibility_created", "messages")
    _drop_scope_index("ix_conversations_deal_participant_created", "conversations")
    with op.batch_alter_table("constraints") as batch_op:
        batch_op.drop_constraint("ck_constraint_visibility", type_="check")
        batch_op.drop_constraint("ck_constraint_status", type_="check")
        batch_op.drop_constraint("ck_constraint_kind", type_="check")
    with op.batch_alter_table("messages") as batch_op:
        batch_op.drop_constraint("ck_message_visibility", type_="check")
    op.drop_column("messages", "source_reference")
