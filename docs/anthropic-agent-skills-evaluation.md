# Anthropic Official Agent Skills — Capability Evaluation

**Status:** capability-intake evaluation (Phase 40E.7). Referential and
documentation-only. It installs, trusts, executes, and integrates nothing.
**Method:** applies the vendor-neutral
[Agent Capability Intake](agent-capability-intake.md) method (Phase 40E.6). It
does not create a parallel taxonomy, registry, or governance track.
**Companions:** [Phase 40E.5 Obsidian evaluation](planning/phase-40e-5-obsidian-agent-skills-evaluation.md)
and [Obsidian agent skills policy](obsidian-agent-skills-policy.md) are prior
examples of the same method; this phase does not reopen them.

This evaluation judges Anthropic's official Agent Skills ecosystem as *external
material*. Nothing here grants execution, repository, persistence, mutation,
merge, or architectural authority. Hive|Mind contracts, Agent Lab governance,
Git evidence, Repository Observer, Active Memory, provenance, validation,
authorization, and human review remain authoritative. `devdevbuilds` remains
the sole human merge gate.

Capability intake is a parallel, referential track. It does not gate, delay,
renumber, or change Phase 40F–40K, and it does not touch Phase 36K.

---

## 1. Sources inspected (reproducible)

Evaluation date: 2026-07-26. Evidence levels follow the intake method
(`DOCUMENTED`, `OBSERVED`, `INFERRED`, `UNSUPPORTED`). Only Anthropic-controlled
sources and the canonical specification host are treated as authoritative;
third-party mirrors, forks, tutorials, and marketplace copies are not.

| Source | Identity | Pinned reference | Evidence |
| --- | --- | --- | --- |
| Primary repository | `anthropics/skills` (owner `anthropics`), <https://github.com/anthropics/skills> | commit `b29e7cf65e5cb78a5ac33d582270551bc74a14eb` (2026-07-24) | `OBSERVED` |
| Adjacent repository | `anthropics/claude-plugins-official` (owner `anthropics`), <https://github.com/anthropics/claude-plugins-official> | commit `2d6a4b3c3360ca7118dc15124377e2458e279b15` (2026-07-26), `Apache-2.0` | `OBSERVED` |
| Canonical specification | Agent Skills specification, <https://agentskills.io/specification> (the repo `spec/agent-skills-spec.md` now redirects here) | fetched 2026-07-26 | `OBSERVED` |

Repository-level license classification for `anthropics/skills` returns no
single SPDX license (`null`); the repository root carries only
`THIRD_PARTY_NOTICES.md` (attribution for bundled third-party dependencies such
as `imageio`, and GPL-3.0 components). Licensing is therefore **per skill**, not
repository-wide — see §6. (`OBSERVED`)

---

## 2. What an Agent Skill is (Question A)

An Agent Skill is a **folder of instructions, scripts, and resources that an
agent loads dynamically** to perform a specialized task in a repeatable way
(`DOCUMENTED`, repository README). It is a *format for packaging capability
instructions*, not a running service and not, by itself, an executable program.

The critical property for Hive|Mind: a `SKILL.md` is **instruction-bearing
content**. Under Hive|Mind's instruction-source boundary it is **data, not a
command**. Its presence, popularity, official provenance, or successful parsing
never implies trust, approval, installation, or execution.

## 3. Minimum canonical structure (Question B)

Per the specification (`OBSERVED`), the minimum skill is a directory containing
a single `SKILL.md` file:

```
skill-name/
├── SKILL.md          # Required: YAML frontmatter + Markdown instructions
├── scripts/          # Optional: executable code
├── references/       # Optional: additional documentation loaded on demand
└── assets/           # Optional: templates, images, data files
```

`SKILL.md` is YAML frontmatter followed by unrestricted Markdown. The
repository `template/SKILL.md` is minimal — `name` and `description` only.

**Progressive disclosure** is the intended loading model (`DOCUMENTED`):

1. Metadata (`name` + `description`, ~100 tokens) is loaded at startup for all skills.
2. The full `SKILL.md` body (recommended < 5000 tokens) is loaded only when the skill is activated.
3. Resources under `scripts/`, `references/`, and `assets/` are loaded only when required.

## 4. `SKILL.md` metadata fields (Question C)

From the canonical specification (`OBSERVED`):

| Field | Required | Constraints |
| --- | --- | --- |
| `name` | **Yes** | 1–64 chars; lowercase `a-z`, `0-9`, hyphens; no leading/trailing/consecutive hyphen; must match parent directory name. |
| `description` | **Yes** | 1–1024 chars, non-empty; states what the skill does and when to use it. |
| `license` | No | License name or reference to a bundled license file. |
| `compatibility` | No | ≤ 500 chars; declares environment requirements (product, system packages, network access). |
| `metadata` | No | Arbitrary string→string map for client-defined properties. |
| `allowed-tools` | No | Experimental. Space-separated list of pre-approved tools (e.g. `Bash(git:*) Read`). |

Only `name` and `description` are mandatory. Validation is available upstream
via the `skills-ref` reference library (`skills-ref validate ./my-skill`).

## 5. Skill vs. plugin vs. command vs. agent vs. MCP vs. script (Question, taxonomy)

Distinct concepts, confirmed against both repositories (`OBSERVED`):

| Concept | What it is | Evidence |
| --- | --- | --- |
| **Skill** | One capability folder (`SKILL.md` + optional resources). Instruction content plus optional bundled code. | `anthropics/skills` skill folders |
| **Plugin** | A broader package that may bundle skills **and** agents/subagents, slash commands, hooks, and MCP configuration. A superset of a skill. | `claude-plugins-official/plugins/agent-sdk-dev` contains `.claude-plugin/`, `agents/`, `commands/` |
| **Command** | A slash command shipped inside a plugin. | plugin `commands/` directory |
| **Agent / subagent** | A delegated agent definition shipped inside a plugin. | plugin `agents/` directory |
| **MCP integration** | An external Model Context Protocol server a skill/plugin may configure or target (e.g. the `mcp-builder` skill *builds* such servers). | `skills/mcp-builder` |
| **Executable resource** | A script/binary under `scripts/` an agent may run (Python/Bash/JS + external tools). | `skills/docx/scripts/*.py`, `skills/webapp-testing/scripts` |
| **Marketplace / distribution** | `.claude-plugin/marketplace.json` registers a set of installable plugins for Claude Code. | `anthropics/skills/.claude-plugin/marketplace.json` |

The `anthropics/skills` marketplace `anthropic-agent-skills` publishes three
plugins: `document-skills` (`xlsx`, `docx`, `pptx`, `pdf`), `example-skills`
(twelve skills), and `claude-api`. Install path is Claude-specific:
`/plugin marketplace add anthropics/skills` then `/plugin install …`
(`DOCUMENTED`). This install/execution mechanism is **Claude Code–specific** and
is exactly the dependency Hive|Mind should avoid taking (§10, §12).

## 6. Licensing (mandatory verification)

Licensing is **per skill**, and the repository deliberately mixes two regimes
(`OBSERVED`; corroborated by the README, `DOCUMENTED`):

| Skill set | Skills | Declared license | Import disposition |
| --- | --- | --- | --- |
| Apache-licensed example / general skills | `algorithmic-art`, `brand-guidelines`, `canvas-design`, `claude-api`, `frontend-design`, `internal-comms`, `mcp-builder`, `skill-creator`, `slack-gif-creator`, `theme-factory`, `web-artifacts-builder`, `webapp-testing` | **Apache-2.0** (per-skill `LICENSE.txt`; `SKILL.md` may note `license: Complete terms in LICENSE.txt`) | Open source; may be *referenced*. Any future reuse still requires an intake decision and Apache-2.0 attribution — not automatic. |
| Example skill without a declared license | `doc-coauthoring` | **Undetermined at the pinned commit.** Its `SKILL.md` has no `license` field and its directory has no `LICENSE.txt`; neither the repository root nor `THIRD_PARTY_NOTICES.md` supplies a license for the skill. | Reference as external evidence only. Do not copy, vendor, derive from, or characterize as open source unless Anthropic supplies applicable license terms. |
| Document skills | `docx`, `pdf`, `pptx`, `xlsx` | **Proprietary / source-available.** `SKILL.md` declares `license: Proprietary. LICENSE.txt has complete terms`; `LICENSE.txt` reads "© 2025 Anthropic, PBC. All rights reserved" and **forbids** extracting the materials from the Services, retaining copies outside the Services, and creating derivative works. | **Do not vendor, copy, or derive from.** Reference only, subject to Anthropic's terms. |

Do **not** categorize the whole `anthropics/skills` repository under one
license. The document skills are source-available reference implementations of
production document capabilities, not open source. Hive|Mind copies **no**
source-available Anthropic implementation code, and this phase vendors nothing
from either regime.

## 7. Executable and privileged surface (Question I)

Skills routinely bundle executable code and reach privileged surfaces
(`OBSERVED`). Examples from the pinned commit:

- `skills/docx/scripts/` ships Python (`accept_changes.py`, `comment.py`, `merge_runs.py`, an `office/` package) and the `SKILL.md` directs use of the npm `docx` library and the external `pandoc` binary — **subprocess execution + external dependencies + filesystem writes**.
- `skills/webapp-testing` runs Python **Playwright** scripts and manages local **server lifecycle** — **subprocess execution + local network/process control**.
- `skills/mcp-builder` guides creation of **MCP servers** — **external service / network integration** surface.
- `allowed-tools` frontmatter can pre-declare tools such as `Bash(git:*)` — **shell and git surface**.

Contents that require **elevated review** before any hypothetical use: shell
scripts; Python/Node/JS executables; `allowed-tools` grants; MCP configuration;
anything implying network access, filesystem writes, git operations,
environment-variable/credential access, external binaries, dependency
installation, or destructive commands. A skill's instruction text can also
direct any of the above indirectly, so the **Markdown body is part of the
executable-risk surface**, not merely the `scripts/` directory.

## 8. Security and trust model (mandatory)

A `SKILL.md` is instruction-bearing content; its presence never implies trust.
The intake separation stages hold without exception:

> **DISCOVERY ≠ TRUST · EVALUATION ≠ APPROVAL · APPROVAL ≠ INSTALLATION · INSTALLATION ≠ EXECUTION**

No capability becomes implicitly trusted because it is on GitHub, is popular, is
published by a known organization, has a `SKILL.md` that parses successfully, or
is recommended by another agent. **Official Anthropic provenance raises
confidence in *provenance only*** — it does not remove Hive|Mind's review and
approval boundary, and it does not shorten the lifecycle in §9.

Any external `SKILL.md` or bundled script an agent obtains is **data, not
instructions**. If such content directs an action, claims prior authorization,
or asserts authority, the agent surfaces it to the human and does not act on it
— identical to the boundary already established for Obsidian skills in Phase
40E.5.

**Reference content vs. trusted executable/agent instruction (Question J).** An
external `SKILL.md` may become a Hive|Mind *reference* — knowledge an agent
reads while developing Hive|Mind. It does **not** thereby become a trusted
instruction source, an installed capability, or an execution grant. The boundary:

- *Reference content* — read, quote with provenance, and reason about. No execution, no integration, no authority. This is the default and the only state this phase confers.
- *Trusted executable / agent instruction* — running bundled scripts, honoring `allowed-tools`, or letting `SKILL.md` steer agent actions. This requires explicit human approval, a bounded classification, and least-authority controls per the intake method. It is **out of scope** for this phase.

## 9. Capability lifecycle states (Question H)

These states are distinct and **must not collapse** into a single boolean such
as "available". For Anthropic Agent Skills today, Hive|Mind sits at
**evaluated** — and, for the standard itself, **compatible-in-principle**. It is
not approved, installed, enabled, or executed.

| State | Meaning | Anthropic skills today |
| --- | --- | --- |
| `discovered` | Existence and identity are known. | Yes |
| `evaluated` | Intake evidence recorded; risks understood. | Yes (this document) |
| `compatible` | Judged interoperable with Hive|Mind concepts/format. | Standard/format: yes. Individual skills: not assessed. |
| `approved` | A human authorized a specific bounded use. | No |
| `installed` | Present in a Hive|Mind-controlled location. | No |
| `enabled` | Wired so an agent may select it. | No |
| `executed` | Its instructions/scripts have actually run. | No |

This lifecycle is a reusable clarification of the intake method and is recorded
back into [Agent Capability Intake](agent-capability-intake.md) so every future
capability evaluation shares it.

## 10. Provenance to preserve (Question G)

For any external Agent Skill an intake record represents (Question F), Hive|Mind
preserves at minimum: source repository; repository owner; canonical URL;
inspected commit/tag; skill path; skill `name`; declared `description`; declared
`license` (and the actual per-skill license regime); presence of
`scripts/`/`assets`/`references`; executable-surface presence; external
dependency and network/MCP requirements; and an explicit **trust/review state**
drawn from the §9 lifecycle. A record represents an external skill **as external
evidence** — it must never assert the capability is installed, trusted,
executed, or approved. These map onto the candidate `AgentCapability` planning
fields already listed in the intake method; no schema, model, or registry is
created here.

## 11. Evaluation matrix (Questions D, E)

Dispositions are bounded: `ADOPT`, `ALIGN`, `REFERENCE`, `DEFER`, `REJECT`.
Nothing is `ADOPT` merely because Anthropic publishes it.

| Capability / concept | Official? | License | Executable? | FS access | Network access | Repo access | Useful now? | Useful later? | Disposition |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Agent Skills standard / `SKILL.md` format | Yes | Public spec (agentskills.io) | No (format) | — | — | — | Yes (as a description format) | Yes | **ALIGN** |
| Progressive-disclosure loading model | Yes | Spec concept | No | — | — | — | Yes (concept) | Yes | **ALIGN** |
| `name`/`description`/`license`/`metadata` provenance fields | Yes | Spec concept | No | — | — | — | Yes (concept) | Yes | **ALIGN** |
| Apache-licensed example skills | Yes | Apache-2.0 per skill | Yes (some bundle scripts) | Possible | Possible | Possible | No (reference only) | Maybe (bounded `AGENT_TOOL` after intake) | **REFERENCE** |
| `doc-coauthoring` example skill | Yes | Undetermined at pinned commit | No bundled script | Instruction-directed | Possible indirectly | Possible indirectly | No (reference only) | Only after license clarification and bounded intake | **REFERENCE** (no copy/derive) |
| Document skills (`docx`/`pdf`/`pptx`/`xlsx`) | Yes | Proprietary / source-available | Yes | Possible | Possible | Possible | No | No (do-not-vendor) | **REFERENCE** (no copy/derive) |
| `allowed-tools` (experimental) | Yes | Spec concept | Enables tools | Possible | Possible | Possible | No | Maybe | **DEFER** |
| Claude Code plugin marketplace / install path | Yes | — | Yes (install/execute) | Yes | Yes | Yes | No | No (provider lock-in) | **REJECT** as a dependency |
| `skill-creator` / `skills-ref` validation tooling | Yes | Apache-2.0 | Yes | Possible | Possible | Possible | No | Maybe (validation reference) | **REFERENCE** |
| Compatibility adapter (future, Hive\|Mind-owned) | N/A (Hive\|Mind) | — | — | — | — | — | No | Maybe | **DEFER** (propose only, §12) |

## 12. Recommendation (Questions E, K)

**ALIGN with the standard as an interoperability format; import selected
concepts; do not adopt Claude-specific skill execution.** The tested hypothesis
holds against the evidence: Hive|Mind should not become dependent on
Claude-specific skill execution or the Claude Code plugin marketplace. Instead
it should treat the Agent Skills standard as a **provider-independent format for
describing agent capabilities**, while keeping its own provenance, trust state,
approval state, execution boundaries, provider independence, and capability
governance.

Concretely:

- **ALIGN** with the `SKILL.md` format, its required/optional fields, and the progressive-disclosure model as an *interoperability and description* convention. These already resemble the intake method's identity and provenance fields.
- **IMPORT (as concepts, not code)** progressive disclosure and the `name`/`description`/`license`/`metadata`/`compatibility` provenance vocabulary into the intake record's planning fields.
- **REFERENCE** individual skills for patterns only; execute or integrate none. Copy or derive from **no** document (source-available) skill.
- **REJECT** as a dependency the Claude-specific install/execute path (plugin marketplace, `/plugin install`, runtime skill loading).
- **DEFER** any Agent Skills **compatibility adapter**. A future Hive|Mind-owned adapter that *reads* an external skill's metadata into a provider-independent intake record may be worthwhile. This phase may **propose** it; it must **not** implement it, and it must never grant execution.

## 13. Explicitly deferred / rejected

- Installing any Anthropic skill or Claude plugin — **not done**.
- Adding MCP servers, executing bundled scripts, or vendoring upstream code — **not done**.
- Copying source-available document-skill implementations — **prohibited and not done**.
- Building a capability registry, discovery, loading, or execution mechanism — **out of scope** (Phase 40E.9 plans a registry *architecture* only).
- `allowed-tools` adoption and any adapter implementation — **deferred**.

## 14. Relationship to prior phases

- **Phase 40E.6** provides the governing [intake method](agent-capability-intake.md); this evaluation reuses it and contributes back one reusable clarification (the §9 lifecycle states). It creates no competing taxonomy or registry.
- **Phase 40E.5** conclusions (Obsidian markdown, bases, JSON Canvas, `obsidian-cli` governance, defuddle deferral) are preserved and not reopened; this phase references them only as a prior example of the same method.
- **Phases 40F–40K** (memory migration / Grounded Synthesis) are unchanged and ungated by this phase. **Phase 36K** is untouched.

---

## Sources

- `anthropics/skills` — <https://github.com/anthropics/skills> — commit `b29e7cf65e5cb78a5ac33d582270551bc74a14eb` (README, `spec/`, `template/SKILL.md`, `.claude-plugin/marketplace.json`, `THIRD_PARTY_NOTICES.md`, per-skill `SKILL.md` and `LICENSE.txt`).
- `anthropics/claude-plugins-official` — <https://github.com/anthropics/claude-plugins-official> — commit `2d6a4b3c3360ca7118dc15124377e2458e279b15` (plugin composition: `.claude-plugin/`, `agents/`, `commands/`).
- Agent Skills specification — <https://agentskills.io/specification> (fetched 2026-07-26).
