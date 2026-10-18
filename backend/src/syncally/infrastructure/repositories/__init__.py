"""Database repository adapters implementing application persistence ports."""

from syncally.infrastructure.repositories.deals import SqlAlchemyDealRepository

__all__ = ["SqlAlchemyDealRepository"]
