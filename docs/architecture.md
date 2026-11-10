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

## Phase 1 domain

A task contains a title, description, category, tags, dates, estimated minutes, importance, completion status, scheduling flexibility, recurrence notes, and audit timestamps. Categories remain strings for the first slice so custom categories work immediately; a normalized category model can be introduced when category-specific settings are implemented.

## Application composition

`app.main` is the production composition root and constructs the API through
`create_app`. The factory accepts explicit settings, database engine, session
factory, and clock dependencies. Production uses local defaults; tests create
isolated application instances with temporary SQLite databases and fixed clocks.

Routes are assembled separately from application construction. This prevents import-
time database state and establishes the injection boundary that Version 1 provider
adapters, the typed-command system, and future hosted deployment will use.

Schema creation still uses SQLAlchemy metadata during startup. V1-F03 will replace
that temporary bootstrap behavior with Alembic migrations and portable UTC timestamp
persistence.

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

