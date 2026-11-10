# Architecture

Jarvis starts as a local web application with a clean boundary between presentation, application logic, and persistence.

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

