# Architecture

This document describes the production architecture WUCupid used before shutdown.

## Overview

WUCupid was a full-stack web application with three main runtime components:

```text
Frontend service  ->  Backend API service  ->  PostgreSQL database
        |                    |
        |                    +-> SMTP email provider
        |                    +-> Sentry/logging
        |
        +-> Sentry/LogRocket-style client monitoring
```

The frontend handled user-facing pages and routed API calls to the backend. The backend owned authentication, survey submission, cycle state, matching logic, email dispatch, and database writes.

## Components

## 1. Frontend

The frontend was built with Next.js, React, and TypeScript.

Responsibilities:

- landing and onboarding pages
- registration/login UI
- survey flow
- saved progress handling
- match display
- cycle-status display
- API calls through `/api/*`
- client-side monitoring instrumentation

The frontend used a rewrite so browser calls to:

```text
/api/:path*
```

could be forwarded to the backend API base URL from the environment.

## 2. Backend

The backend was a Flask app using an application factory pattern.

Major backend responsibilities:

- user registration
- WUSTL email validation
- password hashing
- email verification
- password reset
- session cookies
- CSRF protection
- survey progress saves
- submitted survey persistence
- matching cycle orchestration
- match generation
- match retrieval
- match notification emails
- health checks
- logging/error monitoring

Main route groups:

```text
/api/auth
/api/survey
/api/matches
/api/cycle
```

## 3. Database

The database was PostgreSQL.

Core tables:

```text
users
survey_responses
matches
matching_cycles
matching_attempts
match_email_sends
```

### users

Stored account and matching-profile fields:

- email
- password hash
- name
- Instagram handle
- gender
- academic year
- religion
- political view
- sexual orientation
- preferred years/religions/politics
- verification and password reset metadata
- account creation timestamp

### survey_responses

Stored both incomplete progress and submitted surveys.

Important fields:

- user id
- response JSON
- submitted flag
- submitted timestamp
- matching cycle id
- latest-progress flag

The app enforced one submitted survey per user per cycle and one latest progress record per user per cycle.

### matches

Stored generated matches.

Important fields:

- user1 email
- user2 email
- score
- description
- cycle id
- creation timestamp

A unique constraint prevented duplicate match pairs within the same cycle.

### matching_cycles

Stored cycle timing/state.

Important fields:

- cycle number
- survey start
- survey end
- processing end
- matches-viewable end
- active flag
- emails-sent flag
- production-cycle flag

### matching_attempts

Stored match-generation attempts and whether they succeeded.

Useful for debugging/research:

- started time
- finished time
- success flag
- error text

### match_email_sends

Tracked match-notification email sends.

Useful for operational analysis:

- cycle id
- recipient
- status
- attempt count
- sent timestamp
- error text

## Cycle state machine

WUCupid used recurring matching cycles.

```text
survey_open -> processing -> matches_available -> expired -> next survey_open
```

### survey_open

Users could register, log in, complete the survey, and submit their answers.

### processing

The backend generated matches from submitted survey responses.

### matches_available

Users could view their matches for the current cycle. Match-available notification emails could be sent.

### expired

The cycle ended and the system created the next cycle.

## Automation

The backend used APScheduler to run a cycle tick roughly once per minute.

The tick handled:

- checking the active cycle
- computing the current phase
- generating matches during the processing phase
- recovering from failed/stalled matching attempts
- sending match-available emails once per cycle
- creating the next cycle after expiration

PostgreSQL advisory locks were used to reduce duplicate cycle work when multiple backend workers/instances could run the same scheduled job.

## External services

### Render

Hosted:

- frontend web service
- backend web service
- PostgreSQL database

### Cloudflare

Handled:

- DNS
- domain-level security settings
- email authentication DNS records

### GoDaddy

Domain registrar for the project domain.

### SendPulse SMTP

Handled transactional emails:

- account verification
- password resets
- match notifications

### Sentry

Captured frontend/backend errors and performance data.

### LogRocket

Used for frontend session/error inspection during production debugging.

### Looker Studio

Used for aggregate analytics dashboards.

## Production shutdown implications

Because the scheduler ran inside the backend process, suspending/deleting the backend service stopped:

- cycle advancement
- automatic match generation
- recovery attempts
- match notification email sends
- new account/survey API writes

Deleting the database was intentionally the final infrastructure step, after raw dumps, anonymized exports, aggregate reports, and restore testing were completed.
