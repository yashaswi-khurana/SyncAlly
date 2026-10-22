"""Allowlisted operational output. Never format arbitrary messages or exception text."""

from __future__ import annotations

import json
import logging
from contextvars import ContextVar
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID

correlation_id: ContextVar[UUID | None] = ContextVar("correlation_id", default=None)


class Operation(StrEnum):
    HTTP_COMPLETED = "http.completed"
    OUTBOX_COMPLETED = "outbox.completed"
    PAYMENT_OUTBOX_COMPLETED = "payment_outbox.completed"
    PAYMENT_STATE_CHANGED = "payment.state_changed"
    PAYMENT_LEASE_LOST = "payment_outbox.lease_lost"
    ACTIVITY_COMPLETED = "workflow.activity_completed"
    WORKER_STARTED = "worker.started"
    WORKER_FAILED = "worker.failed"
    CONNECTION_RETRY = "worker.connection_retry"
    CONNECTION_FAILED = "worker.connection_failed"


_STATUSES = frozenset({"PENDING", "PROCESSING", "DELIVERED", "FAILED"})
_EVENT_TYPES = frozenset(
    {
        "AGREEMENT_COMMITTED",
        "DEAL_NOTIFICATION",
        "PAYMENT_INTENT_AUTHORIZED",
        "PAYPAL_WEBHOOK_RECONCILIATION",
    }
)
_PAYMENT_STATUSES = frozenset(
    {
        "AUTHORIZED",
        "CREATE_PENDING",
        "CREATE_UNKNOWN",
        "PROVIDER_CREATED",
        "SENT",
        "PENDING",
        "PARTIALLY_PAID",
        "PAID",
        "FAILED",
        "CANCELLED",
    }
)
_ERROR_CODES = frozenset(
    {
        "PAYMENT_OUTBOX_PAYLOAD_INVALID",
        "PAYMENT_INTENT_NOT_FOUND",
        "PAYMENT_PROVIDER_REFERENCE_MISSING",
        "PAYPAL_INVOICE_NOTICE_MISMATCH",
        "PAYMENT_INVOICE_REQUEST_CHANGED",
        "PAYMENT_CREATE_TIME_UNKNOWN",
        "PAYMENT_CREATE_RETRY_WINDOW_EXPIRED",
        "PAYMENT_PROVIDER_STATE_UNSUPPORTED",
        "PAYMENT_BUYER_CONTACT_MISSING",
        "PAYMENT_BUYER_CONTACT_AMBIGUOUS",
        "PAYMENT_RECONCILIATION_REJECTED",
        "PAYMENT_TERMINAL_STATE_CONFLICT",
        "PAYPAL_RECONCILIATION_MISMATCH",
        "PAYPAL_INVOICE_MATCH_MISMATCH",
        "PAYPAL_INVOICE_MATCH_AMBIGUOUS",
        "PAYPAL_SEARCH_RESPONSE_INVALID",
        "PAYPAL_INVOICE_ID_MISMATCH",
        "PAYPAL_AUTH_FAILED",
        "PAYMENT_PROVIDER_REFERENCE_CONFLICT",
        "PAYMENT_STATE_CHANGED",
        "PAYPAL_TEMPORARILY_UNAVAILABLE",
        "GMAIL_TEMPORARILY_UNAVAILABLE",
        "PAYPAL_OUTCOME_UNKNOWN",
    }
)
_WORKERS = frozenset({"workflow", "outbox", "payment"})
_UUID_FIELDS = ("correlation_id", "deal_id", "payment_intent_id", "outbox_event_id")
_WORKFLOW_MESSAGES = {
    "Deal workflow wait expired; deal requires operational review": "workflow.wait_expired",
    "Deal workflow refresh timed out at its deadline": "workflow.refresh_timed_out",
}


def _uuid(value: object) -> str | None:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, str) and len(value) == 36:
        try:
            parsed = UUID(value)
            return str(parsed) if str(parsed) == value else None
        except ValueError:
            pass
    return None


class SafeOperationalFormatter(logging.Formatter):
    """Project approved values only, including for third-party and exception logs.

    A field name alone is not a privacy guarantee. IDs, enum values and numbers
    are validated; arbitrary message, args, extras, stack and exception text are
    deliberately never rendered. Unknown records retain severity and component.
    """

    def format(self, record: logging.LogRecord) -> str:
        event = record.__dict__.get("operation")
        approved = isinstance(event, Operation)
        output: dict[str, object] = {
            "time": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": logging.getLevelName(record.levelno)
            if record.levelno in (10, 20, 30, 40, 50)
            else "UNKNOWN",
            "component": next(
                (
                    name
                    for name in ("syncally", "uvicorn", "temporalio", "sqlalchemy", "httpx")
                    if record.name == name or record.name.startswith(name + ".")
                ),
                "external",
            ),
            "event": event.value if approved else "log.redacted",
        }
        if not approved and isinstance(record.msg, str) and record.msg in _WORKFLOW_MESSAGES:
            output["event"] = _WORKFLOW_MESSAGES[record.msg]
            approved = True
        current_id = _uuid(correlation_id.get())
        if current_id is not None:
            output["correlation_id"] = current_id
        if approved:
            for key in _UUID_FIELDS:
                value = _uuid(record.__dict__.get(key))
                if value is not None:
                    output[key] = value
            if "deal_id" in output:
                output["workflow_id"] = f"deal/{output['deal_id']}/lifecycle"
            for key, values in (
                ("status", _STATUSES),
                ("event_type", _EVENT_TYPES),
                ("worker", _WORKERS),
                ("payment_status", _PAYMENT_STATUSES),
                ("error_code", _ERROR_CODES),
            ):
                value = record.__dict__.get(key)
                if isinstance(value, str) and value in values:
                    output[key] = value
            failure_kind = record.__dict__.get("failure_kind")
            if failure_kind in ("TRANSIENT", "PERMANENT", "UNEXPECTED"):
                output["failure_kind"] = failure_kind
            for key in ("retry_count", "http_status", "duration_ms", "attempt"):
                value = record.__dict__.get(key)
                if type(value) is int and 0 <= value <= 2**63 - 1:
                    output[key] = value
            next_attempt = record.__dict__.get("next_attempt_at")
            if isinstance(next_attempt, datetime):
                output["next_attempt_at"] = next_attempt.isoformat()
            if type(record.__dict__.get("terminal")) is bool:
                output["terminal"] = record.__dict__["terminal"]
        return json.dumps(output, separators=(",", ":"))


def log_operation(
    logger: logging.Logger, event: Operation, *, level: int = logging.INFO, **fields: object
) -> None:
    logger.log(level, "", extra={"operation": event, **fields})


def configure_logging() -> None:
    """Own console output for a process; replace existing library handlers too.

    Invoke after application imports and before serving/starting worker loops.
    Collectors or handlers installed later must preserve this same policy.
    """
    handler = logging.StreamHandler()
    handler.setFormatter(SafeOperationalFormatter())
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(logging.INFO)
    for item in logging.root.manager.loggerDict.values():
        if isinstance(item, logging.Logger):
            item.handlers.clear()
            item.propagate = True
    # Safe http.completed replaces URL/query-bearing Uvicorn access records.
    logging.getLogger("uvicorn.access").disabled = True
