"""PoultryGuard SMS Notification Module

Provides a pluggable, robust SMS notification system supporting:
- Real provider abstractions (Twilio, Indian SMS Gateway / Fast2SMS, Generic Webhook, Mock)
- Strict phone number normalization (+91 international formatting for Indian numbers)
- Safe masking (+91 75300 ****44)
- Rate-limiting cooldown & event deduplication
- Comprehensive audit trail logged into SQLite database
- Dry-run and test mode support

Safety rule: Credentials are loaded exclusively from local environment variables,
never stored in code, committed to git, or exposed to the browser.
"""
from __future__ import annotations

import os
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Optional, Tuple, Any

import httpx

from . import db
from .config import get_settings


def normalize_phone_number(raw_phone: str, default_country_code: str = "+91") -> Tuple[bool, str, str]:
    """Normalizes and validates a phone number.
    Returns: (is_valid, normalized_e164, error_message)
    """
    if not raw_phone:
        return False, "", "Phone number is empty"

    # Strip whitespace, hyphens, parentheses, dots
    cleaned = re.sub(r"[\s\-\(\)\.]", "", str(raw_phone).strip())

    # If starts with +, ensure digits follow
    if cleaned.startswith("+"):
        digits = cleaned[1:]
        if not digits.isdigit() or len(digits) < 10 or len(digits) > 15:
            return False, cleaned, "Invalid international E.164 phone number length"
        return True, f"+{digits}", ""

    # If starts with 00, treat as international +
    if cleaned.startswith("00"):
        digits = cleaned[2:]
        if digits.isdigit() and 10 <= len(digits) <= 15:
            return True, f"+{digits}", ""

    # If 10 digits (common for Indian mobile numbers starting with 6, 7, 8, 9)
    if cleaned.isdigit() and len(cleaned) == 10:
        if cleaned[0] in "6789":
            return True, f"{default_country_code}{cleaned}", ""
        else:
            return True, f"{default_country_code}{cleaned}", ""

    # If 12 digits starting with 91 (Indian number without +)
    if cleaned.isdigit() and len(cleaned) == 12 and cleaned.startswith("91"):
        return True, f"+{cleaned}", ""

    # If 11 digits starting with 0 (Indian local trunk prefix)
    if cleaned.isdigit() and len(cleaned) == 11 and cleaned.startswith("0"):
        return True, f"{default_country_code}{cleaned[1:]}", ""

    return False, cleaned, f"Unrecognized phone format: {raw_phone}"


def mask_phone_number(phone: str) -> str:
    """Masks a phone number for safe display in UI and logs (e.g. +91 75300 ****44)."""
    if not phone:
        return "(Not Configured)"
    norm = phone.strip()
    if norm.startswith("+91") and len(norm) == 13:
        return f"+91 {norm[3:8]} ****{norm[-2:]}"
    if len(norm) <= 6:
        return "***"
    prefix = norm[:len(norm) - 6]
    suffix = norm[-2:]
    return f"{prefix} ****{suffix}"


@dataclass
class SMSDeliveryResult:
    """Result of an SMS transmission attempt."""
    success: bool
    status: str  # 'sent', 'failed', 'not_configured', 'dry_run', 'cooldown_suppressed'
    provider: str
    recipient: str
    provider_message_id: Optional[str] = None
    error_detail: Optional[str] = None
    message_text: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "status": self.status,
            "provider": self.provider,
            "recipient": mask_phone_number(self.recipient),
            "provider_message_id": self.provider_message_id,
            "error_detail": self.error_detail,
            "message_text": self.message_text
        }


class SMSProvider(ABC):
    """Abstract base class for SMS delivery providers."""
    name: str = "base"

    @abstractmethod
    def is_configured(self) -> Tuple[bool, str]:
        """Returns (is_ready, reason_message)."""
        pass

    @abstractmethod
    def send(self, recipient: str, message: str) -> SMSDeliveryResult:
        """Sends the SMS message to the recipient."""
        pass


class DisabledSMSProvider(SMSProvider):
    name = "disabled"

    def is_configured(self) -> Tuple[bool, str]:
        return False, "SMS notifications are disabled or provider is unconfigured."

    def send(self, recipient: str, message: str) -> SMSDeliveryResult:
        return SMSDeliveryResult(
            success=False,
            status="not_configured",
            provider=self.name,
            recipient=recipient,
            error_detail="SMS sending disabled in application configuration.",
            message_text=message
        )


class MockSMSProvider(SMSProvider):
    name = "mock"

    def __init__(self, simulate_failure: bool = False):
        self.simulate_failure = simulate_failure

    def is_configured(self) -> Tuple[bool, str]:
        return True, "Mock SMS provider active for local development/testing."

    def send(self, recipient: str, message: str) -> SMSDeliveryResult:
        if self.simulate_failure:
            return SMSDeliveryResult(
                success=False,
                status="failed",
                provider=self.name,
                recipient=recipient,
                error_detail="Simulated mock gateway failure for resilience testing.",
                message_text=message
            )
        msg_id = f"mock_{int(time.time())}_{abs(hash(message)) % 100000}"
        return SMSDeliveryResult(
            success=True,
            status="sent",
            provider=self.name,
            recipient=recipient,
            provider_message_id=msg_id,
            message_text=message
        )


class TwilioSMSProvider(SMSProvider):
    name = "twilio"

    def __init__(self):
        self.account_sid = (
            os.getenv("TWILIO_ACCOUNT_SID", "").strip() or 
            os.getenv("SMS_TWILIO_ACCOUNT_SID", "").strip()
        )
        self.auth_token = (
            os.getenv("TWILIO_AUTH_TOKEN", "").strip() or 
            os.getenv("SMS_TWILIO_AUTH_TOKEN", "").strip()
        )
        self.from_number = (
            os.getenv("TWILIO_FROM_NUMBER", "").strip() or 
            os.getenv("SMS_TWILIO_FROM_NUMBER", "").strip()
        )

    def is_configured(self) -> Tuple[bool, str]:
        if not self.account_sid:
            return False, "Twilio Account SID is missing in environment (TWILIO_ACCOUNT_SID)."
        if not self.auth_token:
            return False, "Twilio Auth Token is missing in environment (TWILIO_AUTH_TOKEN)."
        if not self.from_number:
            return True, "Twilio credentials configured (From number will be auto-detected or provided)."
        return True, f"Twilio credentials configured and ready (From: {self.from_number})."

    def send(self, recipient: str, message: str) -> SMSDeliveryResult:
        ready, reason = self.is_configured()
        if not ready:
            return SMSDeliveryResult(
                success=False,
                status="not_configured",
                provider=self.name,
                recipient=recipient,
                error_detail=reason,
                message_text=message
            )

        from_num = self.from_number
        # If from_num is missing or same as recipient, attempt to auto-discover account phone number
        norm_recipient = recipient.replace("+", "").replace("-", "").strip()
        norm_from = from_num.replace("+", "").replace("-", "").strip()

        if not from_num or norm_from == norm_recipient:
            try:
                with httpx.Client(timeout=5.0) as client:
                    num_resp = client.get(
                        f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/IncomingPhoneNumbers.json",
                        auth=(self.account_sid, self.auth_token)
                    )
                    if num_resp.status_code == 200:
                        incoming = num_resp.json().get("incoming_phone_numbers", [])
                        if incoming:
                            from_num = incoming[0].get("phone_number", "")
                            norm_from = from_num.replace("+", "").replace("-", "").strip()
            except Exception:
                pass

        if not from_num or norm_from == norm_recipient:
            return SMSDeliveryResult(
                success=False,
                status="failed",
                provider=self.name,
                recipient=recipient,
                error_detail=(
                    "Twilio sender number missing. In Twilio, 'From' cannot be your own mobile number. "
                    "Log into https://console.twilio.com and click 'Get a Phone Number' to claim your free trial number, "
                    "then set TWILIO_FROM_NUMBER in .env."
                ),
                message_text=message
            )

        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
        data = {
            "To": recipient,
            "From": from_num,
            "Body": message
        }

        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.post(url, data=data, auth=(self.account_sid, self.auth_token))
                if res.status_code in (200, 201):
                    res_json = res.json()
                    sid = res_json.get("sid", "twilio_ok")
                    return SMSDeliveryResult(
                        success=True,
                        status="sent",
                        provider=self.name,
                        recipient=recipient,
                        provider_message_id=sid,
                        message_text=message
                    )
                else:
                    try:
                        err_json = res.json()
                        err_code = err_json.get("code")
                        err_msg = err_json.get("message", res.text[:200])

                        if err_code == 572006:
                            detail = (
                                "Twilio Free Trial restriction (Error 572006): Trial accounts can only use pre-approved "
                                "templates or send to verified numbers. Please verify your phone number in Twilio Console "
                                "under Phone Numbers -> Verified Caller IDs, or upgrade your Twilio account."
                            )
                        elif err_code == 21608:
                            detail = (
                                f"Twilio Free Trial restriction (Error 21608): Recipient {recipient} is unverified. "
                                "Twilio trial accounts can only text numbers added to Verified Caller IDs in Twilio Console."
                            )
                        elif err_code in (21212, 21606):
                            detail = (
                                f"Twilio Error ({err_code}): 'From' number '{from_num}' is not a valid Twilio number for this account. "
                                "Please click 'Get a Phone Number' in Twilio Console and update TWILIO_FROM_NUMBER in .env."
                            )
                        else:
                            detail = f"Twilio API error {res.status_code} (Code {err_code}): {err_msg}"
                    except Exception:
                        detail = f"Twilio API error {res.status_code}: {res.text[:300]}"

                    return SMSDeliveryResult(
                        success=False,
                        status="failed",
                        provider=self.name,
                        recipient=recipient,
                        error_detail=detail,
                        message_text=message
                    )
        except Exception as exc:
            return SMSDeliveryResult(
                success=False,
                status="failed",
                provider=self.name,
                recipient=recipient,
                error_detail=f"Twilio connection failure: {exc}",
                message_text=message
            )


class IndianGatewaySMSProvider(SMSProvider):
    """Indian SMS Gateway provider (Fast2SMS / MSG91 API compatible)."""
    name = "fast2sms"

    def __init__(self):
        self.api_key = os.getenv("SMS_API_KEY", "").strip()
        self.sender_id = os.getenv("SMS_SENDER_ID", "TXTIND").strip()

    def is_configured(self) -> Tuple[bool, str]:
        if not self.api_key:
            return False, "Indian SMS API Key missing in environment (SMS_API_KEY)."
        return True, "Indian SMS Gateway credentials configured."

    def send(self, recipient: str, message: str) -> SMSDeliveryResult:
        ready, reason = self.is_configured()
        if not ready:
            return SMSDeliveryResult(
                success=False,
                status="not_configured",
                provider=self.name,
                recipient=recipient,
                error_detail=reason,
                message_text=message
            )

        # Fast2SMS requires 10-digit Indian numbers without country code prefix
        ten_digit = recipient.replace("+91", "").strip()
        url = "https://www.fast2sms.com/dev/bulkV2"
        headers = {
            "authorization": self.api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "route": "q",
            "message": message,
            "language": "english",
            "flash": 0,
            "numbers": ten_digit
        }

        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.post(url, json=payload, headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    if data.get("return", False):
                        req_id = data.get("request_id", "fast2sms_ok")
                        return SMSDeliveryResult(
                            success=True,
                            status="sent",
                            provider=self.name,
                            recipient=recipient,
                            provider_message_id=str(req_id),
                            message_text=message
                        )
                    else:
                        return SMSDeliveryResult(
                            success=False,
                            status="failed",
                            provider=self.name,
                            recipient=recipient,
                            error_detail=f"Gateway response: {data.get('message', 'Unknown gateway error')}",
                            message_text=message
                        )
                else:
                    return SMSDeliveryResult(
                        success=False,
                        status="failed",
                        provider=self.name,
                        recipient=recipient,
                        error_detail=f"HTTP {res.status_code}: {res.text[:300]}",
                        message_text=message
                    )
        except Exception as exc:
            return SMSDeliveryResult(
                success=False,
                status="failed",
                provider=self.name,
                recipient=recipient,
                error_detail=f"Gateway connection failure: {exc}",
                message_text=message
            )


class GenericWebhookSMSProvider(SMSProvider):
    """Sends notification payload to an operational webhook or SMS bridge URL."""
    name = "webhook"

    def __init__(self):
        self.webhook_url = os.getenv("SMS_WEBHOOK_URL", "").strip()

    def is_configured(self) -> Tuple[bool, str]:
        if not self.webhook_url:
            return False, "SMS Webhook URL missing in environment (SMS_WEBHOOK_URL)."
        return True, "SMS Webhook endpoint configured."

    def send(self, recipient: str, message: str) -> SMSDeliveryResult:
        ready, reason = self.is_configured()
        if not ready:
            return SMSDeliveryResult(
                success=False,
                status="not_configured",
                provider=self.name,
                recipient=recipient,
                error_detail=reason,
                message_text=message
            )

        payload = {
            "channel": "sms",
            "recipient": recipient,
            "message": message,
            "timestamp": time.time(),
            "service": "PoultryGuard"
        }

        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.post(self.webhook_url, json=payload)
                if res.status_code in (200, 201, 202, 204):
                    return SMSDeliveryResult(
                        success=True,
                        status="sent",
                        provider=self.name,
                        recipient=recipient,
                        provider_message_id=f"webhook_{int(time.time())}",
                        message_text=message
                    )
                else:
                    return SMSDeliveryResult(
                        success=False,
                        status="failed",
                        provider=self.name,
                        recipient=recipient,
                        error_detail=f"Webhook returned {res.status_code}",
                        message_text=message
                    )
        except Exception as exc:
            return SMSDeliveryResult(
                success=False,
                status="failed",
                provider=self.name,
                recipient=recipient,
                error_detail=f"Webhook connection failure: {exc}",
                message_text=message
            )


def get_sms_provider() -> SMSProvider:
    """Factory function returning the active configured SMSProvider."""
    provider_name = os.getenv("SMS_PROVIDER", "").lower().strip()

    # If twilio credentials exist and provider is twilio or empty, auto-select twilio
    has_twilio = bool(
        os.getenv("TWILIO_ACCOUNT_SID", "").strip() or 
        os.getenv("SMS_TWILIO_ACCOUNT_SID", "").strip()
    )
    if not provider_name and has_twilio:
        provider_name = "twilio"

    # Check if SMS is globally enabled (default to true if twilio credentials explicitly set)
    default_enabled = "true" if has_twilio else "false"
    sms_enabled = os.getenv("SMS_ENABLED", default_enabled).lower() in ("true", "1", "yes")
    if not sms_enabled:
        return DisabledSMSProvider()

    if provider_name == "twilio":
        return TwilioSMSProvider()
    elif provider_name in ("fast2sms", "indian_gateway", "msg91"):
        return IndianGatewaySMSProvider()
    elif provider_name in ("webhook", "generic_webhook"):
        return GenericWebhookSMSProvider()
    elif provider_name == "mock":
        return MockSMSProvider()
    else:
        return DisabledSMSProvider()


def format_sms_message(
    category: str,
    farm_name: str = "Farm",
    flock_name: str = "Flock",
    zone_id: Optional[str] = None,
    time_str: str = "",
    count: Optional[int] = None,
    details: str = "",
    alert_id: Optional[int] = None
) -> str:
    """Formats concise, factual SMS alerts under 160 characters when possible."""
    ref_tag = f" [Ref #{alert_id}]" if alert_id else ""

    if category == "urgent_health":
        msg = f"PoultryGuard URGENT: Severe signs reported at {farm_name}, {flock_name}. {details}. Consult a veterinarian promptly.{ref_tag}"
    elif category == "persistent_density":
        zid_tag = f", Zone {zone_id}" if zone_id else ""
        cnt_tag = f" ({count} birds)" if count is not None else ""
        msg = f"PoultryGuard REVIEW: Persistent concentration in {flock_name}{zid_tag}{cnt_tag} at {time_str}. Review saved frame. Screening only.{ref_tag}"
    elif category == "unusual_activity":
        msg = f"PoultryGuard WATCH: Persistent low activity observed in {flock_name}. Review camera stream & flock behavior.{ref_tag}"
    elif category == "system_quality":
        msg = f"PoultryGuard SYSTEM: Low video detector coverage in flock {flock_name}. Check coop lighting and camera angle.{ref_tag}"
    else:
        msg = f"PoultryGuard ALERT: {details} at {farm_name}, {flock_name}.{ref_tag}"

    return msg[:300]  # Cap length for SMS compliance


def dispatch_alert_sms(
    category: str,
    message_text: str,
    alert_id: Optional[int] = None,
    force_dry_run: bool = False
) -> SMSDeliveryResult:
    """Dispatches an SMS with validation, cooldown rate-limiting, and SQLite audit logging."""
    raw_recipient = os.getenv("SMS_RECIPIENT", "7530088644").strip()
    valid, recipient, err = normalize_phone_number(raw_recipient)

    if not valid:
        result = SMSDeliveryResult(
            success=False,
            status="failed",
            provider="config",
            recipient=raw_recipient,
            error_detail=f"Recipient validation error: {err}",
            message_text=message_text
        )
        _log_notification(alert_id, category, raw_recipient, result)
        return result

    # Check Cooldown & Deduplication
    cooldown_sec = int(os.getenv("SMS_COOLDOWN_SEC", "300"))
    if not force_dry_run and _is_rate_limited(category, recipient, cooldown_sec):
        result = SMSDeliveryResult(
            success=False,
            status="cooldown_suppressed",
            provider="rate_limiter",
            recipient=recipient,
            error_detail=f"Suppressed duplicate alert: similar alert sent within {cooldown_sec}s cooldown window.",
            message_text=message_text
        )
        _log_notification(alert_id, category, recipient, result)
        return result

    # Check Dry Run Mode
    is_dry_run = force_dry_run or (os.getenv("SMS_DRY_RUN", "false").lower() in ("true", "1", "yes"))
    if is_dry_run:
        result = SMSDeliveryResult(
            success=True,
            status="dry_run",
            provider="dry_run",
            recipient=recipient,
            provider_message_id=f"dryrun_{int(time.time())}",
            message_text=message_text
        )
        _log_notification(alert_id, category, recipient, result)
        return result

    # Send through active provider
    provider = get_sms_provider()
    result = provider.send(recipient, message_text)
    _log_notification(alert_id, category, recipient, result)
    return result


def _is_rate_limited(event_type: str, recipient: str, cooldown_sec: int) -> bool:
    """Checks whether an identical alert type was sent to recipient within cooldown seconds."""
    try:
        with db.connect() as c:
            row = c.execute(
                """SELECT created_at FROM notifications 
                   WHERE event_type=? AND recipient=? AND status IN ('sent', 'dry_run')
                   ORDER BY id DESC LIMIT 1""",
                (event_type, recipient)
            ).fetchone()
            if not row:
                return False
            # Check elapsed seconds
            ts_str = row["created_at"]
            if ts_str:
                import datetime
                try:
                    dt_last = datetime.datetime.fromisoformat(ts_str.replace("Z", ""))
                    if dt_last.tzinfo is None:
                        dt_last = dt_last.replace(tzinfo=datetime.timezone.utc)
                    dt_now = datetime.datetime.now(datetime.timezone.utc)
                    elapsed = (dt_now - dt_last).total_seconds()
                    return elapsed < cooldown_sec
                except Exception:
                    pass
    except Exception:
        pass
    return False


def _log_notification(
    alert_id: Optional[int],
    event_type: str,
    recipient: str,
    result: SMSDeliveryResult
) -> None:
    """Logs the notification attempt into the SQLite notifications audit table."""
    try:
        with db.connect() as c:
            # Ensure notifications table exists
            c.execute("""
                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_id INTEGER,
                    event_type TEXT NOT NULL,
                    recipient TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    message_text TEXT NOT NULL,
                    status TEXT NOT NULL,
                    provider_message_id TEXT,
                    error_detail TEXT,
                    retry_count INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(alert_id) REFERENCES alerts(id) ON DELETE SET NULL
                )
            """)
            c.execute(
                """INSERT INTO notifications
                   (alert_id, event_type, recipient, provider, message_text, status, provider_message_id, error_detail)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    alert_id,
                    event_type,
                    result.recipient,
                    result.provider,
                    result.message_text,
                    result.status,
                    result.provider_message_id,
                    result.error_detail
                )
            )
    except Exception as exc:
        print(f"[SMS Audit Warning] Could not persist notification log: {exc}")
