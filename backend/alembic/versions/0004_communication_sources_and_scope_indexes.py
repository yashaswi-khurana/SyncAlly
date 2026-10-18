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
        batch_op.create_check_constraint(
            "ck_message_source_type", "source_type IN ('USER', 'AGENT')"
        )
        batch_op.create_check_constraint(
            "ck_message_source_matches_author",
            "(source_type = 'USER' AND author_user_id IS NOT NULL AND author_agent_id IS NULL) "
            "OR (source_type = 'AGENT' AND author_user_id IS NULL AND author_agent_id IS NOT NULL)",
        )
        batch_op.create_check_constraint(
            "ck_message_body_nonempty", "length(trim(body)) > 0"
        )
    with op.batch_alter_table("constraints") as batch_op:
        batch_op.create_check_constraint(
            "ck_constraint_kind",
            "kind IN ('HARD_LIMIT', 'PREFERENCE', 'FLEXIBLE_OPTION', 'INFORMATIONAL')",
        )
        batch_op.create_check_constraint(
            "ck_constraint_status",
            "status IN ('EXTRACTED', 'NEEDS_CLARIFICATION', 'CONFIRMED', 'REJECTED', 'SUPERSEDED')",
        )
        batch_op.create_check_constraint(
            "ck_constraint_visibility",
            "visibility IN ('PRIVATE', 'SHAREABLE', 'INTERNAL')",
        )
        batch_op.create_check_constraint(
            "ck_constraint_fact_nonempty",
            "length(trim(field)) > 0 AND length(trim(typed_value)) > 0",
        )
        batch_op.create_check_constraint(
            "ck_constraint_source_present",
            "(source_message_id IS NOT NULL) OR "
            "(source_span IS NOT NULL AND length(trim(source_span)) > 0)",
        )
        batch_op.create_check_constraint(
            "ck_constraint_source_span_nonempty",
            "source_span IS NULL OR length(trim(source_span)) > 0",
        )
        batch_op.create_check_constraint(
            "ck_constraint_version_nonnegative", "version >= 0"
        )
        batch_op.create_check_constraint(
            "ck_constraint_confirmation_metadata_pair",
            "(confirmed_by IS NULL AND confirmed_at IS NULL) "
            "OR (confirmed_by IS NOT NULL AND confirmed_at IS NOT NULL)",
        )
        batch_op.create_check_constraint(
            "ck_constraint_confirmation_status",
            "(status IN ('CONFIRMED', 'SUPERSEDED') AND confirmed_by IS NOT NULL) "
            "OR (status NOT IN ('CONFIRMED', 'SUPERSEDED') AND confirmed_by IS NULL)",
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
        batch_op.drop_constraint("ck_constraint_confirmation_status", type_="check")
        batch_op.drop_constraint("ck_constraint_confirmation_metadata_pair", type_="check")
        batch_op.drop_constraint("ck_constraint_version_nonnegative", type_="check")
        batch_op.drop_constraint("ck_constraint_source_span_nonempty", type_="check")
        batch_op.drop_constraint("ck_constraint_source_present", type_="check")
        batch_op.drop_constraint("ck_constraint_fact_nonempty", type_="check")
        batch_op.drop_constraint("ck_constraint_visibility", type_="check")
        batch_op.drop_constraint("ck_constraint_status", type_="check")
        batch_op.drop_constraint("ck_constraint_kind", type_="check")
    with op.batch_alter_table("messages") as batch_op:
        batch_op.drop_constraint("ck_message_body_nonempty", type_="check")
        batch_op.drop_constraint("ck_message_source_matches_author", type_="check")
        batch_op.drop_constraint("ck_message_source_type", type_="check")
        batch_op.drop_constraint("ck_message_visibility", type_="check")
    op.drop_column("messages", "source_reference")
