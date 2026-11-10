# Architecture

Aria starts as a local web application with a clean boundary between presentation, application logic, and persistence.

```text
React dashboard
      |
      | JSON over HTTP
      v
FastAPI routes -> task service -> priority engine
      |                 |
      v                 v
 SQLAlchemy          pure logic
      |
      v
   SQLite
```

## Key decisions

1. **Local-first:** SQLite is the default and no account is required for the MVP.
2. **Explainable priority:** urgency, importance, effort fit, and status are calculated in ordinary Python. The API returns both the score and human-readable reasons.
3. **AI is an adapter:** a future language model may interpret commands, but it will call validated application services rather than write directly to storage.
4. **Portable boundaries:** database configuration and API URLs come from environment variables so deployment can evolve without replacing domain logic.
5. **Safe integrations:** external calendar and email adapters will be isolated and begin read-only.

## Task organization domain

Tasks reference normalized category and optional project records and use a many-to-many
tag association. Names remain the public API representation, so existing clients can
send `category` and `tags` strings while the repository resolves case-insensitive
identities. The default category remains `Personal`; custom categories, projects, and
tags are created locally as tasks use them.

Recurrence is represented as an iCalendar-style rule plus an explicit optional IANA
time zone. Completion is represented by both `is_completed` and an aware UTC
`completed_at` transition timestamp. Creation and update timestamps remain aware UTC
instants.

Task search covers title, description, category, project, and tag names. Category,
project, tag, and completion filters compose. The application service owns explicit
stable sorting and bounded offset/limit pagination so persistence adapters do not
embed presentation policy.

## Application composition

`app.main` is the production composition root and constructs the API through
`create_app`. The factory accepts explicit settings, database engine, session
factory, and clock dependencies. Production uses local defaults; tests create
isolated application instances with temporary SQLite databases and fixed clocks.

Routes are assembled separately from application construction. This prevents import-
time database state and establishes the injection boundary that Version 1 provider
adapters, the typed-command system, and future hosted deployment will use.

Application startup upgrades the injected database engine to the packaged Alembic
head revision. A clean installation builds its schema from migrations; a database
created by the pre-Alembic foundation is stamped only after its task columns exactly
match the known legacy schema. Unknown schemas fail closed instead of being silently
adopted.

Timestamp columns use the infrastructure `UtcDateTime` adapter. It requires aware
inputs, stores a portable normalized UTC value, and restores an aware UTC instant
when SQLite or another driver returns a timezone-naive value. API timestamps remain
RFC 3339-compatible while application and domain layers stay independent of the
database representation.

Revision `20261109_0002` migrates legacy string categories and comma-separated tags
into normalized records without changing task IDs. Case variants are deduplicated,
legacy recurrence text becomes the recurrence rule, and already-completed tasks use
their last update time as the initial completion timestamp.

## Layer boundaries

The backend is a modular monolith with four explicit layers:

```text
api -> application -> domain
             ^          ^
             |          |
       infrastructure --+
```

- `domain` contains framework-free task models and deterministic engines.
- `application` contains use cases, repository/clock ports, typed command contracts,
  and transport-neutral dispatch.
- `infrastructure` contains SQLAlchemy rows and repositories, database/session
  construction, system time, and future provider adapters.
- `api` maps HTTP schemas and errors to application services without owning business
  rules.

Boundary tests reject FastAPI, SQLAlchemy, model-provider, and audio imports from the
domain and application layers.

## Permanent command contract

Every future text, voice, web, mobile, or household-device request enters Aria through
a versioned `CommandEnvelope`. It carries actor/profile identity, source channel,
correlation and idempotency identifiers, locale, time zone, typed arguments, and an
optional confirmation token.

`CommandResult` returns structured data plus warnings, evidence, action proposals,
confirmation requirements, a display summary, and concise speakable text. The
contract is present before an LLM is introduced so language providers can interpret
requests but never gain authority to calculate or mutate directly.

