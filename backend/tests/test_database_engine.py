"""Application engine configuration tests."""

import unittest
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from syncally.infrastructure.database import create_database_engine
from syncally.infrastructure.models import Base, OrganizationMember


class DatabaseEngineTests(unittest.TestCase):
    def test_sqlite_engine_enforces_foreign_keys(self) -> None:
        engine = create_database_engine("sqlite+pysqlite:///:memory:")
        try:
            Base.metadata.create_all(engine)
            with Session(engine) as session, self.assertRaises(IntegrityError):
                session.add(
                    OrganizationMember(
                        organization_id=uuid4(),
                        user_id=uuid4(),
                        role="MEMBER",
                        status="ACTIVE",
                    )
                )
                session.commit()
        finally:
            Base.metadata.drop_all(engine)
            engine.dispose()


if __name__ == "__main__":
    unittest.main()
