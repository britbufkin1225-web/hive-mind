# Hive|Mind API contract

Local base URL: `http://localhost:8787/api`

All endpoints use `GET` and return JSON.

## `GET /api/health`

Confirms that the backend process is available.

```json
{
  "ok": true,
  "service": "hivemind-backend",
  "version": "0.1.0"
}
```

## `GET /api/status`

Returns the stable Phase 1 application identity and local connection state.

```json
{
  "app": "Hive|Mind",
  "parent": "devdevbuilds",
  "environment": "development",
  "backend": "online",
  "frontend": "connected"
}
```

## `GET /api/vault/summary`

Returns the Phase 1 empty vault state. It does not represent implemented graph behavior.

```json
{
  "totalFiles": 0,
  "totalSources": 0,
  "totalModels": 0,
  "totalNodes": 0,
  "graphMode": "not_initialized",
  "message": "Vault foundation ready. Graph logic not implemented in Phase 1."
}
```
