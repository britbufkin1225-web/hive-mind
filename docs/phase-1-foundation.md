# Phase 1 — Foundation

## Included

Phase 1 establishes two separate local development environments in one repository:

- A Vite, React, and TypeScript frontend with a small typed API client.
- A FastAPI backend with CORS configured for the local frontend.
- Stable health, status, and empty vault-summary API responses.
- A minimal frontend connection check and response display.
- A backend health endpoint test and frontend production build check.

## Intentionally excluded

This phase does not include the final dashboard, honeycomb or 3D graph logic, graph or animation libraries, an asset system, branding assets, legacy assets, database behavior, or complex styling. The vault data is an explicit empty-state contract only.

## Run the frontend

From the repository root:

```bash
npm install
npm run dev:frontend
```

Open http://localhost:5173.

## Run the backend

Create and activate a Python virtual environment, then run:

```bash
python -m pip install -r apps/backend/requirements-dev.txt
npm run dev:backend
```

The API runs at http://localhost:8787.

## Verify the API connection

1. Start the backend and frontend in separate terminals.
2. Open http://localhost:5173.
3. Confirm the connection test reads **Connected**.
4. Confirm the health section shows `hivemind-backend` and version `0.1.0`.
5. Confirm the vault counts are all zero and graph mode is `not_initialized`.

You can also open http://localhost:8787/api/health directly.

## Next phase

The next phase should build the first real product flow on this contract: define vault ingestion requirements, data models, and persistence boundaries before introducing visualization. Dashboard and graph work should begin only after those behaviors and contracts are agreed upon.

