# Shutdown Note

WUCupid is no longer live.

The project completed its production run as a student-built matchmaking platform for Washington University in St. Louis students. After the production period, the service was shut down to stop recurring infrastructure costs and preserve the project as a technical archive.

## What was shut down

The production shutdown included:

- frontend hosting
- backend hosting
- managed PostgreSQL database
- transactional SMTP sending
- public app DNS records
- monitoring projects where no longer needed
- live analytics/database connections

The domain may remain registered until its natural expiration, but the live application is not intended to remain available.

## What was preserved

Private archive:

- raw database dump
- plain SQL export
- schema export
- table counts
- restore-test notes

Research/archive exports:

- anonymized CSVs
- aggregate funnel reports
- aggregate matching reports
- redacted analytics screenshots/PDFs

Public archive:

- source code
- architecture documentation
- matching algorithm notes
- deployment notes
- privacy/security notes
- redacted screenshots

## What is not included publicly

This public repository does not include:

- production database dumps
- raw user data
- emails
- names
- Instagram handles
- password hashes
- verification/reset tokens
- private analytics exports
- SMTP/API credentials
- Render/Cloudflare/Sentry/OpenAI secrets

## Why preserve the repo

WUCupid is preserved because it demonstrates:

- full-stack product development
- production deployment
- database-backed application design
- authentication and email flows
- scheduled background orchestration
- vectorized matching
- privacy-conscious shutdown and archival

## Final status

The repository is now a portfolio/technical archive, not an actively maintained production service.
