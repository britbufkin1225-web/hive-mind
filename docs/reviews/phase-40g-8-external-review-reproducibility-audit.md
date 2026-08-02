# Phase 40G.8 — External Review Reproducibility + Repository Completeness Audit

**Audit date:** 2026-08-02
**Prepared by:** devdevbuilds (audit executed by Claude Code)
**Audit branch:** `phase-40g-8-external-review-reproducibility-audit`
**Locked baseline commit:** `74e71f0c512a58b29b5f955eed8848792e4a4a68` (`origin/main`,
`docs: reconcile Phase 40E persistence-boundary numbering (#197)`, 2026-08-01)

**Final verdict:**
**HARDENING REQUIRED — REVIEW PACKAGE DEFECT CONFIRMED — CANONICAL REPOSITORY REPRODUCIBLE**

Rationale for verdict: the canonical repository is proven reproducible (all reported
modules present and importable; 1252 tests collect and pass). The verdict is
**HARDENING REQUIRED** rather than a bare PASS because narrowly scoped corrections
were necessary and have been completed within this phase's allowance — an explicit
Pydantic v2 dependency declaration, this reproducibility audit, and the external-review
package contract. The proven conclusion that the canonical repository is reproducible
is not weakened by this label.

---

## 1. Purpose

Reviewer **ASH** reported that the supplied external-backend-review ZIP could not
collect tests: seven collection/import errors, zero tests executed, and several
named modules "missing." This phase determines, from repository evidence, whether
the failure is (A) review-package incompleteness, (B) canonical repository
incompleteness, (C) dependency/environment reproducibility failure, (D) inaccurate
documentation/test-count claims, or (E) a combination.

**Conclusion (proven below): the incident is category (A) — review-package
incompleteness.** The supplied artifact was a *curated 45-file source-review
packet*, not a runnable repository. It intentionally omitted the modules ASH named,
which are transitive dependencies of the seven test files that were included. The
canonical repository at the locked baseline contains every named module, imports
cleanly, and runs **1252 tests, all passing**.

## 2. Repository identity

| Field | Value |
| --- | --- |
| Local repository | `C:\Users\britb\Documents\hive-mind` |
| Canonical remote (`origin`) | `https://github.com/britbufkin1225-web/hive-mind.git` |
| Baseline branch | `main` |
| Baseline commit | `74e71f0c512a58b29b5f955eed8848792e4a4a68` |
| Audit branch | `phase-40g-8-external-review-reproducibility-audit` (created at the baseline; 0 commits ahead at start) |

## 3. Supported environment (verification host)

| Component | Value |
| --- | --- |
| OS | Windows 11 (10.0.26200) |
| Python | 3.13.13 |
| Backend directory | `apps/backend` |
| Test runner | `pytest` 8.4.0 (config: `pytest.ini` → `pythonpath = .`, `testpaths = tests`) |
| FastAPI | 0.115.12 |
| Pydantic | 2.11.5 (v2) |
| httpx | 0.28.1 |

**Note on invocation:** `pytest.ini` sets `pythonpath = .`, so the suite must be run
**from `apps/backend/`**. Running from any other root (or against a re-rooted ZIP)
breaks `app.*` imports.

## 4. Exact verification commands

Run from `apps/backend/` with `PYTHONPATH=.`:

```bash
# module existence + git tracking (from repo root)
git ls-files --error-unmatch apps/backend/app/services/validation.py   # etc.

# import resolution (from apps/backend)
python -c "import app.services.validation"                             # etc., all 14

# collection
python -m pytest -q --collect-only

# full suite
python -m pytest -q

# static test-function count
#   count of lines matching ^\s*(async\s+)?def test_ across tests/*.py
```

## 5. Canonical module-completeness matrix

Every module ASH named, verified at the locked baseline. All are **present on disk,
git-tracked, and importable**.

| ASH-named module | Canonical path | On disk | Git-tracked | Imports |
| --- | --- | :---: | :---: | :---: |
| `app.adapters` | `app/adapters/__init__.py` | ✓ | ✓ | ✓ |
| `app.services.validation` | `app/services/validation.py` | ✓ | ✓ | ✓ |
| `app.console.console` | `app/console/console.py` | ✓ | ✓ | ✓ |
| `app.models.hive_models` | `app/models/hive_models.py` | ✓ | ✓ | ✓ |
| `app.models.repository_observer` | `app/models/repository_observer.py` | ✓ | ✓ | ✓ |
| `app.models.repository_observer_api` | `app/models/repository_observer_api.py` | ✓ | ✓ | ✓ |
| `app.routers.obsidian` | `app/routers/obsidian.py` | ✓ | ✓ | ✓ |
| `app.routers.registry` | `app/routers/registry.py` | ✓ | ✓ | ✓ |
| `app.services.intelligence` | `app/services/intelligence.py` | ✓ | ✓ | ✓ |
| `app.services.knowledge_graph` | `app/services/knowledge_graph.py` | ✓ | ✓ | ✓ |
| `app.services.repository_drift_analysis` | `app/services/repository_drift_analysis.py` | ✓ | ✓ | ✓ |
| `app.services.repository_git_adapter` | `app/services/repository_git_adapter.py` | ✓ | ✓ | ✓ |
| `app.services.repository_observation_snapshot` | `app/services/repository_observation_snapshot.py` | ✓ | ✓ | ✓ |
| `app.store.store` | `app/store/store.py` | ✓ | ✓ | ✓ |

**Classification for every named module: present and importable in the canonical
repository; absent only from the supplied review packet.** No module was renamed,
superseded, or referenced only by stale tests. No placeholder modules were created.

## 6. Canonical repository vs. supplied review packet

### 6.0 Packet provenance (recorded from tracked history)

The packet does **not** exist on the locked `origin/main` baseline (`74e71f0`). It is
tracked only on a review-support branch. Provenance recovered from git:

| Field | Value |
| --- | --- |
| Support branch | `support/external-backend-review-2026-07-refresh` |
| Packet path | `docs/reviews/external-backend-2026-07/hive-mind-backend-review-packet.zip` |
| Last commit touching packet | `c35f26ab5cfdbbd08a154f6fa362a2ee2f62de7d` (2026-08-01, "docs: refresh external backend review snapshot") |
| Git blob object id | `921c8719bc7275aa994488d17115b109c494147d` |
| Packet SHA-256 (recovered blob) | `4ec893525f64d4faa51ac02dbef42a85c233d06f9ff05c6ccaba50cedecdeee2` |
| Packet size | 951,669 bytes |
| Present on `origin/main`? | **No** — support branch only |
| Package type | **Type B — curated source-review packet** (per its own `review-manifest.md`) |
| Runnable clone? | **No** — not intended or documented as a runnable repository clone |

Byte-fidelity of the recovered blob was confirmed by extracting one inner file
(`repository/apps/backend/pytest.ini`) and matching its SHA-256 to the manifest's
recorded value (`e6ef972d…`), so the packet SHA-256 above is trustworthy. The packet's
own `baseline-and-validation.txt` records its baseline as `74e71f0` but the artifact
itself was never committed to `main`. No provenance was invented; every value above is
read from tracked history or the recovered blob.

### 6.1 Contents

The supplied artifact is tracked alongside a `review-manifest.md` and
`baseline-and-validation.txt`. The audit extracted the ZIP in isolation (scratch only;
the canonical tree was untouched).

**The packet is a curated source-review packet, not a runnable repository:**

- **45 total files** (per the manifest and confirmed by extraction).
- **20 `app/*.py` files** — only the `memory_migration*`, `grounded_synthesis*`,
  `active_memory*`, `main.py`, and three routers under review.
- **7 of 42 test files** — the manifest explicitly labels these "Repository tests
  (selected)."
- **None** of ASH's 14 named modules are in the packet.

`baseline-and-validation.txt` states the packet's verification method plainly:
"Static, read-only inspection … The full backend test suite was NOT re-run for this
packet; where a number is quoted it is a static count, not a pass/fail claim." So the
packet's own record was honest about scope. **What it lacked was an explicit,
prominent statement that the packet is not runnable and that `pytest` would fail
against it** — the ambiguity that led ASH to attempt a full collection.

### Root-cause reproduction (decisive evidence)

Running `pytest -q` against the extracted packet reproduced ASH's report **exactly**:

```
!!!!! Interrupted: 7 errors during collection !!!!!
7 errors in 0.90s        (exit code 2)
```

Every one of the seven included test files fails at import because they all reach
`app.models.memory_migration`, which at line 110 executes:

```python
from app.services.validation import assert_within_nesting_depth
```

`app/services/validation.py` was **not shipped in the packet**. The first shared
import fails, cascading to all seven test files → 7 collection errors, 0 tests
collected. This matches ASH's "seven test collection/import errors" precisely.

## 7. Exact test results (canonical repository, locked baseline)

| Metric | Canonical repository | Supplied packet (isolated) |
| --- | --- | --- |
| Discovered / collected | **1252** | 0 (interrupted) |
| Executed | **1252** | 0 |
| Passed | **1252** | 0 |
| Failed | **0** | 0 |
| Skipped | **0** | 0 |
| Deselected | **0** | 0 |
| Warnings | **0** | 0 |
| Collection errors | **0** | **7** |
| Wall time | 12.06s | 0.90s |
| Exit code | 0 | 2 |

**Static `def test_` count: 1056**, across 42 backend test files. This is the figure
the packet's baseline record quotes as "1,056 test functions" — an accurate *static
function count*. Parametrization expands it to **1252 collected/executed** tests.
These are different measures and are reported separately here, never conflated.

## 8. Dependency findings

- **Declared runtime deps** (`requirements.txt`): `fastapi>=0.115,<1.0`,
  `uvicorn[standard]>=0.34,<1.0`.
- **Declared dev deps** (`requirements-dev.txt`): `-r requirements.txt`,
  `httpx>=0.28,<1.0`, `pytest>=8.3,<9.0`.
- **Pydantic v2 is a direct dependency but was undeclared.** The backend imports
  `BaseModel`, `ConfigDict`, `field_validator`, and `model_validator` across 18
  files (336 occurrences; `field_validator` ×187, `model_validator` ×50,
  `ConfigDict` ×25). These are **Pydantic v2-only** APIs.
- **Severity is latent, not active.** FastAPI 0.115 requires
  `pydantic <3.0.0,>=1.7.4` (excluding a few versions), so a fresh clone currently
  resolves Pydantic 2.x transitively and the suite passes. The risk is future
  resolver drift or a transitive pin to v1 silently breaking imports.

**Scoped correction applied (Section 12).** The change to
`apps/backend/requirements.txt` adds **5 lines: 4 comment/rationale lines** (each
prefixed `#`, no effect on resolution) **and exactly 1 effective declaration line:**

```
pydantic>=2,<3
```

- **Compatibility:** FastAPI's own metadata requires `pydantic <3.0.0,>=1.7.4`
  (excluding 1.8, 1.8.1, 2.0.0, 2.0.1, 2.1.0). The declared FastAPI range is
  `fastapi>=0.115,<1.0`. `pydantic>=2,<3` is a **strict subset** of FastAPI's
  constraint — no conflict; it merely removes the v1 option.
- **No lock/config to synchronize:** the repository tracks only two dependency files,
  `apps/backend/requirements.txt` and `apps/backend/requirements-dev.txt` (the latter
  begins `-r requirements.txt`). There is no `poetry.lock`, `Pipfile`, `pdm.lock`,
  `constraints.txt`, `pyproject.toml`, or `setup.py/cfg` to keep in sync.
- Declaration-only; no runtime or behavioral effect. All 1252 tests pass after the
  change.

## 9. Fresh-clone reproducibility assessment

**A literal fresh `git clone` was not performed.** The audit performed the strongest
safe equivalents against the locked baseline in the canonical working tree and an
isolated extraction:

- **Isolated packet extraction + run** — reproduced the 7-error failure exactly
  (proves the packet is the failing artifact).
- **Canonical import + collect + full run** from `apps/backend/` — 1252/1252 pass.
- **Dependency resolution analysis** — FastAPI's metadata requires
  `pydantic <3.0.0,>=1.7.4`, so a clean install resolves Pydantic 2.x transitively and
  the suite passes today; the new explicit pin makes that requirement non-incidental.

**Exact supported reproduction commands** (validated environment: Python **3.13.13**,
pytest **8.4.0**, Windows 11). From a clean checkout of commit `74e71f0`, run **from
the `apps/backend/` directory** (its `pytest.ini` sets `pythonpath = .` and
`testpaths = tests`):

```bash
cd apps/backend
python -m pip install -r requirements.txt -r requirements-dev.txt
python -m pytest -q
```

Expected result: `1252 passed` in ~12s, exit code 0, 0 collection errors, 0 skips,
0 warnings. The requirements filenames are literally `requirements.txt` (runtime) and
`requirements-dev.txt` (adds `httpx`, `pytest`, and re-includes runtime via
`-r requirements.txt`). These instructions were not previously consolidated in one
reviewer-facing place; the package contract
(`docs/external-review-package-contract.md`) and Section 4 above now capture them.

## 10. CI findings

**No CI exists** — confirmed from **git-tracked baseline contents**, not merely a
missing local directory. `git ls-files` at the baseline returns no
`.github/workflows/*`, no `.gitlab-ci.yml`, no `azure-pipelines*`, no `.circleci/`, no
`Jenkinsfile`, no `.travis.yml`, and no `.drone.yml`. The locked baseline's test status
therefore cannot be corroborated by an automated pipeline — only by local execution as
recorded here. Establishing a minimal
CI job (`apps/backend` → install both requirements → `pytest -q`) is a recommended
**P2** follow-up. No CI system was built in this audit phase (out of scope).

## 11. Documentation / test-claim findings

| Claim | Where | Classification |
| --- | --- | --- |
| "1,056 test functions across 42 backend test files" | packet `baseline-and-validation.txt` | **Accurate** as a static count; explicitly labeled as such. |
| "the full suite was NOT re-run … a static count, not a pass/fail claim" | packet `baseline-and-validation.txt` | **Accurate and appropriately cautious.** |
| Whole-suite "N tests pass" / "production-ready" claims | canonical `README.md`, `docs/**` | **Not present.** Tracked docs make no inflated whole-suite passing claim; README explicitly frames the project as "a local, single-user developer tool … no authentication" and docs reject "production-ready/secure" framing. |
| Historical per-phase counts (e.g. "267 full", "23 targeted") | dated phase QA docs | **Accurate and scoped** to their phase; not claims about the current suite. |
| `docs/roadmap.md` "Active Phase" still frames Phase 40F as active | canonical `docs/roadmap.md` | **Stale but pre-existing and already documented** (see the support branch's `baseline-and-validation.txt`, finding #1). Unrelated to reproducibility; **out of scope** for Phase 40G.8 and left unchanged. |

No documentation correction was necessary for reproducibility. The distinctions
between static function count, collected tests, executed tests, passing tests, and
packet reproducibility are preserved throughout this report.

## 12. Files changed

| File | Change | Why necessary | Why in scope | Behavior impact |
| --- | --- | --- | --- | --- |
| `apps/backend/requirements.txt` | +5 lines = 4 comment/rationale lines + **1 effective declaration** `pydantic>=2,<3` | Pydantic v2 is directly imported in 18 files but was undeclared, relying on transitive resolution | Section D expressly permits a minimal declaration correction for a directly-used, provably-undeclared dependency | None — declaration only; 1252/1252 tests pass before and after |
| `docs/reviews/phase-40g-8-external-review-reproducibility-audit.md` | New — this audit manifest | Required deliverable (Section H) | Audit documentation | None |
| `docs/external-review-package-contract.md` | New — reusable review-package contract/checklist | Root cause was an ambiguous, non-runnable packet; a contract prevents recurrence | Explicitly permitted (Section I) | None |

## 13. Required matrix (Section H)

| Check | Canonical repository | Supplied review packet | Classification |
| --- | --- | --- | --- |
| Required modules present | **Yes — all 14 present & git-tracked (proven)** | No — 14 named modules omitted (reproduced) | **Packet defect** |
| Imports resolve | **Yes — all 14 import cleanly (proven)** | No — `app.services.validation` etc. absent | **Packet defect** |
| Test collection starts | **Yes — 1252 collected, 0 errors (proven)** | No — 7 collection errors | **Packet defect** |
| Tests execute | **Yes — 1252 executed (proven)** | No — 0 executed | **Packet defect** |
| Reported test count reproducible | **Yes — 1056 static / 1252 collected (proven)** | No | **Repo accurate; packet non-runnable by design** |
| Dependencies explicitly declared | **Partial — FastAPI/uvicorn/httpx/pytest declared; Pydantic v2 was transitive (now declared)** | Same source files (config included) | **Repo hardening (P2), applied** |
| CI validates supported workflow | **No CI exists (proven)** | Not applicable | **Follow-up (P2)** |

## 14. Classification of ASH's findings

| ASH finding | Verdict |
| --- | --- |
| Seven collection/import errors; modules missing | **Confirmed as a packet defect.** Reproduced exactly; canonical repo has all modules. |
| `pytest -q` could not collect; zero tests executed | **True for the packet only.** Canonical repo collects and executes 1252. |
| Documentation referenced 1,056 test functions | **Accurate static count**, correctly labeled in the packet record. 1252 tests actually collect/execute. |
| Pydantic v2 used directly | **True and accurate.** Now declared explicitly (was transitive). |
| Complete suite not reproducible from the supplied packet | **True by design** — the packet is a curated source-review subset, not a runnable clone. This was under-communicated to the reviewer. |

## 15. Known limitations

- Verification ran on one host (Windows 11 / Python 3.13.13) against the developer's
  installed environment; no isolated virtual-env matrix or other OS/Python versions
  were exercised.
- No network fresh-clone was performed; the isolated-packet extraction and canonical
  in-tree run are the safe equivalents.
- The exact ZIP ASH received is assumed identical to the tracked packet at
  `docs/reviews/external-backend-2026-07/…`; the audit did not have ASH's local copy.
  Manifest SHA-256 values were relied upon as the integrity record.

## 16. Follow-ups

- **P0:** None. The canonical repository is reproducible; no P0 defect found.
- **P1:** For any future external review, ship the package with an explicit
  runnable-vs-source-packet statement and reviewer run instructions (now codified in
  `docs/external-review-package-contract.md`). Adopt that contract before the next
  packet.
- **P2:**
  - Establish minimal CI: `apps/backend` → install both requirements → `pytest -q`,
    to corroborate the baseline's test status automatically.
  - Reconcile `docs/roadmap.md` "Active Phase" wording (pre-existing, already tracked;
    unrelated to reproducibility).
  - Consider declaring `pydantic-settings`/other transitive but directly-used
    packages if any are found in future audits (none beyond Pydantic here).

## 17. Recommended next phase

Proceed with the previously planned **Phase 40H** (reviewed persistence + verified
import) only after devdevbuilds accepts this audit and merges (or defers) the two new
docs and the one-line dependency declaration. Optionally interleave the P2 CI job as a
small enabling step so future reviews are self-verifying.

## 18. Scope-percentage accounting

| Bucket | Target | Actual (this phase) |
| --- | --- | --- |
| Evidence collection / reproducibility verification | 70% | ~70% — module matrix, import checks, collection, full suite, packet extraction + reproduction, dependency analysis |
| Audit report / documentation reconciliation | 20% | ~22% — this manifest + package contract |
| Narrowly necessary small fixes | 10% | ~8% — one declaration-only line in `requirements.txt` |

## 19. Assurances

- **Phase 40H was not implemented** — no migration persistence, verified import,
  orchestration, or runtime workflow logic was added.
- **Phase 36K remained paused and untouched.**
- **Nothing was pushed, no PR was opened, and nothing was merged.** No commit was
  created; changes remain uncommitted on the audit branch for devdevbuilds' decision.
