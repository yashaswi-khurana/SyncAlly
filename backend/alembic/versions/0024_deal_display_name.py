"""Add an optional human-readable name to a deal."""

from alembic import op
import sqlalchemy as sa


revision = "0024_deal_display_name"
down_revision = "0023_inviting_party"
branch_labels = None
depends_on = None


def upgrade() -> None:
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


def downgrade() -> None:
    op.drop_column("deals", "display_name")
