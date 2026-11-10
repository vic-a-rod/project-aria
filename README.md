# Project Aria

Aria is a local-first productivity assistant focused on sustainable planning. The first milestone is intentionally useful without an AI model: manage tasks, explain priority recommendations, and keep personal data on the user's computer.

## Current milestone

The repository is building Version 1: the complete local, typed Aria. The current
foundation provides:

- Task creation, editing, completion, deletion, search, and filtering
- User-defined categories and tags
- Deadlines, estimated effort, importance, and fixed/flexible scheduling
- Deterministic, explainable priority scores
- SQLite persistence
- A responsive dashboard
- Backend tests

Version 1 will add the complete task/event/application model, deterministic planning,
typed natural-language commands, and email/calendar connections. Version 2 adds
speech input and output; Version 3 moves the same core to a permanent server for apps
and web; Version 4 adds dedicated household speaker/microphone devices. See
[`docs/roadmap.md`](docs/roadmap.md).

## Repository layout

```text
backend/   FastAPI API, SQLite persistence, and scheduling domain logic
frontend/  React and TypeScript dashboard
docs/      Architecture and project decisions
```

## Run locally

After completing the one-time backend and frontend setup below, Windows users can
double-click **`Start Aria.cmd`** in the repository root. It starts both local
services, waits until they are ready, and opens the dashboard automatically. Use
**`Stop Aria.cmd`** to stop services created by the launcher.

### Backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
uvicorn app.main:app --reload
```

The API is available at `http://localhost:8000`; interactive documentation is at `http://localhost:8000/docs`.

### Frontend

In another terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## Data and privacy

Every clone starts empty. Aria does not ship with the maintainer's tasks, calendar,
applications, preferences, database, credentials, or machine-specific configuration.

Local databases, environment files, credentials, tokens, and real personal data are
ignored by Git. Only fictional sample data should appear in issues, tests,
screenshots, or documentation. See [docs/privacy.md](docs/privacy.md) for the data
boundary contributors must preserve.

## Development principles

- Keep calculations and state changes in deterministic application code.
- Require previews or confirmation before consequential future actions.
- Treat rest and unscheduled time as valid planning results.
- Keep integrations read-only until users explicitly grant narrower permissions.
- Prefer small, reviewable changes with tests.

## License

Project Aria is available under the [MIT License](LICENSE).

