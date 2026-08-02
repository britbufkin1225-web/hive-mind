# External Review Package Contract

**Purpose.** Prevent the Phase 40G.8 incident from recurring: a reviewer received a
*curated source-review packet*, attempted a full `pytest` run against it, and hit
seven collection errors because transitive-dependency modules were intentionally not
shipped. The root cause was not a broken repository — it was an ambiguous artifact
whose runnable/non-runnable nature was under-communicated.

Every external review package MUST declare, up front and unambiguously, **whether it
is a complete runnable repository clone or a focused source-review subset**, and MUST
carry the information a reviewer needs to reproduce (or knowingly not attempt) the
tests.

## Two package types — pick one and label it prominently

| Type | Contains | Reviewer can run tests? |
| --- | --- | --- |
| **A. Complete runnable clone** | The full tracked repository at a commit (or a `git bundle`) — every module and test | **Yes.** Full-suite reproduction is expected. |
| **B. Focused source-review packet** | A curated subset of source/tests/docs for reading | **No.** Tests will fail to collect because transitive dependencies are intentionally absent. This MUST be stated. |

If a Type B packet is supplied, the manifest and a top-of-README banner MUST say, in
plain language: *"This is a source-review packet, not a runnable repository. Do not
run `pytest` against it — imports will fail by design. To run the suite, clone the
repository at the commit below."*

## Required contents (both types)

- **Repository commit SHA** — the exact locked baseline the packet represents.
- **Package purpose and scope** — what the reviewer is being asked to review.
- **Package type** — A or B, stated prominently (see above).
- **Tracked-file manifest** — every file in the package with its repo-relative path
  and a purpose/classification.
- **Checksums** — SHA-256 for every listed file (manifest may self-exclude).
- **Environment / runtime versions** — OS, Python (or other runtime), and key
  dependency versions used to validate.
- **Dependency-install instructions** — exact commands (e.g.
  `pip install -r apps/backend/requirements.txt -r apps/backend/requirements-dev.txt`).
- **Exact test commands** — including the working directory and any path setup
  (for this project: run from `apps/backend/`; `pytest.ini` sets `pythonpath = .`).
- **Exact observed test results** — discovered, collected, executed, passed, failed,
  skipped, deselected, warnings, collection errors, and exit code. Never present a
  static `def test_` count as a passing-test count; if only a static count is
  available, label it as such.
- **Clear statement of whether the package is runnable** — one sentence, unambiguous.
- **Known omissions** — for Type B, list (or characterize) what was deliberately left
  out, especially modules that included files depend on transitively.
- **Known limitations** — host/OS/runtime matrix actually exercised, and anything not
  verified.
- **Source-packet vs. complete-clone distinction** — restate the type and its
  implication for the reviewer.

## Pre-delivery checklist

- [ ] Package type (A or B) chosen and stated at the top of the README/manifest.
- [ ] Baseline commit SHA recorded and matches `git rev-parse HEAD`.
- [ ] Manifest lists every file with purpose + SHA-256; checksums verified.
- [ ] Environment/runtime versions recorded.
- [ ] Install + test commands recorded, including working directory and path setup.
- [ ] Test results recorded with the full metric breakdown (not a static count posing
      as pass count).
- [ ] **Type B only:** explicit "not runnable — do not run pytest" banner present, and
      omitted transitive-dependency modules acknowledged.
- [ ] **Type A only:** a clean extraction was actually installed and the suite run to
      confirm the stated results reproduce.
- [ ] Prohibited-file / secret-pattern scan passed (no `.git`, venvs, caches, DBs,
      logs, credentials, env files, unrelated user data).

## Reference: reproducing the Hive|Mind backend suite (Type A)

```bash
# from a clean clone at the recorded commit
cd apps/backend
python -m pip install -r requirements.txt -r requirements-dev.txt
python -m pytest -q          # pytest.ini sets pythonpath=. and testpaths=tests
```

Expected at baseline `74e71f0`: **1252 collected, 1252 passed, 0 failed/skipped,
0 collection errors, exit 0** (static `def test_` count is 1056 across 42 files).
