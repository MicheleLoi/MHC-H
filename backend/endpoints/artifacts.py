# Part of MHC-H. AGPL v3 — see LICENSE-AGPL
"""
endpoints/artifacts.py — REST handler for artifact rendering + persistence.

Endpoint:
  POST /api/artifacts
    Body (JSON):
      - artifact_type   (str): one of {note, trace, pdl, modlog,
                                       decision_entry, draft, session_log,
                                       prompt}.
      - session_id      (str): the SID the artifact belongs to.
      - title           (str): artifact title.
      - content         (dict): type-specific content fields. See
                                templates.py for the per-type schema.
      - project_name    (str, optional): label propagated to the rendered
                                         markdown.
    Headers:
      - Authorization:    Bearer <key>
      - MHC-Audit-Sig:    hex HMAC-SHA256 over (sid + raw_body) keyed by
                          the bearer token.

    Response 200:
      {
        artifact_id: "ART-<uuid>",
        content_md:  "<rendered markdown>"
      }

    Response 400 on missing/invalid audit signature, invalid JSON, missing
    required fields, or template rendering errors.

Storage: the rendered markdown is persisted server-side in the artifacts
table (artifact_id, user_email, sid, artifact_type, title, content_md,
created_at). The skill can then download the markdown for the lawyer to
save locally if desired — but the server is the authoritative record
("provenance-tracked output", plan §"4 obiettivi MVP").

Stdlib + starlette only (plus internal templates module).
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from starlette.requests import Request
from starlette.responses import JSONResponse

from ..audit import extract_audit_signature, verify_signature
from ..db import connection, init_db
from ..templates import FILL_FUNCTIONS, fill_artifact


SUPPORTED_TYPES = set(FILL_FUNCTIONS.keys()) | {"session_log", "prompt"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


async def create_artifact(request: Request) -> JSONResponse:
    """Render a templated artifact + persist + return rendered markdown."""
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

    artifact_type = body.get("artifact_type")
    session_id = body.get("session_id")
    title = body.get("title") or ""
    project_name = body.get("project_name") or ""
    content = body.get("content") or {}

    # ---------- Field validation ----------
    if not artifact_type:
        return JSONResponse(
            {
                "error": "missing_field",
                "error_description": "artifact_type is required.",
            },
            status_code=400,
        )
    if artifact_type not in SUPPORTED_TYPES:
        return JSONResponse(
            {
                "error": "invalid_artifact_type",
                "error_description": (
                    f"artifact_type '{artifact_type}' not supported. "
                    f"Supported: {sorted(SUPPORTED_TYPES)}."
                ),
            },
            status_code=400,
        )
    if not session_id:
        return JSONResponse(
            {
                "error": "missing_field",
                "error_description": "session_id is required.",
            },
            status_code=400,
        )
    if not isinstance(content, dict):
        return JSONResponse(
            {
                "error": "invalid_field",
                "error_description": "content must be an object.",
            },
            status_code=400,
        )

    # ---------- Audit signature ----------
    provided_sig = extract_audit_signature(request.scope.get("headers", []))
    if not verify_signature(
        bearer_key=bearer,
        sid=session_id,
        body_bytes=body_bytes,
        provided_signature=provided_sig,
    ):
        return JSONResponse(
            {"error": "missing or invalid audit signature"}, status_code=400
        )

    # ---------- Render template ----------
    try:
        content_md = fill_artifact(
            artifact_type=artifact_type,
            session_id=session_id,
            project_name=project_name,
            title=title,
            content=content,
        )
    except ValueError as exc:
        return JSONResponse(
            {"error": "template_error", "error_description": str(exc)},
            status_code=400,
        )

    # ---------- Persist ----------
    artifact_id = f"ART-{uuid.uuid4().hex}"
    created_at = _now_iso()

    init_db()
    with connection() as conn:
        conn.execute(
            """
            INSERT INTO artifacts
                (artifact_id, user_email, sid, artifact_type, title, content_md, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                artifact_id,
                user_email,
                session_id,
                artifact_type,
                title,
                content_md,
                created_at,
            ),
        )

    return JSONResponse(
        {
            "artifact_id": artifact_id,
            "content_md": content_md,
            "created_at": created_at,
        },
        status_code=200,
    )


__all__ = ["create_artifact"]
