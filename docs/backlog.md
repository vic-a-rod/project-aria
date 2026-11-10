# Version 1 development backlog

Version 1 is the complete local, typed Aria. Ticket groups are dependency ordered;
quality work runs alongside every group.

## Group F — Engineering foundation

### V1-F01 — Reproducible dependencies and CI

Status: complete

Owner: Quality, security, and privacy

Pin compatible dependency ranges and add CI for backend tests/lint, frontend
build/lint/tests, production dependency audit, and secret/privacy checks.

### V1-F02 — Application factory and injected configuration

Status: complete

Owner: API/application services

Inject settings, clock, time zone, database/session factory, language provider,
credential vault, and integration adapters. Keep `main.py` composition-only and bind
locally by default.

### V1-F03 — Migrations and portable persistence

Status: complete

Owner: Data and migrations

Add Alembic, test upgrades from an empty database, introduce portable identifiers,
and replace startup `create_all` as the schema-evolution mechanism.

### V1-F04 — Stable layer and command contracts

Status: complete

Owner: Product/architecture with domain and API coordination

Establish `domain`, `application`, `infrastructure`, and `api` boundaries plus a
versioned command/result envelope suitable for text, later voice, remote clients, and
household devices.

Foundation acceptance: a clean Windows installation starts empty, works without an
external service or model, uses isolated deterministic tests, and passes CI without
personal data in fixtures or logs.

## Group D — Complete information model

### V1-D01 — Tasks, projects, categories, and tags

Status: complete

Normalize task storage, custom categories and tags, recurrence, audit timestamps,
completion state, search, filtering, and stable sorting.

### V1-D02 — Events and commitments

Add time-zone-aware events, all-day events, recurrence, fixed/flexible behavior,
appointments, source provenance, and calendar placement.

### V1-D03 — Internship and job applications

Add companies, roles, statuses, postings, recruiter contacts, interviews, follow-ups,
notes, deadlines, and unified calendar/workload representation.

### V1-D04 — Preferences and workload overrides

Add explicit preferences, protected time, quiet hours, temporary focus/lighter modes,
expiration, and approval-required suggested preferences.

### V1-D05 — External-source and synchronization ledger

Store provider-neutral references, connection IDs, external IDs, sync cursors,
hashes, timestamps, tombstones, provenance, and deduplication state.

### V1-D06 — Proposals, confirmations, notifications, and audit

Persist proposed actions, evidence, state-bound expiring confirmation records,
execution results, notification rules, and audit events.

Data acceptance: all responsibility types persist locally, remain attributable to a
source, survive restart, and are scoped to a local profile that can migrate to
Version 3.

## Group E — Deterministic intelligence

### V1-E01 — Explainable priority engine

Calculate priorities for tasks, events, deadlines, applications, and follow-ups using
configurable weights, explicit time, structured score components, and reason codes.

### V1-E02 — Availability and conflict engine

Calculate free intervals using fixed commitments, flexible work, protected time,
rest, time zones, and recurrence. Detect conflicts deterministically.

### V1-E03 — Scheduling and simulation engine

Produce alternative schedules, risk reports, and structured diffs without mutating
persisted state or moving fixed/external commitments.

### V1-E04 — Sustainable workload engine

Support temporary lighter/focused modes, deadline preservation, overload warnings,
protected family/rest periods, and legitimate unscheduled time.

### V1-E05 — Proactive recommendation rules

Generate configurable, deduplicated local recommendations for deadlines, overdue
work, conflicts, interviews, follow-ups, available time, and quiet hours.

Engine acceptance: explanations reconcile exactly with calculations; proposals never
overlap fixed commitments; simulations never persist implicitly; all tests use an
explicit clock and time zone.

## Group C — Typed command system

### V1-C01 — Versioned intents, commands, and results

Define typed reads, proposed mutations, clarification requests, evidence references,
confirmation requirements, display summaries, and concise speakable responses.

### V1-C02 — Command dispatcher and authorization policy

Route validated commands to application use cases. Permit safe reads; require
proposals for consequential mutations; enforce actor/profile boundaries.

### V1-C03 — Replaceable language-model adapter

Support cloud and future local language providers through a bounded adapter. Models
never receive database access, provider credentials, or authority to execute.

### V1-C04 — Typed natural-language interpretation

Interpret task/event/application commands, priority and calendar questions, schedule
simulations, workload changes, and email/calendar queries into typed commands.

### V1-C05 — Evidence, preview, clarification, and confirmation

Show sources, reasoning, proposed changes, ambiguity, risks, and expiring confirmation
tokens before execution.

Command acceptance: ambiguous or invalid language cannot mutate data; deterministic
services perform calculations; Version 2 can submit speech transcripts through the
same contract unchanged.

## Group I — Email and calendar integrations

### V1-I01 — Provider ports and protected credentials

Add provider-neutral email/calendar interfaces and an OS credential-vault adapter.
Credentials never enter Git, logs, ordinary exports, or model prompts.

### V1-I02 — Google read integration

Implement minimum-scope OAuth plus Google Calendar and Gmail read adapters.

### V1-I03 — Microsoft read integration

Implement minimum-scope OAuth plus Outlook Calendar and Outlook Mail read adapters.

### V1-I04 — Incremental safe synchronization

Add cursors, pagination, retries/backoff, idempotency, deduplication, sync status,
disconnect, and revocation.

### V1-I05 — Email and event extraction proposals

Identify potential deadlines, interviews, recruiter messages, appointments, and tasks
as evidence-backed proposals. Never let message content issue commands or silently
create records.

### V1-I06 — Confirmed external-write boundary

Keep sending or calendar mutation behind separately authorized scopes and per-action
confirmation. Read-only integration is the mandatory first release path.

Integration acceptance: Aria remains useful offline; imported data shows provenance;
repeated sync is safe; disconnecting providers does not break local data; no external
write occurs silently.

## Group U — Local user experience

### V1-U01 — Modular frontend and local-only assets

Status: complete

Split the monolithic screen into stable feature boundaries and remove runtime
third-party font requests.

### V1-U02 — Complete responsibility CRUD

Build complete task, project, event, application, preference, and commitment
workflows with pending/success/error feedback and keyboard operation.

### V1-U03 — Calendar and workload views

Add daily, weekly, monthly, custom-range, free-time, conflict, and workload views that
consume deterministic backend results.

### V1-U04 — Search, organization, and provenance

Add search, filters, sorting, custom categories, completed organization, external
source indicators, and stable dashboard summaries.

### V1-U05 — Typed assistant workspace

Display conversation, structured results, evidence, explanations, proposals,
clarifications, confirmations, and execution outcomes.

### V1-U06 — Integration and sync settings

Add connection, scopes, sync status, disconnect/revoke, provider selection, privacy,
and retention controls.

### V1-U07 — Local-first onboarding, accessibility, and Windows packaging

Explain data location and empty-by-default behavior; meet the documented accessibility
baseline; provide startup, export/backup/restore, safe reset, and privacy-preserving
diagnostics.

UX acceptance: every Version 1 workflow is available without voice, works through the
keyboard, remains understandable without AI, and clearly distinguishes proposals
from committed changes.

## Group Q — Verification and release readiness

- V1-Q01: pure-engine invariant and property tests
- V1-Q02: repository and migration integration tests
- V1-Q03: API and typed-command contract tests
- V1-Q04: provider adapter tests using fictional fixtures
- V1-Q05: frontend unit, accessibility, and end-to-end tests — in progress; dashboard
  unit/integration foundation complete
- V1-Q06: privacy, secret, dependency, and telemetry audit
- V1-Q07: offline, expired-token, rate-limit, AI-unavailable, partial-sync, corrupted-
  proposal, and restart-recovery tests
- V1-Q08: complete acceptance scenario

The Version 1 release gate is:

1. Start with an empty local installation.
2. Connect a fictional or sandbox email/calendar provider.
3. Import tasks and events with provenance.
4. Type a planning request.
5. Receive an evidence-backed, explained schedule proposal.
6. Approve selected local changes.
7. Restart Aria and verify the plan persists.

## Parallel execution order

After V1-F02 and V1-F04 contracts are agreed:

- Data lane: V1-F03 and V1-D01 through D06
- Engine lane: V1-E01 and E02 in parallel, then E03 through E05
- Command/API lane: V1-C01 through C05
- Frontend lane: V1-U01, then U02/U04 while other contracts mature
- Integration lane: V1-I01, then Google and Microsoft read adapters in parallel
- Quality lane: V1-F01 and Group Q continuously

