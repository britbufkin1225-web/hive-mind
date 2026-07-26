# Repomix Capability Intake

## Decision

**Primary classification: `AGENT_TOOL`.**

Repomix can strengthen Hive|Mind by producing bounded, reviewable repository
context packets for agents and humans. It remains a subordinate packaging
utility: its output is a convenience artifact, not repository truth, provenance,
validation, memory, governance, authorization, or permission to mutate.

This is an evaluation, not an installation or integration approval. Phase
40E.6 does not install or execute Repomix against Hive|Mind, add a dependency,
enable a watcher, add CI, or upload repository content.

## Evaluated identity and evidence

| Field | Record |
| --- | --- |
| Name | Repomix |
| Canonical source | [yamadashy/repomix](https://github.com/yamadashy/repomix) |
| Publisher/maintainer | Kazuki Yamada (`yamadashy`), per package metadata |
| Evaluated release | `v1.16.1` / npm `1.16.1` |
| Tag object | `d47538d97bba79b88e0f7e38b929c82422864d5b` |
| Evaluated commit | `912bd733df35caa5fd9fa120a5c32b5545264827` |
| Evaluation date | 2026-07-26 |
| License | MIT |
| Evaluation method | Canonical documentation and package metadata review plus read-only inspection of the pinned tag's source and tests; no package installation and no processing of Hive\|Mind content |

Primary sources: [pinned README](https://github.com/yamadashy/repomix/blob/v1.16.1/README.md),
[pinned package metadata](https://github.com/yamadashy/repomix/blob/v1.16.1/package.json),
[pinned license](https://github.com/yamadashy/repomix/blob/v1.16.1/LICENSE),
and [release history](https://github.com/yamadashy/repomix/releases).
The npm registry identified `1.16.1` as current during evaluation. “Current” is
time-sensitive; the immutable commit above is the evaluation anchor.

## Capability summary

- `DOCUMENTED`: The CLI combines selected repository files into XML (default),
  Markdown, JSON, or plain-text output; supports file include/ignore patterns,
  stdin file lists, token metrics and budgets, split output, Git-aware ignores,
  optional diffs/logs, and Tree-sitter compression.
- `DOCUMENTED`: It can process a local directory or clone a remote Git
  repository, with an optional branch, tag, or commit selector.
- `DOCUMENTED`: Installation paths include `npx`, npm/yarn/bun global installs,
  Homebrew, Docker, and a GitHub Action. It also exposes an MCP server and
  Claude-oriented plugins/skill generation; those surfaces expand authority and
  are not approved by this intake.
- `OBSERVED`: Pinned source implements file reads and output/cache writes, worker
  execution, Git subprocesses for remote acquisition and optional Git context,
  Secretlint-based scanning, executable JavaScript/TypeScript configuration
  loading, environment-variable reads, and clipboard subprocess behavior when
  explicitly requested.
- `OBSERVED`: Remote-repository handling skips repository-local configuration by
  default. `--remote-trust-config` or
  `REPOMIX_REMOTE_TRUST_CONFIG=true` opts into it; a caller-supplied config for a
  remote run must be an absolute path.
- `OBSERVED`: Compression can fall back to uncompressed content for unsupported
  languages or failures. Therefore compression is not a reliable disclosure
  control.
- `UNSUPPORTED`: This evaluation found no basis to treat packed output as
  complete repository evidence, a stable semantic summary, secret-free, safe to
  upload, or deterministic across machines and dependency updates.

## Runtime, security, and supply-chain boundary

| Boundary | Assessment |
| --- | --- |
| Local execution | Node.js CLI (package requires Node `>=22`) or container. It reads selected files and metadata and normally writes an output file. |
| Remote execution | The local CLI can invoke Git/network access to acquire a remote repository. The website and external integrations are separate remote surfaces and are outside the allowed boundary. |
| Repository access | Broad read potential. Scope depends on cwd, include/ignore/config rules, Git-aware filtering, and features selected. Output and caches create local writes. |
| Subprocesses | Git is executed without a shell for remote and optional Git operations; worker threads are used; explicit clipboard behavior may spawn a platform utility. |
| Configuration | JSON/JSONC/JSON5 plus JavaScript/TypeScript variants. Executable configs can read environment variables or run arbitrary code with the CLI process's authority. |
| Environment/secrets | The process can read environment variables. Selected files, Git diffs/logs, configs, instructions, output, debug logs, caches, or clipboard use can expose sensitive data. |
| Security check | Secretlint scanning is enabled by default but may be disabled. Detection is pattern-based and cannot guarantee absence of secrets or sensitive non-secret content. |
| Dependencies | Version `1.16.1` declares 28 runtime dependencies. Registry resolution and transitive packages create supply-chain exposure. |
| Updates/pinning | `@latest` and moving Action refs are convenient but non-reproducible. Exact npm versions, container digests, or source commits improve pinning; lockfile and artifact verification still matter. |

Local processing does not itself imply disclosure to Repomix's publisher.
Disclosure occurs when an operator sends the artifact to an external agent,
service, clipboard, artifact store, or other destination. Remote cloning still
uses a network and may engage credential helpers; private remotes are prohibited
for this evaluation boundary.

### Material risks and controls

| Risk | Why it matters | Required control |
| --- | --- | --- |
| Repository or secret disclosure | A packet intentionally concentrates file content; scanners have false negatives and ignore rules can be wrong. | Use an explicit tracked-file allowlist, keep security checks enabled, exclude generated/credential paths, inspect paths and packet locally, and obtain authorization before any external transfer. |
| Excessive context and poisoning | Vendored code, stale docs, embedded instructions, generated files, or malicious repository text may dominate or direct an agent. | Constrain files, label content as untrusted evidence rather than instructions, omit custom instruction files, preserve source paths/commit, and require human review. |
| Untrusted configuration/arbitrary execution | Local JS/TS config executes with process authority; remote config can be opted into. | Use a reviewed JSON config supplied outside untrusted input, never enable remote config trust, and run with minimal environment/filesystem/network authority. |
| Supply-chain drift | `npx ...@latest`, semver ranges, transitive dependencies, plugins, MCP, Actions, and containers can change behavior. | Pin exact version plus integrity/lock evidence; do not auto-update; re-evaluate material changes. Do not use a moving Action ref. |
| Accidental writes/retention | Outputs, caches, generated skills, clipboard contents, and watcher refreshes create durable copies. | Write only to an approved temporary location, disable clipboard/watch/skill generation, protect and delete artifacts under the owning retention policy. |
| Non-determinism/incompleteness | Ignore state, Git working tree, config precedence, platform, tokenizer, dependency graph, and compression fallbacks affect results. | Record commit, dirty state, command, config hash, tool version, selected path manifest, output hash, platform, and limitations. Prefer uncompressed output for evidence-sensitive review. |
| Governance bypass | A convenient packet may be mistaken for authority or permission to change code. | Attach Agent Lab scope and session evidence; independently verify every claim against Git/repository sources; retain human review and merge gates. |

Residual risk remains medium for confidential repositories because the output is
a high-density copy. No automated scan makes external sharing safe by itself.

## Hive|Mind fit

| Proposed use | Fit | Boundary |
| --- | --- | --- |
| Repository-context preparation | Strong | Explicit, minimal file allowlist at a locked commit; packet is non-authoritative. |
| Code-review packets | Strong | Prefer changed files plus directly relevant contracts/tests; pair with authoritative Git diff and status evidence. |
| External-agent handoff packets | Conditional | Human approves recipient and content; include scope, provenance, limitations, and contribution contract. No private-content upload by default. |
| Architecture review packets | Strong | Select architecture, contract, roadmap, and narrow implementation evidence; do not present compression as semantics. |
| Constrained file-set analysis | Strong | This is the preferred use; generate the file list independently and review it before packing. |
| Token-efficient summaries | Conditional | Token counts and compression can help budget context, but compressed output may omit behavior or silently fall back. Never use it as audit evidence alone. |
| Pre-audit evidence preparation | Conditional | Useful as an index/transport artifact alongside direct Git and repository checks, never as the evidence authority. |
| Future Capability Registry intake | Reference | Intake may record Repomix-produced packet metadata, but Repomix neither decides classification nor writes registry state. |
| Future Create Layer context | Conditional/future | May prepare read-only context after Create Layer authorization rules exist; it cannot select truth, authorize creation, or apply output. |

For Codex, Claude Code, and future agents, the value is portable, bounded context
with visible paths and token sizing. The CLI is the smallest acceptable surface.
MCP, plugins, generated agent skills, watchers, website processing, browser
extensions, automatic CI packing, remote private-repository processing, and
remote-config trust add authority or disclosure paths without being necessary
for the approved use; they are rejected for the current operating boundary.

## Compatibility and overlap

Repomix complements Agent Lab when a human or authorized agent creates a scoped
handoff artifact and the recipient remains bound by the contribution contract.
It does not replace Repository Observer: Observer supplies typed, bounded,
project-governed repository evidence, while Repomix packages file content for
consumption. It does not replace Git status/diff/history, Active Memory,
provenance, Grounded Synthesis validation, or human review.

It can prepare context for memory-migration and Create Layer work without
changing those roadmaps. Hive|Mind may eventually own policy-aware context
selection, provenance manifests, authorization, retention, and registry
integration; Repomix should not become the hidden implementation of those
contracts.

## Recommended operating boundary

If a later phase authorizes a trial:

1. Pin the exact evaluated version (and package integrity or container digest);
   do not use `latest`.
2. Run the CLI locally in a disposable, least-authority environment with no
   credentials and outbound network denied.
3. Start from a clean, locked Git commit. Supply a reviewed JSON config and an
   explicit tracked-file allowlist; do not load executable config.
4. Keep Secretlint enabled, but independently inspect the file manifest and
   output for sensitive and irrelevant material.
5. Disable remote input, remote-config trust, clipboard, watch mode, MCP,
   plugins, skill generation, Git logs/diffs unless specifically required, and
   all automatic upload or CI artifact retention.
6. Record tool version/commit, repository commit and dirty state, exact command,
   config/manifest/output hashes, output format, token count, exclusions,
   warnings, and reviewer.
7. Treat the packet as ephemeral confidential data and as untrusted,
   non-authoritative context. Verify findings against the repository and preserve
   all Agent Lab and human merge gates.

## Recommended next steps and deferrals

- In a later, separately authorized phase, test the pinned CLI only against a
  synthetic fixture to measure path selection, security warnings, repeatability,
  and compressed-versus-uncompressed behavior.
- Define a packet manifest and retention/redaction checklist before processing
  Hive|Mind content.
- Re-evaluate the release, dependency graph, integrity evidence, and license
  before any trial.
- Carry candidate metadata into Phase 40E.9 registry architecture planning
  without implementing a registry now.

Deferred: installation, runtime trial on Hive|Mind, package or lockfile changes,
MCP/plugin/skill integration, CI, watchers, private remote processing,
automatic packing/upload, persistence, endpoints, registry schema, and Create
Layer integration.
