# Part of mhc-cowork. AGPL v3 — see LICENSE-AGPL
"""
webhook_handler.py — Stripe webhook handler for mhc-cowork.

Ported verbatim from MHC-L Phase 1 (mcp_server/webhook_handler.py). NOT
activated in the mhc-cowork MVP (free-tier-only). Kept here so paid tier
can be activated post-MVP by simply wiring the route in server.py without
re-implementing the webhook logic.

ASGI route POST /webhooks/stripe. Three event types:
  - checkout.session.completed   → synthesize approved application + issue
                                    API key + email tester via Resend
  - customer.subscription.deleted → revoke api_keys row tied to subscription
  - customer.subscription.updated → mirror Stripe sub status into
                                    api_keys.status

Security model:
  - Stripe signature verification mandatory (stripe.Webhook.construct_event).
    Invalid / missing signature → 400. STRIPE_WEBHOOK_SECRET in env.
  - Idempotency via stripe_events_processed table (PRIMARY KEY on event_id).
    A duplicate redelivery is a no-op returning 200.
  - The route is exempt from BearerAuthMiddleware (path-based skip in auth.py).
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import secrets
import sqlite3
import sys
import uuid
from pathlib import Path
from typing import Any, Awaitable, Callable

import resend  # type: ignore
import stripe  # type: ignore

from .db import connect, init_db, resolve_db_path

Scope = dict[str, Any]
Message = dict[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

WEBHOOK_PATH = "/webhooks/stripe"

PAYMENT_LINK_FIRM_SENTINEL = "__payment_link__"

KEY_PREFIX = "mhc_live_"
SECRET_BYTES = 32

DEFAULT_TIER = "paid"

EMAIL_FROM = "mhc-cowork <noreply@mhc.regia.it>"
EMAIL_SUBJECT = "La tua chiave mhc-cowork (paid tier)"

STRIPE_TO_INTERNAL_STATUS = {
    "active": "active",
    "trialing": "active",
    "past_due": "past_due",
    "unpaid": "past_due",
    "canceled": "revoked",
    "incomplete_expired": "revoked",
}

ENV_WEBHOOK_SECRET = "STRIPE_WEBHOOK_SECRET"
ENV_RESEND_API_KEY = "RESEND_API_KEY"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _generate_plain_key() -> str:
    return KEY_PREFIX + secrets.token_urlsafe(SECRET_BYTES)


def _hash_key(plain: str) -> str:
    return hashlib.sha256(plain.encode("utf-8")).hexdigest()


def _email_body(plain_key: str) -> str:
    return f"""Ciao,

Benvenuto nel programma mhc-cowork.

La tua API key personale e':

  {plain_key}

Per installare il plugin con la chiave gia' pre-popolata, vai su:

  https://claude.ai/plugins/install?marketplace=MicheleLoi/mhc-cowork&plugin=mhc&env=MHC_BEARER={plain_key}

Sicurezza:
- La chiave NON e' recuperabile: conservala in luogo sicuro
- Non condividerla con nessuno (la sottoscrizione e' personale)
- Per revocare/sostituire: scrivi a noreply@mhc.regia.it

La revoca e' immediata: cancellando la sottoscrizione da Stripe la chiave
viene disattivata al primo refresh del webhook.

Buon lavoro,
mhc-cowork
"""


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------

def _event_already_processed(conn: sqlite3.Connection, event_id: str) -> bool:
    cur = conn.execute(
        "SELECT 1 FROM stripe_events_processed WHERE event_id = ?",
        (event_id,),
    )
    return cur.fetchone() is not None


def _mark_event_processed(conn: sqlite3.Connection, event_id: str, event_type: str) -> None:
    conn.execute(
        """
        INSERT INTO stripe_events_processed (event_id, event_type, processed_at)
        VALUES (?, ?, ?)
        """,
        (event_id, event_type, _now_iso()),
    )


# ---------------------------------------------------------------------------
# Email sending (Resend)
# ---------------------------------------------------------------------------

def _send_key_email(*, to_email: str, plain_key: str) -> dict:
    api_key = os.environ.get(ENV_RESEND_API_KEY)
    if not api_key:
        raise RuntimeError(
            f"{ENV_RESEND_API_KEY} not set — cannot send key email to {to_email}"
        )
    resend.api_key = api_key
    return resend.Emails.send(
        {
            "from": EMAIL_FROM,
            "to": [to_email],
            "subject": EMAIL_SUBJECT,
            "text": _email_body(plain_key),
        }
    )


# ---------------------------------------------------------------------------
# DB writes
# ---------------------------------------------------------------------------

def _insert_synthetic_application(
    conn: sqlite3.Connection,
    *,
    email: str,
    checkout_session_id: str,
    payment_link_id: str | None,
    now_iso: str,
) -> str:
    app_id = str(uuid.uuid4())
    use_case = (
        f"Stripe Payment Link {payment_link_id}" if payment_link_id
        else "Stripe Checkout Session"
    )
    conn.execute(
        """
        INSERT INTO applications
            (id, email, firm, role, use_case, notes, submitted_at, status,
             reviewed_at, reviewed_by, rejection_reason, stripe_checkout_session_id)
        VALUES (?, ?, ?, NULL, ?, NULL, ?, 'approved', ?, 'stripe_webhook', NULL, ?)
        """,
        (
            app_id,
            email,
            PAYMENT_LINK_FIRM_SENTINEL,
            use_case,
            now_iso,
            now_iso,
            checkout_session_id,
        ),
    )
    return app_id


def _insert_api_key_row(
    conn: sqlite3.Connection,
    *,
    key_hash: str,
    user_email: str,
    application_id: str,
    stripe_customer_id: str,
    stripe_subscription_id: str,
    tier: str,
    now_iso: str,
) -> None:
    conn.execute(
        """
        INSERT INTO api_keys
            (key_hash, user_email, application_id, stripe_customer_id,
             stripe_subscription_id, tier, status, created_at,
             revoked_at, revoked_reason, last_used_at, request_count)
        VALUES (?, ?, ?, ?, ?, ?, 'active', ?, NULL, NULL, NULL, 0)
        """,
        (
            key_hash, user_email, application_id, stripe_customer_id,
            stripe_subscription_id, tier, now_iso,
        ),
    )


# ---------------------------------------------------------------------------
# Event handlers
# ---------------------------------------------------------------------------

def _handle_checkout_session_completed(
    conn: sqlite3.Connection, event: dict
) -> tuple[bool, str | None]:
    obj = event["data"]["object"]
    session_id = obj.get("id", "")
    payment_status = obj.get("payment_status")
    livemode = obj.get("livemode", False)

    if payment_status != "paid":
        print(
            f"[webhook] checkout.session.completed {session_id}: "
            f"payment_status={payment_status!r} (expected 'paid') — skip",
            file=sys.stderr,
        )
        return False, None

    if not livemode:
        print(
            f"[webhook] checkout.session.completed {session_id}: "
            f"livemode=False — test mode ignored",
            file=sys.stderr,
        )
        return False, None

    customer_id = obj.get("customer")
    subscription_id = obj.get("subscription")
    customer_details = obj.get("customer_details") or {}
    email = customer_details.get("email")
    payment_link_id = obj.get("payment_link")

    if not email:
        raise ValueError(
            f"checkout.session.completed {session_id}: customer_details.email missing"
        )
    if not customer_id:
        raise ValueError(
            f"checkout.session.completed {session_id}: customer field missing"
        )
    if not subscription_id:
        raise ValueError(
            f"checkout.session.completed {session_id}: subscription field missing "
            f"(mode != 'subscription'?)"
        )

    now = _now_iso()

    application_id = _insert_synthetic_application(
        conn,
        email=email,
        checkout_session_id=session_id,
        payment_link_id=payment_link_id,
        now_iso=now,
    )

    plain_key = _generate_plain_key()
    key_hash = _hash_key(plain_key)

    existing = conn.execute(
        "SELECT 1 FROM api_keys WHERE key_hash = ?", (key_hash,)
    ).fetchone()
    if existing is not None:
        raise RuntimeError("key_hash collision — abort and let Stripe retry")

    _insert_api_key_row(
        conn,
        key_hash=key_hash,
        user_email=email,
        application_id=application_id,
        stripe_customer_id=customer_id,
        stripe_subscription_id=subscription_id,
        tier=DEFAULT_TIER,
        now_iso=now,
    )

    print(
        f"[webhook] checkout.session.completed {session_id}: "
        f"key issued for {email} (sub={subscription_id})",
        file=sys.stderr,
    )
    return True, plain_key


def _handle_subscription_deleted(conn: sqlite3.Connection, event: dict) -> None:
    obj = event["data"]["object"]
    subscription_id = obj.get("id")
    if not subscription_id:
        raise ValueError("customer.subscription.deleted: object.id missing")
    cur = conn.execute(
        """
        UPDATE api_keys
           SET status = 'revoked',
               revoked_at = ?,
               revoked_reason = 'subscription_deleted'
         WHERE stripe_subscription_id = ?
           AND status != 'revoked'
        """,
        (_now_iso(), subscription_id),
    )
    print(
        f"[webhook] customer.subscription.deleted {subscription_id}: "
        f"{cur.rowcount} key(s) revoked",
        file=sys.stderr,
    )


def _handle_subscription_updated(conn: sqlite3.Connection, event: dict) -> None:
    obj = event["data"]["object"]
    subscription_id = obj.get("id")
    stripe_status = obj.get("status")
    if not subscription_id:
        raise ValueError("customer.subscription.updated: object.id missing")
    mapped = STRIPE_TO_INTERNAL_STATUS.get(stripe_status)
    if mapped is None:
        print(
            f"[webhook] customer.subscription.updated {subscription_id}: "
            f"unmapped Stripe status={stripe_status!r} — no-op",
            file=sys.stderr,
        )
        return
    if mapped == "revoked":
        cur = conn.execute(
            """
            UPDATE api_keys
               SET status = 'revoked',
                   revoked_at = ?,
                   revoked_reason = ?
             WHERE stripe_subscription_id = ?
               AND status != 'revoked'
            """,
            (_now_iso(), f"subscription_updated:{stripe_status}", subscription_id),
        )
    elif mapped == "active":
        cur = conn.execute(
            """
            UPDATE api_keys
               SET status = 'active',
                   revoked_at = NULL,
                   revoked_reason = NULL
             WHERE stripe_subscription_id = ?
            """,
            (subscription_id,),
        )
    else:
        cur = conn.execute(
            """
            UPDATE api_keys
               SET status = ?
             WHERE stripe_subscription_id = ?
            """,
            (mapped, subscription_id),
        )
    print(
        f"[webhook] customer.subscription.updated {subscription_id}: "
        f"{cur.rowcount} key(s) → {mapped} (stripe={stripe_status})",
        file=sys.stderr,
    )


# ---------------------------------------------------------------------------
# Top-level dispatcher
# ---------------------------------------------------------------------------

def process_event(event: dict, db_path: Path | None = None) -> None:
    event_id = event.get("id")
    event_type = event.get("type")
    if not event_id or not event_type:
        raise ValueError("Stripe event missing id/type")

    path = db_path or resolve_db_path()
    init_db(path)
    conn = connect(path)

    pending_email: tuple[str, str] | None = None

    try:
        if _event_already_processed(conn, event_id):
            print(f"[webhook] duplicate event {event_id} ({event_type}) — ignored",
                  file=sys.stderr)
            return

        conn.execute("BEGIN")
        try:
            if event_type == "checkout.session.completed":
                should_email, plain_key = _handle_checkout_session_completed(conn, event)
                if should_email and plain_key:
                    email_to = event["data"]["object"]["customer_details"]["email"]
                    pending_email = (email_to, plain_key)
            elif event_type == "customer.subscription.deleted":
                _handle_subscription_deleted(conn, event)
            elif event_type == "customer.subscription.updated":
                _handle_subscription_updated(conn, event)
            else:
                print(
                    f"[webhook] unsubscribed event type {event_type!r} "
                    f"({event_id}) — marking processed and ignoring",
                    file=sys.stderr,
                )
            _mark_event_processed(conn, event_id, event_type)
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
    finally:
        conn.close()

    if pending_email is not None:
        to_email, plain_key = pending_email
        _send_key_email(to_email=to_email, plain_key=plain_key)


# ---------------------------------------------------------------------------
# ASGI route
# ---------------------------------------------------------------------------

async def _read_body(receive: Receive) -> bytes:
    chunks: list[bytes] = []
    while True:
        message = await receive()
        if message["type"] == "http.request":
            chunks.append(message.get("body", b"") or b"")
            if not message.get("more_body", False):
                break
        elif message["type"] == "http.disconnect":
            break
    return b"".join(chunks)


async def _send_json(send: Send, status: int, payload: dict) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode("ascii")),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})


async def stripe_webhook_endpoint(scope: Scope, receive: Receive, send: Send) -> None:
    if scope.get("method") != "POST":
        await _send_json(send, 405, {"error": "method_not_allowed"})
        return

    raw_body = await _read_body(receive)

    sig_header: str | None = None
    for name, value in scope.get("headers", []):
        if name.lower() == b"stripe-signature":
            try:
                sig_header = value.decode("latin-1")
            except UnicodeDecodeError:
                sig_header = None
            break

    if not sig_header:
        await _send_json(send, 400, {"error": "missing_stripe_signature"})
        return

    secret = os.environ.get(ENV_WEBHOOK_SECRET)
    if not secret:
        print(
            f"[webhook] FATAL: {ENV_WEBHOOK_SECRET} not set; rejecting event",
            file=sys.stderr,
        )
        await _send_json(send, 500, {"error": "webhook_secret_not_configured"})
        return

    try:
        event = stripe.Webhook.construct_event(raw_body, sig_header, secret)
    except ValueError:
        await _send_json(send, 400, {"error": "invalid_payload"})
        return
    except stripe.error.SignatureVerificationError:
        await _send_json(send, 400, {"error": "invalid_signature"})
        return

    event_dict = event if isinstance(event, dict) else event.to_dict()

    try:
        process_event(event_dict)
    except Exception as exc:
        print(
            f"[webhook] handler exception event={event_dict.get('id')} "
            f"type={event_dict.get('type')}: {exc!r}",
            file=sys.stderr,
        )
        await _send_json(send, 500, {"error": "handler_failed"})
        return

    await _send_json(send, 200, {"received": True})


__all__ = [
    "WEBHOOK_PATH",
    "stripe_webhook_endpoint",
    "process_event",
    "ENV_WEBHOOK_SECRET",
    "ENV_RESEND_API_KEY",
    "PAYMENT_LINK_FIRM_SENTINEL",
    "DEFAULT_TIER",
    "STRIPE_TO_INTERNAL_STATUS",
]
