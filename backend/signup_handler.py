# Part of mhc-cowork. AGPL v3 — see LICENSE-AGPL
"""
signup_handler.py — mhc-cowork signup endpoint (free + paid tiers).

Two routes, both bare ASGI to match the pattern used for legacy MHC-L paths:

  POST /signup/create-checkout-session
    Body (JSON):
      - tier             (str, optional): "free" or absent for paid Stripe
                                          flow. MVP default: "free".
      - email            (str): required for free tier; ignored for paid
                                tier (Stripe Checkout collects it).
      - name             (str, optional, free tier only): label only.
      - firm             (str, optional, free tier only): label only.
      - stripe_price_id  (str, optional): if present (and tier != "free"),
                                          falls through to the paid Stripe
                                          Checkout flow.

    Free tier behaviour:
      1. Generate a fresh Bearer key (32 bytes URL-safe).
      2. Generate a single-use welcome_token (16 bytes URL-safe).
      3. INSERT a synthetic application row (firm=__free_tier__,
         status=approved) and an api_keys row (sentinel customer/sub IDs
         FREE-TIER:<token>).
      4. Send email via Resend containing a link to
         /signup/welcome/<welcome_token>.
      5. Respond 200 {"tier": "free", "status": "email_sent",
                       "email": "<email>"}.

    Paid tier behaviour (post-MVP — gated on stripe_price_id presence):
      Behave as the legacy MHC-L flow: create a Stripe Checkout Session
      and return its url. Stripe webhook then issues the key.

  GET /signup/welcome/<token>
    Read the application row whose notes JSON carries this welcome_token.
    Returns 200 {email, bearer_key, install_url} on first fetch, then
    redacts the plain bearer from notes (one-time reveal). Returns 404 if
    the token is not found or 410 if already consumed.

Security model:
  - Both routes are exempt from BearerAuthMiddleware (path-skip).
  - Plain Bearer is held briefly in applications.notes (JSON) so the
    welcome endpoint can reveal it once; immediately redacted after the
    first read. The SHA-256 hash in api_keys is the long-term store used
    for auth.
  - welcome_token: 16-byte URL-safe random. Single-use (consume-on-read).
  - Threat model assumption: single-tenant VPS, DB readable only by the
    founder's process. (Apollo: assumption stated.)

Stdlib + stripe (paid) + resend (email).
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

import resend  # type: ignore

from .db import connect, init_db

# Stripe is imported lazily — only required if a caller hits the paid tier
# branch with stripe_price_id set. The MVP defaults to free tier and many
# deployments won't have STRIPE_SECRET_KEY configured at all.

Scope = dict[str, Any]
Message = dict[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]


# ---------------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------------

SIGNUP_CHECKOUT_PATH = "/signup/create-checkout-session"
SIGNUP_WELCOME_PREFIX = "/signup/welcome/"

# Marketplace + plugin coordinates baked into the install URL the welcome
# endpoint returns. Override via env at runtime if these change.
DEFAULT_MARKETPLACE = "MicheleLoi/mhc-cowork"
DEFAULT_PLUGIN_NAME = "mhc"

# Synthetic markers in the applications + api_keys tables. The api_keys
# schema requires NOT NULL stripe_customer_id and stripe_subscription_id;
# free-tier rows fill those with a sentinel containing the welcome_token,
# uniqueness-preserving without involving Stripe at all.
FREE_TIER_FIRM_SENTINEL = "__free_tier__"
FREE_TIER_CUSTOMER_PREFIX = "FREE-TIER-CUST-"
FREE_TIER_SUB_PREFIX = "FREE-TIER-SUB-"

KEY_PREFIX = "mhc_live_"
SECRET_BYTES = 32
WELCOME_TOKEN_BYTES = 16

DEFAULT_TIER_LABEL = "free"

# Email envelope (free tier).
DEFAULT_EMAIL_FROM = "mhc-cowork <noreply@mhc.regia.it>"
DEFAULT_EMAIL_SUBJECT = "La tua chiave mhc-cowork"

# Env var names.
ENV_RESEND_API_KEY = "RESEND_API_KEY"
ENV_MARKETPLACE = "MHC_MARKETPLACE"
ENV_PLUGIN_NAME = "MHC_PLUGIN_NAME"
ENV_EMAIL_FROM = "MHC_EMAIL_FROM"
ENV_EMAIL_SUBJECT = "MHC_EMAIL_SUBJECT"
ENV_BASE_URL = "MHC_API_BASE_URL"  # used to build the welcome URL


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _generate_plain_key() -> str:
    return KEY_PREFIX + secrets.token_urlsafe(SECRET_BYTES)


def _hash_key(plain: str) -> str:
    return hashlib.sha256(plain.encode("utf-8")).hexdigest()


def _generate_welcome_token() -> str:
    return secrets.token_urlsafe(WELCOME_TOKEN_BYTES)


def _build_install_url(plain_key: str) -> str:
    """Construct the Claude.ai plugin-install deep link with bearer injected."""
    marketplace = os.environ.get(ENV_MARKETPLACE, DEFAULT_MARKETPLACE)
    plugin = os.environ.get(ENV_PLUGIN_NAME, DEFAULT_PLUGIN_NAME)
    return (
        "https://claude.ai/plugins/install"
        f"?marketplace={marketplace}"
        f"&plugin={plugin}"
        f"&env=MHC_BEARER={plain_key}"
    )


def _build_welcome_url(welcome_token: str) -> str:
    """Construct the public welcome URL for the user's email body."""
    base = os.environ.get(ENV_BASE_URL, "https://api.mhc.regia.it").rstrip("/")
    return f"{base}{SIGNUP_WELCOME_PREFIX}{welcome_token}"


def _email_body(plain_key: str, welcome_token: str, install_url: str) -> str:
    """Plain-text email body for the free-tier welcome message (IT)."""
    welcome_url = _build_welcome_url(welcome_token)
    return f"""Ciao,

benvenuto in mhc-cowork.

La tua API key personale e' inclusa qui sotto. Conservala in luogo sicuro
— NON e' recuperabile.

  {plain_key}

Per installare il plugin con la chiave gia' pre-popolata, apri:

  {install_url}

Oppure usa la pagina di benvenuto (apri una sola volta per recuperare i
parametri):

  {welcome_url}

Sicurezza:
- Non condividere la chiave con nessuno
- La chiave da' accesso al tuo decision log e ai tuoi artifact su mhc-cowork
- Per revoca scrivi a noreply@mhc.regia.it

Buon lavoro,
mhc-cowork
"""


def _send_welcome_email(*, to_email: str, plain_key: str, welcome_token: str) -> dict:
    """Send the free-tier welcome email via Resend. Raises on API error."""
    api_key = os.environ.get(ENV_RESEND_API_KEY)
    if not api_key:
        raise RuntimeError(
            f"{ENV_RESEND_API_KEY} not set — cannot send welcome email to {to_email}"
        )
    resend.api_key = api_key

    sender = os.environ.get(ENV_EMAIL_FROM, DEFAULT_EMAIL_FROM)
    subject = os.environ.get(ENV_EMAIL_SUBJECT, DEFAULT_EMAIL_SUBJECT)
    install_url = _build_install_url(plain_key)

    return resend.Emails.send(
        {
            "from": sender,
            "to": [to_email],
            "subject": subject,
            "text": _email_body(plain_key, welcome_token, install_url),
        }
    )


# ---------------------------------------------------------------------------
# ASGI helpers
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


# ---------------------------------------------------------------------------
# Free-tier free flow
# ---------------------------------------------------------------------------

def _insert_free_tier_rows(
    conn: sqlite3.Connection,
    *,
    email: str,
    name: str | None,
    firm: str | None,
    key_hash: str,
    plain_key: str,
    welcome_token: str,
    now: str,
) -> str:
    """Create the synthetic application row + api_keys row. Returns app_id.

    The plain bearer is stashed in applications.notes (JSON) so the welcome
    endpoint can reveal it once; it is redacted on first fetch.
    """
    app_id = str(uuid.uuid4())
    customer_sentinel = f"{FREE_TIER_CUSTOMER_PREFIX}{welcome_token}"
    sub_sentinel = f"{FREE_TIER_SUB_PREFIX}{welcome_token}"

    notes_payload = json.dumps(
        {
            "welcome_token": welcome_token,
            "plain_bearer": plain_key,
            "welcome_consumed": False,
            "name": name,
        },
        ensure_ascii=False,
    )

    conn.execute(
        """
        INSERT INTO applications
            (id, email, firm, role, use_case, notes, submitted_at, status,
             reviewed_at, reviewed_by, rejection_reason, stripe_checkout_session_id)
        VALUES (?, ?, ?, NULL, ?, ?, ?, 'approved', ?, 'free_tier_signup', NULL, NULL)
        """,
        (
            app_id,
            email,
            firm or FREE_TIER_FIRM_SENTINEL,
            "mhc-cowork free tier signup",
            notes_payload,
            now,
            now,
        ),
    )

    conn.execute(
        """
        INSERT INTO api_keys
            (key_hash, user_email, application_id, stripe_customer_id,
             stripe_subscription_id, tier, status, created_at,
             revoked_at, revoked_reason, last_used_at, request_count)
        VALUES (?, ?, ?, ?, ?, ?, 'active', ?, NULL, NULL, NULL, 0)
        """,
        (
            key_hash, email, app_id,
            customer_sentinel, sub_sentinel,
            DEFAULT_TIER_LABEL, now,
        ),
    )
    return app_id


async def _handle_free_tier_signup(send: Send, body: dict) -> None:
    """Free-tier path: issue Bearer + send email + record both DB rows."""
    email = (body.get("email") or "").strip()
    if not email or "@" not in email:
        await _send_json(
            send,
            400,
            {
                "error": "invalid_email",
                "error_description": "Field 'email' is required and must be a valid address.",
            },
        )
        return

    name = body.get("name")
    firm = body.get("firm")

    plain_key = _generate_plain_key()
    key_hash = _hash_key(plain_key)
    welcome_token = _generate_welcome_token()
    now = _now_iso()

    init_db()
    conn = connect()
    try:
        conn.execute("BEGIN")
        try:
            # Astronomically unlikely collision on either key_hash or token,
            # but check anyway — if it happens, retry on Stripe webhook
            # pattern would just regenerate. Here we bail loud.
            for sql, params, name_msg in (
                ("SELECT 1 FROM api_keys WHERE key_hash = ?",
                 (key_hash,), "key_hash"),
            ):
                if conn.execute(sql, params).fetchone() is not None:
                    conn.execute("ROLLBACK")
                    print(
                        f"[signup] FATAL collision on {name_msg} for {email} — aborting",
                        file=sys.stderr,
                    )
                    await _send_json(
                        send,
                        500,
                        {
                            "error": "internal_error",
                            "error_description": "Please retry.",
                        },
                    )
                    return

            _insert_free_tier_rows(
                conn,
                email=email,
                name=name,
                firm=firm,
                key_hash=key_hash,
                plain_key=plain_key,
                welcome_token=welcome_token,
                now=now,
            )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
    finally:
        conn.close()

    # Post-commit: send the email. If Resend fails we still have a valid
    # bearer in the DB; the lawyer can ask founder to resend. Loud log.
    try:
        _send_welcome_email(
            to_email=email, plain_key=plain_key, welcome_token=welcome_token
        )
        email_sent = True
    except Exception as exc:
        print(f"[signup] free-tier email send failed for {email}: {exc!r}",
              file=sys.stderr)
        email_sent = False

    await _send_json(
        send,
        200,
        {
            "tier": "free",
            "status": "email_sent" if email_sent else "email_failed",
            "email": email,
        },
    )


# ---------------------------------------------------------------------------
# Paid-tier Stripe flow (post-MVP; gated on stripe_price_id)
# ---------------------------------------------------------------------------

def _create_paid_checkout_session(price_id: str) -> dict:
    """Wrap the Stripe SDK call. Lazy-imports stripe so free-tier-only deploys
    don't need the dependency available at import time (it is in
    requirements.txt regardless, but this keeps the failure mode local).
    """
    import stripe  # type: ignore

    secret_key = os.environ.get("STRIPE_SECRET_KEY")
    if not secret_key:
        raise RuntimeError("STRIPE_SECRET_KEY not set — cannot create paid Checkout Session")

    success_url = os.environ.get(
        "MHC_SIGNUP_SUCCESS_URL", "https://mhc.regia.it/benvenuto/"
    )
    cancel_url = os.environ.get(
        "MHC_SIGNUP_CANCEL_URL", "https://mhc.regia.it/signup/"
    )

    stripe.api_key = secret_key
    return stripe.checkout.Session.create(
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        payment_method_collection="if_required",
        success_url=success_url,
        cancel_url=cancel_url,
    )


async def _handle_paid_tier_signup(send: Send, body: dict) -> None:
    """Stripe Checkout flow — webhook later issues the key."""
    price_id = body.get("stripe_price_id")
    try:
        session = _create_paid_checkout_session(price_id)
    except RuntimeError as exc:
        print(f"[signup] paid configuration error: {exc}", file=sys.stderr)
        await _send_json(
            send,
            500,
            {
                "error": "configuration_error",
                "error_description": "Server misconfigured for paid tier.",
            },
        )
        return
    except Exception as exc:
        # Catch StripeError from the lazy-imported SDK without importing it
        # at module level.
        print(f"[signup] paid Stripe error: {exc!r}", file=sys.stderr)
        await _send_json(
            send,
            502,
            {
                "error": "stripe_error",
                "error_description": getattr(exc, "user_message", None) or str(exc),
            },
        )
        return

    url = getattr(session, "url", None) or (
        session.get("url") if hasattr(session, "get") else None
    )
    if not url:
        await _send_json(
            send,
            502,
            {
                "error": "stripe_error",
                "error_description": "Stripe response missing url field.",
            },
        )
        return

    await _send_json(send, 200, {"tier": "paid", "url": url})


# ---------------------------------------------------------------------------
# ASGI routes
# ---------------------------------------------------------------------------

async def signup_endpoint(scope: Scope, receive: Receive, send: Send) -> None:
    """Bare ASGI handler for POST /signup/create-checkout-session.

    Routing:
      - If body.tier == "free" OR no stripe_price_id → free-tier branch.
      - Else → paid Stripe Checkout branch.
    """
    method = scope.get("method", "")
    if method == "OPTIONS":
        # Minimal CORS preflight. Refine allowed origins per deployment.
        await _read_body(receive)
        await send(
            {
                "type": "http.response.start",
                "status": 204,
                "headers": [
                    (b"access-control-allow-origin", b"*"),
                    (b"access-control-allow-methods", b"POST, OPTIONS"),
                    (b"access-control-allow-headers", b"content-type"),
                    (b"access-control-max-age", b"86400"),
                ],
            }
        )
        await send({"type": "http.response.body", "body": b""})
        return

    if method != "POST":
        await _send_json(send, 405, {"error": "method_not_allowed"})
        return

    raw_body = await _read_body(receive)
    try:
        body = json.loads(raw_body) if raw_body else {}
    except json.JSONDecodeError:
        await _send_json(
            send,
            400,
            {"error": "invalid_json", "error_description": "Body is not valid JSON."},
        )
        return

    if not isinstance(body, dict):
        await _send_json(
            send,
            400,
            {"error": "invalid_json", "error_description": "Body must be a JSON object."},
        )
        return

    tier = body.get("tier")
    price_id = body.get("stripe_price_id")

    # Free-tier branch: explicit tier=free OR no stripe_price_id at all.
    if tier == "free" or not price_id:
        await _handle_free_tier_signup(send, body)
        return

    await _handle_paid_tier_signup(send, body)


async def welcome_endpoint(scope: Scope, receive: Receive, send: Send) -> None:
    """Bare ASGI handler for GET /signup/welcome/<token>.

    Mounted under /signup/welcome in server.py — Starlette's Mount strips
    the mount prefix from scope["path"], so inside this handler the path
    is just "/<token>". For the unmounted case (e.g. running this handler
    as a top-level ASGI app in tests), the same parsing works because we
    fall back to the absolute path-prefix strip if the relative form
    doesn't yield a token.

    First successful read returns {email, bearer_key, install_url} and
    redacts plain_bearer from applications.notes. Subsequent reads return
    410 Gone.
    """
    method = scope.get("method", "")
    if method != "GET":
        await _send_json(send, 405, {"error": "method_not_allowed"})
        return

    raw_path = scope.get("path", "") or ""
    # Mounted form: scope["path"] is "/<token>" (mount prefix stripped).
    # Unmounted form: scope["path"] is "/signup/welcome/<token>".
    if raw_path.startswith(SIGNUP_WELCOME_PREFIX):
        token = raw_path[len(SIGNUP_WELCOME_PREFIX):].strip("/")
    else:
        token = raw_path.strip("/")

    if not token:
        await _send_json(send, 404, {"error": "not_found"})
        return

    # Drain the empty GET body (some servers require receive() to be called).
    await _read_body(receive)

    init_db()
    conn = connect()
    try:
        # We search applications.notes for the welcome_token. Since notes is
        # JSON we cannot index on it; the table is small (free-tier signups)
        # so a full scan is acceptable for MVP. Move to a dedicated column
        # if the row count grows.
        rows = conn.execute(
            "SELECT id, email, notes FROM applications WHERE notes LIKE ?",
            (f'%"welcome_token": "{token}"%',),
        ).fetchall()

        match = None
        for row in rows:
            try:
                notes = json.loads(row["notes"]) if row["notes"] else {}
            except (json.JSONDecodeError, TypeError):
                continue
            if notes.get("welcome_token") == token:
                match = (row, notes)
                break

        if match is None:
            await _send_json(send, 404, {"error": "token_not_found"})
            return

        row, notes = match
        if notes.get("welcome_consumed"):
            await _send_json(send, 410, {"error": "token_already_consumed"})
            return

        plain_bearer = notes.get("plain_bearer")
        if not plain_bearer:
            # Defensive: notes intact but plain_bearer missing → treat as gone.
            await _send_json(send, 410, {"error": "token_already_consumed"})
            return

        # Redact plain_bearer and mark consumed.
        notes["welcome_consumed"] = True
        notes.pop("plain_bearer", None)
        notes["welcome_consumed_at"] = _now_iso()
        conn.execute(
            "UPDATE applications SET notes = ? WHERE id = ?",
            (json.dumps(notes, ensure_ascii=False), row["id"]),
        )

        install_url = _build_install_url(plain_bearer)
        await _send_json(
            send,
            200,
            {
                "email": row["email"],
                "bearer_key": plain_bearer,
                "install_url": install_url,
            },
        )
    finally:
        conn.close()


__all__ = [
    "SIGNUP_CHECKOUT_PATH",
    "SIGNUP_WELCOME_PREFIX",
    "signup_endpoint",
    "welcome_endpoint",
    "ENV_RESEND_API_KEY",
    "DEFAULT_TIER_LABEL",
    "FREE_TIER_FIRM_SENTINEL",
]
