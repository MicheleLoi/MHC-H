# Part of mhc-cowork. AGPL v3 — see LICENSE-AGPL
"""
server.py — mhc-cowork HTTP REST API entry point.

Replaces the MCP-protocol transport layer of the original MHC-L mcp_server
package with pure HTTP REST over Starlette. Business logic (template
rendering, audit signature, SQLite schema) is shared with MHC-L.

Signup + Stripe webhook are NOT mounted on this server. Bearer keys are
issued by the MHC-L production signup flow at https://mhc.micheleloi.pro/
(POST /signup/create-checkout-session + /webhooks/stripe), and the same
key authenticates both MHC-L MCP tool calls and the mhc-cowork REST API
below. The shared DB is /root/.mhc-l-keystore.db on the VPS (set via env
MHC_API_DB_PATH). signup_handler.py + webhook_handler.py remain in source
for future paid-tier activation but are not wired into routes.

Routes (Bearer-auth-protected via BearerAuthMiddleware):

  /api/sessions                 [POST]       Open a session.
  /api/sessions/{sid}           [GET]        Read a session (ownership-scoped).
  /api/sessions/{sid}/end       [POST]       Finalize a session.
  /api/artifacts                [POST]       Render + persist an artifact.
                                              Requires MHC-Audit-Sig.
  /api/decisions                [POST]       Append a decision entry.
                                              Requires MHC-Audit-Sig.
  /api/decisions                [GET]        List caller's decisions
                                              (optional ?since=, ?sid=).

Run:
  python -m backend.server                   # uvicorn on 0.0.0.0:8080
  python -m backend.server --port 9000       # custom port

Env vars (see README.md for details):
  MHC_API_DB_PATH                  SQLite path (default ~/.mhc-cowork-keystore.db
                                                 — on VPS set to MHC-L canonical
                                                 /root/.mhc-l-keystore.db for
                                                 shared-key access)
"""

from __future__ import annotations

import argparse
import sys

from starlette.applications import Starlette
from starlette.routing import Route

from .auth import BearerAuthMiddleware
from .db import init_db
from .endpoints.artifacts import create_artifact
from .endpoints.decisions import create_decision, list_decisions
from .endpoints.sessions import create_session, end_session, get_session


# ---------------------------------------------------------------------------
# Starlette app factory
# ---------------------------------------------------------------------------

def build_app() -> Starlette:
    """Build the Starlette ASGI app with Bearer middleware wired in."""
    # init_db is also called lazily by every handler, but doing it once at
    # startup makes the schema's existence visible in logs and surfaces any
    # path/permissions misconfiguration immediately. Creates mhc-cowork
    # governance tables (lawyer_sessions, decisions, artifacts) alongside
    # the existing MHC-L tables (applications, api_keys, stripe_events_processed)
    # via CREATE TABLE IF NOT EXISTS — no collision on shared DB.
    db_path = init_db()
    print(f"[server] SQLite DB initialized at {db_path}", file=sys.stderr)

    routes = [
        # REST endpoints (Bearer-auth-protected).
        Route("/api/sessions", create_session, methods=["POST"]),
        Route("/api/sessions/{sid}", get_session, methods=["GET"]),
        Route("/api/sessions/{sid}/end", end_session, methods=["POST"]),
        Route("/api/artifacts", create_artifact, methods=["POST"]),
        Route("/api/decisions", create_decision, methods=["POST"]),
        Route("/api/decisions", list_decisions, methods=["GET"]),
    ]

    starlette_app = Starlette(routes=routes)

    # Wrap with Bearer middleware. Outermost callable receives the request
    # first, so auth runs before Starlette routing. No path-skips needed on
    # this server — signup + webhook live on the MHC-L production endpoint.
    asgi_app = BearerAuthMiddleware(starlette_app, skip_path_prefixes=())
    return asgi_app


# Module-level app object for `uvicorn backend.server:app`.
app = build_app()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="mhc-cowork HTTP REST API")
    parser.add_argument("--host", default="0.0.0.0", help="bind address (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8080, help="port (default: 8080)")
    parser.add_argument(
        "--log-level",
        default="info",
        choices=("critical", "error", "warning", "info", "debug", "trace"),
    )
    return parser.parse_args()


def main() -> None:
    import uvicorn  # type: ignore

    args = parse_args()
    print(
        f"[server] mhc-cowork listening on http://{args.host}:{args.port} "
        f"(Bearer auth enabled, all routes protected — signup via MHC-L)",
        file=sys.stderr,
    )
    uvicorn.run(
        "backend.server:app",
        host=args.host,
        port=args.port,
        log_level=args.log_level,
    )


if __name__ == "__main__":
    main()
