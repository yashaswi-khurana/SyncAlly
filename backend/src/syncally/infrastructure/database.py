"""SQLAlchemy engine and session management."""

from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session, sessionmaker

from syncally.config import settings


def create_database_engine(database_url: str, *, echo: bool = False) -> Engine:
    """Create the configured SQLAlchemy engine with SQLite integrity enabled."""
    is_sqlite = make_url(database_url).get_backend_name() == "sqlite"
    engine_options = {"pool_pre_ping": True}
    if not is_sqlite:
        engine_options["pool_timeout"] = 30
    db_engine = create_engine(
        database_url,
        echo=echo,
        connect_args={"timeout": 10} if is_sqlite else {"connect_timeout": 10},
        **engine_options,
    )

    if is_sqlite:

        @event.listens_for(db_engine, "connect")
        def enable_sqlite_foreign_keys(connection, _record) -> None:
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return db_engine


engine = create_database_engine(settings.database_url, echo=settings.debug)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """Yield a database session and roll it back if request handling fails."""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
