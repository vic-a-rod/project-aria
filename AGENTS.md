# Project Aria agent guide

This file defines how development agents work in this repository. Read it together
with `README.md`, `docs/architecture.md`, `docs/privacy.md`, and
`docs/roadmap.md` before making changes.

## Product identity

Aria is all of the following:

1. A useful local-first tool for personal responsibilities, education, career and
   internship applications, software projects, appointments, and family time.
2. A public, portfolio-quality open-source engineering project that contains no
   maintainer or user data.
3. A progressively intelligent assistant in which AI interprets and recommends,
   deterministic services calculate and mutate, and the user remains in control.

Optimize sustainable productivity, not maximum workload. Rest and unallocated time
are valid scheduling results.

## Non-negotiable guardrails

- Every clean installation starts empty and works without an account or AI model.
- Never commit real tasks, schedules, messages, contacts, applications, databases,
  credentials, tokens, logs, exports, screenshots, or machine-specific paths.
- Use fictional data in tests, examples, screenshots, and documentation.
- Keep priority, availability, conflict, and scheduling calculations deterministic
  and explainable.
- An LLM may produce typed intents; it must not write directly to the database or
  hold provider credentials.
- Consequential changes require a preview or confirmation.
- Schedule simulation returns a proposal and never silently persists changes.
- External integrations begin read-only and request the minimum necessary scope.
- Never send email or modify an external calendar without explicit authorization and
  confirmation.
- Suggested learned preferences require user approval before becoming persistent.
- Aria must not diagnose burnout or infer medical or psychological conditions.

## Agent workstreams

Agents should own one primary workstream per task. Cross-boundary contract changes
must be documented before implementation, and agents should avoid editing the same
files concurrently.

### Product and architecture

Owns roadmap, acceptance criteria, architecture decisions, cross-module contracts,
and scope control. This agent does not implement unrelated feature details.

### Data and migrations

Owns SQLAlchemy entities, repository implementations, Alembic migrations, and
SQLite/portable persistence. It does not own API presentation or frontend code.

### Domain engines

Owns pure priority, availability, conflict, and scheduling logic. Domain modules may
not import FastAPI, SQLAlchemy, an LLM SDK, or an external provider SDK.

### API and application services

Owns typed request/response contracts, use cases, validation, FastAPI routers,
dependency composition, and stable error mapping. It depends on domain logic and
repository interfaces rather than embedding their behavior in routes.

### Frontend features

Owns task workflows, API-facing UI state, dashboard and later calendar screens.
Backend contract changes require coordination with the API workstream.

### Design and accessibility

Owns reusable components, design tokens, responsive behavior, keyboard and focus
behavior, semantics, contrast, reduced motion, and WCAG 2.2 AA quality. It avoids
feature business logic.

### Quality, security, and privacy

Owns test infrastructure, CI gates, migration and contract tests, dependency policy,
secret/privacy checks, and threat-model notes. It may fix a verified defect but does
not redesign product behavior without coordination.

### AI and integrations

This workstream remains inactive until the roadmap reaches the relevant version. It
will own typed intent adapters and provider adapters, never core calculations or
direct persistence.

## Required workflow

1. Select one ticket from `docs/backlog.md` and state its acceptance criteria.
2. Inspect current code and tests before editing.
3. Keep the change within one primary workstream whenever possible.
4. Add or update tests in proportion to the behavior changed.
5. Run the relevant verification commands.
6. Check staged files and commit metadata for personal data and secrets.
7. Use a focused commit message referencing the ticket when practical.
8. Report completed acceptance criteria, checks run, and any follow-up risk.

Do not introduce a future-version capability merely because a dependency or UI makes
it convenient. Version boundaries in `docs/roadmap.md` are product constraints.

## Verification commands

Backend:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\ruff.exe check app tests
```

Frontend:

```powershell
cd frontend
npm run build
npm run lint
```

Before publishing:

```powershell
git diff --check
git status --short
```

Never treat a successful build as sufficient when behavior changed; exercise or test
the affected user workflow.

