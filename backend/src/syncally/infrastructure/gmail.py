"""Optional Gmail SMTP delivery for PayPal invoice notifications."""

from __future__ import annotations

import smtplib
import ssl
from datetime import UTC, datetime
from email.message import EmailMessage
from html import escape
from urllib.parse import urlsplit

from syncally.application.payment_processing import (
    PaymentInvoiceNotice,
    PaymentNeedsAction,
    PaymentRetryableError,
)
from syncally.domain.shared.money import canonical_decimal

_GMAIL_SMTP_HOST = "smtp.gmail.com"
_GMAIL_SMTP_PORT = 587
_GMAIL_SMTP_TIMEOUT_SECONDS = 20.0


def _escape_html(value: str) -> str:
    return escape(value, quote=True)


def _safe_action_url(value: str) -> str:
    try:
        parsed = urlsplit(value)
    except ValueError as error:
        raise ValueError("Email action URLs must be valid HTTP(S) URLs.") from error
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise ValueError("Email action URLs must be valid HTTP(S) URLs.")
    return _escape_html(value)


def _format_expiry(value: str) -> str:
    try:
        expiry = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return value
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=UTC)
    return expiry.astimezone(UTC).strftime("%B %d, %Y at %I:%M %p UTC")


def _invitation_html(
    *,
    preheader: str,
    eyebrow: str,
    heading: str,
    description: str,
    detail_label: str,
    detail_value: str,
    action_label: str,
    action_url: str,
    note: str,
) -> str:
    escaped_url = _safe_action_url(action_url)
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="x-apple-disable-message-reformatting">
    <title>{_escape_html(heading)}</title>
  </head>
  <body style="margin:0;padding:0;background-color:#f2f0e9;font-family:Arial,Helvetica,sans-serif;color:#1b2d27;">
    <div style="display:none;max-height:0;overflow:hidden;opacity:0;color:transparent;">
      {_escape_html(preheader)}
    </div>
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#f2f0e9;width:100%;">
      <tr>
        <td align="center" style="padding:32px 14px;">
          <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="width:100%;max-width:600px;background-color:#ffffff;border:1px solid #e5e1d8;border-radius:12px;overflow:hidden;">
            <tr>
              <td style="padding:24px 32px;background-color:#1b2d27;border-bottom:4px solid #d75030;">
                <div style="font-size:21px;line-height:26px;font-weight:700;letter-spacing:-0.4px;color:#ffffff;">SyncAlly</div>
                <div style="padding-top:5px;font-size:10px;line-height:14px;letter-spacing:1.5px;color:#bac9bd;">TRADE RECORDS, KEPT TOGETHER</div>
              </td>
            </tr>
            <tr>
              <td style="padding:36px 32px 30px;">
                <div style="font-size:11px;line-height:16px;font-weight:700;letter-spacing:1.6px;color:#d75030;">{_escape_html(eyebrow)}</div>
                <h1 style="margin:10px 0 12px;font-size:28px;line-height:35px;font-weight:700;letter-spacing:-0.6px;color:#1b2d27;">{_escape_html(heading)}</h1>
                <p style="margin:0;font-size:16px;line-height:25px;color:#59655e;">{_escape_html(description)}</p>
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="width:100%;margin-top:24px;background-color:#f7f5ef;border:1px solid #ebe7de;border-radius:8px;">
                  <tr>
                    <td style="padding:15px 18px;">
                      <div style="font-size:10px;line-height:15px;font-weight:700;letter-spacing:1.2px;color:#77827a;">{_escape_html(detail_label)}</div>
                      <div style="padding-top:4px;font-size:16px;line-height:23px;font-weight:700;color:#1b2d27;word-break:break-word;overflow-wrap:anywhere;">{_escape_html(detail_value)}</div>
                    </td>
                  </tr>
                </table>
                <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin-top:28px;">
                  <tr>
                    <td align="center" bgcolor="#d75030" style="border-radius:7px;background-color:#d75030;">
                      <a href="{escaped_url}" style="display:inline-block;padding:14px 22px;border:1px solid #d75030;border-radius:7px;background-color:#d75030;color:#ffffff;text-decoration:none;font-size:15px;line-height:20px;font-weight:700;">{_escape_html(action_label)}</a>
                    </td>
                  </tr>
                </table>
                <p style="margin:22px 0 0;font-size:13px;line-height:21px;color:#77827a;">{_escape_html(note)}</p>
                <p style="margin:20px 0 0;font-size:13px;line-height:20px;color:#77827a;">If the button doesn’t open, <a href="{escaped_url}" style="color:#a93e25;text-decoration:underline;">open SyncAlly here</a>.</p>
              </td>
            </tr>
            <tr>
              <td style="padding:18px 32px;border-top:1px solid #ebe7de;background-color:#fbfaf7;font-size:12px;line-height:18px;color:#89928b;">
                SyncAlly · A clearer way to manage trade
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>"""


class GmailSMTPInvoiceNotifier:
    """Send a plain-text copy of a Sandbox invoice using Gmail SMTP."""

    def __init__(
        self,
        username: str,
        app_password: str,
        from_email: str | None = None,
    ) -> None:
        if not username.strip() or not app_password.strip():
            raise ValueError("GMAIL_SMTP_USERNAME and GMAIL_APP_PASSWORD are required.")
        configured_username = username.strip()
        configured_from_email = (from_email or username).strip()
        if any(
            address.count("@") != 1
            or any(character.isspace() for character in address)
            for address in (configured_username, configured_from_email)
        ):
            raise ValueError("Gmail sender addresses must be valid email addresses.")
        self._username = configured_username
        self._app_password = "".join(app_password.split())
        self._from_email = configured_from_email

    def send_invoice_notice(self, notice: PaymentInvoiceNotice) -> None:
        message = EmailMessage()
        message["From"] = self._from_email
        message["To"] = notice.recipient_email
        message["Subject"] = f"Your SyncAlly PayPal Sandbox invoice {notice.invoice_number}"
        message["X-SyncAlly-Invoice-Number"] = notice.invoice_number
        message.set_content(
            "A PayPal Sandbox invoice has been created for your SyncAlly transaction.\n\n"
            f"Invoice: {notice.invoice_number}\n"
            f"Amount: {notice.amount.currency} {canonical_decimal(notice.amount.amount)}\n\n"
            f"View invoice: {notice.recipient_view_url}\n\n"
            "This is a Sandbox invoice for testing. PayPal Sandbox notifications are not sent "
            "to real Gmail inboxes; SyncAlly sent this separate email so you can open the "
            "invoice link."
        )

        try:
            with smtplib.SMTP(
                _GMAIL_SMTP_HOST,
                _GMAIL_SMTP_PORT,
                timeout=_GMAIL_SMTP_TIMEOUT_SECONDS,
            ) as smtp:
                smtp.ehlo()
                smtp.starttls(context=ssl.create_default_context())
                smtp.ehlo()
                smtp.login(self._username, self._app_password)
                smtp.send_message(message)
        except smtplib.SMTPAuthenticationError as error:
            raise PaymentNeedsAction(
                "GMAIL_SMTP_AUTH_FAILED",
                "Gmail rejected SMTP authentication; verify the sender address and App Password.",
            ) from error
        except smtplib.SMTPResponseException as error:
            if 400 <= error.smtp_code < 500:
                raise PaymentRetryableError(
                    "GMAIL_TEMPORARILY_UNAVAILABLE",
                    "Gmail temporarily rejected the invoice email; it will be retried.",
                ) from error
            raise PaymentNeedsAction(
                "GMAIL_SMTP_REJECTED",
                "Gmail rejected the invoice email; check the sender configuration and recipient.",
            ) from error
        except smtplib.SMTPRecipientsRefused as error:
            codes = [code for code, _ in error.recipients.values()]
            if codes and all(400 <= code < 500 for code in codes):
                raise PaymentRetryableError(
                    "GMAIL_TEMPORARILY_UNAVAILABLE",
                    "Gmail temporarily rejected the invoice email; it will be retried.",
                ) from error
            raise PaymentNeedsAction(
                "GMAIL_SMTP_RECIPIENT_REJECTED",
                "Gmail rejected the invoice recipient; verify the buyer contact email.",
            ) from error
        except (smtplib.SMTPException, OSError, TimeoutError) as error:
            raise PaymentRetryableError(
                "GMAIL_TEMPORARILY_UNAVAILABLE",
                "Gmail is temporarily unavailable; the invoice email will be retried.",
            ) from error


class InvitationEmailDeliveryError(RuntimeError):
    """A safe-to-display summary for an invitation email delivery failure."""


class GmailSMTPInvitationNotifier:
    """Deliver organization and deal invitation notices through configured Gmail SMTP."""

    def __init__(self, username: str, app_password: str, from_email: str | None = None) -> None:
        if not username.strip() or not app_password.strip():
            raise ValueError("GMAIL_SMTP_USERNAME and GMAIL_APP_PASSWORD are required.")
        configured_username = username.strip()
        configured_from_email = (from_email or username).strip()
        if any(
            address.count("@") != 1 or any(character.isspace() for character in address)
            for address in (configured_username, configured_from_email)
        ):
            raise ValueError("Gmail sender addresses must be valid email addresses.")
        self._username = configured_username
        self._app_password = "".join(app_password.split())
        self._from_email = configured_from_email

    def send_team_invitation(
        self, recipient_email: str, organization_name: str, invite_url: str, expires_at: str
    ) -> None:
        expiry = _format_expiry(expires_at)
        description = "You’ve been invited to join a team workspace on SyncAlly."
        self._send(
            recipient_email,
            f"You’re invited to join {organization_name} on SyncAlly",
            f"{description}\n"
            f"Organization: {organization_name}\n\n"
            f"Accept your single-use invitation: {invite_url}\n\n"
            f"This invitation expires on {expiry}. If you were not expecting it, you can ignore this email.",
            preheader=f"Join {organization_name} on SyncAlly.",
            eyebrow="TEAM INVITATION",
            heading="You’re invited",
            description=description,
            detail_label="ORGANIZATION",
            detail_value=organization_name,
            action_label="Accept invitation",
            action_url=invite_url,
            note=f"Accept first, then create a password for future sign-ins. This single-use invitation expires on {expiry}.",
        )

    def send_counterparty_invitation(
        self, recipient_email: str, organization_name: str, deal_name: str,
        invite_url: str, expires_at: str,
    ) -> None:
        description = f"{organization_name} invited your organization to join a deal on SyncAlly."
        self._send(
            recipient_email,
            f"{organization_name} invited you to a SyncAlly deal",
            f"{description}\n"
            f"Inviting organization: {organization_name}\n"
            f"Deal: {deal_name}\n\n"
            f"Set up your organization and accept the single-use invitation: {invite_url}\n\n"
            f"This invitation expires on {_format_expiry(expires_at)}. If you were not expecting it, you can ignore this email.",
            preheader=f"Review the invitation from {organization_name}.",
            eyebrow="DEAL INVITATION",
            heading="A deal is ready to review",
            description=description,
            detail_label="INVITATION FOR",
            detail_value=deal_name,
            action_label="Review deal invitation",
            action_url=invite_url,
            note=f"After accepting, create a password before entering your workspace. This single-use invitation expires on {_format_expiry(expires_at)}.",
        )

    def send_member_added_notice(
        self, recipient_email: str, organization_name: str, sign_in_url: str
    ) -> None:
        description = "An administrator added your account to an organization workspace."
        self._send(
            recipient_email,
            f"You’ve been added to {organization_name} on SyncAlly",
            f"{description}\n"
            f"Organization: {organization_name}\n\n"
            f"Sign in to open your organization workspace: {sign_in_url}\n\n"
            "If you were not expecting this change, contact the organization administrator.",
            preheader=f"Your SyncAlly access to {organization_name} is ready.",
            eyebrow="TEAM UPDATE",
            heading="You’ve been added",
            description=description,
            detail_label="ORGANIZATION",
            detail_value=organization_name,
            action_label="Open SyncAlly",
            action_url=sign_in_url,
            note="Sign in with your existing SyncAlly account to open the workspace.",
        )

    def _send(
        self,
        recipient_email: str,
        subject: str,
        text_content: str,
        *,
        preheader: str,
        eyebrow: str,
        heading: str,
        description: str,
        detail_label: str,
        detail_value: str,
        action_label: str,
        action_url: str,
        note: str,
    ) -> None:
        message = EmailMessage()
        message["From"] = self._from_email
        message["To"] = recipient_email
        message["Subject"] = " ".join(subject.split())
        message["X-SyncAlly-Notification"] = "organization-invitation"
        message.set_content(text_content)
        message.add_alternative(
            _invitation_html(
                preheader=preheader,
                eyebrow=eyebrow,
                heading=heading,
                description=description,
                detail_label=detail_label,
                detail_value=detail_value,
                action_label=action_label,
                action_url=action_url,
                note=note,
            ),
            subtype="html",
        )
        try:
            with smtplib.SMTP(
                _GMAIL_SMTP_HOST,
                _GMAIL_SMTP_PORT,
                timeout=_GMAIL_SMTP_TIMEOUT_SECONDS,
            ) as smtp:
                smtp.ehlo()
                smtp.starttls(context=ssl.create_default_context())
                smtp.ehlo()
                smtp.login(self._username, self._app_password)
                smtp.send_message(message)
        except (smtplib.SMTPException, OSError, TimeoutError) as error:
            raise InvitationEmailDeliveryError("Invitation email could not be delivered.") from error
