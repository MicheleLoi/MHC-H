# Part of mhc-cowork. AGPL v3 — see LICENSE-AGPL
"""
audit.py — Audit signature verification for write endpoints.

POST endpoints that mutate governance state (/api/artifacts, /api/decisions)
require an `MHC-Audit-Sig` header containing the hex HMAC-SHA256 of the
concatenated string `<sid> + <body_json>` keyed by the caller's Bearer
token.

Scheme (canon, plan §"Audit signature scheme"):

    sig = hmac.new(
        key=bearer_key.encode("utf-8"),
        msg=(sid + body_json).encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()

Server receives the same body bytes the skill computed against; we
reconstruct the signature from (bearer, sid, raw_body) and compare with
hmac.compare_digest. Bearer is taken from scope (set by
BearerAuthMiddleware on auth success). `sid` is read from the parsed
JSON body — endpoints already need to parse the body to extract their
domain fields, so the body is parsed once and the sid string is passed
in here for verification.

If sid is missing from the body, verification fails — every write
endpoint requires a sid for the session-scoped audit trail (decisions
optionally tolerate `sid: null` in their domain model, but the audit
signature still requires the literal value the skill used, which can be
the empty string).

Stdlib only.
"""

from __future__ import annotations

import hashlib
import hmac
from typing import Any, Awaitable, Callable

# Type aliases for clarity
Send = Callable[[dict], Awaitable[None]]


AUDIT_HEADER = b"mhc-audit-sig"


def extract_audit_signature(headers: list[tuple[bytes, bytes]]) -> str | None:
    """Return the MHC-Audit-Sig header value (case-insensitive), or None."""
    for name, value in headers:
        if name.lower() == AUDIT_HEADER:
            try:
                return value.decode("latin-1").strip()
            except UnicodeDecodeError:
                return None
    return None


def compute_signature(bearer_key: str, sid: str, body_bytes: bytes) -> str:
    """Compute hex HMAC-SHA256(bearer_key, sid + body) as the canon prescribes.

    `body_bytes` is the raw HTTP request body (the JSON the skill sent). We
    treat sid and body_bytes as bytes joined in that order, keyed by the
    bearer token's UTF-8 encoding. Returns a lowercase hex digest.
    """
    msg = sid.encode("utf-8") + body_bytes
    return hmac.new(
        key=bearer_key.encode("utf-8"),
        msg=msg,
        digestmod=hashlib.sha256,
    ).hexdigest()


def verify_signature(
    *,
    bearer_key: str,
    sid: str,
    body_bytes: bytes,
    provided_signature: str | None,
) -> bool:
    """Compare provided signature against the freshly computed one.

    Uses hmac.compare_digest for constant-time equality. Returns False if
    `provided_signature` is missing or doesn't match.
    """
    if not provided_signature:
        return False
    expected = compute_signature(bearer_key, sid, body_bytes)
    return hmac.compare_digest(expected, provided_signature)


__all__ = [
    "AUDIT_HEADER",
    "extract_audit_signature",
    "compute_signature",
    "verify_signature",
]
