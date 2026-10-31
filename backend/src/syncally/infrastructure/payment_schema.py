"""SQLite payment identity DDL shared by migrations and fresh ORM schemas."""

SQLITE_PAYMENT_IDENTITY_TRIGGER = """CREATE TRIGGER payment_identity_immutable BEFORE UPDATE OF provider, execution_mode ON payment_intents
        WHEN NEW.provider <> OLD.provider OR NEW.execution_mode <> OLD.execution_mode
        BEGIN SELECT RAISE(ABORT, 'payment provider and mode are immutable'); END"""