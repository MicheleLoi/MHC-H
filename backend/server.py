# Part of mhc-cowork. AGPL v3 — see LICENSE-AGPL
"""
server.py — mhc-cowork HTTP REST API entry point.

Replaces the MCP-protocol transport layer of the original MHC-L mcp_server
package with pure HTTP REST over Starlette. Business logic (template
rendering, audit signature, SQLite schema) is shared with MHC-L.

Routes (in middleware order — paths under skip_path_prefixes bypass auth):

  /webhooks/stripe              [bare ASGI]  Stripe webhook delivery
                                              (signature-verified; not active
                                               in free-tier MVP).
  /signup/create-checkout-session
                                [bare ASGI]  Free-tier issuance + paid
                                              Checkout creation.
  /signup/welcome/<token>       [bare ASGI]  One-time bearer + install URL
                                              reveal.

  --- Bearer-auth-protected ---

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
  MHC_API_DB_PATH                  SQLite path (default ~/.mhc-cowork-keystore.db)
  RESEND_API_KEY                   Free-tier welcome email + paid-tier email
  STRIPE_SECRET_KEY                Paid tier only (post-MVP)
  STRIPE_WEBHOOK_SECRET            Paid tier webhooks (post-MVP)
  MHC_API_BASE_URL                 Public base URL — used to build welcome URLs
  MHC_MARKETPLACE                  Override marketplace coordinate
  MHC_PLUGIN_NAME                  Override plugin name
"""

from __future__ import annotations

import argparse
import sys

from starlette.applications import Starlette
from starlette.routing import Mount, Route

from .auth import BearerAuthMiddleware
from .db import init_db
from .endpoints.artifacts import create_artifact
from .endpoints.decisions import create_decision, list_decisions
from .endpoints.sessions import create_session, end_session, get_session
from .signup_handler import (
    SIGNUP_CHECKOUT_PATH,
    SIGNUP_WELCOME_PREFIX,
    signup_endpoint,
    welcome_endpoint,
)
from .webhook_handler import WEBHOOK_PATH, stripe_webhook_endpoint


# ---------------------------------------------------------------------------
# Starlette app factory
# ---------------------------------------------------------------------------

def build_app() -> Starlette:
    """Build the Starlette ASGI app with Bearer middleware wired in."""
    # init_db is also called lazily by every handler, but doing it once at
    # startup makes the schema's existence visible in logs and surfaces any
    # path/permissions misconfiguration immediately.
    db_path = init_db()
    print(f"[server] SQLite DB initialized at {db_path}", file=sys.stderr)

    routes = [
        # Bare ASGI mounts for paths the middleware skips (Stripe webhook,
        # self-service signup). Mount accepts any ASGI3 app, including our
        # raw handlers.
        Mount(WEBHOOK_PATH, app=stripe_webhook_endpoint),
        Mount(SIGNUP_CHECKOUT_PATH, app=signup_endpoint),
        # Welcome URL is /signup/welcome/<token> — Mount with the prefix and
        # the handler reads the token from scope["path"].
        Mount(SIGNUP_WELCOME_PREFIX.rstrip("/"), app=welcome_endpoint),

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
    # first, so auth runs before Starlette routing. The middleware path-skips
    # /webhooks/stripe and /signup (covers both create-checkout-session and
    # welcome/<token>).
    asgi_app = BearerAuthMiddleware(starlette_app)
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
        f"(Bearer auth enabled, skip_paths=/webhooks/stripe + /signup)",
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
