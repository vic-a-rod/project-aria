# Privacy and data isolation

The public repository contains application source code only. It must never be used
as a backup or synchronization location for a user's Aria data.

## Local-only data

The following belong to each installation and must remain untracked:

- SQLite databases and database journals
- `.env` files and machine-specific configuration
- Tasks, notes, schedules, job applications, contacts, and preferences
- Calendar and email content
- API keys, access tokens, refresh tokens, passwords, and session data
- Logs, exports, backups, screenshots, and diagnostic bundles containing user data

The repository's `.gitignore` blocks the current local database and configuration
formats. New features that introduce another data format must add its runtime files
to `.gitignore` in the same change.

## Safe public material

Tests, documentation, demonstrations, and screenshots may contain fictional data
that cannot be mistaken for or traced back to a real person. `.env.example` may list
variable names and safe placeholder values but never working credentials.

## External integrations

Future email and calendar integrations must use minimum necessary permissions, begin
read-only, and keep credentials outside the repository. Aria must not send messages
or modify an external calendar without explicit authorization and confirmation.

## Before publishing

Contributors should inspect staged files and commit metadata for personal data and
secrets. If sensitive information enters Git history, remove it from history and
rotate any exposed credential before publishing or sharing the repository.

