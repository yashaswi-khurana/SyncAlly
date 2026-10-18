"""Application engine configuration and safe SQL logging tests."""

import unittest
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from syncally.domain.deals.communications import (
    Message as DomainMessage,
)
from syncally.domain.deals.communications import (
    Visibility,
)
from syncally.domain.shared.identifiers import (
    DealId,
    MessageId,
    OrganizationId,
    UserId,
)
from syncally.infrastructure.database import create_database_engine
from syncally.infrastructure.models import (
    Base,
    Conversation,
    Deal,
    Organization,
    OrganizationMember,
    User,
)
from syncally.infrastructure.repositories import SqlAlchemyCommunicationRepository


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

    def test_echo_logging_hides_message_content_and_source_reference(self) -> None:
        secret_body = "private message content that must never appear in logs"
        secret_source = "sensitive:source-reference"
        with TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "messages.sqlite3"
            database_url = f"sqlite+pysqlite:///{database_path.as_posix()}"
            setup_engine = create_database_engine(database_url)
            logging_engine = None
            try:
                Base.metadata.create_all(setup_engine)
                with Session(setup_engine) as session:
                    buyer = Organization(legal_name="Buyer", country_code="US")
                    seller = Organization(legal_name="Seller", country_code="CA")
                    user = User(email="buyer@example.com", display_name="Buyer")
                    session.add_all([buyer, seller, user])
                    session.flush()
                    deal = Deal(
                        buyer_organization_id=buyer.id,
                        seller_organization_id=seller.id,
                    )
                    session.add(deal)
                    session.flush()
                    conversation = Conversation(
                        deal_id=deal.id,
                        participant_organization_id=buyer.id,
                    )
                    session.add(conversation)
                    session.commit()
                    deal_id = deal.id
                    conversation_id = conversation.id
                    buyer_id = buyer.id
                    user_id = user.id

                logging_engine = create_database_engine(database_url, echo=True)
                with Session(logging_engine) as session:
                    repository = SqlAlchemyCommunicationRepository(session)
                    message = DomainMessage(
                        id=MessageId(uuid4()),
                        conversation_id=conversation_id,
                        deal_id=DealId(deal_id),
                        owner_organization_id=OrganizationId(buyer_id),
                        author_user_id=UserId(user_id),
                        author_agent_id=None,
                        body=secret_body,
                        visibility=Visibility.PRIVATE,
                        source_type="USER",
                        source_reference=secret_source,
                        created_at=datetime.now(UTC),
                    )
                    self.assertNotIn(secret_body, repr(message))
                    self.assertNotIn(secret_source, repr(message))
                    with self.assertLogs(
                        "sqlalchemy.engine.Engine", level="INFO"
                    ) as captured:
                        repository.add_message(message)
                        session.commit()

                emitted_logs = "\n".join(captured.output)
                self.assertNotIn(secret_body, emitted_logs)
                self.assertNotIn(secret_source, emitted_logs)
                self.assertIn("SQL parameters hidden", emitted_logs)
            finally:
                if logging_engine is not None:
                    logging_engine.dispose()
                Base.metadata.drop_all(setup_engine)
                setup_engine.dispose()


if __name__ == "__main__":
    unittest.main()
