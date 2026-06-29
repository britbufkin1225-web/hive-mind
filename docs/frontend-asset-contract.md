# Hive&#124;Mind Frontend Asset Contract

Parent label: **devdevbuilds**

**Status: active (planning / documentation only).** This document defines how
approved visual assets — icons, marks, logos, badges, SVGs, and image/screenshot
evidence — may be used in the Hive&#124;Mind frontend going forward. It is a
**contract, not an implementation**: it adds no asset, no CSS, no markup, no
dependency, and changes no application behavior. It is written **before** the next
icon/asset implementation pass so that work has explicit rules to follow.

- **Phase name:** Phase 25B.5 — Frontend Asset Contract + Icon Usage Planning
- **Date:** 2026-06-28
- **Branch:** `phase-25b5-frontend-asset-contract-icon-usage-planning`
- **Repo:** `hive-mind` (Hive&#124;Mind under devdevbuilds)
- **Successor to:** [Phase 25A Premium Visual Design System / Frontend Presentation Direction](ui/phase-25a-premium-visual-system-planning.md)
  and the merged Phase 25B premium visual system frontend pass.

> **Authenticity rule (carried from Phase 20A/21D/24A/25A).** Every asset choice
> below must keep the UI an honest reflection of real, deterministic, read-only app
> behavior. A premium look improves how the *implemented* product reads; assets
> never imply AI, automation, persistence, multi-user, production hosting, or
> third-party integrations that do not exist. An icon is a label for a real surface,
> not decoration that fakes capability.

---

## Why this contract exists (before deeper UI asset implementation)

Phase 25A defined the dark-metallic intelligence-console visual identity and Phase
25B applied it as a token-driven reskin. The next natural step is visual
asset work — a favicon, an app mark, status/section icons, badges. That is exactly
the point where a portfolio-visible developer tool tends to accumulate **mismatched,
unattributed, or auto-generated assets**: a Lucide icon here, a random emoji there, a
stock SVG with the wrong stroke weight, a logo that drifts from the parent brand.
Each looks fine alone; together they read as noise and quietly undercut the "premium,
intentional" story the visual system is trying to tell.

A contract prevents that by making three things explicit **before** the first asset
lands:

1. **One source of authority.** Assets come from the approved devdevbuilds /
   Hive&#124;Mind lockup, not from ad-hoc downloads, icon libraries, or generation.
2. **One place they live and one way they are named**, so review and replacement are
   mechanical, not archaeological.
3. **One set of theming/accessibility/honesty rules**, so every asset reads
   correctly on the dark metallic surfaces and never misrepresents the product.

For a portfolio-visible dev tool the asset layer *is* part of the credibility
argument: consistent, attributable, accessible assets signal the same discipline the
rest of the codebase claims. This document is that discipline written down.

---

## 1. Current asset inventory (audit of existing repo files)

This inventory is based **only** on files already in the repository at the time of
writing. No assets were added, moved, or modified to produce it.

### 1.1 Static image assets

| File | Role | Notes |
| --- | --- | --- |
| `docs/assets/branding/hivemind-readme-banner.png` | devdevbuilds-approved README banner / brand lockup | The single approved brand image asset. Referenced by [README.md](../README.md) only. Treated here as the **brand authority reference**, not a frontend UI asset. |

### 1.2 Screenshot / demo evidence assets

| Location | Role |
| --- | --- |
| `docs/demo/screenshots/phase-20d-*` … `phase-23b-*` (`*.png`) | Honest, captured runtime evidence of the connected dashboard across phases. **Evidence, not UI assets** — they are never imported into the running app. |

### 1.3 Frontend application assets

- **No** favicon, app logo, app mark, badge, or `<img>` element exists in
  `apps/frontend/`.
- **No** static `.svg`, `.png`, `.ico`, or other asset file is shipped from the
  frontend (no `public/` asset directory; `apps/frontend/index.html` declares no
  `<link rel="icon">`).
- The **only** SVG in the running app is the **inline, data-driven** Knowledge Graph
  visualization in `apps/frontend/src/components/KnowledgeGraphPanel.tsx` (it renders
  nodes/edges from the backend view model, carries `role="group"` +
  `aria-label="Knowledge graph visualization"`, and is styled by tokenized CSS
  classes). This is **rendered output, not a stored asset**, and is explicitly **out
  of scope** for this contract (it is governed by the Phase 25A graph visual-language
  rules and the read-only graph boundary).

### 1.4 Existing asset governance

- There is **no** pre-existing frontend asset contract, icon registry, or asset usage
  documentation in the repo. **This document is the first.**
- The closest existing governance is the README banner reference (brand authority) and
  the Phase 25A/25B visual system (theming authority). This contract sits between
  them: it governs *what asset files may exist and how they are used*, deferring
  *how they are colored/elevated* to the token system.

**Audit conclusion.** Hive&#124;Mind currently ships **zero** frontend image/icon
asset files. That is a clean baseline: this contract governs the *first* such asset
rather than retrofitting rules onto an existing mess.

---

## 2. Approved asset source authority

There is exactly one authority chain for Hive&#124;Mind frontend assets:

1. **devdevbuilds parent brand system** — the approved devdevbuilds asset lockup and
   usage rules are the **top-level authority**. Hive&#124;Mind is a product/app *under*
   devdevbuilds and must not contradict or fork the parent lockup.
2. **The approved Hive&#124;Mind lockup** — the product-level marks derived from and
   consistent with the parent system. The committed
   `docs/assets/branding/hivemind-readme-banner.png` is the current reference point
   for the approved Hive&#124;Mind visual lockup.
3. **This contract** — governs how assets from (1)/(2) are placed, named, themed, and
   referenced inside `apps/frontend/`.

An asset is **approved** only if it traces to (1) or (2) and satisfies this contract.
Anything else is **unapproved** until a human review (the devdevbuilds merge gate)
says otherwise. "I found a nice icon" is not an approval path.

---

## 3. Allowed asset categories

The following categories *may* be introduced by a future, separately-authorized
implementation phase, provided each asset traces to the source authority (§2) and
follows the location (§5), naming (§6), safety (§7), accessibility (§8), and theming
(§9) rules:

- **App marks / logos** — the Hive&#124;Mind product mark and any devdevbuilds parent
  mark, used for identity (header lockup, favicon, app icon). Governed by §10.
- **Functional UI icons** — small glyphs that label a real surface or action already
  present in the app (e.g. a graph icon next to the Knowledge Graph heading, a console
  glyph next to the Console). Governed by §10.
- **Status / state icons** — glyphs that reflect a **real** read-only state the app
  already computes (connected/disconnected, read-only mode, empty state). Governed by
  §9.5.
- **Badges** — small static marks for honest facts only (e.g. "local-first",
  "read-only"). Never production/uptime/deploy/SaaS badges (see §11 and Phase 25A
  non-goals).
- **Brand/banner imagery** — documentation banners and README lockups (the existing
  `hivemind-readme-banner.png` category).
- **Screenshot / demo evidence** — honest captured runtime screenshots used as
  evidence in docs. Governed by §12.

If a desired asset does not fit one of these categories, it is out of scope until the
contract is extended.

---

## 4. Forbidden before approval

The following are **forbidden** unless and until a human review explicitly authorizes
them in a future phase. This list is enforceable — a reviewer can reject a PR on any
single item.

- **No icon-library dependency.** Do **not** add Lucide, Font Awesome, Heroicons,
  React Icons, Material Icons, Tabler, Phosphor, or any other icon package, font, or
  CDN. (Reaffirms the Phase 25A "no icon package / no dependency" non-goal.)
- **No external CDN or remote asset references.** No `<img src="https://…">`, no
  `@import url(https://…)`, no remote SVG sprite. Assets are local, committed, and
  reviewable.
- **No generated / AI-generated / random assets.** No model-generated logos, icons, or
  textures; no "placeholder until we find a real one" art. An asset that cannot be
  traced to the approved lockup does not ship.
- **No screenshot-derived UI assets.** Demo screenshots and generated images must
  **not** be cropped, traced, or converted into app icons, marks, textures, or
  backgrounds.
- **No emoji-as-icon** in product chrome where a real mark is expected (emoji are
  inconsistent cross-platform and read as unpolished in a premium console). Existing
  textual/emoji affordances are not in scope to change here.
- **No unverified third-party SVGs.** No copy-pasted SVG from an unknown source, and no
  SVG containing scripts, external references, or tracking (see §7).
- **No fabricated/aspirational marks** — no integration logos, partner badges, award
  badges, or "as seen on" marks for relationships that do not exist.
- **No favicon/app-icon churn** outside an authorized implementation phase. The first
  favicon is itself an asset that must clear this contract.

---

## 5. File location conventions

When a future phase adds frontend assets, they live in **one** predictable place so
review and replacement are mechanical.

- **Frontend UI assets** (favicon, app mark, functional/status icons used by the
  running app) live under a single frontend asset root:
  `apps/frontend/src/assets/` (preferred, so the bundler can hash and tree-shake), or
  `apps/frontend/public/` for assets that must be served at a fixed path (e.g.
  `favicon.svg`). A future phase picks one root per asset type and stays consistent;
  it does **not** scatter assets next to arbitrary components.
- **Brand / lockup reference assets** stay under `docs/assets/branding/` (where
  `hivemind-readme-banner.png` already lives). Documentation references the brand from
  here; the running app does not reach into `docs/`.
- **Screenshot / demo evidence** stays under `docs/demo/screenshots/` (the existing
  convention). Evidence never moves into the frontend asset roots.
- **One asset, one home.** No duplicate copies of the same mark across roots; docs and
  app reference by path rather than cloning files.

> These are *target* conventions for future work. This phase creates **no** directory
> and moves **no** file. `apps/frontend/src/assets/` does not yet exist and must not be
> created until an implementation phase needs it.

---

## 6. Naming conventions

All asset filenames are **lowercase kebab-case**, descriptive, and namespaced by role.
No spaces, no uppercase, no version/date suffixes baked into the canonical name, no
generic names (`icon.svg`, `logo2-final.png`).

| Asset type | Pattern | Example |
| --- | --- | --- |
| Product app mark | `hivemind-mark[-variant].svg` | `hivemind-mark.svg`, `hivemind-mark-mono.svg` |
| Parent brand mark | `devdevbuilds-mark[-variant].svg` | `devdevbuilds-mark.svg` |
| Favicon | `favicon.svg` / `favicon.ico` | `favicon.svg` |
| Functional UI icon | `icon-<concept>.svg` | `icon-graph.svg`, `icon-console.svg`, `icon-source.svg` |
| Status icon | `status-<state>.svg` | `status-connected.svg`, `status-readonly.svg` |
| Badge | `badge-<fact>.svg` | `badge-local-first.svg` |
| Brand/banner image | `hivemind-<context>-banner.<ext>` | `hivemind-readme-banner.png` (existing) |
| Screenshot evidence | `phase-<id>-<surface>.png` | `phase-23b-connected-knowledge-graph.png` (existing) |

Rules:

- **`<concept>` describes the real surface/action**, not the visual shape
  (`icon-graph.svg`, not `icon-circle.svg`).
- **Variants are explicit suffixes** (`-mono`, `-duotone`, `-sm`), never separate
  undocumented files.
- **Theme is expressed via CSS/`currentColor`, not the filename.** Avoid
  `icon-graph-dark.svg` / `icon-graph-light.svg` when one tokenized monochrome asset
  can serve both (see §9).

---

## 7. SVG / icon safety expectations

SVG is the preferred format for marks and icons (crisp, themeable, tiny). Every SVG
that enters the repo must be **clean and inert**:

- **No scripts or interactivity** — no `<script>`, no `on*` event attributes, no
  `<foreignObject>`, no embedded JS.
- **No external references** — no remote `xlink:href` / `href` to off-repo URLs, no
  embedded tracking pixels, no remote fonts. Assets are fully self-contained.
- **No embedded raster bloat** — no base64-embedded PNGs masquerading as SVG.
- **Minimized and reviewed** — stripped of editor metadata (Illustrator/Figma cruft,
  comments, hidden layers) so the committed file is small and a human can read the diff.
- **A defined `viewBox`** and no hardcoded pixel `width`/`height` that fights CSS
  sizing; icons scale from CSS.
- **Single-purpose `id`s** scoped to avoid collisions if multiple inline SVGs share a
  document (mirrors the existing `graph-arrow` marker pattern in `KnowledgeGraphPanel`).

Raster assets (PNG/ICO) are allowed for brand banners and favicons where SVG is
impractical, but must be appropriately sized/compressed and never used where a
themeable SVG would serve.

---

## 8. Accessibility expectations

Assets must not degrade accessibility on a console UI that already practices it (the
inline graph SVG already ships `role`/`aria-label`, the nav already ships a skip link
and `aria-current`).

- **Meaningful images get text alternatives.** Brand/banner `<img>` carry a descriptive
  `alt`; meaningful inline SVGs carry `role="img"` + `aria-label` (or `<title>`).
- **Decorative assets are hidden from assistive tech** — `alt=""` for decorative
  `<img>`, `aria-hidden="true"` (and/or `focusable="false"`) for purely decorative
  inline SVGs, so screen readers are not spammed.
- **Icon-only controls must still have an accessible name** — an icon button without
  visible text needs `aria-label` (or visually-hidden text). An icon never becomes the
  *only* way to understand a control.
- **Icons reinforce, they don't replace, text** for status — color/glyph is paired with
  a real text label, so meaning does not depend on color or shape alone (contrast +
  colorblind safety).
- **Contrast holds on dark surfaces** — monochrome icon strokes meet legibility against
  the L0–L3 elevation surfaces (see §9).
- **Respect `prefers-reduced-motion`** — any future animated/`glow` treatment must have
  a reduced-motion fallback, consistent with the existing nav scroll behavior.

---

## 9. Theming expectations (dark metallic UI)

Assets are themed by the Phase 25B token system in `apps/frontend/src/styles.css`, not
by hardcoded colors. This keeps assets consistent with the surfaces around them and
re-themeable from one place.

- **Prefer `currentColor`** in icon SVGs so an icon inherits the text/accent color of
  its context and re-themes automatically with the tokens — no per-theme asset copies.
- **Color via tokens, not literals.** When an asset must carry its own color, it maps to
  existing tokens (`--accent` `#8b7cf0`, `--text`, `--text-muted`, `--success`,
  `--warn`, `--error`) rather than new hardcoded hex values. Assets do **not** introduce
  a parallel palette.
- **Read against the elevation scale.** Icons must remain legible on `--bg` (L0),
  `--surface` (L1), `--surface-raised` (L2), and `--surface-overlay` (L3); test the
  same asset across the surfaces it will appear on.
- **Glow is emphasis, not ambiance.** Any glow uses the existing `--glow-accent` /
  focus tokens and is reserved for focus/selection emphasis (per the Phase 25A glow
  rule) — assets do not ship baked-in glow that fakes "liveliness."

### 9.1 Monochrome icons (default)

Single-color, `currentColor`-driven glyphs are the **default** treatment for functional
UI icons. Consistent stroke weight and corner radius across the set; sized from CSS;
no baked color.

### 9.2 Duotone icons (sparingly)

A second tone is allowed **only** when it aids comprehension (e.g. distinguishing a
filled vs. outline state), using a token pair (`--accent` + `--accent-soft`, or
`--text` + `--text-subtle`). Duotone is the exception, not the house style; never
decorative two-tone for its own sake.

### 9.3 Glow treatment

Glow is allowed only as **focus/selection emphasis** via the existing `--glow-accent`
token, never as an always-on aura and never as fake activity/telemetry. Must respect
reduced-motion (§8).

### 9.4 Metallic treatment

The "metallic" feel comes from the **surface/elevation system** (layered slate + the
hairline top-highlight already in `--shadow-panel`), not from chrome-gradient icons.
Icons stay flat/monochrome and sit *on* metallic surfaces; they do not try to *be*
metal. No heavy gradients, bevels, or skeuomorphic chrome on glyphs.

### 9.5 Status icons

Status glyphs reflect a **real, app-computed read-only state** (connected,
disconnected, read-only mode, empty). They use the semantic tokens
(`--success`/`--warn`/`--error`/`--text-muted`), are always paired with a text label
(§8), and never imply uptime, deploy health, background jobs, or live telemetry that
does not exist.

---

## 10. App marks/logos vs. decorative UI icons

A clear line, because the rules differ:

- **App marks / logos (identity)** — the Hive&#124;Mind product mark and the
  devdevbuilds parent mark. These **must** trace to the approved lockup (§2), preserve
  the parent/product relationship (devdevbuilds is the parent label; Hive&#124;Mind is
  the product), keep approved proportions/clear-space, and **must not** be recolored,
  stretched, re-drawn, recombined, or re-generated. There is exactly one canonical
  Hive&#124;Mind mark; variants are explicit, approved files (§6).
- **Functional UI icons (wayfinding)** — small glyphs that label a real surface/action.
  These follow the monochrome/token theming rules (§9) and may be recolored *via tokens*
  because they are functional, not identity. They must still map to a **real** surface
  and never imply a feature the app lacks.
- **Decorative icons** — discouraged. If used at all, they are `aria-hidden` (§8), carry
  no meaning, and never substitute for a brand mark or a functional label.

Marks are governed by the brand authority; functional icons are governed by the token
system. Do not treat a brand mark as a recolorable icon, and do not treat a wayfinding
icon as a brand statement.

---

## 11. Screenshot / demo evidence assets

Reaffirms the rules already practiced across Phases 21F/22C/23B/24A:

- Screenshots are **honestly captured** from the real connected app — never fabricated,
  composited, re-touched to imply different data, or generated.
- They live under `docs/demo/screenshots/` and are named `phase-<id>-<surface>.png`
  (§6).
- History is **preserved** — a new evidence set supersedes but does not delete prior
  captures (per the Phase 24A/25A evidence rules).
- Screenshots are **evidence, not UI assets** — they are never imported into the
  running frontend, nor cropped/traced into icons, marks, or textures (§4).

---

## 12. Asset replacement / removal rules

- **Replace in place under the same name** when refreshing an existing approved asset
  (e.g. a new favicon), so references do not break and the diff is reviewable; bump the
  asset behind the stable name rather than minting `*-v2`/`*-final` files.
- **Removal requires confirming no live reference remains** (search `apps/frontend` and
  `docs` for the path) before deleting, so no broken `<img>`/`href` is left behind.
- **Brand-mark changes go through the devdevbuilds brand authority** (§2), not an ad-hoc
  frontend edit.
- **Screenshot evidence is appended, not rewritten** (§11) — supersede, preserve
  history.
- **Every add/replace/remove states its source and category** in its PR so the
  authority chain (§2) and category (§3) are auditable.

---

## 13. How future phases must reference this contract

Any future Hive&#124;Mind phase that adds, replaces, or removes a frontend visual asset
**must**:

1. **Cite this contract by name** in its planning/PR description and confirm the asset's
   **source authority (§2)** and **category (§3)**.
2. **Follow location (§5), naming (§6), safety (§7), accessibility (§8), and theming
   (§9)** for every asset it touches, and state which apply.
3. **Confirm it adds no forbidden item (§4)** — no icon dependency, no CDN, no
   generated/random asset, no screenshot-derived asset.
4. **Stay inside the Phase 25 honesty boundaries** — assets reflect only real,
   read-only, local-first, single-user, demo-grade behavior; no production/SaaS/uptime
   signaling and no faked liveliness.
5. **Record evidence honestly** if it produces screenshots (§11/§12).

A reviewer (the devdevbuilds merge gate) can reject an asset PR for failing any of the
above. This contract is intent and enforcement criteria; it is not itself an
authorization to add assets — each implementation phase is authorized separately.

---

## Honesty boundaries (unchanged)

- The Knowledge Graph SVG stays **read-only, data-driven rendered output** — it is not
  an "asset" and this contract does not authorize any change to it.
- Assets reflect a **local, single-user, demo-grade** runtime — never production,
  hosted, multi-user, or integrated capability that does not exist.
- devdevbuilds remains the **parent brand system and human merge gate**;
  Hive&#124;Mind remains the **product/app under devdevbuilds**.
- This document is design/governance intent, not a guarantee that any specific asset
  ships; the human merge gate decides what lands.

## Scope confirmation

Phase 25B.5 did **not** change frontend source, CSS, backend, source code, package
files, configs, schema, dependencies, tests, any API contract, or any runtime
behavior; added, moved, or removed **no** image/SVG/icon/favicon asset; added no icon
or font dependency and no CDN reference; created no screenshots; and added no UI
implementation. The change set is **documentation/planning only**: this contract
document plus narrow status/link updates to the roadmap (and README reference if
applied). **No application behavior changed and no asset was added or modified.**
