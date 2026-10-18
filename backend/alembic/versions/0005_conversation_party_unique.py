"""Enforce one conversation per deal party and deduplicate existing rows.

Two concurrent first messages could each lazily create a conversation for the
same ``(deal_id, participant_organization_id)`` pair. Reads tolerated the
duplicates, but the invariant is one conversation per party per deal. This
migration moves any messages off duplicate conversations, removes the
duplicates, and then enforces the invariant with a unique constraint.

Revision ID: 0005_conversation_party_unique
Revises: 0004_communication_sources
"""

import sqlalchemy as sa

from alembic import op

revision = "0005_conversation_party_unique"
down_revision = "0004_communication_sources"
branch_labels = None
depends_on = None

_CONSTRAINT_NAME = "uq_conversations_deal_participant"


def _deduplicate_conversations() -> None:
    """Keep the earliest conversation per deal party and repoint its siblings."""
    connection = op.get_bind()
    rows = connection.execute(
        sa.text(
            "SELECT id, deal_id, participant_organization_id "
            "FROM conversations "
            "ORDER BY deal_id, participant_organization_id, created_at, id"
        )
    ).fetchall()

    keeper_by_party: dict[tuple[object, object], object] = {}
    for conversation_id, deal_id, organization_id in rows:
        party = (deal_id, organization_id)
        keeper_id = keeper_by_party.get(party)
        if keeper_id is None:
            keeper_by_party[party] = conversation_id
            continue
        connection.execute(
            sa.text(
                "UPDATE messages SET conversation_id = :keeper_id "
                "WHERE conversation_id = :duplicate_id"
            ),
            {"keeper_id": keeper_id, "duplicate_id": conversation_id},
        )
        connection.execute(
            sa.text("DELETE FROM conversations WHERE id = :duplicate_id"),
            {"duplicate_id": conversation_id},
        )


def _create_party_unique_constraint() -> None:
    context = op.get_context()
    if context.dialect.name == "postgresql":
        with context.autocommit_block():
            op.create_index(
                _CONSTRAINT_NAME,
                "conversations",
                ["deal_id", "participant_organization_id"],
                unique=True,
                postgresql_concurrently=True,
            )
        with context.autocommit_block():
            op.execute(
                f'ALTER TABLE conversations ADD CONSTRAINT "{_CONSTRAINT_NAME}" '
                f'UNIQUE USING INDEX "{_CONSTRAINT_NAME}"'
            )
    else:
        with op.batch_alter_table("conversations") as batch_op:
            batch_op.create_unique_constraint(
                _CONSTRAINT_NAME,
                ["deal_id", "participant_organization_id"],
            )


def _drop_party_unique_constraint() -> None:
    context = op.get_context()
    if context.dialect.name == "postgresql":
        with context.autocommit_block():
            op.execute(
                f'ALTER TABLE conversations DROP CONSTRAINT IF EXISTS "{_CONSTRAINT_NAME}"'
            )
    else:
        with op.batch_alter_table("conversations") as batch_op:
            batch_op.drop_constraint(_CONSTRAINT_NAME, type_="unique")


def upgrade() -> None:
    _deduplicate_conversations()
    _create_party_unique_constraint()


def downgrade() -> None:
    _drop_party_unique_constraint()
