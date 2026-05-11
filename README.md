
## WUCUPID

WUCUPID was a student-built matchmaking platform for Washington University in St. Louis students. It let students register with a WUSTL email, complete a personality/preference survey during an open cycle, get matched with other users, and view mutual matches once the matching window opened.

The live service has been shut down. This repository is preserved as a public technical archive and portfolio project.

## Project status

**Status:** archived / no longer live  
**Original deployment:** Render + PostgreSQL + Cloudflare + SendPulse SMTP  
**Audience:** WashU students  
**Scale:** 900+ registered users during the production run

No production secrets, raw database dumps, private analytics exports, or identifiable user data are included in this public repository.

## What this project demonstrates

- Full-stack product development with a production frontend, backend, database, authentication flow, and email system.
- A cycle-based matching workflow: survey collection, processing, match release, expiration, and next-cycle creation.
- A vectorized matching algorithm using hard compatibility constraints, weighted soft preferences, cosine similarity, and mutual top-k selection.
- Production operations work: Render hosting, PostgreSQL, Cloudflare DNS/security, SMTP email delivery, Sentry/LogRocket-style monitoring, and analytics dashboards.
- Privacy-conscious archival after shutdown: raw data retained privately, public code released without production user data.

## Core features

- WUSTL email registration and verification.
- Session-based authentication with CSRF protection.
- Survey progress saving and final submission.
- Matching cycles with automatic phase transitions.
- Vector-based compatibility scoring.
- Mutual top-k match selection.
- Match availability windows.
- Match notification emails.
- Operational logging and error monitoring.
- Aggregate analytics through external dashboards.

## Tech stack

### Frontend

- Next.js
- React
- TypeScript
- Sentry client/server instrumentation
- LogRocket dependency during production monitoring

### Backend

- Flask
- SQLAlchemy
- Flask-Migrate / Alembic
- Flask-Mail
- Flask-CORS
- APScheduler
- PyJWT
- NumPy
- Sentry Flask integration

### Database

- PostgreSQL
- pgAdmin / Render database tooling
- SQLAlchemy ORM models and migrations

### Infrastructure

- Render web services and managed Postgres
- Cloudflare DNS/security
- GoDaddy domain registration
- SendPulse SMTP
- Google Looker Studio analytics

## High-level architecture

```text
User Browser
    |
    v
Next.js Frontend
    |
    | /api/* rewrite
    v
Flask Backend API
    |
    +--> PostgreSQL
    +--> SendPulse SMTP
    +--> Sentry / logs
    +--> APScheduler cycle tick
```

See [`ARCHITECTURE.md`](./ARCHITECTURE.md) for the detailed system design.

## Matching algorithm

The matching system separates **hard constraints** from **soft preferences**.

Hard constraints determine whether two users are eligible to match at all. Soft preferences affect the score but do not override compatibility.

The final selection uses mutual top-k matching, which means a pair is created only when both users rank each other within their top candidate set.

See [`MATCHING_ALGORITHM.md`](./MATCHING_ALGORITHM.md) for details.

## Deployment

The production service is no longer running. The original production deployment used Render for the frontend, backend, and PostgreSQL database.

See [`DEPLOYMENT.md`](./DEPLOYMENT.md) for historical deployment details and local setup notes.

## Privacy

This public archive intentionally excludes:

- raw production database dumps
- user emails
- names
- Instagram handles
- password hashes
- verification/reset tokens
- private survey exports
- SMTP/API credentials
- Render/Cloudflare/Sentry/OpenAI secrets

See [`PRIVACY_AND_SECURITY.md`](./PRIVACY_AND_SECURITY.md).

## Shutdown note

WUCupid was shut down after its production run to stop recurring infrastructure costs and preserve the project as an engineering/research artifact.

See [`SHUTDOWN_NOTE.md`](./SHUTDOWN_NOTE.md).

## Local setup

This project is preserved primarily as an archive. Local setup may require small edits depending on current package versions and environment.

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create a local `.env` file based on `.env.example` or the variables described in `DEPLOYMENT.md`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## License

Add a license before treating this as an open-source project. For a portfolio archive, keeping all rights reserved is also reasonable.
