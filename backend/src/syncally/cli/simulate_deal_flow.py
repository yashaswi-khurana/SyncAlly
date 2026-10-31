"""Standalone CLI simulation script for the full two-sided SyncAlly deal lifecycle.

Performs end-to-end verification across Buyer and Seller roles:
1. Authenticates as Buyer and Seller via JWT credentials.
2. Discovers counterparty in organization directory and creates a draft deal.
3. Posts buyer proposal message into deal conversation.
4. Triggers AI fact suggestion and confirms all extracted terms.
5. Generates proposal draft, records bilateral approvals from both parties.
6. Commits agreement and verifies committed state.
7. Authorizes payment milestone and prints simulated PayPal invoice URL.

Executable directly via:
    python -m syncally.cli.simulate_deal_flow
Or registered console script:
    simulate-deal-flow
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
import warnings
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

import httpx

warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=Warning, module="starlette.*")
warnings.filterwarnings("ignore", message=".*starlette.testclient.*")
warnings.filterwarnings("ignore", message=".*StarletteDeprecationWarning.*")
warnings.filterwarnings("ignore", message=".*httpx.*")
logging.getLogger("syncally").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

DEFAULT_BASE_URL = os.environ.get("SYNCALLY_API_URL", "http://127.0.0.1:8000")
DEFAULT_BUYER_EMAIL = "buyer@syncally.demo"
DEFAULT_BUYER_PASSWORD = os.environ.get("BUYER_PASSWORD", "buyer-password-123")
DEFAULT_SELLER_EMAIL = "seller@syncally.demo"
DEFAULT_SELLER_PASSWORD = os.environ.get("SELLER_PASSWORD", "seller-password-456")
REQUEST_TIMEOUT_SECONDS = 5.0
MAX_TOTAL_RUNTIME_SECONDS = 5.0


class SimulationError(Exception):
    """Raised when an API assertion or simulation invariant is violated."""

    def __init__(self, step: str, message: str, status_code: int | None = None, body: str | None = None) -> None:
        self.step = step
        self.status_code = status_code
        self.body = body
        detail = f"[{step}] {message}"
        if status_code is not None:
            detail += f" (HTTP {status_code})"
        if body:
            detail += f": {body}"
        super().__init__(detail)


class TerminalFormatter:
    """Zero-dependency ANSI color formatter respecting TTY state and NO_COLOR."""

    def __init__(self, enable_color: bool = True) -> None:
        self.enabled = enable_color and sys.stdout.isatty() and not bool(os.environ.get("NO_COLOR"))

    def cyan(self, text: str) -> str:
        return f"\033[36m{text}\033[0m" if self.enabled else text

    def green(self, text: str) -> str:
        return f"\033[32m{text}\033[0m" if self.enabled else text

    def yellow(self, text: str) -> str:
        return f"\033[33m{text}\033[0m" if self.enabled else text

    def red(self, text: str) -> str:
        return f"\033[31m{text}\033[0m" if self.enabled else text

    def magenta(self, text: str) -> str:
        return f"\033[35m{text}\033[0m" if self.enabled else text

    def bold(self, text: str) -> str:
        return f"\033[1m{text}\033[0m" if self.enabled else text


@dataclass
class StepRecord:
    number: int
    name: str
    duration_ms: float
    status: str = "PASS"
    details: str = ""


@dataclass
class DealFlowContext:
    buyer_token: str = ""
    seller_token: str = ""
    buyer_org_id: str = ""
    seller_org_id: str = ""
    deal_id: str = ""
    version_number: int = 1
    terms_hash: str = ""
    payment_intent_id: str = ""
    invoice_url: str = ""


class DealFlowSimulator:
    """Orchestrates and verifies the two-sided deal lifecycle across REST endpoints."""

    def __init__(
        self,
        client: httpx.Client,
        fmt: TerminalFormatter,
        buyer_email: str = DEFAULT_BUYER_EMAIL,
        buyer_password: str = DEFAULT_BUYER_PASSWORD,
        seller_email: str = DEFAULT_SELLER_EMAIL,
        seller_password: str = DEFAULT_SELLER_PASSWORD,
    ) -> None:
        self.client = client
        self.fmt = fmt
        self.buyer_email = buyer_email
        self.buyer_password = buyer_password
        self.seller_email = seller_email
        self.seller_password = seller_password
        self.ctx = DealFlowContext()
        self.step_records: list[StepRecord] = []

    def _auth_header(self, token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}

    def _request(
        self,
        method: str,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
        expected_status: int | tuple[int, ...],
        step_name: str,
    ) -> httpx.Response:
        expected_statuses = (expected_status,) if isinstance(expected_status, int) else expected_status
        req_kwargs: dict[str, Any] = {"headers": headers, "json": json}
        # TestClient does not accept timeout keyword argument in Starlette
        if not hasattr(self.client, "app"):
            req_kwargs["timeout"] = REQUEST_TIMEOUT_SECONDS

        try:
            response = self.client.request(
                method=method,
                url=path,
                **req_kwargs,
            )
        except httpx.RequestError as exc:
            raise SimulationError(step_name, f"Network transport error: {exc}") from exc

        if response.status_code not in expected_statuses:
            raise SimulationError(
                step_name,
                f"Expected status {expected_statuses}, got {response.status_code}",
                status_code=response.status_code,
                body=response.text[:300],
            )
        return response

    def _execute_step(self, number: int, name: str, action: Callable[[], str]) -> None:
        start_time = time.perf_counter()
        print(f"  {self.fmt.cyan(f'[{number}/7]')} {name.ljust(48)}", end="", flush=True)
        try:
            details = action()
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            print(f" {self.fmt.green('[PASS]')} {self.fmt.yellow(f'({duration_ms:.1f}ms)')}")
            if details:
                print(f"        {self.fmt.magenta('↳')} {details}")
            self.step_records.append(StepRecord(number, name, duration_ms, "PASS", details))
        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            print(f" {self.fmt.red('[FAIL]')} {self.fmt.yellow(f'({duration_ms:.1f}ms)')}")
            self.step_records.append(StepRecord(number, name, duration_ms, "FAIL", str(exc)))
            raise

    def step_1_authenticate(self) -> str:
        # Buyer Login
        buyer_resp = self._request(
            "POST",
            "/auth/login",
            json={"email": self.buyer_email, "password": self.buyer_password},
            expected_status=200,
            step_name="Authenticate Buyer",
        )
        buyer_data = buyer_resp.json()
        if "access_token" not in buyer_data:
            raise SimulationError("Authenticate Buyer", "Missing access_token in response")
        self.ctx.buyer_token = buyer_data["access_token"]

        # Seller Login
        seller_resp = self._request(
            "POST",
            "/auth/login",
            json={"email": self.seller_email, "password": self.seller_password},
            expected_status=200,
            step_name="Authenticate Seller",
        )
        seller_data = seller_resp.json()
        if "access_token" not in seller_data:
            raise SimulationError("Authenticate Seller", "Missing access_token in response")
        self.ctx.seller_token = seller_data["access_token"]

        return f"Buyer ({self.buyer_email}) and Seller ({self.seller_email}) tokens acquired"

    def step_2_directory_and_create_deal(self) -> str:
        # Buyer checks own organization
        my_orgs_resp = self._request(
            "GET",
            "/organizations",
            headers=self._auth_header(self.ctx.buyer_token),
            expected_status=200,
            step_name="List Buyer Organizations",
        )
        buyer_orgs = my_orgs_resp.json()
        if not buyer_orgs:
            raise SimulationError("List Buyer Organizations", "Buyer has no active organizations")
        self.ctx.buyer_org_id = str(buyer_orgs[0]["id"])

        # Buyer searches directory for seller counterparty
        directory_resp = self._request(
            "GET",
            "/organizations/directory?q=Seller",
            headers=self._auth_header(self.ctx.buyer_token),
            expected_status=200,
            step_name="Search Counterparty Directory",
        )
        directory_entries = directory_resp.json()
        if not directory_entries:
            # Fallback to searching without query filter
            directory_resp = self._request(
                "GET",
                "/organizations/directory",
                headers=self._auth_header(self.ctx.buyer_token),
                expected_status=200,
                step_name="Search Counterparty Directory (All)",
            )
            directory_entries = directory_resp.json()

        # Find an organization different from buyer_org_id
        seller_org_id = None
        seller_org_name = None
        for entry in directory_entries:
            if str(entry["id"]) != self.ctx.buyer_org_id:
                seller_org_id = str(entry["id"])
                seller_org_name = entry.get("legal_name", "Counterparty")
                break

        if not seller_org_id:
            raise SimulationError("Search Counterparty Directory", "No counterparty organization found")
        self.ctx.seller_org_id = seller_org_id

        # Buyer creates deal
        deal_resp = self._request(
            "POST",
            "/deals",
            headers=self._auth_header(self.ctx.buyer_token),
            json={
                "buyer_organization_id": self.ctx.buyer_org_id,
                "seller_organization_id": self.ctx.seller_org_id,
            },
            expected_status=201,
            step_name="Create Deal",
        )
        deal_data = deal_resp.json()
        self.ctx.deal_id = str(deal_data["id"])
        return f"Deal {self.ctx.deal_id} created with {seller_org_name}"

    def step_3_post_proposal_message(self) -> str:
        message_body = "Item: Widget, 12 boxes at USD 2.50, deliver to Toronto by 2026-12-01."
        msg_resp = self._request(
            "POST",
            f"/deals/{self.ctx.deal_id}/messages",
            headers=self._auth_header(self.ctx.buyer_token),
            json={"body": message_body, "visibility": "SHAREABLE"},
            expected_status=201,
            step_name="Post Buyer Proposal Message",
        )
        msg_id = msg_resp.json().get("id")
        return f"Message {msg_id} posted with terms: '{message_body}'"

    def step_4_suggest_and_confirm_facts(self) -> str:
        # Trigger fact suggestion
        facts_resp = self._request(
            "POST",
            f"/deals/{self.ctx.deal_id}/ai/facts",
            headers=self._auth_header(self.ctx.buyer_token),
            json={"organization_id": self.ctx.buyer_org_id},
            expected_status=200,
            step_name="Trigger Fact Suggestion",
        )
        facts_data = facts_resp.json()
        facts_list = facts_data.get("facts", [])
        if not facts_list:
            raise SimulationError("Trigger Fact Suggestion", "AI fact suggestion returned 0 terms")

        # Confirm each fact
        confirmed_count = 0
        for fact in facts_list:
            fact_id = fact["id"]
            self._request(
                "POST",
                f"/deals/{self.ctx.deal_id}/facts/{fact_id}/confirm",
                headers=self._auth_header(self.ctx.buyer_token),
                expected_status=200,
                step_name=f"Confirm Fact {fact_id}",
            )
            confirmed_count += 1

        return f"Extracted and confirmed {confirmed_count} commercial facts ({', '.join(f['field'] for f in facts_list)})"

    def step_5_draft_and_approve_agreement(self) -> str:
        # Suggest proposal draft
        proposal_resp = self._request(
            "POST",
            f"/deals/{self.ctx.deal_id}/ai/proposal",
            headers=self._auth_header(self.ctx.buyer_token),
            json={"organization_id": self.ctx.buyer_org_id},
            expected_status=200,
            step_name="Suggest Proposal Draft",
        )
        proposal_data = proposal_resp.json()
        if proposal_data.get("status") not in ("DRAFT", "VALID", "PROPOSED"):
            raise SimulationError(
                "Suggest Proposal Draft",
                f"Unexpected proposal status: {proposal_data.get('status')}",
                body=str(proposal_data),
            )

        # Create agreement draft from reviewed terms
        reviewed_payload = {
            key: value
            for key, value in proposal_data.items()
            if key != "status"
        }
        reviewed_payload["payment_trigger"] = "seller_invoice"
        reviewed_payload["organization_id"] = self.ctx.buyer_org_id

        draft_resp = self._request(
            "POST",
            f"/deals/{self.ctx.deal_id}/agreements/from-reviewed-terms",
            headers=self._auth_header(self.ctx.buyer_token),
            json=reviewed_payload,
            expected_status=201,
            step_name="Create Reviewed Agreement Draft",
        )
        draft_data = draft_resp.json()
        self.ctx.version_number = draft_data["version_number"]
        self.ctx.terms_hash = draft_data["terms_hash"]

        # Buyer approves
        self._request(
            "POST",
            f"/deals/{self.ctx.deal_id}/agreements/{self.ctx.version_number}/approve",
            headers=self._auth_header(self.ctx.buyer_token),
            json={"terms_hash": self.ctx.terms_hash},
            expected_status=200,
            step_name="Approve Agreement (Buyer)",
        )

        # Seller approves
        self._request(
            "POST",
            f"/deals/{self.ctx.deal_id}/agreements/{self.ctx.version_number}/approve",
            headers=self._auth_header(self.ctx.seller_token),
            json={"terms_hash": self.ctx.terms_hash},
            expected_status=200,
            step_name="Approve Agreement (Seller)",
        )

        return f"Version {self.ctx.version_number} drafted and bilaterally approved (hash: {self.ctx.terms_hash[:12]}...)"

    def step_6_commit_and_verify_agreement(self) -> str:
        # Commit agreement
        commit_resp = self._request(
            "POST",
            f"/deals/{self.ctx.deal_id}/agreements/{self.ctx.version_number}/commit",
            headers=self._auth_header(self.ctx.buyer_token),
            json={"terms_hash": self.ctx.terms_hash},
            expected_status=200,
            step_name="Commit Agreement",
        )
        commit_data = commit_resp.json()
        if commit_data.get("status") != "COMMITTED":
            raise SimulationError("Commit Agreement", f"Agreement status is not COMMITTED: {commit_data.get('status')}")

        # Verify commitment state independently
        current_resp = self._request(
            "GET",
            f"/deals/{self.ctx.deal_id}/agreements/current",
            headers=self._auth_header(self.ctx.buyer_token),
            expected_status=200,
            step_name="Verify Agreement Commitment",
        )
        current_data = current_resp.json()
        if current_data.get("status") != "COMMITTED":
            raise SimulationError("Verify Agreement Commitment", f"Agreement status read is {current_data.get('status')}")

        committed_at = current_data.get("committed_at", "N/A")
        return f"Agreement v{self.ctx.version_number} committed successfully at {committed_at}"

    def step_7_authorize_payment_milestone(self) -> str:
        idempotency_key = f"sim-pay-{uuid4()}"
        pay_resp = self._request(
            "POST",
            f"/deals/{self.ctx.deal_id}/payments",
            headers=self._auth_header(self.ctx.seller_token),
            json={"idempotency_key": idempotency_key},
            expected_status=202,
            step_name="Authorize Payment Milestone",
        )
        pay_data = pay_resp.json()
        self.ctx.payment_intent_id = str(pay_data["id"])

        # Read payment statuses
        status_resp = self._request(
            "GET",
            f"/deals/{self.ctx.deal_id}/payments",
            headers=self._auth_header(self.ctx.buyer_token),
            expected_status=200,
            step_name="Read Payment Statuses",
        )
        statuses = status_resp.json()
        simulated_invoice_id = f"INV2-SIM-{self.ctx.payment_intent_id[:8].upper()}"
        default_invoice_url = f"https://www.sandbox.paypal.com/invoice/p/#{simulated_invoice_id}"

        if statuses and statuses[0].get("invoice_url"):
            self.ctx.invoice_url = statuses[0]["invoice_url"]
        else:
            self.ctx.invoice_url = default_invoice_url

        return f"PaymentIntent: {self.ctx.payment_intent_id} | Invoice URL: {self.ctx.invoice_url}"

    def run(self) -> int:
        print(f"\n{self.fmt.bold('======================================================================')}")
        print(f"{self.fmt.bold('   SyncAlly End-to-End Deal Flow Simulation (Dual-Role Sandbox)')}")
        print(f"{self.fmt.bold('======================================================================')}")

        overall_start = time.perf_counter()

        steps: list[tuple[int, str, Callable[[], str]]] = [
            (1, "Authenticate as Buyer & Seller", self.step_1_authenticate),
            (2, "Search Directory & Create Deal", self.step_2_directory_and_create_deal),
            (3, "Post Buyer Proposal Message", self.step_3_post_proposal_message),
            (4, "Trigger Fact Suggestion & Confirm Terms", self.step_4_suggest_and_confirm_facts),
            (5, "Generate Proposal & Approve Agreement", self.step_5_draft_and_approve_agreement),
            (6, "Commit Agreement & Verify Status", self.step_6_commit_and_verify_agreement),
            (7, "Authorize Payment & Print PayPal URL", self.step_7_authorize_payment_milestone),
        ]

        try:
            for num, name, action in steps:
                self._execute_step(num, name, action)
        except SimulationError as err:
            total_duration_s = time.perf_counter() - overall_start
            print(f"\n{self.fmt.red(self.fmt.bold('SIMULATION ABORTED WITH ERROR:'))}")
            print(f"  {self.fmt.red(str(err))}")
            print(f"\nTotal Elapsed Time: {total_duration_s:.3f}s (Failed at Step {self.step_records[-1].number if self.step_records else 0})")
            return 1
        except Exception as exc:
            total_duration_s = time.perf_counter() - overall_start
            print(f"\n{self.fmt.red(self.fmt.bold('UNHANDLED SIMULATION EXCEPTION:'))}")
            print(f"  {self.fmt.red(repr(exc))}")
            print(f"\nTotal Elapsed Time: {total_duration_s:.3f}s")
            return 1

        total_duration_s = time.perf_counter() - overall_start

        print(f"\n{self.fmt.bold('----------------------------------------------------------------------')}")
        print(f"{self.fmt.bold('Simulation Checkpoints Summary:')}")
        for rec in self.step_records:
            print(f"  Step {rec.number}: {rec.name.ljust(42)} {self.fmt.green(rec.status)} [{rec.duration_ms:6.1f}ms]")

        print(f"\n{self.fmt.bold('Artifacts Produced:')}")
        print(f"  Deal ID:             {self.fmt.cyan(self.ctx.deal_id)}")
        print(f"  Agreement Version:   {self.fmt.cyan(str(self.ctx.version_number))}")
        print(f"  Terms Hash:          {self.fmt.cyan(self.ctx.terms_hash)}")
        print(f"  Payment Intent ID:   {self.fmt.cyan(self.ctx.payment_intent_id)}")
        print(f"  PayPal Invoice URL:  {self.fmt.green(self.ctx.invoice_url)}")

        timing_color = self.fmt.green if total_duration_s < MAX_TOTAL_RUNTIME_SECONDS else self.fmt.red
        print(f"\nTotal Duration: {timing_color(f'{total_duration_s:.3f}s')} (Target: < {MAX_TOTAL_RUNTIME_SECONDS:.1f}s)")

        if total_duration_s >= MAX_TOTAL_RUNTIME_SECONDS:
            print(f"{self.fmt.red(f'WARNING: Simulation exceeded maximum target budget of {MAX_TOTAL_RUNTIME_SECONDS}s')}")
            return 1

        print(f"{self.fmt.green(self.fmt.bold('✔ DEAL LIFECYCLE SIMULATION COMPLETED SUCCESSFULLY (EXIT 0)'))}\n")
        return 0


def _build_in_process_client(
    buyer_password: str, seller_password: str
) -> tuple[httpx.Client, Callable[[], None]]:
    """Construct an in-process ASGI test harness with an isolated SQLite database."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from sqlalchemy.pool import StaticPool
    from starlette.testclient import TestClient

    from syncally.api.main import app
    from syncally.cli.seed_demo import seed_demo_data
    from syncally.config import settings
    from syncally.infrastructure.database import get_db
    from syncally.infrastructure.models import Base

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = Session(engine, expire_on_commit=False)

    original_env = settings.app_env
    settings.app_env = "test"

    seed_demo_data(session, (buyer_password, seller_password))

    app.dependency_overrides[get_db] = lambda: session

    def cleanup() -> None:
        app.dependency_overrides.clear()
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()
        settings.app_env = original_env

    client = TestClient(app=app, base_url="http://testserver")
    return client, cleanup


def _is_live_backend_healthy(base_url: str) -> bool:
    """Probe /health on the target backend."""
    try:
        with httpx.Client(base_url=base_url, timeout=1.5) as probe:
            resp = probe.get("/health")
            return resp.status_code == 200
    except Exception:
        return False


def run_simulation(
    base_url: str = DEFAULT_BASE_URL,
    buyer_email: str = DEFAULT_BUYER_EMAIL,
    buyer_password: str = DEFAULT_BUYER_PASSWORD,
    seller_email: str = DEFAULT_SELLER_EMAIL,
    seller_password: str = DEFAULT_SELLER_PASSWORD,
    in_process: bool = False,
    enable_color: bool = True,
) -> int:
    """Execute the full deal flow simulation and return the exit code."""
    fmt = TerminalFormatter(enable_color=enable_color)
    cleanup_fn: Callable[[], None] | None = None

    if in_process:
        print(fmt.cyan("[Mode] Running via in-process ASGI engine (isolated SQLite test harness)..."))
        client, cleanup_fn = _build_in_process_client(buyer_password, seller_password)
    else:
        # Check if live server is reachable
        print(fmt.cyan(f"[Mode] Probing target backend at {base_url}..."))
        if _is_live_backend_healthy(base_url):
            print(fmt.green(f"[Mode] Connected to live backend at {base_url}"))
            client = httpx.Client(base_url=base_url, timeout=REQUEST_TIMEOUT_SECONDS)
        else:
            print(fmt.yellow(f"[Mode] Live backend at {base_url} is unreachable."))
            print(fmt.cyan("[Mode] Automatically falling back to in-process FastAPI engine for CI/standalone run..."))
            client, cleanup_fn = _build_in_process_client(buyer_password, seller_password)

    try:
        simulator = DealFlowSimulator(
            client=client,
            fmt=fmt,
            buyer_email=buyer_email,
            buyer_password=buyer_password,
            seller_email=seller_email,
            seller_password=seller_password,
        )
        return simulator.run()
    finally:
        client.close()
        if cleanup_fn is not None:
            cleanup_fn()


def ci_deal_flow_hook() -> int:
    """Automated CI integration hook for test runners or pre-commit scripts.

    Returns:
        0 on success, 1 on failure.
    """
    return run_simulation(in_process=True, enable_color=False)


def main(argv: list[str] | None = None) -> None:
    """Entry point for terminal execution."""
    parser = argparse.ArgumentParser(
        description="SyncAlly two-sided automated deal flow simulation",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help="Base URL of the running FastAPI backend",
    )
    parser.add_argument(
        "--buyer-email",
        default=DEFAULT_BUYER_EMAIL,
        help="Buyer demo account email",
    )
    parser.add_argument(
        "--buyer-password",
        default=DEFAULT_BUYER_PASSWORD,
        help="Buyer demo account password",
    )
    parser.add_argument(
        "--seller-email",
        default=DEFAULT_SELLER_EMAIL,
        help="Seller demo account email",
    )
    parser.add_argument(
        "--seller-password",
        default=DEFAULT_SELLER_PASSWORD,
        help="Seller demo account password",
    )
    parser.add_argument(
        "--in-process",
        action="store_true",
        help="Force execution against in-process FastAPI app with isolated test DB",
    )
    parser.add_argument(
        "--ci",
        action="store_true",
        help="Execute in CI mode (in-process, headless, strictly zero-daemon)",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable ANSI color output",
    )

    args = parser.parse_args(argv)

    is_in_process = args.in_process or args.ci
    enable_color = not args.no_color

    exit_code = run_simulation(
        base_url=args.base_url,
        buyer_email=args.buyer_email,
        buyer_password=args.buyer_password,
        seller_email=args.seller_email,
        seller_password=args.seller_password,
        in_process=is_in_process,
        enable_color=enable_color,
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
