# Deployment

This document records how WUCupid was deployed during its production run and how to run it locally for archival/testing purposes.

The live deployment has been shut down.

## Historical production infrastructure

## Hosting

WUCupid was hosted on Render using separate services for:

- frontend web service
- backend web service
- PostgreSQL database

## Domain/DNS

The project domain was registered through GoDaddy and configured through Cloudflare DNS.

Typical records during production:

```text
wucupid.com      -> frontend
www.wucupid.com  -> frontend
api.wucupid.com  -> backend
```

## Email

Transactional email was sent through SendPulse SMTP.

Email types:

- verification email
- password reset email
- match-available notification email

## Monitoring

Production monitoring included:

- Sentry for frontend/backend errors
- LogRocket-style frontend session/error inspection
- Render logs
- Google Looker Studio aggregate analytics

## Backend environment variables

The backend used environment variables rather than hardcoded production secrets.

Representative variables:

```bash
DATABASE_URL=
SECRET_KEY=

MAIL_SERVER=
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=
MAIL_PASSWORD=
MAIL_DEFAULT_SENDER=noreply@wucupid.com

FRONTEND_URL=http://localhost:3000
FLASK_DEBUG=false

SENTRY_DSN=
OPENAI_API_KEY=
ADMIN_SECRET=

FIRST_CYCLE_START=
DISABLE_OUTBOUND_EMAILS=false
DISABLE_MATCH_EMAILS=false
ENABLE_FILLER_MATCHES=false
```

Do not commit real values.

## Frontend environment variables

Representative variables:

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:5000
NEXT_PUBLIC_SENTRY_DSN=
```

For the public archive, production `.env` files should not be committed.

## Local development

## 1. Clone the repository

```bash
git clone https://github.com/<your-username>/<repo-name>.git
cd <repo-name>
```

## 2. Start PostgreSQL

Use local PostgreSQL or Docker.

Example Docker Postgres:

```bash
docker run --name wucupid_postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=wucupid \
  -p 5432:5432 \
  -d postgres:16
```

Local connection string:

```bash
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/wucupid
```

## 3. Backend setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create `backend/.env`:

```bash
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/wucupid
SECRET_KEY=dev-secret-key-change-me
FRONTEND_URL=http://localhost:3000
FLASK_DEBUG=true

MAIL_SERVER=smtp.example.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=
MAIL_PASSWORD=
MAIL_DEFAULT_SENDER=noreply@example.com

DISABLE_OUTBOUND_EMAILS=true
DISABLE_MATCH_EMAILS=true
SKIP_EMAIL_SEND=true
```

Run migrations if available:

```bash
flask db upgrade
```

Then start the backend according to the app's entrypoint. Depending on the current repo state, this may be one of:

```bash
flask run
```

or:

```bash
gunicorn "app:create_app()"
```

## 4. Frontend setup

```bash
cd frontend
npm install
```

Create `frontend/.env.local`:

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:5000
```

Start frontend:

```bash
npm run dev
```

## Production shutdown notes

The shutdown sequence used for the historical production deployment was:

1. Suspend frontend/backend services.
2. Keep database running.
3. Export full raw database dump.
4. Export anonymized CSVs.
5. Export aggregate reports.
6. Restore-test the database dump.
7. Remove Render custom domains.
8. Remove Cloudflare records pointing to Render.
9. Delete frontend/backend Render services.
10. Delete Render PostgreSQL database.
11. Disable GoDaddy auto-renew.
12. Revoke SMTP/API credentials.
13. Preserve the project as a public code archive without user data.

## Public archive policy

The public repository should not include:

- `.env`
- `.env.production`
- database dumps
- anonymized row-level research exports unless intentionally reviewed
- raw CSVs
- private logs
- Sentry/LogRocket exports
- user screenshots
- generated build directories such as `.next/`
- `node_modules`
- Python virtual environments
