# Part of mhc-cowork. AGPL v3 — see LICENSE-AGPL
"""
endpoints/decisions.py — REST handlers for the append-only decision log.

Endpoints:
  POST /api/decisions
    Append a single decision entry. Append-only — no UPDATE or DELETE
    handlers are exposed here, by design (Themis: the decision log is
    immutable cross-domain authority).

    Body (JSON):
      - topic        (str, required)
      - decision     (str, required)
      - context      (str, optional)
      - options      (list, optional) — anything; persisted as JSON string
      - rationale    (str, optional)
      - sid          (str, optional) — session ID this decision belongs to

    Headers:
      - Authorization:    Bearer <key>
      - MHC-Audit-Sig:    hex HMAC-SHA256 over (sid + raw_body) keyed by
                          the bearer token. If sid is omitted from body, the
                          empty string is used as the signature's sid input
                          (skill side must mirror this).

    Response 200:
      {decision_id: "DEC-<uuid>", created_at: "<iso>"}

  GET /api/decisions
    Read the caller's own decision log (ownership-scoped by user_email).
    Optional query params:
      - since   (YYYY-MM-DD): filter created_at >= since (date interpreted
                              as 00:00:00Z of the given calendar day).
      - sid     (str):        filter to a single session.

    Response 200:
      [
        {decision_id, sid, topic, context, options, decision, rationale,
         created_at},
        ...
      ]

    Read-only — no audit signature required (Themis: audit is on writes,
    reads are observation, not authority).

Stdlib + starlette only.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from starlette.requests import Request
from starlette.responses import JSONResponse

from ..audit import extract_audit_signature, verify_signature
from ..db import connection, init_db


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# POST /api/decisions
# ---------------------------------------------------------------------------

async def create_decision(request: Request) -> JSONResponse:
    """Append a decision entry. Audit-signed, append-only."""
    user_email = request.scope.get("mhc_user_email")
    bearer = request.scope.get("mhc_bearer_token")
    if not user_email or not bearer:
        return JSONResponse({"error": "unauthenticated"}, status_code=401)

    body_bytes = await request.body()

    try:
        body = json.loads(body_bytes) if body_bytes else {}
    except json.JSONDecodeError:
        return JSONResponse(
            {"error": "invalid_json", "error_description": "Body is not valid JSON."},
            status_code=400,
        )

    if not isinstance(body, dict):
        return JSONResponse(
            {"error": "invalid_json", "error_description": "Body must be a JSON object."},
            status_code=400,
        )

    topic = body.get("topic")
    decision_text = body.get("decision")
    context = body.get("context")
    options = body.get("options")
    rationale = body.get("rationale")
    sid = body.get("sid")  # may be None — decisions can be SID-less

    # ---------- Field validation ----------
    if not topic or not isinstance(topic, str):
        return JSONResponse(
            {"error": "missing_field", "error_description": "topic is required."},
            status_code=400,
        )
    if not decision_text or not isinstance(decision_text, str):
        return JSONResponse(
            {
                "error": "missing_field",
                "error_description": "decision is required.",
            },
            status_code=400,
        )

    # ---------- Audit signature ----------
    # The signature is computed against `sid + body_json`; if sid is omitted
    # the empty string is used so the skill side has a deterministic rule.
    sig_sid_input = sid if isinstance(sid, str) else ""
    provided_sig = extract_audit_signature(request.scope.get("headers", []))
    if not verify_signature(
        bearer_key=bearer,
        sid=sig_sid_input,
        body_bytes=body_bytes,
        provided_signature=provided_sig,
    ):
        return JSONResponse(
            {"error": "missing or invalid audit signature"}, status_code=400
        )

    # ---------- Serialize options ----------
    if options is None:
        options_json = None
    else:
        try:
            options_json = json.dumps(options, ensure_ascii=False)
        except (TypeError, ValueError):
            return JSONResponse(
                {
                    "error": "invalid_field",
                    "error_description": "options must be JSON-serializable.",
                },
                status_code=400,
            )

    decision_id = f"DEC-{uuid.uuid4().hex}"
    created_at = _now_iso()

    init_db()
    with connection() as conn:
        conn.execute(
            """
            INSERT INTO decisions
                (decision_id, user_email, sid, topic, context, options_json,
                 decision, rationale, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                decision_id,
                user_email,
                sid,
                topic,
                context,
                options_json,
                decision_text,
                rationale,
                created_at,
            ),
        )

    return JSONResponse(
        {"decision_id": decision_id, "created_at": created_at},
        status_code=200,
    )


# ---------------------------------------------------------------------------
# GET /api/decisions
# ---------------------------------------------------------------------------

async def list_decisions(request: Request) -> JSONResponse:
    """Return the caller's decisions, optionally filtered by since + sid."""
    user_email = request.scope.get("mhc_user_email")
    if not user_email:
        return JSONResponse({"error": "unauthenticated"}, status_code=401)

    qp = request.query_params
    since_str = qp.get("since")
    sid_filter = qp.get("sid")

    # Validate the since parameter — if provided, must be YYYY-MM-DD and
    # parseable. We then expand it to the start-of-day ISO timestamp the
    # column stores (`YYYY-MM-DDTHH:MM:SSZ`).
    since_iso: str | None = None
    if since_str:
        try:
            day = datetime.strptime(since_str, "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            return JSONResponse(
                {
                    "error": "invalid_query",
                    "error_description": "since must be YYYY-MM-DD.",
                },
                status_code=400,
            )
        since_iso = day.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Build the query.
    where_clauses = ["user_email = ?"]
    params: list = [user_email]
    if since_iso is not None:
        where_clauses.append("created_at >= ?")
        params.append(since_iso)
    if sid_filter:
        where_clauses.append("sid = ?")
        params.append(sid_filter)

    where_sql = " AND ".join(where_clauses)
    sql = (
        "SELECT decision_id, sid, topic, context, options_json, decision, "
        "       rationale, created_at "
        f"  FROM decisions "
        f" WHERE {where_sql} "
        " ORDER BY created_at ASC"
    )

    init_db()
    with connection() as conn:
        rows = conn.execute(sql, params).fetchall()

    out: list[dict] = []
    for r in rows:
        options_val = None
        if r["options_json"]:
            try:
                options_val = json.loads(r["options_json"])
            except (json.JSONDecodeError, TypeError):
                # Stored value is unparseable — return it raw so the caller
                # can investigate, but don't crash.
                options_val = r["options_json"]
        out.append(
            {
                "decision_id": r["decision_id"],
                "sid": r["sid"],
                "topic": r["topic"],
                "context": r["context"],
                "options": options_val,
                "decision": r["decision"],
                "rationale": r["rationale"],
                "created_at": r["created_at"],
            }
        )

    return JSONResponse(out, status_code=200)


__all__ = ["create_decision", "list_decisions"]
