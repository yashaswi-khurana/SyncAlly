"""Temporal activities that perform database work for the deal workflow.

Activities are the only place workflow processes touch persistence. Every
activity reloads authoritative records from saved identifiers and ignores any
business state captured in older workflow input. Transient database errors are
left to Temporal's bounded retry policy; permanent validation and business
rejections are raised as non-retryable ``ApplicationError`` types.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from typing import Any

from sqlalchemy.orm import Session
from temporalio import activity
from temporalio.exceptions import ApplicationError

from syncally.application.workflow_notifications import DealWorkflowNotification
from syncally.application.workflow_state import (
    load_deal_workflow_state,
    parse_workflow_uuid,
)
from syncally.domain.shared.errors import DomainError
from syncally.infrastructure.repositories.agreements import SqlAlchemyAgreementRepository
from syncally.infrastructure.repositories.deals import SqlAlchemyDealRepository
from syncally.operations import Operation, log_operation
from syncally.workflows.deal import REFRESH_DEAL_STATE_ACTIVITY
from syncally.workflows.errors import (
    BUSINESS_REJECTION_ERROR_TYPE,
    VALIDATION_ERROR_TYPE,
)

logger = logging.getLogger(__name__)

SessionFactory = Callable[[], Session]


class RefreshDealStateActivity:
    """Reload persisted deal state after a workflow wake-up notification."""

    def __init__(self, session_factory: SessionFactory | None = None) -> None:
        if session_factory is None:
            from syncally.infrastructure.database import SessionLocal

            session_factory = SessionLocal
        self._session_factory = session_factory

    @activity.defn(name=REFRESH_DEAL_STATE_ACTIVITY)
    def refresh_deal_state(
        self,
        workflow_input: Any,
        notification: DealWorkflowNotification,
    ) -> bool:
        """Return whether the reloaded deal has reached a terminal status.

        ``notification`` is only a wake-up hint. It is intentionally not used
        to decide current approval, version, or payment state.
        """
        try:
            deal_id = parse_workflow_uuid(
                _workflow_input_value(workflow_input, "deal_id"), "deal_id"
            )
            with self._session_factory() as db:
                state = load_deal_workflow_state(
                    deal_id,
                    SqlAlchemyDealRepository(db),
                    SqlAlchemyAgreementRepository(db),
                )
                log_operation(
                    logger,
                    Operation.ACTIVITY_COMPLETED,
                    deal_id=deal_id,
                    terminal=state.is_terminal,
                    attempt=activity.info().attempt if activity.in_activity() else 1,
                )
                return state.is_terminal
        except DomainError as error:
            raise ApplicationError(
                str(error),
                type=BUSINESS_REJECTION_ERROR_TYPE,
                non_retryable=True,
            ) from error
        except ValueError as error:
            raise ApplicationError(
                str(error),
                type=VALIDATION_ERROR_TYPE,
                non_retryable=True,
            ) from error


def _workflow_input_value(workflow_input: Any, field_name: str) -> Any:
    if isinstance(workflow_input, Mapping):
        return workflow_input.get(field_name)
    return getattr(workflow_input, field_name, None)
