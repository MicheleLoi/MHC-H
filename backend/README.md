# MHC-H backend HTTP REST API

Part of MHC-H. AGPL v3 — see `../LICENSE-AGPL`.

Pure Starlette HTTP REST API. Powers the MHC-H MVP:
session lifecycle, append-only decisions log, provenance-tracked
artifacts.

## Setup

```bash
# Create + activate venv (Python 3.11+ recommended)
python -m venv .venv
source .venv/bin/activate           # Linux/macOS
.venv\Scripts\activate              # Windows

pip install -r backend/requirements.txt
```

## Environment variables

| Var | Purpose | Default |
|---|---|---|
| `MHC_API_DB_PATH` | SQLite keystore + governance store | `~/.mhc-h-keystore.db` |
| `RESEND_API_KEY` | Send free-tier welcome emails (and paid-tier emails) | required for email |
| `MHC_API_BASE_URL` | Public base URL used to build welcome links sent in emails | `https://api.mhc.regia.it` |
| `MHC_MARKETPLACE` | Override marketplace coordinate in install URL | `MicheleLoi/MHC-H` |
| `MHC_PLUGIN_NAME` | Override plugin name in install URL | `mhc-h` |
| `MHC_EMAIL_FROM` | Sender label in welcome email | `MHC-H <noreply@mhc.regia.it>` |
| `MHC_EMAIL_SUBJECT` | Subject of welcome email | `La tua chiave MHC-H` |
| `STRIPE_SECRET_KEY` | Paid tier only (post-MVP) | — |
| `STRIPE_WEBHOOK_SECRET` | Paid tier webhook signature | — |
| `MHC_SIGNUP_SUCCESS_URL` | Paid Stripe Checkout success redirect | `https://mhc.regia.it/benvenuto/` |
| `MHC_SIGNUP_CANCEL_URL` | Paid Stripe Checkout cancel redirect | `https://mhc.regia.it/signup/` |

## Run

Two equivalent forms — both work, choose one:

```bash
# Form 1: invoke the package's __main__ block (recommended for local dev)
python -m backend.server --port 8080

# Form 2: invoke uvicorn directly, pointing at the module-level app
uvicorn backend.server:app --host 0.0.0.0 --port 8080
```

The server initializes the SQLite schema on startup (idempotent — safe to
re-run). On first run with default paths, the keystore is created at
`~/.mhc-h-keystore.db`.

## Endpoints

### Public (no Bearer)

| Method | Path | Notes |
|---|---|---|
| `POST` | `/signup/create-checkout-session` | Free-tier issuance OR paid Stripe Checkout |
| `GET`  | `/signup/welcome/<token>` | One-time reveal of `{email, bearer_key, install_url}` |
| `POST` | `/webhooks/stripe` | Stripe webhook delivery (paid tier, post-MVP) |

### Authenticated (Bearer required)

| Method | Path | Audit-Sig | Notes |
|---|---|---|---|
| `POST` | `/api/sessions` | no | Open a session. Body: `{config_json?, project_name?}` |
| `GET`  | `/api/sessions/{sid}` | no | Read a session (ownership-scoped) |
| `POST` | `/api/sessions/{sid}/end` | no | Finalize a session. Body: `{goal?, artifacts_produced?[], exported?}` |
| `POST` | `/api/artifacts` | **yes** | Render + persist artifact (note, trace, pdl, modlog, decision_entry, draft) |
| `POST` | `/api/decisions` | **yes** | Append a decision entry |
| `GET`  | `/api/decisions` | no | List caller's decisions. Query: `since=YYYY-MM-DD`, `sid=` |

### Audit signature

POST endpoints that write to append-only governance tables require an
`MHC-Audit-Sig` header. Compute as:

```python
import hashlib, hmac
sig = hmac.new(
    key=bearer_key.encode("utf-8"),
    msg=(sid + body_json_string).encode("utf-8"),
    digestmod=hashlib.sha256,
).hexdigest()
```

Where:
- `bearer_key` — the same plain bearer used in `Authorization: Bearer ...`
- `sid` — the session ID. For `/api/decisions` where `sid` is omitted from
  the body, use the empty string `""`.
- `body_json_string` — the exact JSON string the client serialized as the
  HTTP body. The server reads the raw body bytes; any whitespace difference
  vs. what the skill computed against will cause a signature mismatch.

Missing or invalid signature → 400 `{"error": "missing or invalid audit signature"}`.

## Issuing a test Bearer

For local smoke tests before the website signup flow is wired up:

```python
# Run inside the venv with backend/ on the path
import os, hashlib, secrets, sqlite3, uuid
from datetime import datetime, timezone

os.environ.setdefault("MHC_API_DB_PATH", str(os.path.expanduser("~/.mhc-h-keystore.db")))

from backend.db import init_db, connect
init_db()

plain = "mhc_live_" + secrets.token_urlsafe(32)
key_hash = hashlib.sha256(plain.encode()).hexdigest()
now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
app_id = str(uuid.uuid4())

with connect() as conn:
    conn.execute("BEGIN")
    conn.execute(
        "INSERT INTO applications (id, email, firm, role, use_case, notes, submitted_at, status, reviewed_at, reviewed_by, rejection_reason, stripe_checkout_session_id)"
        " VALUES (?, 'tester@example.com', '__admin__', NULL, 'local test', NULL, ?, 'approved', ?, 'cli', NULL, NULL)",
        (app_id, now, now)
    )
    conn.execute(
        "INSERT INTO api_keys (key_hash, user_email, application_id, stripe_customer_id, stripe_subscription_id, tier, status, created_at, revoked_at, revoked_reason, last_used_at, request_count)"
        " VALUES (?, 'tester@example.com', ?, 'TEST-CUST', 'TEST-SUB', 'admin', 'active', ?, NULL, NULL, NULL, 0)",
        (key_hash, app_id, now)
    )
    conn.execute("COMMIT")

print("PLAIN BEARER:", plain)
```

## Smoke tests

```bash
# Create a session
curl -X POST http://localhost:8080/api/sessions \
  -H "Authorization: Bearer $TEST_KEY" \
  -H "Content-Type: application/json" \
  -d '{"config_json": "{}"}'

# Append a decision (requires audit sig)
BODY='{"sid":"SID-...","topic":"test","decision":"go"}'
SIG=$(python -c "import hmac, hashlib, os; b=os.environ['BODY']; print(hmac.new(os.environ['KEY'].encode(), ('SID-...'+b).encode(), hashlib.sha256).hexdigest())")
curl -X POST http://localhost:8080/api/decisions \
  -H "Authorization: Bearer $TEST_KEY" \
  -H "MHC-Audit-Sig: $SIG" \
  -d "$BODY"
```
