# Agent Composition Manifest

Complete one manifest for each contribution. Empty lists are explicit evidence;
unknown facts must not be converted to favorable Boolean values.

```yaml
manifest_version: agent-composition.v1
contract_version: agent-contribution.v1
project:
  name: Hive|Mind
  parent_label: devdevbuilds
  repository_root: C:/canonical/repository
  remote_url: https://example.com/owner/repository.git
phase:
  id: Phase 00
  name: Example
  status_at_start: Planned
  status_at_end: Implemented locally
  paused_tracks: []
agent:
  name: example-agent
  assigned_role: primary-implementer
  capability_level: L2
  composition_mode: sequential-isolated
authority:
  write_authority: bounded-path-write
  owned_paths: []
  read_only_paths: []
  forbidden_paths: []
git:
  expected_baseline: 0000000000000000000000000000000000000000
  actual_baseline: 0000000000000000000000000000000000000000
  merge_base: 0000000000000000000000000000000000000000
  working_branch: phase-00-example
  input_commit: 0000000000000000000000000000000000000000
  output_commit: 0000000000000000000000000000000000000000
  earlier_commits_preserved: true
  destructive_operations_used: false
contribution:
  objective: Example objective
  summary: Example summary
  changed_files: []
  added_files: []
  deleted_files: []
  renamed_files: []
  diff_statistics:
    files_changed: 0
    insertions: 0
    deletions: 0
  scope_deviations: []
validation:
  commands: []
  outcomes: []
  tests_not_run: []
  evidence_limitations: []
reporting:
  assumptions: []
  known_limitations: []
  blockers: []
handoff:
  recommended_next_actor: human-project-owner
  recommended_next_role: independent-auditor-hardener
  required_follow_up: []
  safe_to_compose: false
  safe_to_push: false
  safe_to_open_pr: false
  independently_audited: false
  hardened: false
  pushed: false
  pr_opened: false
  merged: false
  local_main_normalized: false
  working_tree_clean: true
```

Each validation outcome is exactly `PASS`, `FAIL`, `NOT RUN`, `BLOCKED`, or
`NOT APPLICABLE`, paired with its exact command or check. No self-audit may set
`independently_audited: true`.

## Composition acceptance checklist

- Header, manifest, repository identity, baseline, input/output commits, and
  provenance agree with direct Git evidence.
- Changed, added, deleted, and renamed paths satisfy typed ownership rules;
  forbidden paths override ownership and rename endpoints are both authorized.
- Required validations passed or have an honestly accepted non-pass outcome.
- Earlier commits are preserved and implementation/hardening commits are separate.
- Paused tracks and non-goals remain untouched; deviations have human approval.

`safe_to_compose` requires all acceptance checks and a declared integration
order. `safe_to_push` additionally requires a clean contribution tree and human
authorization for the push workflow. `safe_to_open_pr` additionally requires
the expected remote branch and intended base to be verified. None implies safe
to merge.

Independent audit is required before merge-ready status. Hardening is separate
when defects are found. After approved merge, final normalization requires local
`main` to fast-forward to `origin/main`, removal of no branches unless separately
authorized, and WTC verification by the human owner. These gates prevent
composition convenience from erasing provenance or overstating completion.

Phase 38B may generate and validate this manifest, but it must not infer missing
evidence, perform repairs, or make human-only decisions.
