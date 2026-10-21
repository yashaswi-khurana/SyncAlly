import io
import unittest
from contextlib import redirect_stderr
from unittest.mock import patch

from syncally.cli.payment_worker import main


class PaymentWorkerCliTests(unittest.TestCase):
    def test_startup_gate_runs_before_credentials_or_database_access(self):
        with patch("sys.argv", ["payment_worker"]), redirect_stderr(io.StringIO()):
            with patch("syncally.cli.payment_worker.SandboxSettings") as config:
                with self.assertRaises(SystemExit) as result:
                    main()
                self.assertEqual(result.exception.code, 2)
                config.assert_not_called()

    def test_invalid_config_error_does_not_echo_secrets(self):
        output = io.StringIO()
        with (
            patch("sys.argv", ["payment_worker", "--stage-gate-verified"]),
            redirect_stderr(output),
        ):
            with patch(
                "syncally.cli.payment_worker.SandboxSettings",
                side_effect=ValueError("secret-test-value"),
            ):
                with self.assertRaises(SystemExit):
                    main()
        self.assertNotIn("secret-test-value", output.getvalue())
