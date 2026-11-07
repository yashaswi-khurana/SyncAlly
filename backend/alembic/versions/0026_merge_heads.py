"""Merge the deal-display-name and cancel-disputes branches into one head."""

revision = "0026_merge_heads"
down_revision = ("0024_deal_display_name", "0025_cancel_disputes")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
