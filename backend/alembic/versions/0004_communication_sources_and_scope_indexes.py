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


def upgrade() -> None:
    op.add_column("messages", sa.Column("source_reference", sa.Text(), nullable=True))
    op.create_index(
        "ix_conversations_deal_participant_created",
        "conversations",
        ["deal_id", "participant_organization_id", "created_at"],
    )
    op.create_index(
        "ix_messages_conversation_visibility_created",
        "messages",
        ["conversation_id", "visibility", "created_at"],
    )
    op.create_index(
        "ix_constraints_deal_owner_visibility_created",
        "constraints",
        ["deal_id", "owner_organization_id", "visibility", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_constraints_deal_owner_visibility_created", table_name="constraints")
    op.drop_index("ix_messages_conversation_visibility_created", table_name="messages")
    op.drop_index("ix_conversations_deal_participant_created", table_name="conversations")
    op.drop_column("messages", "source_reference")
