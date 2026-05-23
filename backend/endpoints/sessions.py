# Part of MHC-H. AGPL v3 — see LICENSE-AGPL
"""
endpoints/sessions.py — REST handlers for lawyer-side session lifecycle.

Endpoints:
  POST /api/sessions
    Open a new session. Body (JSON, all fields optional):
      - config_json   (str): stringified JSON used as the session state seed.
                             Defaults to "{}".
      - project_name  (str): human-readable label.
    Response 200: {sid, state_json, started_at}
    Inserts a row into lawyer_sessions, owned by the authenticated user.

  GET /api/sessions/{sid}
    Read a session. Ownership-scoped (the caller can only fetch their own
    sessions).
    Response 200: {sid, state_json, started_at, ended_at, exported, project_name}
    Response 404: {error: "not_found"} if no row matches (sid, user_email).

  POST /api/sessions/{sid}/end
    Finalize a session. Body (JSON, all fields optional):
      - goal                (str)
      - artifacts_produced  (list[str])
      - exported            (bool, default False)
    Response 200: {sid, ended_at, exported, transcript_md}
    Server-side conversation transcript is empty in MVP (`transcript_md: ""`);
    a post-MVP follow-up may capture chat history server-side via a separate
    skill-driven endpoint.

Authentication: BearerAuthMiddleware. The user_email + bearer token are read
from `scope["mhc_user_email"]` / `scope["mhc_bearer_token"]`.

These endpoints do NOT require MHC-Audit-Sig — they manage session lifecycle,
not append-only governance artifacts. (POST /api/sessions starts a session and
generates the SID itself, so the client cannot compute a signature in advance;
POST /api/sessions/{sid}/end is idempotent end-of-life metadata only. The
governance write endpoints — /api/artifacts, /api/decisions — are the ones
audit-signed.)

Stdlib + starlette only.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from starlette.requests import Request
from starlette.responses import JSONResponse

from ..db import connection, init_db


def _now_iso() -> str:
    """UTC ISO-8601 timestamp with seconds precision (and Z suffix)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _generate_sid() -> str:
    """Generate a session ID from current UTC time, format SID-YYYYMMDD-HHMMSS."""
    return f"SID-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"


def _user_email_from_request(request: Request) -> str | None:
    return request.scope.get("mhc_user_email")


# ---------------------------------------------------------------------------
# POST /api/sessions
# ---------------------------------------------------------------------------

async def create_session(request: Request) -> JSONResponse:
    """Open a new session row for the authenticated user."""
    user_email = _user_email_from_request(request)
    if not user_email:
        # Defensive — middleware should never let an unauthenticated request
        # reach here. If it does, fail closed.
        return JSONResponse({"error": "unauthenticated"}, status_code=401)

    try:
        body_bytes = await request.body()
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

    config_json = body.get("config_json", "{}")
    project_name = body.get("project_name")

    if not isinstance(config_json, str):
        # Accept dicts too as a kindness (some clients send the object).
        if isinstance(config_json, dict):
            config_json = json.dumps(config_json, ensure_ascii=False)
        else:
            return JSONResponse(
                {
                    "error": "invalid_field",
                    "error_description": "config_json must be a JSON string.",
                },
                status_code=400,
            )

    sid = _generate_sid()
    started_at = _now_iso()

    init_db()
    with connection() as conn:
        conn.execute(
            """
            INSERT INTO lawyer_sessions
                (sid, user_email, project_name, state_json, started_at, ended_at, exported)
            VALUES (?, ?, ?, ?, ?, NULL, 0)
            """,
            (sid, user_email, project_name, config_json, started_at),
        )

    return JSONResponse(
        {
            "sid": sid,
            "state_json": config_json,
            "started_at": started_at,
        },
        status_code=200,
    )


# ---------------------------------------------------------------------------
# GET /api/sessions/{sid}
# ---------------------------------------------------------------------------

async def get_session(request: Request) -> JSONResponse:
    """Read a single session, scoped to the caller's user_email."""
    user_email = _user_email_from_request(request)
    if not user_email:
        return JSONResponse({"error": "unauthenticated"}, status_code=401)

    sid = request.path_params.get("sid", "")
    if not sid:
        return JSONResponse({"error": "missing_sid"}, status_code=400)

    init_db()
    with connection() as conn:
        row = conn.execute(
            """
            SELECT sid, state_json, started_at, ended_at, exported, project_name
              FROM lawyer_sessions
             WHERE sid = ?
               AND user_email = ?
            """,
            (sid, user_email),
        ).fetchone()

    if row is None:
        return JSONResponse({"error": "not_found"}, status_code=404)

    return JSONResponse(
        {
            "sid": row["sid"],
            "state_json": row["state_json"],
            "started_at": row["started_at"],
            "ended_at": row["ended_at"],
            "exported": bool(row["exported"]),
            "project_name": row["project_name"],
        },
        status_code=200,
    )


# ---------------------------------------------------------------------------
# POST /api/sessions/{sid}/end
# ---------------------------------------------------------------------------

async def end_session(request: Request) -> JSONResponse:
    """Mark a session ended; record optional goal + artifacts_produced.

    The lawyer_sessions schema (Fase 1 plan) does not include columns for
    goal / artifacts_produced — they are not part of the append-only audit
    trail (which lives in decisions + artifacts tables). We accept them in
    the body for API symmetry with the MHC-L MCP `mhc_end_session` tool,
    and we echo them in the response for client convenience, but they are
    NOT persisted on the lawyer_sessions row. If post-MVP requirements
    surface a need to persist them, add columns and migrate forward.

    `exported` flag IS persisted (it's a column on lawyer_sessions).
    """
    user_email = _user_email_from_request(request)
    if not user_email:
        return JSONResponse({"error": "unauthenticated"}, status_code=401)

    sid = request.path_params.get("sid", "")
    if not sid:
        return JSONResponse({"error": "missing_sid"}, status_code=400)

    try:
        body_bytes = await request.body()
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

    goal = body.get("goal")
    artifacts_produced = body.get("artifacts_produced") or []
    exported = bool(body.get("exported", False))

    if not isinstance(artifacts_produced, list):
        return JSONResponse(
            {
                "error": "invalid_field",
                "error_description": "artifacts_produced must be a list.",
            },
            status_code=400,
        )

    ended_at = _now_iso()

    init_db()
    with connection() as conn:
        # Ownership-scoped UPDATE: cannot end someone else's session.
        cur = conn.execute(
            """
            UPDATE lawyer_sessions
               SET ended_at = ?,
                   exported = ?
             WHERE sid = ?
               AND user_email = ?
               AND ended_at IS NULL
            """,
            (ended_at, 1 if exported else 0, sid, user_email),
        )
        if cur.rowcount == 0:
            # Either row doesn't exist for this user, or already ended.
            existing = conn.execute(
                "SELECT ended_at FROM lawyer_sessions WHERE sid = ? AND user_email = ?",
                (sid, user_email),
            ).fetchone()
            if existing is None:
                return JSONResponse({"error": "not_found"}, status_code=404)
            # Already ended — return current state (idempotent).
            return JSONResponse(
                {
                    "sid": sid,
                    "ended_at": existing["ended_at"],
                    "exported": bool(exported),
                    "transcript_md": "",
                    "already_ended": True,
                },
                status_code=200,
            )

    return JSONResponse(
        {
            "sid": sid,
            "ended_at": ended_at,
            "exported": exported,
            "goal": goal,
            "artifacts_produced": artifacts_produced,
            # TODO(post-MVP): server-side transcript capture. Today the chat
            # history lives client-side (Anthropic plugin runtime); we have
            # no upload pipeline. Empty string preserves API shape.
            "transcript_md": "",
        },
        status_code=200,
    )


__all__ = [
    "create_session",
    "get_session",
    "end_session",
]
