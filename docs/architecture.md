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

## Event and commitment domain

Events use either an exclusive all-day date range or timezone-aware timed bounds;
the two shapes cannot be mixed. Timed instants are normalized to UTC for storage and
retain an explicit IANA time zone for display and recurrence interpretation. Event
kinds distinguish general events, appointments, and commitments. Fixed/flexible and
busy/free flags are separate so deterministic availability can consume them without
guessing from presentation text.

Every event records a calendar placement name and provider-neutral provenance type
plus an optional external reference. External content remains data, never an
instruction. Revision `20261109_0003` adds the event store without changing existing
task records.

## Application tracking domain

Internship and job applications store company, role, lifecycle status, posting
provenance, deadlines, notes, fictional-test contacts, interviews, and follow-ups in
normalized local tables. Interview instants and application deadlines are aware UTC
values with an explicit IANA display time zone. Follow-ups carry due dates, effort,
importance, and completion state.

The application service projects deadlines, non-cancelled interviews, and unfinished
follow-ups into one transport-neutral workload feed. Later calendar, priority, and
scheduling engines consume that feed instead of duplicating application records.

## Explainable priority engine

One pure engine scores tasks, events, deadlines, applications, and follow-ups from a
typed responsibility input. Callers must supply an aware current instant; the engine
never reads the system clock. Weight sets are immutable inputs, so configuration can
change policy without hiding calculations in persistence or presentation code.

Every result contains stable reason codes and point-bearing components in addition
to display text. Component points reconcile exactly to the bounded score, including
an explicit cap adjustment when a raw total falls outside 0–100. Completed items
return zero without urgency or effort bonuses.

## Availability and conflict engine

Availability is calculated by a pure UTC-normalizing engine over an explicit window
and typed blocks. Fixed commitments, protected time, and rest are hard constraints;
flexible work occupies ordinary free time but remains visible in a separate hard-free
result so later scheduling can move it. Overlaps between hard constraints are hard
conflicts, while overlaps involving flexible work are classified as resolvable.

Recurring wall-clock blocks retain an IANA time zone and preserve local times across
offset changes. The engine currently supports the Version 1 recurrence subset used
by tasks, events, protected time, and quiet hours: daily or weekly frequency plus
`INTERVAL`, `BYDAY`, `COUNT`, and `UNTIL`. Unsupported frequencies fail explicitly
instead of being approximated. Free intervals, occurrences, and conflicts are sorted
stably and returned without mutating persisted records.

## Scheduling and simulation engine

Scheduling consumes hard-free intervals from the availability engine and immutable
responsibility inputs. It produces separate priority-first and deadline-first
proposals; neither proposal writes to storage. Fixed records and externally sourced
commitments are locked to their current placements, including when they conflict.

Each proposal contains UTC placements, a stable before/after diff, unscheduled
references, scheduled effort, and structured risks for overdue work, deadline
pressure, insufficient capacity, and locked conflicts. Flexible work is allocated as
one contiguous interval and never placed after its deadline. Applying a selected
proposal remains a separate confirmed action handled by the proposal lifecycle.

## Sustainable workload engine

The sustainable-workload layer limits schedule simulation by local-day capacity and
always reserves unscheduled time. A temporary lighter mode reduces the daily ceiling;
a focus mode defers out-of-scope work only when doing so cannot hide a deadline in the
planning horizon. Expired modes revert to normal automatically.

Protected family and rest intervals are subtracted again at this boundary as a
defense in depth. Results report scheduled, capacity, and genuinely unscheduled
minutes per local day. Deadline-bound effort above sustainable capacity produces an
overload warning rather than expanding the workday, deleting protected time, or
silently dropping responsibilities. Focus and capacity deferrals remain structured
and attributable.

## Proactive recommendation rules

Typed local signals feed a pure recommendation engine for approaching and overdue
deadlines, conflicts, interviews, follow-ups, useful free intervals, and active quiet
hours. Policy inputs control enabled rule codes, lookahead windows, priority and
available-time thresholds, and whether critical recommendations may bypass quiet
hours.

Every recommendation carries a stable deduplication key, severity, delivery state,
and validity bound. Callers pass previously emitted keys, so repeated evaluations do
not recreate the same recommendation. Quiet hours defer noncritical delivery rather
than discarding evidence; critical alerts remain configurable. Generation itself is
local, deterministic, and side-effect free—notification persistence and delivery
remain separate application concerns.

## Preferences and workload overrides

Preferences are explicit local records: general key/value choices, recurring protected
time, quiet hours, and temporary focus or lighter-workload modes. Scheduled rules use
an explicit IANA time zone and weekday/time bounds; overnight quiet hours are valid.
Workload modes require an expiration so temporary constraints cannot silently become
permanent.

Suggested preferences remain in a separate `suggested` state and are excluded from
effective preference queries. Only the explicit approval operation activates them and
records the approval time; users may instead dismiss them. Expired records remain
available for history but are excluded from effective queries.

## External-source synchronization ledger

External connections have portable UUID identifiers, a local profile scope, a
provider label, and an explicit active/disconnected/revoked lifecycle. Per-connection
and per-resource checkpoints store opaque provider cursors without interpreting them.

The external-record ledger keys each item by connection, resource type, and provider
external ID. Repeated imports update the same record while retaining first/last-seen
timestamps, content hashes, provider timestamps, provenance, optional local-record
links, and recoverable tombstones. Deduplication is explicit: matching keys support
discovery, while a duplicate link requires both records to share their connection and
resource type. Imported content remains untrusted data and never authorizes an action.

## Proposals, confirmations, notifications, and audit

Consequential actions begin as expiring proposals containing a structured payload, a
hash of the target state, and normalized evidence. Confirmation tokens are random,
returned only when issued, and stored solely as SHA-256 hashes. Confirmation requires
the token and the current state hash; expiry, state drift, replay, and cross-proposal
use fail closed. A confirmed token is consumed by exactly one persisted execution
result.

Notification rules are explicit, profile-scoped records with priority, channel,
enabled, and quiet-hours behavior. Proposal, confirmation, execution, and notification
rule transitions append audit events with actor, entity, outcome, optional correlation
ID, and structured details. Each lifecycle transition and its audit event commit as
one database transaction; failures roll back confirmation consumption, execution
results, proposal state, and audit state together. Audit events have no update or
delete application path.

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
adopted. SQLite connections explicitly enable foreign-key enforcement so declared
references and cascade behavior are not silently ignored by the default driver.

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
correlation and idempotency identifiers, locale, time zone, a discriminated intent,
and an optional confirmation token. Read intents and proposed-mutation intents are
different wire types. Mutations require an idempotency key, identify an optional
target, explain why they were requested, and never imply authority to execute.

`CommandResult` returns structured data plus warnings, evidence, action proposals,
confirmation requirements, a display summary, and concise speakable text. The
contract is present before an LLM is introduced so language providers can interpret
requests but never gain authority to calculate or mutate directly.

Result lifecycle metadata is fail-closed: clarification status requires a structured
question and answer mode, proposal status requires at least one proposal, and a
confirmation must reference a proposal returned in the same result. Evidence sources
use provider-neutral types and optional timezone-aware observation timestamps.

The command dispatcher receives a trusted `AuthorizationContext` from its transport
boundary and compares it with the actor and profile claimed by the envelope before
route lookup or handler execution. Routes are registered for exactly one intent kind,
so a mutation cannot enter a read handler. An unconfirmed proposed mutation may be
rejected, request clarification, or return proposals, but it cannot report successful
execution. A confirmed mutation may report success only after its application handler
validates and consumes the confirmation through the proposal lifecycle.

## Language-model adapter

Natural-language providers implement one bounded `LanguageModelAdapter` port. Cloud
and future local adapters receive only an explicit instruction, user text, allowed
command names, attributable context items, a correlation ID, and an output-size
limit. The port exposes no repository, database session, credential vault, command
dispatcher, or execution callback.

`LanguageModelGateway` verifies response identity, nonblank content, and the requested
output bound before any interpretation layer may consume provider output. Provider
content remains untrusted data; Version 1 command validation and authorization still
determine what may be proposed or executed. The composition root injects the gateway,
and the default disabled adapter keeps every deterministic feature available when no
model is configured.

