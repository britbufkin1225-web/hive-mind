# Repository Observer — Operator Workflow (Phase 39D)

The Repository Observer is a **read-only** surface that turns the current state
of a local Git repository into a bounded, deterministic snapshot (and an optional
drift analysis against `HEAD`). It never watches, stages, commits, switches
branches, repairs, pushes, pulls, fetches, or otherwise mutates a repository, and
it never inserts anything into Active Memory on its own.

This guide describes the whole operator path — from a configured workspace,
through the managed runtime, to a snapshot and its evidence — and, most
importantly, **what each failure looks like and how to recover from it**. It does
not re-document the pieces it builds on:

- Workspace configuration: [Phase 39B workspace tool](../scripts/workspaces/README.md)
- Managed runtime (`start`/`status`/`verify`/`restart`/`stop`): [operator-runtime.md](operator-runtime.md)

## The end-to-end workflow

1. **Configure or select a workspace** (once). The Phase 39B tool records which
   local Git repository Hive|Mind should run against, stored outside the
   repository and never committed. Override the config location for a session
   with `HIVEMIND_WORKSPACE_CONFIG_PATH`.
2. **Start the runtime.** From the repository root:
   `./scripts/runtime/Invoke-HiveMindRuntime.ps1 start`. This resolves the active
   workspace, launches the backend (uvicorn, `8787`) and frontend (vite, `5173`),
   and waits — bounded — for both to become reachable.
3. **Confirm health.** `Invoke-HiveMindRuntime.ps1 status` (or `verify`) reports
   whether the managed backend and frontend are up. The frontend expects the
   backend at `http://localhost:8787/api`.
4. **Open the frontend** at `http://localhost:5173` and go to the Repository
   Observer panel.
5. **Observe.** Enter the **absolute** path of the repository to observe (this is
   the workspace repository path; the observer does not infer it) and choose
   *Observe snapshot*. Optionally choose *Analyze Drift* to compare the working
   tree against the supported `HEAD` baseline.
6. **Read the evidence.** A successful response shows repository identity, branch
   and HEAD, working-tree state, changed files, evidence excerpts, warnings,
   limitations, and overflow/completeness. See below for how to read a clean vs.
   dirty result.
7. **Stop the runtime** when done: `Invoke-HiveMindRuntime.ps1 stop`. Only the
   processes the launcher started are stopped; unrelated Node/Python processes
   are left running.

## Reading a result

- **Clean repository.** Working-tree state is exactly `clean`, zero changed
  files, `completeness: complete`. The panel shows a green *Clean repository*
  chip.
- **Dirty repository.** Working-tree state includes some of `staged`,
  `modified`, `untracked`, `conflicted`, and changed files are listed. **This is
  valid evidence, not an error** — the request still succeeds (HTTP 200). The
  panel shows a *Dirty or changed repository* chip.
- **Warnings are not failures.** A detached `HEAD`, an unborn branch (a repo with
  no commits), or a missing upstream/remote each surface as an explicit warning
  on an otherwise successful snapshot. A local-only repository with no remote is
  a normal, observable state.
- **Partial / truncated.** When output exceeds a configured bound, the snapshot
  is marked partial and an overflow record states the limit, the retained count,
  and (when safely known) the observed total. Evidence is bounded, never silently
  dropped.

## Failure-state taxonomy and recovery

Failures are classified by the layer that produced them so the recovery action
is unambiguous. Operator-visible errors are concise and never expose raw
tracebacks, credentials, or credential-bearing remote URLs.

| Layer | Example condition | What you see | Recovery |
| --- | --- | --- | --- |
| Configuration | No workspace configured / config missing or malformed / unsupported version | Workspace tool reports a typed error before the runtime starts | Re-run the Phase 39B workspace tool; fix or recreate the config, or set `HIVEMIND_WORKSPACE_CONFIG_PATH` |
| Runtime | Backend/frontend not started, partial start, stale metadata, port in use | `status`/`verify` reports not-ready; `start` rolls back a partial start | `Invoke-HiveMindRuntime.ps1 restart`; free ports `8787`/`5173`; re-run `verify` |
| Transport | Backend unreachable, or the request exceeds the client timeout | Panel: *Repository Observer is unavailable* or *Repository Observer request timed out* | Confirm the runtime is healthy (`status`), then retry — both states are recoverable and the controls re-enable |
| Repository (input) | Path missing (404), not a directory (400), or not a Git repository (400) | Panel: *Repository root was not found* / *…could not be observed* | Correct the absolute path; confirm it is the intended workspace repository |
| Request (contract) | Empty/relative path, parent traversal, out-of-range bounds, unknown field (422) | Panel: *Request did not match the contract* | Fix the offending field; the panel validates the same rules client-side before sending |
| Git / snapshot / drift | Git subprocess failed, timed out, output-bound exceeded, or unparseable (502); Git unavailable (503) | Panel: *Repository Observer is unavailable* (bounded-failure message) | Retry; confirm the repository is intact and `git` is installed and on `PATH` |
| Server | Any unexpected internal error (500) | Panel: *…unexpected server error* → "Internal server error" | Retry; collect diagnostics from the runtime logs (see below) |

The **snapshot request has a bounded client-side timeout** so a hung backend
fails as a distinct, recoverable *timed out* state rather than pending forever;
the underlying Git observation is itself bounded (subprocess timeout). Only the
**newest** request updates the panel — a slow earlier response can never
overwrite a newer result, and a failed request leaves the previous successful
snapshot visible.

## Safe diagnostic collection

- Runtime and service logs live **outside** the repository under the user's
  local application-data directory (relocatable with `HIVEMIND_RUNTIME_HOME`).
  See [operator-runtime.md](operator-runtime.md#runtime-metadata-and-logs).
- Logs and API output are credential-safe: remote URLs that embed a username,
  password, or access token are redacted before they are logged, returned, or
  displayed, while enough of the remote is preserved to identify it.
- Do not paste raw remote URLs that may contain tokens into reports; the observer
  already redacts them, and the workspace/runtime tooling does the same.

## Known limitations

- Metadata-only: the observer reads Git status/branch/remote metadata and does
  **not** read file contents.
- Only the current `HEAD` baseline is supported for drift analysis.
- The observer observes exactly the absolute path provided; it does not itself
  read the workspace config to choose a repository (the operator supplies the
  workspace repository path).
- Output is bounded (files, warnings, limitations, and command bytes); very large
  working trees are reported as partial with explicit overflow records.
- Read-only by contract: the observer runs no mutating Git command and performs
  no automatic Active Memory insertion.
