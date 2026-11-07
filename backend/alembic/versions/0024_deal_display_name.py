"""Add an optional human-readable name to a deal."""

import sqlalchemy as sa
from sqlalchemy.sql.selectable import TableClause

from alembic import op

revision = "0024_deal_display_name"
down_revision = "0023_inviting_party"
branch_labels = None
depends_on = None

_ROLLBACK_BACKUP_TABLE = "deal_display_name_rollback_backup"


def _deal_names_table() -> TableClause:
    return sa.table(
        "deals",
        sa.column("id", sa.Uuid()),
        sa.column("display_name", sa.String(length=160)),
    )


def _rollback_backup_table() -> TableClause:
    return sa.table(
        _ROLLBACK_BACKUP_TABLE,
        sa.column("deal_id", sa.Uuid()),
        sa.column("display_name", sa.String(length=160)),
    )


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
    from alembic import context

    if not context.is_offline_mode() and sa.inspect(op.get_bind()).has_table(_ROLLBACK_BACKUP_TABLE):
        deals = _deal_names_table()
        backup = _rollback_backup_table()
        backup_name = (
            sa.select(backup.c.display_name)
            .where(backup.c.deal_id == deals.c.id)
            .scalar_subquery()
        )
        has_backup = sa.exists(
            sa.select(1).select_from(backup).where(backup.c.deal_id == deals.c.id)
        ).correlate(deals)
        op.get_bind().execute(
            sa.update(deals).where(has_backup).values(display_name=backup_name)
        )


def downgrade() -> None:
    """Keep deal names in a durable table before removing the application column."""
    from alembic import context

    if not context.is_offline_mode():
        bind = op.get_bind()
        if not sa.inspect(bind).has_table(_ROLLBACK_BACKUP_TABLE):
            op.create_table(
                _ROLLBACK_BACKUP_TABLE,
                sa.Column("deal_id", sa.Uuid(), primary_key=True),
                sa.Column("display_name", sa.String(length=160), nullable=False),
            )
        deals = _deal_names_table()
        backup = _rollback_backup_table()
        current_name = (
            sa.select(deals.c.display_name)
            .where(deals.c.id == backup.c.deal_id)
            .scalar_subquery()
        )
        has_current_name = sa.exists(
            sa.select(1)
            .select_from(deals)
            .where(deals.c.id == backup.c.deal_id, deals.c.display_name.is_not(None))
        ).correlate(backup)
        bind.execute(
            sa.update(backup)
            .where(has_current_name)
            .values(display_name=current_name)
        )
        already_backed_up = sa.exists(
            sa.select(1).select_from(backup).where(backup.c.deal_id == deals.c.id)
        ).correlate(deals)
        names_to_preserve = sa.select(deals.c.id, deals.c.display_name).where(
            deals.c.display_name.is_not(None), ~already_backed_up
        )
        bind.execute(sa.insert(backup).from_select(["deal_id", "display_name"], names_to_preserve))
    op.drop_column("deals", "display_name")
