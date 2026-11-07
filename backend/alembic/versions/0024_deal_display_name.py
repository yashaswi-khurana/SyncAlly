"""Add an optional human-readable name to a deal."""

from alembic import op
import sqlalchemy as sa


revision = "0024_deal_display_name"
down_revision = "0023_inviting_party"
branch_labels = None
depends_on = None

_ROLLBACK_BACKUP_TABLE = "deal_display_name_rollback_backup"


def upgrade() -> None:
    """Add deal names and restore names retained by an earlier downgrade."""
    op.add_column("deals", sa.Column("display_name", sa.String(length=160), nullable=True))
    op.execute(
        """
        UPDATE deals AS deal
        SET display_name = LEFT(buyer.legal_name || ' ↔ ' || seller.legal_name, 160)
        FROM organizations AS buyer, organizations AS seller
        WHERE deal.buyer_organization_id = buyer.id
          AND deal.seller_organization_id = seller.id
        """
    )
    if sa.inspect(op.get_bind()).has_table(_ROLLBACK_BACKUP_TABLE):
        op.execute(
            f"""
            UPDATE deals
            SET display_name = (
                SELECT backup.display_name
                FROM {_ROLLBACK_BACKUP_TABLE} AS backup
                WHERE backup.deal_id = deals.id
            )
            WHERE EXISTS (
                SELECT 1
                FROM {_ROLLBACK_BACKUP_TABLE} AS backup
                WHERE backup.deal_id = deals.id
            )
            """
        )


def downgrade() -> None:
    """Keep deal names in a durable table before removing the application column."""
    bind = op.get_bind()
    if not sa.inspect(bind).has_table(_ROLLBACK_BACKUP_TABLE):
        op.create_table(
            _ROLLBACK_BACKUP_TABLE,
            sa.Column("deal_id", sa.Uuid(), primary_key=True),
            sa.Column("display_name", sa.String(length=160), nullable=False),
        )
    op.execute(
        f"""
        UPDATE {_ROLLBACK_BACKUP_TABLE}
        SET display_name = (
            SELECT deals.display_name
            FROM deals
            WHERE deals.id = {_ROLLBACK_BACKUP_TABLE}.deal_id
        )
        WHERE EXISTS (
            SELECT 1
            FROM deals
            WHERE deals.id = {_ROLLBACK_BACKUP_TABLE}.deal_id
              AND deals.display_name IS NOT NULL
        )
        """
    )
    op.execute(
        f"""
        INSERT INTO {_ROLLBACK_BACKUP_TABLE} (deal_id, display_name)
        SELECT deals.id, deals.display_name
        FROM deals
        WHERE deals.display_name IS NOT NULL
          AND NOT EXISTS (
              SELECT 1
              FROM {_ROLLBACK_BACKUP_TABLE}
              WHERE {_ROLLBACK_BACKUP_TABLE}.deal_id = deals.id
          )
        """
    )
    op.drop_column("deals", "display_name")
