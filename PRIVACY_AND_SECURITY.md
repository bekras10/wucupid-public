# Privacy and Security

WUCupid handled sensitive user information. This public repository is intentionally scrubbed and does not contain production data.

## Sensitive data categories

During production, the system processed or stored:

- WUSTL email addresses
- names
- Instagram handles
- password hashes
- email verification tokens
- password reset tokens
- gender
- sexual orientation / dating interest
- academic year
- religion
- political views
- partner preferences
- survey answers
- match scores and pairings
- email-delivery metadata
- operational logs

Some of these categories are sensitive even when not traditionally considered private because they can reveal identity, preferences, beliefs, or relationship-related information.

## Public repository policy

The public repository must not contain:

- raw production database dumps
- real user emails
- real names
- real Instagram handles
- password hashes
- verification tokens
- password reset tokens
- SMTP credentials
- Render database URLs
- OpenAI keys
- Sentry auth tokens
- Cloudflare API tokens
- SendPulse SMTP passwords
- private analytics exports
- production `.env` files
- generated build artifacts containing hidden keys or metadata

## Data archival policy

Private archives may exist separately from this public repository.

Recommended separation:

```text
private archive:
  raw database dump
  encrypted SQL dump
  restore-test notes
  table counts
  private operational screenshots

research archive:
  anonymized CSVs
  aggregate reports
  redacted dashboards

public repo:
  code
  documentation
  architecture notes
  screenshots without user data
```

Raw data should be encrypted and stored outside GitHub.

## Anonymized exports

Anonymized row-level exports should replace user identifiers with generated IDs such as:

```text
u_00001
u_00002
u_00003
```

Fields that should not appear in anonymized public data:

- email
- name
- Instagram handle
- password hash
- verification token
- reset token
- exact free-text identifiers

Even anonymized data can be risky when the population is small. For public writing, aggregate statistics are safer than row-level exports.

## Aggregate reporting

Aggregate reports are safer when they avoid small-cell disclosure.

Recommended rule:

```text
Do not publish demographic buckets with fewer than 5 users.
```

Examples of safer aggregate metrics:

- total registered users
- verified users
- survey submissions by cycle
- total matches by cycle
- average match score by cycle
- score distribution percentiles
- broad funnel conversion rates

## Authentication and session security

The backend included:

- password hashing
- email verification
- password reset tokens
- session cookies
- CSRF protection
- CORS restrictions
- security headers

Production secrets were loaded from environment variables rather than hardcoded values.

## Email safety

The app supported email kill switches for match notification emails:

```bash
DISABLE_OUTBOUND_EMAILS=true
DISABLE_MATCH_EMAILS=true
```

During shutdown, SMTP credentials should be revoked and DNS email authorization should be removed or locked down.

A safe no-sending SPF policy is:

```text
v=spf1 -all
```

A strict DMARC policy is:

```text
v=DMARC1; p=reject; adkim=s; aspf=s
```

## Monitoring tools

Sentry and LogRocket-style tools can capture URLs, error payloads, browser metadata, and potentially user identifiers.

Before public release or account deletion:

- export only aggregate/redacted summaries
- delete or disable project DSNs
- remove hardcoded DSNs from public code
- avoid publishing raw session replays or logs

## Secret scanning

Before making the public repository visible, run a secret scanner.

Example:

```bash
gitleaks detect \
  --source . \
  --report-format json \
  --report-path ../wucupid_gitleaks_report.json
```

If leaks are found in old git history, the safest public-release approach is a fresh repository with clean history.

## Recommended public-release strategy

1. Clone/copy the repository.
2. Remove `.git`.
3. Remove private files and generated artifacts.
4. Add a strong `.gitignore`.
5. Initialize a fresh public repo.
6. Run a secret scanner.
7. Publish only after the scan is clean.

This avoids exposing old commits containing build artifacts, secrets, or private data.
