"""Tests for Step 11 Judge Demo full two-party journey simulation."""

from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from syncally.cli.simulate_deal_flow import run_simulation


class JudgeDemoSimulationTests(unittest.TestCase):
    def test_judge_demo_full_journey_in_process(self) -> None:
        """Verify all 12 checkpoints of the two-party judge journey pass in-process."""
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = run_simulation(
                in_process=True,
                offline=True,
                enable_color=False,
            )
        stdout = output.getvalue()
        self.assertEqual(exit_code, 0, stdout)

        # Verify key milestone checkpoints are documented in summary
        self.assertIn("Step 1: Authenticate as Buyer & Seller", stdout)
        self.assertIn("Step 2: Search Directory & Create Deal", stdout)
        self.assertIn("Step 3: Post Buyer Proposal Message", stdout)
        self.assertIn("Step 4: Trigger Fact Suggestion & Confirm Terms", stdout)
        self.assertIn("Step 5: Generate Proposal & Approve Agreement", stdout)
        self.assertIn("Step 6: Commit Agreement & Verify Status", stdout)
        self.assertIn("Step 7: Authorize Payment & Read Stored Invoice", stdout)
        self.assertIn("Step 8: Simulate Offline Payment Reconciliation", stdout)
        self.assertIn("Step 9: Record Partial Fulfillment & Verify Completion", stdout)
        self.assertIn("Step 10: Assess Impact & Commit Agreement Amendment v2", stdout)
        self.assertIn("Step 11: Raise Dispute Deal Case & Record Consent", stdout)
        self.assertIn("Step 12: Sync Reminders & Export F12 Trade Pack", stdout)

        # Verify required artifact lines
        self.assertIn("Payment Mode:        OFFLINE_DEMO", stdout)
        self.assertIn("Invoice Reference:   OFFLINE-", stdout)
        self.assertIn("Payment State:       SENT (queued/sent is not paid)", stdout)
        self.assertIn("Reconciled State:    PAID (reconciliation_source=OFFLINE_DEMO)", stdout)
        self.assertIn("Amended Version:     2", stdout)
        self.assertIn("DEAL LIFECYCLE SIMULATION COMPLETED SUCCESSFULLY", stdout)

    def test_judge_demo_is_idempotent(self) -> None:
        """Verify running simulation sequentially in fresh in-process harnesses is reproducible."""
        with redirect_stdout(io.StringIO()):
            self.assertEqual(run_simulation(in_process=True, offline=True, enable_color=False), 0)
            self.assertEqual(run_simulation(in_process=True, offline=True, enable_color=False), 0)

    def test_unreachable_backend_fails_closed(self) -> None:
        """Live simulation without explicit offline/in_process must fail closed without fallback."""
        with redirect_stdout(io.StringIO()), patch("syncally.cli.simulate_deal_flow._is_live_backend_healthy", return_value=False):
            self.assertEqual(run_simulation(in_process=False, offline=False), 1)
