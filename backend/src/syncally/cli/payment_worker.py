"""Explicit operator-only Sandbox entry point; stage integration stays opt-in."""

import argparse
import logging
import time
from uuid import UUID

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from syncally.infrastructure.database import SessionLocal
from syncally.infrastructure.paypal.adapter import SandboxPayPalAdapter
from syncally.infrastructure.paypal.worker import (
    SandboxMerchant,
    authorize_sandbox_issuance,
    dispatch_one_payment,
)


class SandboxSettings(BaseSettings):
    paypal_sandbox_client_id: SecretStr
    paypal_sandbox_client_secret: SecretStr
    paypal_sandbox_seller_organization_id: UUID
    paypal_sandbox_buyer_organization_id: UUID
    paypal_sandbox_seller_email: str
    paypal_sandbox_buyer_email: str
    model_config = SettingsConfigDict(extra="ignore")  # Environment/secrets injection only.


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stage-gate-verified",
        action="store_true",
        help="Operator attests #29–#32 and Stage 6 exit check are complete",
    )
    parser.add_argument("--authorize-intent", type=UUID)
    parser.add_argument("--seller-user-id", type=UUID)
    args = parser.parse_args()
    if not args.stage_gate_verified:
        parser.error("Stage 6 integration gate must be verified before Sandbox operation")
    if bool(args.authorize_intent) != bool(args.seller_user_id):
        parser.error("--authorize-intent and --seller-user-id must be provided together")
    try:
        settings = SandboxSettings()
    except ValueError:
        parser.error("Required Sandbox configuration is missing or invalid")
    merchant = SandboxMerchant(
        settings.paypal_sandbox_seller_organization_id,
        settings.paypal_sandbox_buyer_organization_id,
        settings.paypal_sandbox_seller_email,
        settings.paypal_sandbox_buyer_email,
    )
    if args.authorize_intent:
        authorize_sandbox_issuance(
            SessionLocal, args.authorize_intent, args.seller_user_id, merchant
        )
        return
    logging.basicConfig(level=logging.INFO)
    adapter = SandboxPayPalAdapter(
        settings.paypal_sandbox_client_id, settings.paypal_sandbox_client_secret
    )
    try:
        while True:
            try:
                dispatch_one_payment(SessionLocal, adapter, merchant)
            except Exception:
                # No raw exception: it could contain a provider request/token.
                logging.error("Payment worker iteration interrupted; lease recovery will reconcile")
            time.sleep(2)
    finally:
        adapter.close()


if __name__ == "__main__":
    main()
