# Development backlog

Tickets are ordered to reduce cross-agent conflicts. Agents should take the highest
unblocked ticket in their workstream unless the maintainer changes priority.

## Foundation

### ARIA-101 — Modularize the frontend

Owner: Frontend features

Extract the monolithic `App.tsx` into page shell, task feature, reusable component,
and API client boundaries without changing behavior.

Acceptance: build and lint pass; existing appearance and workflows remain unchanged;
future task UI work no longer requires every agent to edit `App.tsx`.

### ARIA-102 — Remove runtime third-party font requests

Owner: Design and accessibility

Replace the Google Fonts CSS import with a system stack or checked-in licensed
assets.

Acceptance: the dashboard renders fully when networking is limited to the localhost
API; no font request is sent to a third party.

### ARIA-103 — Establish reproducible dependencies and CI

Owner: Quality, security, and privacy

Replace `latest` dependency declarations with compatible pinned ranges and add CI for
backend tests/lint, frontend build/lint/tests, a production audit, and secret checks.

Acceptance: a clean lockfile install produces repeatable checks and GitHub CI passes.

### ARIA-104 — Add migrations and an application factory

Owner: Data and migrations with API/application coordination

Add Alembic, replace startup `create_all` as the schema evolution mechanism, inject
settings/session factory, and provide isolated temporary databases and a fixed clock
for tests.

Acceptance: migration from an empty database passes; tests do not share a database or
system clock; application startup remains simple on Windows.

### ARIA-105 — Define normalized task storage

Owner: Data and migrations

Normalize categories and tags, add a completed timestamp, preserve UTC audit fields,
and document the migration from comma-separated tags.

Acceptance: custom categories and tags filter reliably; migration tests preserve
existing task data; lifecycle timestamps are correct.

## Complete the v0.1 task experience

### ARIA-106 — Complete and harden the task API

Owner: API and application services

Add get-one, pagination, stable sorting, due/status/category/tag filters, clearable
nullable fields, date validation, and a stable error envelope.

Acceptance: contract tests cover success, validation, not-found, filtering, and
pagination; equal priorities use stable tie-breaking.

### ARIA-107 — Make priority configuration deterministic

Owner: Domain engines

Represent priority weights as a value object/configuration; inject `today`; return
structured reason codes and display text; add boundary and property-oriented tests.

Acceptance: completed tasks score zero, score components reconcile with explanations,
and tests never depend on the wall clock.

### ARIA-108 — Add frontend test infrastructure

Owner: Quality, security, and privacy

Add Vitest, React Testing Library, user-event, axe checks, and one Playwright task
lifecycle smoke test.

Acceptance: automated tests cover empty/loading/error states plus create, complete,
edit, and delete workflows; no serious axe violations.

### ARIA-109 — Complete task CRUD in the UI

Owner: Frontend features

Support every v0.1 task field, editing, confirmed deletion, pending/success/error
feedback, and persistence across restart.

Acceptance: the full lifecycle is keyboard operable and verified against the API.

### ARIA-110 — Add search, filters, sorting, and custom categories

Owner: Frontend features

Use backend query parameters for title/description/tag search, category/status
filters, priority/due sorting, completed organization, and generic custom categories.

Acceptance: results are predictable, keyboard usable, and contain no personal
defaults or seeded records.

### ARIA-111 — Add local-first onboarding and accessibility baseline

Owner: Design and accessibility

Explain empty-by-default local storage and add visible focus, live error regions,
semantic labels, contrast, responsive behavior, and reduced-motion support.

Acceptance: onboarding is dismissible, CRUD is keyboard usable, and automated plus
manual accessibility checks pass the documented baseline.

### ARIA-112 — Add dashboard summary contracts

Owner: API/application services and Frontend features through a documented contract

Provide overdue, upcoming, open-minutes, and top-priority summaries through an
application service and keep UI metrics/order consistent after mutations.

Acceptance: dashboard values always match persisted state and summary contract tests
cover empty, overdue, due-soon, completed, and tied-priority cases.

