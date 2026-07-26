# Agent Capability Intake

## Purpose and authority

This document defines Hive|Mind's vendor-neutral method for evaluating an
external agent or developer capability before it receives any project role. It
applies to agent skills, coding-agent extensions, CLI utilities,
repository-analysis tools, MCP servers, plugins, hooks, workflows, agent
harnesses, and external development automation.

An intake record is evidence for a human decision. It grants no execution,
repository, persistence, mutation, merge, or architectural authority. Existing
Hive|Mind contracts, Agent Lab governance, Git evidence, Repository Observer,
Active Memory, provenance, validation, authorization, and human review remain
authoritative.

Capability intake is a parallel, referential architecture track. It does not
gate or change Phase 40F–40K.

## Evidence discipline

Record every material claim with one of these evidence levels:

| Level | Meaning |
| --- | --- |
| `DOCUMENTED` | The canonical publisher documentation makes the claim. This is not proof of implementation or fitness. |
| `OBSERVED` | The evaluator directly inspected pinned source, tests, package metadata, or controlled execution and records exactly what was observed. |
| `INFERRED` | Evidence supports the conclusion, but it was not directly demonstrated. State the reasoning and uncertainty. |
| `UNSUPPORTED` | No adequate evidence was found. Do not rely on the claim. |

Marketing language is never upgraded above `DOCUMENTED` without independent
evidence. Record the evaluation date, because releases, dependencies, and
documentation drift. Pin a version and, when possible, an immutable commit.
Distinguish source inspection from runtime testing and describe the test
environment and inputs for any executed evaluation. Never use private Hive|Mind
content merely to test an external capability.

## Intake workflow

1. **Lock identity.** Record name, publisher/maintainer, canonical source and
   repository URL, evaluated version/tag/commit, evaluation date, and license.
   Verify release and source identity from primary sources.
2. **Describe the proposed use.** Name the narrow problem, intended operators,
   inputs, outputs, and explicit non-goals. Do not begin with an adoption
   presumption.
3. **Map execution and data flow.** Identify local and remote components,
   network calls, filesystem and repository reads/writes, subprocesses,
   configuration execution, environment access, generated artifacts, and every
   point where repository content or secrets could cross a boundary.
4. **Assess the supply chain.** Record installation mechanism and registry,
   direct and transitive dependency surface, lifecycle scripts, remote
   code/config behavior, update path, version/commit pinning, artifact
   verification options, and reproducibility limits.
5. **Compare with Hive|Mind.** Evaluate overlap and compatibility with Agent Lab
   contribution contracts, human review/merge gates, Repository Observer,
   Active Memory, provenance, future memory migration, and the future Create
   Layer. Identify both useful delegation and functionality Hive|Mind may
   eventually own.
6. **Model risk and controls.** Rate relevant hazards, specify mitigations, and
   state residual risk. A scanner or sandbox is a defense, not a guarantee.
7. **Test safely when justified.** Prefer a disposable environment, public or
   synthetic fixtures, no credentials, denied outbound access unless required,
   pinned artifacts, and captured commands/results. Testing is optional when
   source inspection is sufficient or execution risk is disproportionate.
8. **Classify once.** Assign exactly one primary classification and explain why.
   Record rejected mechanisms and a least-authority operating boundary.
9. **Review and expire.** Require human approval before adoption. Re-evaluate on
   material version, maintainer, license, dependency, permission, remote
   behavior, or intended-use changes. Give time-sensitive approvals a review
   date.

## Required assessment record

### Identity

- Capability/tool name and stable intake ID
- Canonical upstream source and repository URL
- Publisher/maintainer
- Version, tag, and immutable commit evaluated
- Evaluation date and evaluator
- License and any distribution constraints

### Execution boundary

For each item, record `none`, `read`, `write`, `execute`, or `unknown`, plus
scope and evidence:

- local execution and remote execution
- network access and destinations
- filesystem and repository read/write access
- subprocess execution
- configuration loading or execution
- environment-variable access
- secret exposure potential
- input, intermediate, output, cache, log, and telemetry locations

### Supply chain

- installation mechanism and package registries
- direct/transitive dependencies and lifecycle scripts
- remote code, configuration, model, or instruction behavior
- update mechanism and whether updates are automatic
- exact-version and commit/digest pinning capability
- lockfile, artifact-signing, checksum, and reproducibility considerations

### Hive|Mind compatibility

- overlap with existing capabilities and likely future ownership
- Agent Lab governance and contribution-contract compatibility
- human review and merge-gate compatibility
- Repository Observer relationship
- memory-migration and future Create Layer compatibility
- context-preparation value, provenance preservation, and limitation signaling
- whether the capability would bypass or silently redefine any contract

### Risk register

At minimum consider repository disclosure, secret disclosure, excessive context
exposure, untrusted configuration, arbitrary execution, dependency/supply-chain
exposure, context poisoning, stale external instructions, governance bypass,
accidental write authority, and non-deterministic behavior. For each applicable
risk record likelihood, impact, evidence, required control, residual risk, and
an owner. Unknowns are risks, not assurances.

### Classification

Assign exactly one:

- `REJECT` — unacceptable or unmitigable risk, authority conflict, or no
  legitimate fit.
- `REFERENCE` — useful knowledge or patterns only; do not execute or integrate.
- `AGENT_TOOL` — a bounded, subordinate tool an authorized human or agent may
  invoke under explicit controls.
- `FUTURE` — plausible fit, but evidence, architecture, or prerequisites are not
  ready.
- `ADOPT` — approved project capability with an owned integration and lifecycle.
  This requires stronger operational evidence than `AGENT_TOOL`.

The record must state the primary classification once, its reasoning, allowed
uses, prohibited uses, required controls, residual risks, and the authority
responsible for any later change.

## Decision gates

Reject or pause the intake when identity or license is unclear; an immutable
version cannot be selected; required access exceeds the proposed use; repository
content would be disclosed without explicit authorization; executable remote
configuration is trusted by default; secrets cannot be kept out of inputs and
artifacts; the tool would bypass contribution or merge controls; or claims
required for safe use remain unsupported.

An `AGENT_TOOL` or `ADOPT` decision should prefer: local-only processing,
explicit file allowlists, immutable version pins, no automatic updates, no
untrusted executable configuration, security checks kept enabled, generated
artifacts treated as sensitive and ephemeral, human inspection before sharing,
and independently reproducible commands and hashes.

## Candidate future `AgentCapability` fields

These are planning fields, not a schema or implementation:

`id`, `name`, `source`, `upstream_url`, `publisher`,
`evaluated_version`, `evaluated_commit`, `license`, `classification`,
`permissions`, `runtime_access`, `repository_access`, `network_access`,
`configuration_access`, `environment_access`, `security_risk`, `overlap`,
`contract_compatibility`, `governance_notes`, `allowed_uses`,
`prohibited_uses`, `required_controls`, `evidence`, `evaluation_status`,
`evaluated_at`, `review_after`, and `supersedes`.

Any future registry must preserve evidence provenance, distinguish a proposed
classification from an approved operating authorization, and fail closed when
an evaluation is stale. Phase 40E.6 implements no registry, contract, endpoint,
database, or UI.
