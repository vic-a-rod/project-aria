# Four-version roadmap

Aria's versions are defined by interaction and deployment form. Version 1 contains
the complete functional intelligence. Versions 2–4 reuse that intelligence through
new transports, hosting, and devices.

> Build each functional capability once behind stable application commands.
> Later versions add clients and infrastructure, not duplicate business logic.

## Version 1 — Local typed Aria

Aria runs on a Windows computer and is controlled through screens and typed
natural-language requests. Text-only describes the interaction medium, not a reduced
feature set.

Version 1 includes:

- Tasks, projects, categories, tags, events, appointments, commitments, and recurring
  responsibilities
- Internship and job applications, interviews, contacts, follow-ups, and deadlines
- Daily, weekly, monthly, custom-range, and workload calendar views
- Fixed versus flexible commitments, free-time calculation, and conflict detection
- Deterministic priorities, scheduling proposals, workload simulations, and
  explainable recommendations
- Sustainable workload modes, protected rest/family time, preferences, reminders,
  quiet hours, and proactive local recommendations
- Typed natural-language commands using validated structured intents
- Email and calendar connections with read-only scopes first, source provenance, and
  proposed tasks/events derived from external information
- Explicit previews and confirmations before consequential mutations or external
  writes
- Local SQLite storage, protected credentials, offline degradation, and Windows-
  friendly installation and startup

Version 1 is complete when a user can type a request such as “Review my email and
calendar, identify important responsibilities, and propose a manageable week,”
inspect the evidence and deterministic reasoning, approve selected changes, restart
Aria, and continue using the saved plan.

## Version 2 — Conversational voice Aria

Version 2 adds speech to the complete Version 1 assistant:

- Microphone capture and speech-to-text
- Spoken responses through text-to-speech
- Push-to-talk and configurable listening modes
- Interruption, cancellation, and clear listening/processing/speaking indicators
- Voice confirmation flows that retain the same safety rules as typed commands

Speech transcripts enter the Version 1 command contract. Responses use a structured
short speaking form. No scheduling, priority, email, calendar, or task logic may be
implemented inside the audio layer.

Version 2 is complete when every supported typed workflow can be performed
conversationally without bypassing validation, evidence, authorization, or
confirmation.

## Version 3 — Permanent server and application platform

Version 3 moves the same domain and application core to an always-available server
used by authenticated apps and a website.

It adds:

- Authentication, authorization, sessions, and per-user data isolation
- An authenticated, versioned multi-client API
- A server-grade database, durable background workers, and encrypted secret storage
- Secure remote access, rate limits, observability, backups, and recovery
- Multi-device synchronization, concurrency, idempotency, and conflict handling
- Web and application clients using the existing command/result contracts

Version 3 is complete when authorized clients safely use one persistent Aria account
without rewriting Version 1 domain engines.

## Version 4 — Dedicated household Aria hardware

Version 4 adds custom speaker/microphone devices similar in purpose to an Alexa or
Echo Dot. Each unit is a thin client of the Version 3 service.

It adds:

- Far-field microphone array, speaker, acoustic echo cancellation, and interruption
- Wake-word or physical activation
- Visible hardware mute and recording-state controls
- Secure device enrollment, identity, revocation, and room association
- Encrypted communication with the Version 3 server
- Signed firmware, secure boot where supported, and safe update mechanisms
- Minimal local audio buffering and graceful degraded/offline behavior

Household devices do not store the primary user database, email credentials, or
planning engine. Version 4 is complete when enrolled devices provide reliable,
privacy-visible household access to the same Aria account.

## Compatibility constraints established in Version 1

- Scope user-owned records through a local profile/workspace identifier even though
  Version 1 is single-user.
- Use portable IDs, UTC instants, explicit IANA time zones, migrations, and repository
  interfaces.
- Keep domain and application layers independent of FastAPI, SQLAlchemy, LLM SDKs,
  provider SDKs, microphone libraries, and deployment assumptions.
- Convert all requests into versioned typed commands before execution.
- Return structured data, explanations, proposals, warnings, and concise speakable
  text rather than UI-only strings.
- Separate proposals from execution through expiring confirmation tokens and audit
  records.
- Keep provider credentials behind a vault abstraction and external content behind
  provider-neutral models with provenance.
- Treat email, calendar, and web content as untrusted data that can never authorize
  actions or override application rules.
- Abstract recurring/background work so Version 1 can use an in-process scheduler and
  Version 3 can use durable workers without changing application behavior.

