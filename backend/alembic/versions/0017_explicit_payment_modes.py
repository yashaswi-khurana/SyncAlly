"""Persist immutable payment routing and explicit reconciliation provenance."""

import sqlalchemy as sa

from alembic import op
from syncally.infrastructure.payment_schema import SQLITE_PAYMENT_IDENTITY_TRIGGER

revision = "0017_explicit_payment_modes"
down_revision = "0016_persisted_negotiation_rounds"
branch_labels = None
depends_on = None

_PAIR_CHECK = "(provider = 'PAYPAL' AND execution_mode = 'PAYPAL_SANDBOX') OR (provider = 'OFFLINE_DEMO' AND execution_mode = 'OFFLINE_DEMO') OR (provider <> 'PAYPAL' AND execution_mode = 'LEGACY_UNRESOLVED')"
_SOURCE_CHECK = "reconciliation_source IN ('NONE', 'LEGACY_UNVERIFIED') OR (reconciliation_source = 'PAYPAL_SANDBOX' AND execution_mode = 'PAYPAL_SANDBOX') OR (reconciliation_source = 'OFFLINE_DEMO' AND execution_mode = 'OFFLINE_DEMO')"


def upgrade() -> None:
    op.add_column("payment_intents", sa.Column("execution_mode", sa.String(32), nullable=False, server_default="LEGACY_UNRESOLVED"))
    op.add_column("payment_intents", sa.Column("reconciliation_source", sa.String(32), nullable=False, server_default="LEGACY_UNVERIFIED"))
    op.execute("UPDATE payment_intents SET execution_mode = CASE WHEN provider = 'PAYPAL' THEN 'PAYPAL_SANDBOX' ELSE 'LEGACY_UNRESOLVED' END")
    with op.batch_alter_table("payment_intents") as batch:
        batch.create_check_constraint("ck_payment_intent_provider_mode", _PAIR_CHECK)
        batch.create_check_constraint("ck_payment_intent_reconciliation_source", _SOURCE_CHECK)
    if op.get_bind().dialect.name == "postgresql":
        op.execute("""CREATE FUNCTION syncally_payment_identity_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF NEW.provider IS DISTINCT FROM OLD.provider OR NEW.execution_mode IS DISTINCT FROM OLD.execution_mode THEN
            RAISE EXCEPTION 'payment provider and mode are immutable';
          END IF;
          RETURN NEW;
        END $$""")
        op.execute("CREATE TRIGGER payment_identity_immutable BEFORE UPDATE ON payment_intents FOR EACH ROW EXECUTE FUNCTION syncally_payment_identity_immutable()")
    elif op.get_bind().dialect.name == "sqlite":
        op.execute(SQLITE_PAYMENT_IDENTITY_TRIGGER)


def downgrade() -> None:
    if op.get_bind().scalar(sa.text("SELECT COUNT(*) FROM payment_intents WHERE reconciliation_source <> 'LEGACY_UNVERIFIED' OR execution_mode = 'OFFLINE_DEMO'")):
        raise RuntimeError("Cannot downgrade 0017 with payment provenance; retain schema and roll back application code only")
    if op.get_bind().scalar(sa.text("SELECT COUNT(*) FROM webhook_events WHERE provider = 'OFFLINE_DEMO'")):
        raise RuntimeError("Cannot downgrade 0017 with simulation provenance")
    op.execute("DROP TRIGGER IF EXISTS payment_identity_immutable" + (" ON payment_intents" if op.get_bind().dialect.name == "postgresql" else ""))
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP FUNCTION IF EXISTS syncally_payment_identity_immutable()")
    with op.batch_alter_table("payment_intents") as batch:
        batch.drop_constraint("ck_payment_intent_provider_mode", type_="check")
        batch.drop_constraint("ck_payment_intent_reconciliation_source", type_="check")
        batch.drop_column("reconciliation_source")
        batch.drop_column("execution_mode")