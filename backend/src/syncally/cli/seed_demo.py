"""Create the fixed buyer/seller accounts used by the local demo."""

from __future__ import annotations

import getpass
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from syncally.application.passwords import hash_password
from syncally.config import settings
from syncally.infrastructure.database import SessionLocal
from syncally.infrastructure.models import Organization, OrganizationMember, User


@dataclass(frozen=True)
class DemoIdentity:
    email: str
    display_name: str
    organization_name: str


DEMO_IDENTITIES = (
    DemoIdentity("buyer@syncally.demo", "Demo Buyer", "Demo Buyer Co"),
    DemoIdentity("seller@syncally.demo", "Demo Seller", "Demo Seller Co"),
)


def _password_for(
    identity: DemoIdentity, supplied_password: str | None, *, allow_prompt: bool
) -> str:
    if supplied_password is not None:
        password = supplied_password
    elif not allow_prompt:
        raise ValueError(f"A password must be supplied for {identity.email}")
    else:
        password = getpass.getpass(f"Set password for {identity.email} (12+ characters): ")
        confirmation = getpass.getpass("Confirm password: ")
        if password != confirmation:
            raise ValueError("Passwords do not match")
    if len(password) < 12 or len(password) > 128:
        raise ValueError("Passwords must be between 12 and 128 characters")
    return password


def seed_demo_data(
    db: Session,
    passwords: tuple[str | None, str | None] = (None, None),
    *,
    allow_prompt: bool = True,
) -> None:
    """Idempotently create demo users, organizations, and admin memberships."""
    if not settings.is_local_environment:
        raise RuntimeError("Demo seeding is only allowed in development or test")
    try:
        for identity, supplied_password in zip(DEMO_IDENTITIES, passwords, strict=True):
            user = db.scalar(select(User).where(User.email == identity.email))
            if user is None:
                user = User(
                    email=identity.email,
                    display_name=identity.display_name,
                    password_hash=hash_password(
                        _password_for(
                            identity, supplied_password, allow_prompt=allow_prompt
                        )
                    ),
                    status="ACTIVE",
                )
                db.add(user)
                db.flush()
            else:
                if user.status != "ACTIVE":
                    user.status = "ACTIVE"
                if user.password_hash is None:
                    user.password_hash = hash_password(
                        _password_for(
                            identity, supplied_password, allow_prompt=allow_prompt
                        )
                    )

            organization = db.scalar(
                select(Organization).where(
                    Organization.legal_name == identity.organization_name,
                    Organization.country_code == "US",
                )
            )
            if organization is None:
                organization = Organization(
                    legal_name=identity.organization_name,
                    country_code="US",
                    status="ACTIVE",
                )
                db.add(organization)
                db.flush()

            membership = db.scalar(
                select(OrganizationMember).where(
                    OrganizationMember.organization_id == organization.id,
                    OrganizationMember.user_id == user.id,
                )
            )
            if membership is None:
                db.add(
                    OrganizationMember(
                        organization_id=organization.id,
                        user_id=user.id,
                        role="ADMIN",
                        status="ACTIVE",
                    )
                )
            else:
                membership.role = "ADMIN"
                membership.status = "ACTIVE"
        db.commit()
    except Exception:
        db.rollback()
        raise


def main() -> None:
    """Prompt for any missing demo passwords and seed the configured database."""
    if not settings.is_local_environment:
        raise SystemExit("Demo seeding is only allowed in development or test")
    with SessionLocal() as db:
        seed_demo_data(db)
    print("Demo buyer and seller accounts, organizations, and admin memberships are ready.")
    print("Sign in with buyer@syncally.demo or seller@syncally.demo and the password you set.")


if __name__ == "__main__":
    main()
