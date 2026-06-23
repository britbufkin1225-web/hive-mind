![Hive|Mind GitHub README banner](./docs/assets/branding/hivemind-readme-banner.png)

# Hive|Mind

Parent label: **devdevbuilds**

Hive|Mind is beginning with a small, stable application foundation: a React frontend and a FastAPI backend with an explicit API contract. The project is currently in **Phase 1 — Foundation**.

## Stack

- Frontend: Vite, React, TypeScript, plain CSS
- Backend: Python, FastAPI, Pydantic
- Tests: pytest

## Setup

Prerequisites: Node.js 20+ and Python 3.11+.

```bash
cd hivemind
npm install
python -m venv .venv
```

Activate the virtual environment, then install backend dependencies:

```bash
python -m pip install -r apps/backend/requirements-dev.txt
```

Optionally copy `.env.example` to `.env` or `apps/frontend/.env`. The frontend defaults to the local backend URL when the variable is absent.

## Run

Run each service in a separate terminal from the repository root:

```bash
npm run dev:backend
npm run dev:frontend
```

- Frontend: [http://localhost:5173](http://localhost:5173)
- Backend: [http://localhost:8787](http://localhost:8787)
- API health: [http://localhost:8787/api/health](http://localhost:8787/api/health)
- Interactive API docs: [http://localhost:8787/docs](http://localhost:8787/docs)

## Verification checklist

- [ ] `npm run check:frontend` completes successfully.
- [ ] `npm run check:backend` passes.
- [ ] `/api/health` returns `ok: true`.
- [ ] The frontend shows the backend as connected.
- [ ] The vault summary shows zeroed foundation values.

See [Phase 1 foundation](docs/phase-1-foundation.md) and the [API contract](docs/api-contract.md) for details.

