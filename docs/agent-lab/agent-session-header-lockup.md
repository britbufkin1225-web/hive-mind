# Agent Session Header Lockup

A session header is mandatory before contribution work. It narrows the contract
for one session and is copy-paste-ready YAML.

```yaml
contract_version: agent-contribution.v1
session_id: phase-00-example-agent-001
phase_id: Phase 00
phase_name: Example bounded contribution
agent_name: example-agent
assigned_role: primary-implementer
capability_level: L2
composition_mode: sequential-isolated
repository_root: C:/canonical/repository
expected_remote: https://example.com/owner/repository.git
baseline_commit: 0000000000000000000000000000000000000000
required_branch: phase-00-example
input_commit: 0000000000000000000000000000000000000000
write_authority: bounded-path-write
owned_paths:
  - type: prefix
    value: docs/example/
read_only_paths:
  - type: prefix
    value: docs/
forbidden_paths:
  - type: prefix
    value: apps/
objective: Create the locked deliverables.
required_deliverables:
  - docs/example/README.md
required_validation:
  - git diff --check
explicit_non_goals:
  - Application changes
paused_track_locks:
  - Phase 36K
stop_conditions:
  - STOP: The working tree contains unexplained changes.
required_final_report:
  - Commit hash
  - Changed files and validation outcomes
```

All displayed fields are mandatory; use `[]` only when a list genuinely has no
entries. `assigned_role`, `capability_level`, `composition_mode`, and
`write_authority` are enumerated. Controlled values are:

```text
assigned_role: primary-implementer | independent-auditor-hardener |
  specialist-contributor | read-only-scout | integration-composer |
  human-project-owner
capability_level: L0 | L1 | L2 | L3 | L4
composition_mode: sequential-isolated | sequential-audit | parallel-read-only |
  parallel-isolated | integration-composition | adversarial-verification
write_authority: none | documentation-only | tests-only | bounded-path-write |
  full-locked-phase-scope
```

`owned_paths`, `read_only_paths`, `forbidden_paths`, `required_deliverables`,
`required_validation`, `explicit_non_goals`, `paused_track_locks`,
`stop_conditions`, and `required_final_report` are list-valued. Path authority
entries require an explicit `exact`, `prefix`, or `glob` type and a normalized
repository-relative value; absolute paths and parent traversal are rejected.
`baseline_commit` and `input_commit` require full 40-character hexadecimal Git
object ids. Repository root and remote are identity fields, not path-authority
entries. Optional explanatory metadata may be added, but it cannot change or
override mandatory fields.

The header exists to make authority portable without assuming shared chat state.
Phase 38B may validate its schema and normalized paths before writes.
