# Part of mhc-cowork. AGPL v3 — see LICENSE-AGPL
"""
auth.py — mhc-cowork Bearer token validation (HTTP transport).

Thin ASGI middleware that:
  1. Reads `Authorization: Bearer <token>` header from the incoming request.
  2. SHA-256 hashes the token and looks it up in the SQLite `api_keys` table
     (constant-time comparison via hmac.compare_digest against the row found).
  3. Returns 401 + minimal JSON error body if missing / invalid / inactive.
  4. Attaches scope["mhc_bearer_token"] and scope["mhc_user_email"] so
     downstream handlers (audit signature verification, ownership scoping)
     can read them without re-querying.
  5. Otherwise passes through to the wrapped ASGI app.

Storage:
  SQLite (see db.py). Path resolved from env var MHC_API_DB_PATH,
  defaulting to ~/.mhc-cowork-keystore.db.

Design choice (verbatim from MHC-L Phase 1):
  We do NOT use mcp.server.auth.middleware.bearer_auth.RequireAuthMiddleware.
  That class is part of the MCP SDK's OAuth 2.1 stack. mhc-cowork has no
  OAuth flow, no scopes, no expiring tokens — just static SHA-256 keystore
  lookup against an invitation list. Custom thin middleware is ~60 lines, no
  SDK coupling, easier to audit. (Principle 9 Ockham.)

Hot-reload semantics:
  No in-process cache: every HTTP request opens a fresh SQLite connection
  and runs a single indexed SELECT on key_hash (PRIMARY KEY, O(log N)).
  MVP traffic is low; correctness > micro-optimization.

Path-skip exemptions:
  Some HTTP routes must not require Bearer auth — by design. The middleware
  accepts a `skip_path_prefixes` parameter (defaulting to DEFAULT_SKIP_PATHS)
  and bypasses auth when the request path startswith any prefix in the list.

  Default exemptions:
    - /webhooks/stripe         (Stripe webhook delivery — verified by Stripe
                                signature, not Bearer)
    - /signup/                 (Self-service signup — applicant has no key
                                yet, the endpoint exists to issue one.
                                Covers /signup/create-checkout-session and
                                /signup/welcome/<token>. Trailing slash
                                prevents an accidental match on something
                                like /signups or /signupfoo.)

Stdlib only.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any, Awaitable, Callable

from .db import DB_PATH_ENV, DEFAULT_DB_PATH, connect, resolve_db_path

# Type aliases (avoid hard dep on starlette/asgi typing for clarity)
Scope = dict[str, Any]
Message = dict[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]
ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BEARER_PREFIX = "bearer "  # case-insensitive match

# Default list of path prefixes that bypass Bearer auth. See module docstring
# "Path-skip exemptions" for rationale per entry.
DEFAULT_SKIP_PATHS: tuple[str, ...] = (
    "/webhooks/stripe",
    "/signup/",
)


# ---------------------------------------------------------------------------
# Token lookup
# ---------------------------------------------------------------------------

def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def validate_token(
    token: str, db_path: Path | None = None
) -> tuple[bool, str | None, str | None]:
    """
    Look up `token` in the SQLite api_keys table.

    Returns (is_valid, reason_if_invalid_or_None, user_email_if_valid_or_None).

    Reasons returned (negative path):
      - "missing_token"  — empty / None token
      - "invalid_token"  — no api_keys row matches the SHA-256 hash
      - "revoked_token"  — row exists but status != 'active'
                           (covers 'revoked', 'expired', 'past_due')

    Constant-time discipline:
      The PRIMARY KEY index lookup itself is not strictly constant-time across
      "hit" vs "miss", but the secret is the bearer token, never the hash.
      An attacker controls the hash candidate (= H(token_guess)); the timing
      of an indexed dict-lookup on the key_hash column reveals presence of
      that hash in the table, which is identical information to what 401 vs
      200 already reveals. We additionally call hmac.compare_digest on the
      retrieved row to harden the equality step itself.
    """
    if not token:
        return False, "missing_token", None
    candidate_hash = _hash_token(token)
    path = db_path or resolve_db_path()
    try:
        conn = connect(path)
    except sqlite3.Error:
        # Surface as caller-visible failure; the middleware fail-closes.
        raise
    try:
        cur = conn.execute(
            "SELECT key_hash, status, user_email FROM api_keys WHERE key_hash = ?",
            (candidate_hash,),
        )
        row = cur.fetchone()
    finally:
        conn.close()
    if row is None:
        return False, "invalid_token", None
    # Defensive constant-time equality re-check on the stored hash.
    if not hmac.compare_digest(candidate_hash, row["key_hash"]):
        return False, "invalid_token", None
    if row["status"] != "active":
        return False, "revoked_token", None
    return True, None, row["user_email"]


# ---------------------------------------------------------------------------
# ASGI middleware
# ---------------------------------------------------------------------------

class BearerAuthMiddleware:
    """
    ASGI middleware enforcing Bearer token auth against the mhc-cowork SQLite
    api_keys table.

    On success, the middleware attaches the bearer token and user email to the
    ASGI scope:
      scope["mhc_bearer_token"]  → str (plain bearer, used for audit signature
                                   reconstruction by POST endpoints)
      scope["mhc_user_email"]    → str (used for row ownership scoping by REST
                                   handlers)

    No keystore caching: the DB is queried on every HTTP request (MVP
    traffic is low; SQLite indexed lookup on PRIMARY KEY is microseconds).
    """

    def __init__(
        self,
        app: ASGIApp,
        db_path: Path | None = None,
        skip_path_prefixes: tuple[str, ...] | list[str] | None = None,
    ):
        self.app = app
        self.db_path = db_path or resolve_db_path()
        # Normalize to tuple of strings. None → use DEFAULT_SKIP_PATHS.
        # Empty tuple/list → no skipping (every path requires auth, useful in
        # tests).
        if skip_path_prefixes is None:
            self.skip_path_prefixes: tuple[str, ...] = DEFAULT_SKIP_PATHS
        else:
            self.skip_path_prefixes = tuple(skip_path_prefixes)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        # Pass-through for non-HTTP scopes (lifespan, websocket — defensive).
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        # Path-skip: routes that must not require Bearer auth.
        path = scope.get("path", "") or ""
        for prefix in self.skip_path_prefixes:
            if path.startswith(prefix):
                await self.app(scope, receive, send)
                return

        token = _extract_bearer(scope.get("headers", []))
        if token is None:
            await _send_401(
                send,
                error="missing_bearer",
                description="Missing or malformed Authorization header.",
            )
            return

        try:
            valid, reason, user_email = validate_token(token, self.db_path)
        except sqlite3.Error as exc:
            # Fail closed — never grant access on DB errors.
            print(f"[auth] DB lookup error: {exc}", file=sys.stderr)
            await _send_401(
                send, error="server_error", description="Auth backend unavailable."
            )
            return

        if not valid:
            await _send_401(
                send,
                error=reason or "invalid_token",
                description="Bearer token rejected.",
            )
            return

        # Stash the bearer + user email for downstream handlers. The bearer is
        # required for audit signature reconstruction (POST endpoints that
        # require MHC-Audit-Sig); user_email is used for ownership scoping on
        # SELECT queries.
        scope["mhc_bearer_token"] = token
        scope["mhc_user_email"] = user_email

        await self.app(scope, receive, send)


def _extract_bearer(raw_headers: list[tuple[bytes, bytes]]) -> str | None:
    """Return the Bearer token from the ASGI headers list, or None."""
    for name, value in raw_headers:
        if name.lower() == b"authorization":
            try:
                decoded = value.decode("latin-1")
            except UnicodeDecodeError:
                return None
            if decoded.lower().startswith(BEARER_PREFIX):
                tok = decoded[len(BEARER_PREFIX):].strip()
                return tok or None
            return None
    return None


async def _send_401(send: Send, *, error: str, description: str) -> None:
    body = json.dumps(
        {"error": error, "error_description": description}, ensure_ascii=False
    ).encode("utf-8")
    await send(
        {
            "type": "http.response.start",
            "status": 401,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode("ascii")),
                (b"www-authenticate", f'Bearer error="{error}"'.encode("latin-1")),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})


__all__ = [
    "BearerAuthMiddleware",
    "validate_token",
    "DB_PATH_ENV",
    "DEFAULT_DB_PATH",
    "DEFAULT_SKIP_PATHS",
]
