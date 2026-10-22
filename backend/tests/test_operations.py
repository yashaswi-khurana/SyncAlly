"""Exercise configured output with hostile content at real request/worker boundaries."""

from __future__ import annotations

import asyncio
import io
import json
import logging
import unittest
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from uuid import UUID, uuid4

import httpx
import test_outbox_dispatcher as workflow_fixtures
import test_payment_outbox as payment_fixtures
from sqlalchemy import select

from syncally.api.main import app
from syncally.api.operations import OperationalFastAPI
from syncally.application.outbox import WorkflowStartPermanentError, WorkflowStartTransientError
from syncally.application.payment_processing import PaymentRetryableError
from syncally.infrastructure.database import get_db
from syncally.infrastructure.models import OutboxEvent
from syncally.infrastructure.outbox import dispatch_one_pending_event
from syncally.infrastructure.payment_outbox import (
    _finish_event,
    claim_next_payment_event,
    dispatch_one_payment_event,
)
from syncally.operations import Operation, configure_logging, correlation_id, log_operation

CANARY = "private-prompt credential bearer refresh-token buyer@example.com https://paypal.com/invoice/p/secret"


@contextmanager
def captured_output():
    root = logging.getLogger()
    root_state = (root.handlers[:], root.level)
    states = [
        (item, item.handlers[:], item.propagate, item.disabled)
        for item in logging.root.manager.loggerDict.values()
        if isinstance(item, logging.Logger)
    ]
    output = io.StringIO()
    with patch("sys.stderr", output):
        configure_logging()
        try:
            yield output
        finally:
            root.handlers, root.level = root_state
            for item, handlers, propagate, disabled in states:
                item.handlers, item.propagate, item.disabled = handlers, propagate, disabled


class SafeOperationsTests(unittest.TestCase):
    def assert_private_values_absent(self, output):
        for value in ("private-prompt", "credential", "bearer", "refresh-token",
                      "buyer@example.com", "paypal.com/invoice/p/secret"):
            self.assertNotIn(value, output)

    def test_actual_output_drops_messages_exceptions_chains_unknown_extras_and_codes(self):
        with captured_output() as output:
            logger = logging.getLogger("uvicorn.error")
            try:
                try:
                    raise ValueError(CANARY)
                except ValueError as error:
                    raise RuntimeError(CANARY) from error
            except RuntimeError:
                logger.exception(CANARY, extra={"private_prompt": CANARY}, stack_info=True)
            log_operation(
                logger,
                Operation.OUTBOX_COMPLETED,
                deal_id=uuid4(),
                status=CANARY,
                error_code=CANARY,
                correlation_id=CANARY,
                next_attempt_at=CANARY,
                retry_count=CANARY,
                payload=CANARY,
            )
            logging.getLogger("httpx").info("HTTP POST %s", CANARY)
            logging.getLogger("sqlalchemy.engine.Engine").warning("%s", CANARY)
            logging.getLogger("uvicorn.access").info("GET /?token=%s", CANARY)
        self.assert_private_values_absent(output.getvalue())
        rows = [json.loads(line) for line in output.getvalue().splitlines() if line.startswith("{")]
        self.assertEqual(rows[0]["event"], "log.redacted")
        self.assertIn("deal_id", rows[1])
        self.assertNotIn("error_code", rows[1])
        self.assertEqual(len(rows), 4)

    def test_api_success_rejections_and_unhandled_error_have_safe_correlated_outcome(self):
        def failed_db():
            raise RuntimeError(CANARY)
            yield

        async def exercise():
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
                base_url="http://test",
            ) as client:
                responses = [
                    await client.get(
                        "/health?token=" + CANARY, headers={"X-Correlation-ID": CANARY}
                    )
                ]
                responses.append(await client.get("/deals"))
                responses.append(await client.post("/auth/login", json={"email": CANARY}))
                responses.append(await client.post("/auth/login", content=CANARY * 1000))
                app.dependency_overrides[get_db] = failed_db
                try:
                    responses.append(await client.get("/health/database"))
                finally:
                    app.dependency_overrides.pop(get_db, None)
                return responses

        with captured_output() as output:
            responses = asyncio.run(exercise())
        self.assertEqual(
            [response.status_code for response in responses], [200, 401, 422, 413, 500]
        )
        ids = [response.headers["x-correlation-id"] for response in responses]
        self.assertEqual(len(set(ids)), 5)
        for value in ids:
            UUID(value)
        self.assert_private_values_absent(output.getvalue())
        rows = [json.loads(line) for line in output.getvalue().splitlines() if line.startswith("{")]
        events = [row for row in rows if row["event"] == "http.completed"]
        self.assertEqual([event["correlation_id"] for event in events], ids)
        self.assertEqual([event["http_status"] for event in events], [200, 401, 422, 413, 500])
        self.assertIsNone(correlation_id.get())

    def test_concurrent_requests_keep_distinct_context_and_reset_after_logging_failure(self):
        local_app = OperationalFastAPI()

        @local_app.get("/work")
        async def work():
            before = correlation_id.get()
            await asyncio.sleep(0)
            self.assertEqual(before, correlation_id.get())
            return {"id": str(before)}

        async def exercise():
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=local_app), base_url="http://test"
            ) as client:
                responses = await asyncio.gather(client.get("/work"), client.get("/work"))
                for response in responses:
                    self.assertEqual(response.json()["id"], response.headers["x-correlation-id"])
                self.assertNotEqual(responses[0].json(), responses[1].json())
                with patch(
                    "syncally.api.operations.log_operation", side_effect=RuntimeError("sink failed")
                ):
                    with self.assertRaises(RuntimeError):
                        await client.get("/work")
                self.assertIsNone(correlation_id.get())

        with captured_output():
            asyncio.run(exercise())

    def test_real_workflow_dispatch_outcomes_redact_and_report_persisted_retry(self):
        for failure, status in [
            (None, "DELIVERED"),
            (WorkflowStartTransientError(CANARY), "PENDING"),
            (WorkflowStartPermanentError(CANARY), "FAILED"),
            (RuntimeError(CANARY), "PENDING"),
        ]:
            with self.subTest(status=status, failure=type(failure).__name__):
                fixture = workflow_fixtures.OutboxDispatcherTests()
                fixture.setUp()
                try:
                    # Agreement events need not use the deal as their aggregate.
                    fixture.session.scalar(select(OutboxEvent)).aggregate_id = uuid4()
                    fixture.session.commit()
                    starter = workflow_fixtures.FakeDealWorkflowStarter(
                        failures=[failure] if failure else []
                    )
                    with captured_output() as output:
                        dispatch_one_pending_event(fixture.session, starter)
                    row = fixture.session.scalar(select(OutboxEvent))
                    event = json.loads(output.getvalue().splitlines()[-1])
                    self.assertEqual(event["status"], row.status)
                    self.assertEqual(event["retry_count"], row.retry_count)
                    self.assertEqual(event["deal_id"], str(fixture.deal.id))
                    self.assertEqual(row.status, status)
                    self.assert_private_values_absent(output.getvalue())
                    self.assert_private_values_absent(row.error_detail or "")
                finally:
                    fixture.tearDown()

    def test_payment_retry_and_stale_lease_report_only_committed_outcomes(self):
        fixture = payment_fixtures.PaymentOutboxWorkerTests()
        fixture.setUp()
        try:
            event_id = fixture._event()
            repository = payment_fixtures.FakeRepository(
                error=PaymentRetryableError("UNKNOWN_PRIVATE_CODE", CANARY)
            )
            with captured_output() as output:
                dispatch_one_payment_event(
                    fixture.session_factory, repository, payment_fixtures.NoCallProvider()
                )
            event = json.loads(output.getvalue().splitlines()[-1])
            self.assertEqual(event["status"], "PENDING")
            self.assertEqual(event["retry_count"], 1)
            self.assertIn("payment_intent_id", event)
            self.assertIn("next_attempt_at", event)
            self.assert_private_values_absent(output.getvalue())
            now = datetime.now(UTC) + timedelta(minutes=10)
            with fixture.session_factory() as db:
                stale = claim_next_payment_event(db, now=now)
            with fixture.session_factory() as db:
                current = claim_next_payment_event(db, now=now + timedelta(minutes=6))
            self.assertEqual(stale.id, current.id)
            with captured_output() as output:
                _finish_event(
                    fixture.session_factory,
                    stale,
                    status="DELIVERED",
                    error_detail=None,
                    retry=False,
                    now=now,
                )
            self.assertEqual(json.loads(output.getvalue())["event"], "payment_outbox.lease_lost")
            with fixture.session_factory() as db:
                self.assertEqual(db.get(OutboxEvent, event_id).status, "PROCESSING")
        finally:
            fixture.tearDown()

    def test_worker_fatal_runtime_error_has_no_raw_traceback(self):
        from syncally.cli import outbox_worker, payment_worker
        from syncally.workflows import worker

        for module, target in [
            (outbox_worker, "run_forever"),
            (payment_worker, "run_forever"),
            (worker, "run_worker"),
        ]:
            with self.subTest(module=module.__name__), captured_output() as output:
                with patch.object(module, target, side_effect=RuntimeError(CANARY)):
                    with self.assertRaises(SystemExit) as raised:
                        module.main()
                self.assertEqual(raised.exception.code, 1)
                self.assert_private_values_absent(output.getvalue())
                self.assertEqual(
                    json.loads(output.getvalue().splitlines()[-1])["event"], "worker.failed"
                )
