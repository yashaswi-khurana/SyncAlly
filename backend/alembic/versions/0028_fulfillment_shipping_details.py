"""Add carrier and delivery estimates to shipment facts."""

import sqlalchemy as sa

from alembic import op

revision = "0028_fulfillment_shipping_details"
down_revision = "0027_approval_routing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("fulfillment_events", sa.Column("carrier", sa.String(length=120), nullable=True))
    op.add_column(
        "fulfillment_events", sa.Column("tracking_number", sa.String(length=128), nullable=True)
    )
    op.add_column("fulfillment_events", sa.Column("dispatch_date", sa.Date(), nullable=True))
    op.add_column(
        "fulfillment_events", sa.Column("expected_delivery_date", sa.Date(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("fulfillment_events", "expected_delivery_date")
    op.drop_column("fulfillment_events", "dispatch_date")
    op.drop_column("fulfillment_events", "tracking_number")
    op.drop_column("fulfillment_events", "carrier")
