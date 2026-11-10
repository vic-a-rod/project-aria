# Version roadmap

Aria grows in capability layers. Each version must remain usable without later
layers, and local-only operation remains supported throughout the project.

## v0.1 — Local core MVP

Purpose: provide dependable personal task management without AI or external
accounts.

Includes task CRUD, categories and tags, search and filtering, dates, estimated
effort, importance, fixed/flexible status, deterministic priority explanations,
SQLite persistence, a responsive dashboard, and automated checks.

Done when a Windows user can install Aria, manage tasks entirely through the UI,
restart it without losing data, and understand every priority recommendation.

Out of scope: LLMs, chat, voice, automatic scheduling, external calendar/email,
accounts, cloud sync, learned preferences, and proactive notifications.

## v0.2 — Calendar foundation

Purpose: represent commitments, free time, and workload accurately before adding AI.

Includes day/week/month views, fixed commitments versus flexible tasks, available
time, manual placement, conflict detection, workload summaries, and unified display
of classes, study, interviews, appointments, projects, and personal commitments.

Done when users can inspect obligations and free time across useful ranges, fixed
commitments cannot be moved accidentally, and conflicts are detected
deterministically.

Out of scope: automatic calendar changes, external sync, natural-language commands,
and LLM optimization.

## v0.3 — Structured text assistant

Purpose: add natural-language convenience without transferring authority to a model.

Includes a text interface, typed command schema, task commands, summaries, workload
questions, priority explanations, ambiguity handling, and previews before
consequential mutations.

Done when common commands map reliably to validated application operations and the
model cannot write directly to storage.

Out of scope: voice, autonomy, learning, external integrations, and silent changes.

## v0.4 — Adaptive scheduling

Purpose: simulate sustainable plans and temporary workload changes.

Includes an explainable scheduling engine, alternative schedule previews, temporary
workload profiles, protected rest/family periods, configurable priority weights,
risk reporting, alerts, and quiet hours.

Done when users can preview feasible schedules without mutating committed data,
temporary overrides expire predictably, and essential deadlines remain visible when
workload is reduced.

Out of scope: unapproved persistent learning, external writes, and autonomous
planning.

## v0.5 — Approved personalization

Purpose: adapt to the user through inspectable, reversible preferences.

Includes explicit preferences, temporary overrides, evidence-backed suggested
preferences, approval before persistence, review/edit/reset/disable controls, and
category-specific duration and scheduling rules.

Done when users can distinguish explicit, temporary, and inferred rules and can
restore predictable defaults at any time.

Out of scope: hidden profiling, medical inference, irreversible rules, and training
from private user data.

## v0.6 — External integrations

Purpose: safely incorporate calendar, email, coursework, and application workflows.

Includes an internship application tracker, read-only Google/Microsoft calendar
import, explicitly authorized email discovery, task/draft suggestions, source
provenance, minimal OAuth scopes, revocation, and sync status.

Done when integrations can be disconnected without breaking Aria, credentials remain
private, and no external write occurs without explicit confirmation.

Out of scope: automatic sending, silent calendar writes, broad inbox ingestion, and
unnecessary permissions.

## v1.0 and later — Advanced access

Purpose: expand interaction and deployment after the core is trustworthy.

Candidates include voice using the same validated command pipeline, optional local
LLMs, home-server deployment, secure multi-device synchronization, and a community
integration framework.

Security design is required before public server exposure, always-listening voice,
or multi-device synchronization.

